"""Helper ligero para inicializar la conexión a pydataxm de forma perezosa (lazy).

Los módulos de la carpeta `pages` deben llamar a `get_objetoAPI()` cuando necesiten
usar la API en vez de inicializar al importar el módulo. Esto evita que imports largos
bloqueen el arranque del servidor Dash.

Incluye sistema de caché para optimizar consultas repetidas.
"""
from typing import Optional
import logging
import signal
from contextlib import contextmanager
from datetime import date
import pandas as pd

# Importar sistema de cache
from utils.cache_manager import cached_function, get_cache_key, get_from_cache, save_to_cache, find_any_cache_for_metric

class TimeoutException(Exception):
    pass

@contextmanager
def time_limit(seconds):
    """Context manager para limitar el tiempo de ejecución de un bloque de código"""
    def signal_handler(signum, frame):
        raise TimeoutException("Timed out!")
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

try:
    from pydataxm.pydataxm import ReadDB
    _PYDATAXM_AVAILABLE = True
except Exception:
    ReadDB = None  # type: ignore
    _PYDATAXM_AVAILABLE = False

_objetoAPI = None

def get_objetoAPI():
    """Retorna una instancia única de ReadDB si está disponible, o None.

    Inicializa la instancia la primera vez que se llama.
    Si la importación o inicialización falla, retorna None y registra un warning.
    """
    global _objetoAPI
    if _objetoAPI is not None:
        return _objetoAPI

    logger = logging.getLogger('xm_helper')
    if not _PYDATAXM_AVAILABLE:
        logger.warning('pydataxm no disponible (get_objetoAPI)')
        _objetoAPI = None
        return None

    try:
        # Intentar inicializar ReadDB sin timeout
        logger.info('Iniciando conexión a API XM...')
        _objetoAPI = ReadDB()
        logger.info('✅ pydataxm ReadDB inicializada correctamente')
    except Exception as e:
        logger.exception('❌ Error inicializando ReadDB: %s', e)
        _objetoAPI = None
    return _objetoAPI

def fetch_metric_data(metric: str, entity: str, start_date: date, end_date: date):
    """
    Función para obtener datos de métricas desde XM API con cache manual y fallback histórico.
    
    Args:
        metric: Nombre de la métrica (ej: 'Gene', 'VolEmbalDiar', 'AporEner')
        entity: Entidad (ej: 'Sistema', 'Recurso')
        start_date: Fecha de inicio
        end_date: Fecha de fin
    
    Returns:
        DataFrame con los datos o None si hay error
    """
    logger = logging.getLogger('xm_helper')
    
    # Intentar cache normal primero
    cache_key = get_cache_key('fetch_metric_data', metric, entity, start_date, end_date)
    cached_data = get_from_cache(cache_key, allow_expired=False)
    if cached_data is not None:
        return cached_data
    
    # No hay cache, intentar API
    objetoAPI = get_objetoAPI()
    
    if objetoAPI is None:
        logger.warning(f'API no disponible para {metric}/{entity} - intentando usar datos históricos')
        
        # Intentar cache expirado
        historical_data = get_from_cache(cache_key, allow_expired=True)
        if historical_data is not None:
            logger.info(f'📊 Usando datos históricos (cache expirado) para {metric}/{entity}')
            return historical_data
        
        # Si no hay cache exacto, buscar CUALQUIER cache para esta métrica
        any_cache = find_any_cache_for_metric('fetch_metric_data', metric, entity)
        if any_cache is not None:
            logger.info(f'📊 Usando cache alternativo para {metric}/{entity}')
            return any_cache
        
        logger.warning(f'❌ No hay datos históricos disponibles para {metric}/{entity}')
        return None
    
    # API disponible, intentar consultar
    try:
        logger.info(f'🔍 Consultando {metric}/{entity} desde {start_date} hasta {end_date}')
        data = objetoAPI.request_data(metric, entity, start_date, end_date)
        
        if data is not None and not data.empty:
            logger.info(f'✅ Obtenidos {len(data)} registros de {metric}/{entity}')
            # Guardar en cache
            save_to_cache(cache_key, data, cache_type='default')
            return data
        else:
            logger.warning(f'⚠️ No hay datos para {metric}/{entity}')
            
            # Si no hay datos nuevos, intentar usar históricos
            historical_data = get_from_cache(cache_key, allow_expired=True)
            if historical_data is not None:
                logger.info(f'📊 Usando datos históricos (no hay nuevos) para {metric}/{entity}')
                return historical_data
            
            # Buscar cualquier cache alternativo
            any_cache = find_any_cache_for_metric('fetch_metric_data', metric, entity)
            if any_cache is not None:
                logger.info(f'📊 Usando cache alternativo (no hay nuevos) para {metric}/{entity}')
                return any_cache
            
            return None
            
    except Exception as e:
        logger.error(f'❌ Error consultando {metric}/{entity}: {e}')
        
        # En caso de error, intentar datos históricos
        historical_data = get_from_cache(cache_key, allow_expired=True)
        if historical_data is not None:
            logger.info(f'📊 Usando datos históricos (por error) para {metric}/{entity}')
            return historical_data
        
        # Buscar cualquier cache alternativo
        any_cache = find_any_cache_for_metric('fetch_metric_data', metric, entity)
        if any_cache is not None:
            logger.info(f'📊 Usando cache alternativo (por error) para {metric}/{entity}')
            return any_cache
        
        return None
