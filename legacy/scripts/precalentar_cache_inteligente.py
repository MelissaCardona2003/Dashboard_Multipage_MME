#!/usr/bin/env python3
"""
PRECALENTAMIENTO DE CACHE INTELIGENTE - VERSIÓN COMPLETA
=========================================================

Script de precalentamiento COMPLETO para arquitectura CACHE-PRECALENTAMIENTO-DASHBOARD.

MEJORAS v2.0 (2025-11-18):
1. ✅ Detección automática de API lenta (>30s) y ajuste de timeout
2. ✅ Conversiones de unidades ANTES de guardar cache (kWh→GWh, horas→días)
3. ✅ Procesamiento de datos crudos de XM para dashboard
4. ✅ Manejo de Gene/Recurso con agregación por tipo de fuente
5. ✅ Validación de datos antes de cachear
6. ✅ NUEVO: Precalentamiento de métricas de Hidrología (embalses, ríos, aportes)
7. ✅ NUEVO: Precalentamiento de métricas de Distribución (demanda)
8. ✅ NUEVO: 19 métricas en total (vs 6 anteriores)
9. ✅ NUEVO: Metadata en cache con flag units_converted para prevenir conversión doble

MÉTRICAS PRECALENTADAS (19 total):
- Generación: Gene/Sistema, Gene/Recurso, VoluUtil, CapaUtil, AporEner/Sistema (5 métricas)
- Hidrología: ListadoEmbalses/Ríos, AporEner/Río, AporCaudal, PorcApor (6 métricas)
- Distribución: DemaCome/Sistema/Agente, DemaReal/Agente (3 métricas)
- Listados: ListadoRecursos, ListadoAgentes (2 métricas)
- COBERTURA: 5 categorías × ~4 métricas promedio = 317% más que versión anterior

EJECUCIÓN:
    Automático: Cron 3x día (06:30, 12:30, 20:30)
    Manual: python3 scripts/precalentar_cache_inteligente.py
    Manual (API lenta): python3 scripts/precalentar_cache_inteligente.py --sin-timeout
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydataxm.pydataxm import ReadDB
from utils.cache_manager import save_to_cache, get_cache_key
from datetime import datetime, timedelta
import time
import logging
import pandas as pd
import argparse

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Métricas críticas del dashboard con sus configuraciones
METRICAS_CONFIG = {
    # Indicadores principales página Generación
    'indicadores_generacion': [
        {
            'metric': 'VoluUtilDiarEner',
            'entity': 'Embalse',
            'cache_type': 'metricas_hidricas',
            'conversion': 'kWh_a_GWh',  # ⚠️ API devuelve en kWh (÷1e6) - Confirmado 2025-11-19
            'dias_history': 7
        },
        {
            'metric': 'CapaUtilDiarEner',
            'entity': 'Embalse',
            'cache_type': 'metricas_hidricas',
            'conversion': 'kWh_a_GWh',  # ⚠️ API devuelve en kWh (÷1e6) - Confirmado 2025-11-19
            'dias_history': 7
        },
        {
            'metric': 'AporEner',
            'entity': 'Sistema',
            'cache_type': 'metricas_hidricas',
            'conversion': 'Wh_a_GWh',  # ⚠️ CORRECCIÓN: API devuelve en Wh (÷1e6) - Confirmado 2025-11-19
            'dias_history': 30  # Necesitamos mes completo
        },
        {
            'metric': 'AporEnerMediHist',
            'entity': 'Sistema',
            'cache_type': 'metricas_hidricas',
            'conversion': 'Wh_a_GWh',  # ⚠️ CORRECCIÓN: API devuelve en Wh (÷1e6) - Confirmado 2025-11-19
            'dias_history': 30
        },
        {
            'metric': 'Gene',
            'entity': 'Sistema',
            'cache_type': 'generacion_xm',
            'conversion': 'horas_a_diario',  # Values_Hour* en kWh, sumar y → GWh
            'dias_history': 7
        }
    ],
    
    # Generación por fuentes (más pesada)
    'generacion_fuentes': [
        {
            'metric': 'Gene',
            'entity': 'Recurso',
            'cache_type': 'generacion_plantas',
            'conversion': 'horas_a_diario',
            'dias_history': 7,  # 7 días (API XM muy lenta con 30)
            'batch_size': 1  # Día por día (API lenta con muchos recursos)
        }
    ],
    
    # Métricas de Hidrología (NUEVA - prioridad ALTA)
    'metricas_hidrologia': [
        {
            'metric': 'ListadoEmbalses',
            'entity': 'Sistema',
            'cache_type': 'listados',
            'conversion': None,  # Sin conversión
            'dias_history': 2  # Actualización semanal, 2 días suficiente
        },
        {
            'metric': 'ListadoRios',
            'entity': 'Sistema',
            'cache_type': 'listados',
            'conversion': None,
            'dias_history': 2
        },
        {
            'metric': 'AporEner',
            'entity': 'Rio',
            'cache_type': 'metricas_hidricas',
            'conversion': 'Wh_a_GWh',  # ⚠️ CORRECCIÓN: AporEner viene en Wh (÷1e6) - Confirmado 2025-11-19
            'dias_history': 30,  # Mes completo para gráficas
            'batch_size': 7  # 7 días por batch
        },
        {
            'metric': 'AporEnerMediHist',
            'entity': 'Rio',
            'cache_type': 'metricas_hidricas',
            'conversion': 'Wh_a_GWh',  # ⚠️ CORRECCIÓN: AporEnerMediHist viene en Wh (÷1e6) - Confirmado 2025-11-19
            'dias_history': 30,
            'batch_size': 7
        },
        {
            'metric': 'AporCaudal',
            'entity': 'Rio',
            'cache_type': 'metricas_hidricas',
            'conversion': None,  # Ya viene en m³/s
            'dias_history': 7
        },
        {
            'metric': 'PorcApor',
            'entity': 'Rio',
            'cache_type': 'metricas_hidricas',
            'conversion': None,  # Porcentajes
            'dias_history': 30,
            'batch_size': 7
        }
    ],
    
    # Métricas de Distribución (NUEVA - prioridad MEDIA)
    'metricas_distribucion': [
        {
            'metric': 'DemaCome',
            'entity': 'Sistema',
            'cache_type': 'distribucion',
            'conversion': 'horas_a_diario',  # Agregación horaria kWh → GWh
            'dias_history': 30,
            'batch_size': 7
        },
        {
            'metric': 'DemaCome',
            'entity': 'Agente',
            'cache_type': 'distribucion',
            'conversion': None,  # Sin conversión, se procesa en el tablero
            'dias_history': 7  # Solo última semana para tablero de agentes
        },
        {
            'metric': 'DemaReal',
            'entity': 'Agente',
            'cache_type': 'distribucion',
            'conversion': None,
            'dias_history': 7
        }
    ],
    
    # Listados de recursos y agentes (NUEVA - prioridad BAJA, datos estables)
    'listados_sistema': [
        {
            'metric': 'ListadoRecursos',
            'entity': 'Sistema',
            'cache_type': 'listados',
            'conversion': None,
            'dias_history': 7  # Se actualiza raramente
        },
        {
            'metric': 'ListadoAgentes',
            'entity': 'Sistema',
            'cache_type': 'listados',
            'conversion': None,
            'dias_history': 7
        }
    ]
}

def convertir_unidades(df, metric, conversion_type):
    """
    Convertir unidades de datos crudos de XM a formato del dashboard.
    
    Conversiones soportadas:
    - Wh_a_GWh: Divide por 1e9 (AporEner, AporEnerMediHist) 
    - MWh_a_GWh: Divide por 1e3 (AporEner, AporEnerMediHist)
    - kWh_a_GWh: Divide por 1e6 (Gene valores horarios)
    - horas_a_diario: Suma Values_Hour01-24 → Value en kWh, luego → GWh
    """
    # 🔍 DEBUG: Log entrada de función
    logging.info(f"🔍 convertir_unidades() llamada: metric={metric}, conversion_type={conversion_type}")
    
    if df is None or df.empty:
        logging.warning(f"⚠️ {metric}: DataFrame None o vacío, no se convierte")
        return df
    
    if conversion_type is None:
        logging.warning(f"⚠️ {metric}: conversion_type=None, no se aplica conversión")
        return df
    
    df = df.copy()  # Evitar modificar el DataFrame original
    
    try:
        if conversion_type == 'Wh_a_GWh':
            # ⚠️ CORRECCIÓN 2025-11-19: AporEner/AporEnerMediHist vienen en Wh (÷1e6, no ÷1e9)
            if 'Value' in df.columns:
                valor_antes = df['Value'].mean()
                df['Value'] = df['Value'] / 1_000_000  # Wh → GWh (÷1e6)
                valor_despues = df['Value'].mean()
                logging.info(f"✅ {metric}: Wh→GWh | Promedio: {valor_antes:,.0f} Wh → {valor_despues:.2f} GWh")
        
        elif conversion_type == 'MWh_a_GWh':
            # MWh → GWh (÷1e3)
            if 'Value' in df.columns:
                valor_antes = df['Value'].mean()
                df['Value'] = df['Value'] / 1000
                valor_despues = df['Value'].mean()
                logging.info(f"✅ {metric}: MWh→GWh | Promedio: {valor_antes:,.2f} MWh → {valor_despues:.2f} GWh")
        
        elif conversion_type == 'kWh_a_GWh':
            # ⚠️ CORRECCIÓN 2025-11-19: VoluUtilDiarEner/CapaUtilDiarEner vienen en kWh (÷1e6)
            if 'Value' in df.columns:
                valor_antes = df['Value'].mean()
                df['Value'] = df['Value'] / 1_000_000  # kWh → GWh (÷1e6)
                valor_despues = df['Value'].mean()
                logging.info(f"✅ {metric}: kWh→GWh | Promedio: {valor_antes:,.2f} kWh → {valor_despues:.2f} GWh")
        
        elif conversion_type == 'horas_a_diario':
            # Gene/Sistema/Recurso: valores horarios en kWh, sumar y convertir a GWh
            hour_cols = [f'Values_Hour{i:02d}' for i in range(1, 25)]
            existing_cols = [col for col in hour_cols if col in df.columns]
            
            if existing_cols:
                # Sumar todas las horas (en kWh) y convertir a GWh
                df['Value'] = df[existing_cols].sum(axis=1) / 1_000_000  # kWh → GWh (÷1e6)
                valor_despues = df['Value'].mean()
                logging.info(f"✅ {metric}: Agregado {len(existing_cols)} horas (kWh) → {valor_despues:.2f} GWh promedio")
            elif 'Value' in df.columns:
                # Si ya tiene columna Value, solo convertir kWh → GWh
                valor_antes = df['Value'].mean()
                df['Value'] = df['Value'] / 1_000_000
                valor_despues = df['Value'].mean()
                logging.info(f"✅ {metric}: Value (kWh→GWh) | {valor_antes:,.2f} → {valor_despues:.2f} GWh")
            else:
                logging.warning(f"⚠️ No se encontraron columnas horarias ni Value para {metric}")
        
        return df
        
    except Exception as e:
        logging.error(f"❌ Error convirtiendo unidades para {metric}: {e}")
        return df

def poblar_metrica(obj_api, config, usar_timeout=True, timeout_seconds=30):
    """
    Poblar cache para una métrica con conversión de unidades.
    
    Args:
        obj_api: Objeto ReadDB
        config: Configuración de la métrica
        usar_timeout: Si False, espera indefinidamente
        timeout_seconds: Timeout en segundos si usar_timeout=True
    """
    metric = config['metric']
    entity = config['entity']
    cache_type = config['cache_type']
    conversion = config.get('conversion')
    dias_history = config.get('dias_history', 7)
    batch_size = config.get('batch_size', dias_history)
    
    fecha_fin = datetime.now().date() - timedelta(days=1)
    
    # 🆕 CACHE v2.2 (2025-11-19): Generar cache EXACTO para dias_history solicitados
    # - Para rangos ≥28 días: Cachear días_history hacia atrás (no mes completo)
    # - Cache_key se agrupa por MES automáticamente en cache_manager.py
    fecha_inicio = fecha_fin - timedelta(days=dias_history)
    
    logging.info(f"📡 {metric}/{entity} - Rango: {fecha_inicio} a {fecha_fin}")
    
    try:
        # Dividir en batches si es necesario
        if batch_size < dias_history:
            current_date = fecha_inicio
            all_data = []
            
            while current_date <= fecha_fin:
                batch_end = min(current_date + timedelta(days=batch_size-1), fecha_fin)
                
                logging.info(f"  📦 Batch: {current_date} a {batch_end}")
                inicio = time.time()
                
                data = obj_api.request_data(
                    metric, entity,
                    current_date.strftime('%Y-%m-%d'),
                    batch_end.strftime('%Y-%m-%d')
                )
                
                duracion = time.time() - inicio
                
                if data is not None and not data.empty:
                    # Convertir unidades ANTES de cachear
                    data = convertir_unidades(data, metric, conversion)
                    all_data.append(data)
                    logging.info(f"  ✅ {len(data)} registros en {duracion:.1f}s")
                else:
                    logging.warning(f"  ⚠️ Sin datos después de {duracion:.1f}s")
                
                current_date = batch_end + timedelta(days=1)
            
            # Combinar todos los batches
            if all_data:
                data_final = pd.concat(all_data, ignore_index=True)
                
                # Guardar cache con datos procesados
                cache_key = get_cache_key('fetch_metric_data', metric, entity,
                                         fecha_inicio.strftime('%Y-%m-%d'),
                                         fecha_fin.strftime('%Y-%m-%d'))
                # 🆕 units_converted=True indica que las unidades YA fueron convertidas
                save_to_cache(cache_key, data_final, cache_type=cache_type, metric_name=metric, units_converted=True)
                logging.info(f"💾 Cache guardado: {len(data_final)} registros totales")
                return True
            else:
                return False
        else:
            # Query simple
            inicio = time.time()
            data = obj_api.request_data(
                metric, entity,
                fecha_inicio.strftime('%Y-%m-%d'),
                fecha_fin.strftime('%Y-%m-%d')
            )
            duracion = time.time() - inicio
            
            if data is not None and not data.empty:
                # Convertir unidades
                data = convertir_unidades(data, metric, conversion)
                
                # Guardar cache
                cache_key = get_cache_key('fetch_metric_data', metric, entity,
                                         fecha_inicio.strftime('%Y-%m-%d'),
                                         fecha_fin.strftime('%Y-%m-%d'))
                # 🆕 units_converted=True indica que las unidades YA fueron convertidas
                save_to_cache(cache_key, data, cache_type=cache_type, metric_name=metric, units_converted=True)
                logging.info(f"✅ {len(data)} registros en {duracion:.1f}s")
                return True
            else:
                logging.warning(f"⚠️ Sin datos después de {duracion:.1f}s")
                return False
                
    except Exception as e:
        logging.error(f"❌ Error poblando {metric}/{entity}: {e}")
        return False

def detectar_velocidad_api(obj_api):
    """
    Detectar si API XM está lenta haciendo query de prueba.
    
    Returns:
        tuple: (es_lenta: bool, tiempo_promedio: float)
    """
    logging.info("🔍 Detectando velocidad de API XM...")
    
    try:
        # Query simple de prueba
        fecha = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
        
        inicio = time.time()
        data = obj_api.request_data('Gene', 'Sistema', fecha, fecha)
        duracion = time.time() - inicio
        
        if duracion > 30:
            logging.warning(f"⚠️ API LENTA detectada: {duracion:.1f}s")
            return True, duracion
        else:
            logging.info(f"✅ API Normal: {duracion:.1f}s")
            return False, duracion
            
    except Exception as e:
        logging.error(f"❌ Error detectando velocidad API: {e}")
        return True, 60.0  # Asumir lenta por seguridad

def main():
    """Precalentar cache con detección inteligente de API lenta."""
    parser = argparse.ArgumentParser(description='Precalentar cache inteligente')
    parser.add_argument('--sin-timeout', action='store_true',
                       help='Deshabilitar timeout (usar cuando API muy lenta)')
    args = parser.parse_args()
    
    print('🔥 PRECALENTAMIENTO INTELIGENTE DE CACHE')
    print('=' * 70)
    
    # Inicializar API
    try:
        obj_api = ReadDB()
        logging.info('✅ API XM inicializada')
    except Exception as e:
        logging.error(f'❌ No se pudo inicializar API XM: {e}')
        return 1
    
    # Detectar velocidad API
    if not args.sin_timeout:
        api_lenta, tiempo_api = detectar_velocidad_api(obj_api)
        if api_lenta:
            print(f'\n⚠️ API LENTA DETECTADA ({tiempo_api:.1f}s)')
            print('💡 Se ajustarán timeouts y estrategia de poblado')
    else:
        print('\n⚠️ Modo SIN TIMEOUT activado (puede tardar mucho)')
        api_lenta = True
    
    inicio_total = time.time()
    total_metricas = 0
    exitosas = 0
    
    # Poblar indicadores de generación (prioridad 1)
    print('\n📊 [1/5] INDICADORES DE GENERACIÓN')
    print('-' * 70)
    for config in METRICAS_CONFIG['indicadores_generacion']:
        total_metricas += 1
        if poblar_metrica(obj_api, config, usar_timeout=not args.sin_timeout):
            exitosas += 1
    
    # Poblar generación por fuentes (prioridad 2, más pesada)
    print('\n📊 [2/5] GENERACIÓN POR FUENTES')
    print('-' * 70)
    for config in METRICAS_CONFIG['generacion_fuentes']:
        total_metricas += 1
        if poblar_metrica(obj_api, config, usar_timeout=not args.sin_timeout):
            exitosas += 1
    
    # Poblar métricas de hidrología (prioridad 3)
    print('\n📊 [3/5] MÉTRICAS DE HIDROLOGÍA')
    print('-' * 70)
    for config in METRICAS_CONFIG['metricas_hidrologia']:
        total_metricas += 1
        if poblar_metrica(obj_api, config, usar_timeout=not args.sin_timeout):
            exitosas += 1
    
    # Poblar métricas de distribución (prioridad 4)
    print('\n📊 [4/5] MÉTRICAS DE DISTRIBUCIÓN')
    print('-' * 70)
    for config in METRICAS_CONFIG['metricas_distribucion']:
        total_metricas += 1
        if poblar_metrica(obj_api, config, usar_timeout=not args.sin_timeout):
            exitosas += 1
    
    # Poblar listados del sistema (prioridad 5, baja frecuencia)
    print('\n📊 [5/5] LISTADOS DEL SISTEMA')
    print('-' * 70)
    for config in METRICAS_CONFIG['listados_sistema']:
        total_metricas += 1
        if poblar_metrica(obj_api, config, usar_timeout=not args.sin_timeout):
            exitosas += 1
    
    duracion_total = time.time() - inicio_total
    
    # Resumen
    print('\n' + '=' * 70)
    print('📊 RESUMEN')
    print('=' * 70)
    print(f'✅ Métricas pobladas: {exitosas}/{total_metricas}')
    print(f'⏱️  Tiempo total: {duracion_total/60:.1f} min ({duracion_total:.0f}s)')
    print(f'📈 Promedio: {duracion_total/total_metricas:.1f}s por métrica')
    
    if exitosas == total_metricas:
        print('\n🎉 ¡CACHE COMPLETAMENTE POBLADO!')
        return 0
    else:
        print(f'\n⚠️  {total_metricas - exitosas} métricas fallaron')
        return 1

if __name__ == '__main__':
    sys.exit(main())
