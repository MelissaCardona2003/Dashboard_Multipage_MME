#!/usr/bin/env python3
"""
ETL Dedicado para Métricas de Embalse
Portal Energético MME

Carga histórica de VoluUtilDiarEner/Embalse y CapaUtilDiarEner/Embalse
con manejo robusto de errores y reintentos.

Autor: Sistema ETL MME
Fecha: 2025-11-25
"""

import sys
import logging
from datetime import datetime, timedelta
import time

sys.path.insert(0, '/home/admonctrlxm/server')

from pydataxm import pydataxm
from etl import etl_xm_to_sqlite
from utils import db_manager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s',
    handlers=[
        logging.FileHandler('/home/admonctrlxm/server/logs/etl_embalse_dedicated_output.log'),
        logging.StreamHandler()
    ]
)

# Configuración de métricas a cargar
METRICAS_EMBALSE = [
    {
        'metric': 'VoluUtilDiarEner',
        'entity': 'Embalse',
        'conversion': 'kWh_a_GWh',
        'batch_size': 30  # 30 días por batch
    },
    {
        'metric': 'CapaUtilDiarEner',
        'entity': 'Embalse',
        'conversion': 'kWh_a_GWh',
        'batch_size': 30
    }
]

# Rango de fechas objetivo: 5 años (2020-01-01 a 2025-11-24)
FECHA_INICIO_TARGET = datetime(2020, 1, 1).date()
FECHA_FIN_TARGET = datetime(2025, 11, 24).date()

# Configuración de reintentos
MAX_REINTENTOS = 3
DELAY_ENTRE_REINTENTOS = 10  # segundos


def obtener_fechas_faltantes(metric_name, entity_name, fecha_inicio, fecha_fin):
    """
    Detecta qué fechas faltan en SQLite para una métrica
    
    Returns:
        list of (fecha_inicio, fecha_fin) tuples con rangos faltantes
    """
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        
        # Obtener todas las fechas presentes
        cursor.execute("""
            SELECT DISTINCT fecha
            FROM metrics
            WHERE metrica = ? AND entidad = ?
            AND fecha BETWEEN ? AND ?
            ORDER BY fecha
        """, (metric_name, entity_name, str(fecha_inicio), str(fecha_fin)))
        
        fechas_presentes = set(row[0] for row in cursor.fetchall())
    
    # Generar todas las fechas esperadas
    fechas_esperadas = []
    fecha_actual = fecha_inicio
    while fecha_actual <= fecha_fin:
        fechas_esperadas.append(str(fecha_actual))
        fecha_actual += timedelta(days=1)
    
    # Identificar fechas faltantes
    fechas_faltantes = [f for f in fechas_esperadas if f not in fechas_presentes]
    
    if not fechas_faltantes:
        return []
    
    # Agrupar fechas consecutivas en rangos
    rangos = []
    rango_inicio = datetime.strptime(fechas_faltantes[0], '%Y-%m-%d').date()
    rango_fin = rango_inicio
    
    for fecha_str in fechas_faltantes[1:]:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        if fecha == rango_fin + timedelta(days=1):
            # Fecha consecutiva, extender rango
            rango_fin = fecha
        else:
            # Nueva brecha, guardar rango anterior y empezar uno nuevo
            rangos.append((rango_inicio, rango_fin))
            rango_inicio = fecha
            rango_fin = fecha
    
    # Agregar el último rango
    rangos.append((rango_inicio, rango_fin))
    
    return rangos


def dividir_rango_en_chunks(fecha_inicio, fecha_fin, batch_size):
    """
    Divide un rango de fechas en chunks más pequeños
    
    Returns:
        list of (fecha_inicio, fecha_fin) tuples
    """
    chunks = []
    current = fecha_inicio
    
    while current <= fecha_fin:
        chunk_end = min(current + timedelta(days=batch_size - 1), fecha_fin)
        chunks.append((current, chunk_end))
        current = chunk_end + timedelta(days=1)
    
    return chunks


def procesar_chunk_con_reintentos(obj_api, config, fecha_inicio, fecha_fin, intento=1):
    """
    Procesa un chunk de datos con reintentos automáticos
    
    Returns:
        int: Número de registros insertados (0 si falla después de todos los intentos)
    """
    metric = config['metric']
    entity = config['entity']
    
    try:
        logging.info(f"📅 Procesando: {fecha_inicio} → {fecha_fin} (Intento {intento}/{MAX_REINTENTOS})")
        
        registros = etl_xm_to_sqlite.poblar_metrica(
            obj_api,
            config,
            usar_timeout=False,
            fecha_inicio_custom=str(fecha_inicio),
            fecha_fin_custom=str(fecha_fin)
        )
        
        if registros > 0:
            logging.info(f"✅ Rango completado: {registros} registros")
            return registros
        else:
            logging.warning(f"⚠️  Rango sin datos")
            if intento < MAX_REINTENTOS:
                logging.info(f"🔄 Reintentando en {DELAY_ENTRE_REINTENTOS}s...")
                time.sleep(DELAY_ENTRE_REINTENTOS)
                return procesar_chunk_con_reintentos(obj_api, config, fecha_inicio, fecha_fin, intento + 1)
            else:
                logging.error(f"❌ Máximo de reintentos alcanzado para {fecha_inicio} → {fecha_fin}")
                return 0
    
    except Exception as e:
        logging.error(f"❌ Error procesando {fecha_inicio} → {fecha_fin}: {e}")
        
        if intento < MAX_REINTENTOS:
            logging.info(f"🔄 Reintentando en {DELAY_ENTRE_REINTENTOS}s...")
            time.sleep(DELAY_ENTRE_REINTENTOS)
            return procesar_chunk_con_reintentos(obj_api, config, fecha_inicio, fecha_fin, intento + 1)
        else:
            logging.error(f"❌ Máximo de reintentos alcanzado para {fecha_inicio} → {fecha_fin}")
            import traceback
            traceback.print_exc()
            return 0


def main():
    logging.info("="*80)
    logging.info("🚀 INICIANDO ETL DEDICADO PARA MÉTRICAS DE EMBALSE")
    logging.info("="*80)
    logging.info(f"📅 Rango objetivo: {FECHA_INICIO_TARGET} a {FECHA_FIN_TARGET}")
    logging.info(f"📊 Métricas: VoluUtilDiarEner/Embalse, CapaUtilDiarEner/Embalse")
    logging.info(f"🔄 Reintentos por chunk: {MAX_REINTENTOS}")
    logging.info("="*80)
    
    # Inicializar API XM
    obj_api = pydataxm.ReadDB()
    
    # Procesar cada métrica
    for config in METRICAS_EMBALSE:
        metric = config['metric']
        entity = config['entity']
        batch_size = config['batch_size']
        
        logging.info(f"\n{'='*80}")
        logging.info(f"📊 MÉTRICA: {metric}/{entity}")
        logging.info(f"{'='*80}")
        
        # Detectar fechas faltantes
        logging.info("🔍 Analizando fechas faltantes...")
        rangos_faltantes = obtener_fechas_faltantes(
            metric, entity, 
            FECHA_INICIO_TARGET, FECHA_FIN_TARGET
        )
        
        if not rangos_faltantes:
            logging.info(f"✅ {metric}/{entity} ya está completo!")
            continue
        
        # Mostrar rangos faltantes
        total_dias_faltantes = sum((r[1] - r[0]).days + 1 for r in rangos_faltantes)
        logging.info(f"📋 Rangos faltantes: {len(rangos_faltantes)}")
        logging.info(f"📅 Días totales faltantes: {total_dias_faltantes}")
        
        for i, (inicio, fin) in enumerate(rangos_faltantes, 1):
            dias = (fin - inicio).days + 1
            logging.info(f"   {i}. {inicio} → {fin} ({dias} días)")
        
        # Procesar cada rango en chunks
        registros_totales = 0
        chunks_procesados = 0
        chunks_fallidos = 0
        
        for inicio_rango, fin_rango in rangos_faltantes:
            logging.info(f"\n🎯 Procesando rango: {inicio_rango} → {fin_rango}")
            
            # Dividir en chunks
            chunks = dividir_rango_en_chunks(inicio_rango, fin_rango, batch_size)
            logging.info(f"   📦 Chunks a procesar: {len(chunks)}")
            
            for chunk_inicio, chunk_fin in chunks:
                registros = procesar_chunk_con_reintentos(
                    obj_api, config, 
                    chunk_inicio, chunk_fin
                )
                
                if registros > 0:
                    registros_totales += registros
                    chunks_procesados += 1
                else:
                    chunks_fallidos += 1
                
                # Pequeña pausa entre chunks
                time.sleep(1)
        
        # Resumen de la métrica
        logging.info(f"\n{'='*80}")
        logging.info(f"📊 RESUMEN: {metric}/{entity}")
        logging.info(f"   ✅ Chunks exitosos: {chunks_procesados}")
        logging.info(f"   ❌ Chunks fallidos: {chunks_fallidos}")
        logging.info(f"   📝 Registros totales insertados: {registros_totales}")
        logging.info(f"{'='*80}")
    
    # Resumen final
    logging.info(f"\n{'='*80}")
    logging.info("✅ ETL DE MÉTRICAS DE EMBALSE COMPLETADO")
    logging.info("="*80)
    
    # Verificación final
    logging.info("\n🔍 VERIFICACIÓN FINAL:")
    for config in METRICAS_EMBALSE:
        metric = config['metric']
        entity = config['entity']
        
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_registros,
                    COUNT(DISTINCT fecha) as dias_distintos,
                    COUNT(DISTINCT recurso) as embalses_distintos,
                    MIN(fecha) as primera_fecha,
                    MAX(fecha) as ultima_fecha
                FROM metrics
                WHERE metrica = ? AND entidad = ?
            """, (metric, entity))
            
            result = cursor.fetchone()
            dias_esperados = (FECHA_FIN_TARGET - FECHA_INICIO_TARGET).days + 1
            completitud = (result[1] / dias_esperados * 100) if dias_esperados > 0 else 0
            
            logging.info(f"\n📊 {metric}/{entity}:")
            logging.info(f"   Total registros: {result[0]:,}")
            logging.info(f"   Días con datos: {result[1]}/{dias_esperados} ({completitud:.1f}%)")
            logging.info(f"   Embalses: {result[2]}")
            logging.info(f"   Rango: {result[3]} → {result[4]}")
    
    logging.info("\n✨ Proceso completado exitosamente\n")


if __name__ == "__main__":
    main()
