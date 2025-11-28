#!/usr/bin/env python3
"""
ETL especializado SOLO para DemaCome/Agente
Con reintentos y manejo robusto de errores
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pydataxm.pydataxm import ReadDB
from datetime import datetime, timedelta, date
import time
import logging
import sqlite3

# Importar funciones del ETL principal
from etl.etl_xm_to_sqlite import poblar_metrica

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/etl_demacome_agente_dedicated.log'),
        logging.StreamHandler()
    ]
)

def obtener_fechas_faltantes():
    """Detectar qué fechas faltan en SQLite"""
    conn = sqlite3.connect("portal_energetico.db")
    cursor = conn.cursor()
    
    # Obtener fechas existentes
    cursor.execute("""
        SELECT DISTINCT fecha 
        FROM metrics
        WHERE metrica = 'DemaCome' AND entidad = 'Agente'
        ORDER BY fecha
    """)
    
    fechas_existentes = {row[0] for row in cursor.fetchall()}
    conn.close()
    
    # Generar rango completo esperado
    inicio = date(2020, 1, 1)
    fin = date.today() - timedelta(days=1)
    delta = fin - inicio
    
    fechas_esperadas = {(inicio + timedelta(days=i)).strftime('%Y-%m-%d') 
                        for i in range(delta.days + 1)}
    
    fechas_faltantes = sorted(fechas_esperadas - fechas_existentes)
    
    return fechas_faltantes

def procesar_rango_con_reintentos(obj_api, config, fecha_inicio, fecha_fin, max_reintentos=3):
    """Procesar un rango con reintentos en caso de error"""
    
    for intento in range(1, max_reintentos + 1):
        try:
            logging.info(f"{'='*70}")
            logging.info(f"📅 Procesando: {fecha_inicio} → {fecha_fin} (Intento {intento}/{max_reintentos})")
            logging.info(f"{'='*70}")
            
            registros = poblar_metrica(
                obj_api,
                config,
                usar_timeout=False,
                fecha_inicio_custom=fecha_inicio,
                fecha_fin_custom=fecha_fin
            )
            
            if registros > 0:
                logging.info(f"✅ Rango completado: {registros} registros")
                return True
            else:
                logging.warning(f"⚠️  Rango sin registros insertados")
                if intento < max_reintentos:
                    time.sleep(5)
                    continue
                return False
                
        except Exception as e:
            logging.error(f"❌ Error en intento {intento}: {type(e).__name__}: {e}")
            if intento < max_reintentos:
                logging.info(f"⏳ Esperando 10s antes de reintentar...")
                time.sleep(10)
            else:
                logging.error(f"❌ Rango falló después de {max_reintentos} intentos")
                return False
    
    return False

def main():
    logging.info("="*70)
    logging.info("🚀 ETL DEDICADO: DemaCome/Agente")
    logging.info("="*70)
    logging.info(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Detectar fechas faltantes
    logging.info("\n🔍 Analizando fechas faltantes...")
    fechas_faltantes = obtener_fechas_faltantes()
    
    logging.info(f"📊 Análisis:")
    logging.info(f"   - Total fechas faltantes: {len(fechas_faltantes)}")
    
    if len(fechas_faltantes) == 0:
        logging.info("✅ No hay fechas faltantes. Base de datos completa.")
        return
    
    # Agrupar fechas en rangos contiguos
    rangos = []
    if fechas_faltantes:
        fecha_inicio = datetime.strptime(fechas_faltantes[0], '%Y-%m-%d').date()
        fecha_fin = fecha_inicio
        
        for i in range(1, len(fechas_faltantes)):
            fecha_actual = datetime.strptime(fechas_faltantes[i], '%Y-%m-%d').date()
            if (fecha_actual - fecha_fin).days == 1:
                fecha_fin = fecha_actual
            else:
                rangos.append((str(fecha_inicio), str(fecha_fin)))
                fecha_inicio = fecha_actual
                fecha_fin = fecha_actual
        
        rangos.append((str(fecha_inicio), str(fecha_fin)))
    
    logging.info(f"   - Rangos a procesar: {len(rangos)}")
    for inicio, fin in rangos:
        dias = (datetime.strptime(fin, '%Y-%m-%d').date() - 
                datetime.strptime(inicio, '%Y-%m-%d').date()).days + 1
        logging.info(f"     • {inicio} → {fin} ({dias} días)")
    
    # Conectar a API
    logging.info("\n🔌 Conectando a API XM...")
    obj_api = ReadDB()
    logging.info("✅ Conexión establecida")
    
    # Configuración
    config = {
        'metric': 'DemaCome',
        'entity': 'Agente',
        'conversion': 'horas_a_diario',
        'dias_history': 1826,
        'batch_size': 7
    }
    
    # Procesar cada rango
    rangos_exitosos = 0
    rangos_fallidos = 0
    
    inicio_global = time.time()
    
    for i, (fecha_inicio, fecha_fin) in enumerate(rangos, 1):
        dias = (datetime.strptime(fecha_fin, '%Y-%m-%d').date() - 
                datetime.strptime(fecha_inicio, '%Y-%m-%d').date()).days + 1
        
        logging.info(f"\n{'='*70}")
        logging.info(f"📦 Rango {i}/{len(rangos)}")
        logging.info(f"{'='*70}")
        
        # Si el rango es muy grande (>30 días), dividir en chunks de 7 días
        if dias > 30:
            logging.info(f"⚠️  Rango grande ({dias} días), dividiendo en chunks de 7 días")
            
            fecha_actual = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_final = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            
            chunk_num = 0
            while fecha_actual <= fecha_final:
                chunk_num += 1
                chunk_fin = min(fecha_actual + timedelta(days=6), fecha_final)
                
                exito = procesar_rango_con_reintentos(
                    obj_api, config, 
                    str(fecha_actual), str(chunk_fin), 
                    max_reintentos=3
                )
                
                if exito:
                    rangos_exitosos += 1
                else:
                    rangos_fallidos += 1
                    logging.error(f"❌ Chunk {chunk_num} falló: {fecha_actual} → {chunk_fin}")
                
                fecha_actual = chunk_fin + timedelta(days=1)
                time.sleep(2)  # Pausa entre chunks
        else:
            exito = procesar_rango_con_reintentos(
                obj_api, config, 
                fecha_inicio, fecha_fin, 
                max_reintentos=3
            )
            
            if exito:
                rangos_exitosos += 1
            else:
                rangos_fallidos += 1
    
    # Resumen final
    tiempo_total = time.time() - inicio_global
    
    logging.info("\n" + "="*70)
    logging.info("📊 RESUMEN FINAL")
    logging.info("="*70)
    logging.info(f"✅ Rangos exitosos: {rangos_exitosos}")
    logging.info(f"❌ Rangos fallidos: {rangos_fallidos}")
    logging.info(f"⏱️  Tiempo total: {tiempo_total/60:.1f} minutos")
    
    # Verificación final
    logging.info("\n🔍 Verificación final...")
    fechas_faltantes_final = obtener_fechas_faltantes()
    logging.info(f"📊 Fechas faltantes restantes: {len(fechas_faltantes_final)}")
    
    if len(fechas_faltantes_final) == 0:
        logging.info("\n🎉 ¡ETL COMPLETADO! Base de datos completa.")
    else:
        logging.warning(f"\n⚠️  Quedan {len(fechas_faltantes_final)} fechas faltantes")
        if len(fechas_faltantes_final) <= 20:
            for fecha in fechas_faltantes_final:
                logging.warning(f"   - {fecha}")
    
    logging.info(f"\nFin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
