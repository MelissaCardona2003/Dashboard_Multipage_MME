#!/usr/bin/env python3
"""
SCRIPT ESPECIAL: Poblar Cache SIN Timeout
==========================================

Este script se ejecuta SOLO cuando la API XM está MUY LENTA (>60s por query)
para actualizar el cache permitiendo tiempos de espera largos.

USO:
    python3 scripts/poblar_cache_sin_timeout.py
    
OBJETIVO:
    - Poblar cache con métricas críticas del dashboard
    - NO usar timeout artificial - esperar lo necesario
    - Ejecutar SOLO cuando API XM está lenta pero funcional
    - Una vez poblado el cache, el dashboard será rápido
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydataxm.pydataxm import ReadDB
from utils.cache_manager import save_to_cache, get_cache_key
from datetime import datetime, timedelta
import time
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Métricas críticas para el dashboard de Generación
METRICAS_CRITICAS = [
    # Indicadores principales (generacion.py)
    ('VoluUtilDiarEner', 'Embalse', 'metricas_hidricas'),
    ('CapaUtilDiarEner', 'Embalse', 'metricas_hidricas'),
    ('AporEner', 'Sistema', 'metricas_hidricas'),
    ('AporEnerMediHist', 'Sistema', 'metricas_hidricas'),
    ('Gene', 'Sistema', 'generacion_xm'),
    
    # Generación por fuentes (generacion_fuentes_unificado.py)
    ('Gene', 'Recurso', 'generacion_plantas'),
]

def poblar_metrica_sin_timeout(obj_api, metric, entity, start_date, end_date, cache_type):
    """
    Poblar cache para una métrica SIN timeout - esperar lo necesario.
    
    Args:
        obj_api: Objeto ReadDB de pydataxm
        metric: Nombre de la métrica
        entity: Tipo de entidad (Sistema, Embalse, Recurso)
        start_date: Fecha inicio (str YYYY-MM-DD)
        end_date: Fecha fin (str YYYY-MM-DD)
        cache_type: Tipo de cache para expiración
        
    Returns:
        bool: True si se pobló correctamente
    """
    cache_key = get_cache_key('fetch_metric_data', metric, entity, start_date, end_date)
    
    try:
        logging.info(f'📡 Consultando {metric}/{entity} desde {start_date} hasta {end_date}...')
        inicio = time.time()
        
        # SIN TIMEOUT - esperar lo necesario
        data = obj_api.request_data(metric, entity, start_date, end_date)
        
        duracion = time.time() - inicio
        
        if data is not None and not data.empty:
            logging.info(f'✅ Datos recibidos en {duracion:.1f}s: {len(data)} registros')
            
            # Guardar en cache
            save_to_cache(cache_key, data, cache_type=cache_type, metric_name=metric)
            logging.info(f'💾 Cache guardado: {cache_key}')
            
            return True
        else:
            logging.warning(f'⚠️  Sin datos después de {duracion:.1f}s')
            return False
            
    except Exception as e:
        duracion = time.time() - inicio if 'inicio' in locals() else 0
        logging.error(f'❌ Error después de {duracion:.1f}s: {e}')
        return False

def main():
    """Poblar cache con todas las métricas críticas."""
    print('🔥 POBLANDO CACHE SIN TIMEOUT - API XM Lenta')
    print('=' * 70)
    print('⚠️  ADVERTENCIA: Este proceso puede tardar VARIOS MINUTOS')
    print('⚠️  La API XM está lenta (~77s por query)')
    print('=' * 70)
    
    # Inicializar API
    try:
        obj_api = ReadDB()
        logging.info('✅ API XM inicializada')
    except Exception as e:
        logging.error(f'❌ No se pudo inicializar API XM: {e}')
        return 1
    
    # Calcular fechas
    # Buscar últimos datos disponibles (hasta 7 días atrás)
    fecha_fin = datetime.now().date()
    fecha_inicio = fecha_fin - timedelta(days=7)
    
    logging.info(f'📅 Rango de fechas: {fecha_inicio} a {fecha_fin}')
    
    # Contadores
    total_metricas = len(METRICAS_CRITICAS)
    exitosas = 0
    fallidas = 0
    
    inicio_total = time.time()
    
    # Poblar cada métrica
    for i, (metric, entity, cache_type) in enumerate(METRICAS_CRITICAS, 1):
        print(f'\n📊 [{i}/{total_metricas}] {metric}/{entity}')
        print('-' * 70)
        
        # Para Gene/Recurso, usar menos días (es la más pesada)
        if metric == 'Gene' and entity == 'Recurso':
            fecha_inicio_metrica = fecha_fin - timedelta(days=3)
            logging.info(f'⚡ Gene/Recurso: Limitando a 3 días para evitar sobrecarga')
        else:
            fecha_inicio_metrica = fecha_inicio
        
        # Poblar día por día para métricas pesadas
        if metric == 'Gene' and entity == 'Recurso':
            # Gene/Recurso día por día
            current_date = fecha_inicio_metrica
            metrica_exitosa = True
            
            while current_date <= fecha_fin:
                fecha_str = current_date.strftime('%Y-%m-%d')
                
                exito = poblar_metrica_sin_timeout(
                    obj_api, metric, entity, fecha_str, fecha_str, cache_type
                )
                
                if not exito:
                    metrica_exitosa = False
                    
                current_date += timedelta(days=1)
            
            if metrica_exitosa:
                exitosas += 1
            else:
                fallidas += 1
        else:
            # Métricas normales: todo el rango
            fecha_inicio_str = fecha_inicio_metrica.strftime('%Y-%m-%d')
            fecha_fin_str = fecha_fin.strftime('%Y-%m-%d')
            
            exito = poblar_metrica_sin_timeout(
                obj_api, metric, entity, fecha_inicio_str, fecha_fin_str, cache_type
            )
            
            if exito:
                exitosas += 1
            else:
                fallidas += 1
    
    duracion_total = time.time() - inicio_total
    
    # Resumen final
    print('\n' + '=' * 70)
    print('📊 RESUMEN FINAL')
    print('=' * 70)
    print(f'✅ Métricas pobladas: {exitosas}/{total_metricas}')
    print(f'❌ Métricas fallidas: {fallidas}/{total_metricas}')
    print(f'⏱️  Tiempo total: {duracion_total/60:.1f} minutos ({duracion_total:.0f}s)')
    print(f'📈 Promedio por métrica: {duracion_total/total_metricas:.1f}s')
    
    if exitosas == total_metricas:
        print('\n🎉 ¡CACHE COMPLETAMENTE POBLADO!')
        print('💡 Ahora el dashboard cargará en <3 segundos')
        print('💡 El sistema de precalentamiento automático mantendrá el cache actualizado')
        return 0
    else:
        print(f'\n⚠️  {fallidas} métricas no se pudieron poblar')
        print('💡 El dashboard funcionará con los datos disponibles')
        return 1

if __name__ == '__main__':
    sys.exit(main())
