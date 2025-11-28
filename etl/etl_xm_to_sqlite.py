#!/usr/bin/env python3
"""
ETL: XM API → SQLite
Portal Energético MME
=====================

Script ETL que consulta la API de XM y popula la base de datos SQLite.
Reemplaza: scripts/precalentar_cache_inteligente.py

Ejecución:
    Automático: Cron 3×/día (06:30, 12:30, 20:30)
    Manual: python3 etl/etl_xm_to_sqlite.py
    Manual (sin timeout): python3 etl/etl_xm_to_sqlite.py --sin-timeout
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydataxm.pydataxm import ReadDB
from datetime import datetime, timedelta
import time
import logging
import pandas as pd
import argparse
from utils import db_manager
from etl.config_metricas import METRICAS_CONFIG

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def convertir_unidades(df, metric, conversion_type):
    """
    Convertir unidades de datos crudos de XM a GWh
    
    Conversiones:
    - Wh_a_GWh: Divide por 1e6 (AporEner)
    - kWh_a_GWh: Divide por 1e6 (VoluUtil, CapaUtil)
    - horas_a_diario: Suma Values_Hour01-24 en kWh → GWh
    """
    if df is None or df.empty:
        logging.warning(f"⚠️ {metric}: DataFrame vacío")
        return df
    
    if conversion_type is None:
        return df
    
    df = df.copy()
    
    try:
        if conversion_type == 'Wh_a_GWh':
            if 'Value' in df.columns:
                valor_antes = df['Value'].mean()
                df['Value'] = df['Value'] / 1_000_000  # Wh → GWh
                valor_despues = df['Value'].mean()
                logging.info(f"✅ {metric}: Wh→GWh | Promedio: {valor_antes:,.0f} Wh → {valor_despues:.2f} GWh")
        
        elif conversion_type == 'kWh_a_GWh':
            if 'Value' in df.columns:
                valor_antes = df['Value'].mean()
                df['Value'] = df['Value'] / 1_000_000  # kWh → GWh
                valor_despues = df['Value'].mean()
                logging.info(f"✅ {metric}: kWh→GWh | Promedio: {valor_antes:,.2f} kWh → {valor_despues:.2f} GWh")
        
        elif conversion_type == 'horas_a_diario':
            # Sumar valores horarios (Values_Hour01-24)
            hour_cols = [f'Values_Hour{i:02d}' for i in range(1, 25)]
            existing_cols = [col for col in hour_cols if col in df.columns]
            
            if existing_cols:
                df['Value'] = df[existing_cols].sum(axis=1) / 1_000_000  # kWh → GWh
                valor_despues = df['Value'].mean()
                logging.info(f"✅ {metric}: Agregado {len(existing_cols)} horas → {valor_despues:.2f} GWh promedio")
            elif 'Value' in df.columns:
                valor_antes = df['Value'].mean()
                df['Value'] = df['Value'] / 1_000_000
                valor_despues = df['Value'].mean()
                logging.info(f"✅ {metric}: Value (kWh→GWh) | {valor_antes:,.2f} → {valor_despues:.2f} GWh")
        
        return df
        
    except Exception as e:
        logging.error(f"❌ Error convirtiendo unidades para {metric}: {e}")
        return df


def poblar_catalogo(obj_api, catalogo_name: str) -> int:
    """
    Consulta y guarda un catálogo de XM en SQLite (ListadoRecursos, ListadoEmbalses, etc.)
    Los catálogos son datos estáticos/semi-estáticos que mapean códigos a nombres.
    
    Args:
        obj_api: Objeto ReadDB de pydataxm
        catalogo_name: Nombre del catálogo ('ListadoRecursos', 'ListadoEmbalses', etc.)
    
    Returns:
        Número de registros insertados
    """
    logging.info(f"\n{'='*60}")
    logging.info(f"📚 CATÁLOGO: {catalogo_name}")
    logging.info(f"{'='*60}")
    
    try:
        # Los catálogos no tienen rango de fechas, usar fecha actual
        fecha = datetime.now()
        
        logging.info(f"🔄 Consultando API XM...")
        df = obj_api.request_data(catalogo_name, "Sistema", fecha, fecha)
        
        if df is None or df.empty:
            logging.warning(f"⚠️ {catalogo_name}: Sin datos")
            return 0
        
        logging.info(f"✅ API devolvió {len(df)} registros")
        logging.info(f"📋 Columnas: {df.columns.tolist()}")
        
        # Mapeo de columnas según catálogo
        registros = []
        
        if catalogo_name == 'ListadoRecursos':
            # Columnas esperadas: Values_Code, Values_Name, Values_Type, etc.
            for _, row in df.iterrows():
                codigo = str(row.get('Values_Code', row.get('Values_code', '')))
                if codigo and codigo != 'nan':
                    registros.append({
                        'codigo': codigo.upper(),
                        'nombre': str(row.get('Values_Name', row.get('Values_name', codigo))),
                        'tipo': str(row.get('Values_Type', row.get('Values_Recurso', ''))).upper(),
                        'region': str(row.get('Values_Region', '')),
                        'capacidad': float(row.get('Values_Capacity', 0)) if pd.notna(row.get('Values_Capacity')) else None,
                        'metadata': None
                    })
        
        elif catalogo_name == 'ListadoEmbalses':
            # Columnas esperadas: Values_Code, Values_Name, Values_CentralName, etc.
            for _, row in df.iterrows():
                codigo = str(row.get('Values_Code', row.get('Values_code', '')))
                if codigo and codigo != 'nan':
                    registros.append({
                        'codigo': codigo.upper(),
                        'nombre': str(row.get('Values_Name', row.get('Values_name', codigo))),
                        'tipo': 'EMBALSE',
                        'region': str(row.get('Values_Region', '')),
                        'capacidad': float(row.get('Values_Capacity', 0)) if pd.notna(row.get('Values_Capacity')) else None,
                        'metadata': None
                    })
        
        elif catalogo_name == 'ListadoRios':
            # Similar a embalses
            for _, row in df.iterrows():
                codigo = str(row.get('Values_Code', row.get('Values_code', '')))
                if codigo and codigo != 'nan':
                    registros.append({
                        'codigo': codigo.upper(),
                        'nombre': str(row.get('Values_Name', row.get('Values_name', codigo))),
                        'tipo': 'RIO',
                        'region': str(row.get('Values_Region', '')),
                        'capacidad': None,
                        'metadata': None
                    })
        
        elif catalogo_name == 'ListadoAgentes':
            for _, row in df.iterrows():
                codigo = str(row.get('Values_Code', row.get('Values_code', '')))
                if codigo and codigo != 'nan':
                    registros.append({
                        'codigo': codigo.upper(),
                        'nombre': str(row.get('Values_Name', row.get('Values_name', codigo))),
                        'tipo': 'AGENTE',
                        'region': None,
                        'capacidad': None,
                        'metadata': None
                    })
        
        if not registros:
            logging.warning(f"⚠️ {catalogo_name}: No se pudieron extraer registros válidos")
            return 0
        
        # Guardar en SQLite
        registros_guardados = db_manager.upsert_catalogo_bulk(catalogo_name, registros)
        logging.info(f"✅ {catalogo_name}: {registros_guardados} registros guardados en SQLite")
        
        return registros_guardados
        
    except Exception as e:
        logging.error(f"❌ Error procesando {catalogo_name}: {e}")
        import traceback
        traceback.print_exc()
        return 0


def poblar_metrica(obj_api, config, usar_timeout=True, timeout_seconds=60, fecha_inicio_custom=None, fecha_fin_custom=None):
    """
    Consulta API XM y popula SQLite para una métrica
    
    Args:
        obj_api: Objeto ReadDB de pydataxm
        config: Configuración de la métrica
        usar_timeout: Si False, espera indefinidamente
        fecha_inicio_custom: Fecha inicio personalizada (str YYYY-MM-DD)
        fecha_fin_custom: Fecha fin personalizada (str YYYY-MM-DD)
        timeout_seconds: Timeout en segundos
    
    Returns:
        Número de registros insertados
    """
    metric = config['metric']
    entity = config['entity']
    conversion = config.get('conversion')
    dias_history = config.get('dias_history', 7)
    batch_size = config.get('batch_size', dias_history)
    
    # Usar fechas personalizadas o calcular automáticamente
    if fecha_inicio_custom:
        fecha_inicio = datetime.strptime(fecha_inicio_custom, '%Y-%m-%d').date()
    else:
        fecha_fin_auto = datetime.now().date() - timedelta(days=1)
        fecha_inicio = fecha_fin_auto - timedelta(days=dias_history)
    
    if fecha_fin_custom:
        fecha_fin = datetime.strptime(fecha_fin_custom, '%Y-%m-%d').date()
    else:
        fecha_fin = datetime.now().date() - timedelta(days=1)
    
    dias_totales = (fecha_fin - fecha_inicio).days + 1
    logging.info(f"📡 {metric}/{entity} - Rango: {fecha_inicio} a {fecha_fin} ({dias_totales} días)")
    
    total_insertados = 0
    
    try:
        # Dividir en batches si es necesario
        if batch_size < dias_history:
            current_date = fecha_inicio
            all_data = []
            
            while current_date <= fecha_fin:
                batch_end = min(current_date + timedelta(days=batch_size - 1), fecha_fin)
                
                logging.info(f"  📦 Batch: {current_date} a {batch_end}")
                
                # Consultar API XM
                start_time = time.time()
                df = obj_api.request_data(
                    metric, 
                    entity,
                    start_date=str(current_date),
                    end_date=str(batch_end)
                )
                elapsed = time.time() - start_time
                
                if df is not None and not df.empty:
                    all_data.append(df)
                    logging.info(f"  ✅ Batch OK: {len(df)} filas en {elapsed:.1f}s")
                else:
                    logging.warning(f"  ⚠️ Batch sin datos")
                
                current_date = batch_end + timedelta(days=1)
                time.sleep(0.5)  # Evitar sobrecargar API
            
            # Concatenar todos los batches
            if all_data:
                df = pd.concat(all_data, ignore_index=True)
            else:
                df = pd.DataFrame()
        
        else:
            # Sin batches, query completo
            start_time = time.time()
            df = obj_api.request_data(
                metric,
                entity,
                start_date=str(fecha_inicio),
                end_date=str(fecha_fin)
            )
            elapsed = time.time() - start_time
            logging.info(f"  ⏱️ API respondió en {elapsed:.1f}s")
        
        # Validar datos
        if df is None or df.empty:
            logging.warning(f"❌ {metric}/{entity}: Sin datos de API")
            return 0
        
        logging.info(f"  📊 Datos recibidos: {len(df)} filas")
        
        # Convertir unidades
        if conversion:
            logging.info(f"  🔄 Aplicando conversión: {conversion}")
            df = convertir_unidades(df, metric, conversion)
            if df is None or df.empty:
                logging.error(f"❌ {metric}/{entity}: Conversión falló (DataFrame vacío)")
                return 0
        
        # Preparar datos para inserción
        metrics_to_insert = []
        
        # Detectar columnas necesarias
        if 'Date' not in df.columns:
            logging.error(f"❌ {metric}/{entity}: Falta columna 'Date'")
            logging.error(f"   Columnas disponibles: {list(df.columns)}")
            return 0
        
        if 'Value' not in df.columns:
            logging.error(f"❌ {metric}/{entity}: Falta columna 'Value'")
            logging.error(f"   Columnas disponibles: {list(df.columns)}")
            logging.error(f"   Conversión aplicada: {conversion}")
            return 0
        
        # OPTIMIZACIÓN: Cargar catálogo de Embalses UNA VEZ si es necesario
        nombre_a_codigo_embalses = None
        if entity == 'Embalse':
            catalogos_nombres = db_manager.get_catalogo('ListadoEmbalses')
            if catalogos_nombres is not None and len(catalogos_nombres) > 0:
                # FIX: get_catalogo devuelve DataFrame, convertir a lista de diccionarios
                nombre_a_codigo_embalses = {
                    str(item['nombre']).strip().upper(): str(item['codigo']).strip() 
                    for item in catalogos_nombres.to_dict('records')
                }
                logging.info(f"📖 Catálogo de Embalses cargado: {len(nombre_a_codigo_embalses)} embalses")
        
        # Iterar sobre filas
        for _, row in df.iterrows():
            fecha = str(row['Date'])[:10]  # 'YYYY-MM-DD'
            valor_gwh = float(row['Value'])
            
            # VALIDACIÓN: Rechazar DemaCome con valores anormalmente bajos
            # Threshold reducido de 100 a 10 GWh para permitir datos parciales válidos
            if metric == 'DemaCome' and entity == 'Sistema' and valor_gwh < 10:
                logging.warning(f"⚠️  {metric}/{entity} ({fecha}): Valor {valor_gwh:.2f} GWh muy bajo, RECHAZADO (posible dato incompleto de API XM)")
                continue  # Saltar este registro
            
            # VALIDACIÓN: Para DemaCome/DemaReal por Agente, rechazar valores muy bajos (probablemente errores)
            if metric in ['DemaCome', 'DemaReal'] and entity == 'Agente' and valor_gwh < 0.001:
                continue  # Saltar valores casi cero
            
            # Detectar recurso (columnas según tipo de métrica)
            # Para DemaCome/DemaReal por Agente, el código está en 'Values_code'
            # Name: AporEner/Rio
            # Values_code: Gene/Recurso, DemaCome/Agente, DemaReal/Agente
            # Resources, Embalse, Rio, Agente: otros casos legacy
            # Id: Para algunas métricas como Gene/Sistema, AporEner/Sistema
            recurso = None
            for col_name in ['Values_code', 'Name', 'Id', 'Resources', 'Embalse', 'Rio', 'Agente']:
                if col_name in df.columns:
                    recurso = row.get(col_name)
                    if pd.notna(recurso):
                        recurso = str(recurso)
                        # NORMALIZAR 'Sistema' → '_SISTEMA_' para evitar duplicados
                        if recurso.strip().lower() == 'sistema':
                            recurso = '_SISTEMA_'
                    break
            
            # FIX MAPEO EMBALSES: API devuelve nombres completos, necesitamos códigos
            # Para Embalse, buscar código en catálogo usando mapeo inverso nombre→código
            if entity == 'Embalse' and recurso is not None and nombre_a_codigo_embalses:
                # Buscar código por nombre (case-insensitive, stripped)
                recurso_upper = str(recurso).strip().upper()
                if recurso_upper in nombre_a_codigo_embalses:
                    codigo_embalse = nombre_a_codigo_embalses[recurso_upper]
                    logging.debug(f"🔄 Embalse mapeado: {recurso} → {codigo_embalse}")
                    recurso = codigo_embalse
                else:
                    # Si no se encuentra, intentar match parcial
                    encontrado = False
                    for nombre_cat, codigo_cat in nombre_a_codigo_embalses.items():
                        if recurso_upper in nombre_cat or nombre_cat in recurso_upper:
                            logging.info(f"🔄 Embalse match parcial: {recurso} → {codigo_cat}")
                            recurso = codigo_cat
                            encontrado = True
                            break
                    
                    if not encontrado:
                        logging.warning(f"⚠️  Embalse sin mapeo: '{recurso}' no encontrado en catálogo")
                        # Mantener el nombre original si no se encuentra código
            
            # FIX DUPLICADOS: Para entidad=Sistema, si recurso=None, usar placeholder
            # Esto evita que SQLite inserte múltiples NULL (no los considera iguales en UNIQUE)
            if entity == 'Sistema' and recurso is None:
                recurso = '_SISTEMA_'
            
            metrics_to_insert.append((
                fecha,
                metric,
                entity,
                recurso,
                valor_gwh,
                'GWh'
            ))
        
        # Insertar en SQLite (bulk)
        if metrics_to_insert:
            total_insertados = db_manager.upsert_metrics_bulk(metrics_to_insert)
            logging.info(f"✅ {metric}/{entity}: {total_insertados} registros guardados en SQLite")
        
        # =========================================================================
        # GUARDAR DATOS HORARIOS (si existen columnas Values_Hour01-24)
        # =========================================================================
        hour_cols = [col for col in df.columns if 'Hour' in col and col.startswith('Values_Hour')]
        
        if hour_cols and len(hour_cols) == 24:
            logging.info(f"  💾 Guardando datos horarios para {metric}/{entity}...")
            
            hourly_data = []
            
            for _, row in df.iterrows():
                fecha = str(row['Date'])[:10]
                
                # Obtener código de recurso/agente
                recurso = None
                for col_name in ['Values_code', 'Name', 'Id', 'Resources', 'Embalse', 'Rio', 'Agente']:
                    if col_name in df.columns:
                        recurso = row.get(col_name)
                        if pd.notna(recurso):
                            recurso = str(recurso)
                            if recurso.strip().lower() == 'sistema':
                                recurso = '_SISTEMA_'
                        break
                
                # FIX: Para Sistema, usar placeholder
                if entity == 'Sistema' and recurso is None:
                    recurso = '_SISTEMA_'
                
                # Extraer valores horarios
                for h in range(1, 25):
                    col_name = f'Values_Hour{h:02d}'
                    if col_name in df.columns:
                        valor_kwh = row.get(col_name)
                        if pd.notna(valor_kwh) and valor_kwh > 0:
                            valor_mwh = float(valor_kwh) / 1000  # kWh → MWh
                            
                            # Validación: rechazar valores muy bajos en métricas de demanda por agente
                            if metric in ['DemaCome', 'DemaReal'] and entity == 'Agente' and valor_mwh < 0.001:
                                continue
                            
                            hourly_data.append((
                                fecha,
                                metric,
                                entity,
                                recurso,
                                h,
                                valor_mwh
                            ))
            
            # Insertar datos horarios en bulk
            if hourly_data:
                registros_horarios = db_manager.upsert_hourly_metrics_bulk(hourly_data)
                logging.info(f"  ✅ Datos horarios: {registros_horarios} registros guardados ({len(hourly_data)//24} días × 24 horas)")
        
        return total_insertados
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logging.error(f"❌ Error poblando {metric}/{entity}: {e}")
        logging.error(f"Detalles del error:\n{error_details}")
        return 0


def ejecutar_etl(usar_timeout=True, fecha_inicio_custom=None, fecha_fin_custom=None):
    """
    Ejecuta ETL completo: consulta API XM y popula SQLite
    
    Args:
        usar_timeout: Si False, espera indefinidamente en API lenta
        fecha_inicio_custom: Fecha inicio personalizada (YYYY-MM-DD)
        fecha_fin_custom: Fecha fin personalizada (YYYY-MM-DD)
    
    Returns:
        Diccionario con estadísticas de ejecución
    """
    inicio_global = time.time()
    
    logging.info("╔══════════════════════════════════════════════════════════════╗")
    logging.info("║       ETL: Portal Energético MME (XM API → SQLite)          ║")
    logging.info("╚══════════════════════════════════════════════════════════════╝")
    logging.info(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if fecha_inicio_custom or fecha_fin_custom:
        logging.info(f"🎯 Modo personalizado: {fecha_inicio_custom or 'auto'} → {fecha_fin_custom or 'auto'}")
    
    # Inicializar API XM
    try:
        obj_api = ReadDB()
        logging.info("✅ Conexión a API XM inicializada")
    except Exception as e:
        logging.error(f"❌ Error conectando a API XM: {e}")
        return {'exito': False, 'error': str(e)}
    
    # Verificar base de datos
    if not db_manager.test_connection():
        logging.error("❌ Error de conexión a SQLite")
        return {'exito': False, 'error': 'Conexión SQLite fallida'}
    
    # Estadísticas
    stats = {
        'total_metricas': 0,
        'metricas_exitosas': 0,
        'metricas_fallidas': 0,
        'total_registros': 0,
        'tiempo_total': 0,
        'exito': True
    }
    
    # =========================================================================
    # FASE 1: POBLAR CATÁLOGOS (ListadoRecursos, ListadoEmbalses, etc.)
    # =========================================================================
    logging.info("\n" + "="*60)
    logging.info("FASE 1: CATÁLOGOS DE MAPEO (códigos → nombres)")
    logging.info("="*60)
    
    catalogos = ['ListadoRecursos', 'ListadoEmbalses', 'ListadoRios', 'ListadoAgentes']
    
    for catalogo in catalogos:
        try:
            logging.info(f"\n🔄 Procesando {catalogo}...")
            registros = poblar_catalogo(obj_api, catalogo)
            if registros > 0:
                stats['total_registros'] += registros
                logging.info(f"✅ {catalogo}: {registros} códigos guardados")
            else:
                logging.warning(f"⚠️ {catalogo}: Sin registros")
        except Exception as e:
            logging.error(f"❌ Error en catálogo {catalogo}: {e}")
        
        time.sleep(0.5)  # Pausa entre catálogos
    
    # =========================================================================
    # FASE 2: POBLAR MÉTRICAS TEMPORALES (Gene, AporEner, etc.)
    # =========================================================================
    logging.info("\n" + "="*60)
    logging.info("FASE 2: MÉTRICAS TEMPORALES (datos históricos)")
    logging.info("="*60)
    
    # Procesar cada categoría de métricas
    for categoria, metricas in METRICAS_CONFIG.items():
        logging.info(f"\n{'='*60}")
        logging.info(f"📂 Categoría: {categoria}")
        logging.info(f"{'='*60}")
        
        for config in metricas:
            stats['total_metricas'] += 1
            metric = config['metric']
            entity = config['entity']
            
            try:
                registros = poblar_metrica(
                    obj_api, 
                    config, 
                    usar_timeout,
                    fecha_inicio_custom=fecha_inicio_custom,
                    fecha_fin_custom=fecha_fin_custom
                )
                
                if registros > 0:
                    stats['metricas_exitosas'] += 1
                    stats['total_registros'] += registros
                else:
                    stats['metricas_fallidas'] += 1
                
            except Exception as e:
                logging.error(f"❌ Excepción en {metric}/{entity}: {e}")
                stats['metricas_fallidas'] += 1
            
            time.sleep(0.3)  # Pausa entre métricas
    
    # Fin de ETL
    stats['tiempo_total'] = time.time() - inicio_global
    
    logging.info("\n╔══════════════════════════════════════════════════════════════╗")
    logging.info("║                   RESUMEN DE ETL                             ║")
    logging.info("╚══════════════════════════════════════════════════════════════╝")
    logging.info(f"Total métricas procesadas: {stats['total_metricas']}")
    logging.info(f"  ✅ Exitosas: {stats['metricas_exitosas']}")
    logging.info(f"  ❌ Fallidas: {stats['metricas_fallidas']}")
    logging.info(f"Total registros insertados: {stats['total_registros']}")
    logging.info(f"Tiempo total: {stats['tiempo_total']:.1f} segundos ({stats['tiempo_total']/60:.1f} min)")
    
    # Mostrar estadísticas de BD
    db_stats = db_manager.get_database_stats()
    logging.info(f"\n📊 Estadísticas de base de datos:")
    logging.info(f"  Total registros: {db_stats.get('total_registros', 0):,}")
    logging.info(f"  Métricas únicas: {db_stats.get('metricas_unicas', 0)}")
    logging.info(f"  Rango fechas: {db_stats.get('fecha_minima')} a {db_stats.get('fecha_maxima')}")
    logging.info(f"  Tamaño BD: {db_stats.get('tamano_db_mb', 0):.2f} MB")
    
    logging.info(f"\nFin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return stats


if __name__ == "__main__":
    # Parse argumentos
    parser = argparse.ArgumentParser(description='ETL: XM API → SQLite')
    parser.add_argument(
        '--sin-timeout',
        action='store_true',
        help='Desactiva timeout (espera indefinida en API lenta)'
    )
    parser.add_argument(
        '--fecha-inicio',
        type=str,
        help='Fecha inicio (YYYY-MM-DD). Por defecto: según dias_history'
    )
    parser.add_argument(
        '--fecha-fin',
        type=str,
        help='Fecha fin (YYYY-MM-DD). Por defecto: ayer'
    )
    args = parser.parse_args()
    
    # Ejecutar ETL
    resultado = ejecutar_etl(
        usar_timeout=not args.sin_timeout,
        fecha_inicio_custom=args.fecha_inicio,
        fecha_fin_custom=args.fecha_fin
    )
    
    # Exit code
    sys.exit(0 if resultado.get('exito', False) else 1)
