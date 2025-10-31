"""
Sistema de caché centralizado para optimizar la aplicación
Evita recalcular los mismos datos cada vez que se recarga la página
"""
import logging
import pandas as pd
from datetime import datetime, timedelta
from functools import wraps
import pickle
import os
import hashlib

# Directorio para almacenar cache en disco
CACHE_DIR = "/tmp/portal_energetico_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Cache en memoria (más rápido)
_memory_cache = {}

# Tiempos de expiración por tipo de dato
CACHE_EXPIRATION = {
    'metricas_hidricas': timedelta(hours=1),      # Reservas, aportes
    'generacion_xm': timedelta(hours=1),          # Datos de XM
    'generacion_plantas': timedelta(hours=2),     # Generación por plantas
    'listado_recursos': timedelta(hours=12),      # Listado de recursos (cambia poco)
    'precios': timedelta(minutes=30),             # Precios de bolsa
    'default': timedelta(hours=1)
}

def get_cache_key(prefix, *args, **kwargs):
    """Generar una clave única para el cache basada en los parámetros"""
    # Combinar todos los argumentos en una cadena
    key_parts = [prefix]
    key_parts.extend([str(arg) for arg in args])
    key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
    
    # Crear hash MD5 para claves largas
    key_string = "|".join(key_parts)
    key_hash = hashlib.md5(key_string.encode()).hexdigest()
    
    return f"{prefix}_{key_hash}"

def get_from_cache(cache_key, allow_expired=False):
    """
    Obtener dato del cache (primero memoria, luego disco)
    
    Args:
        cache_key: Clave del cache
        allow_expired: Si True, retorna datos expirados si no hay alternativa
    """
    # Intentar cache en memoria primero
    if cache_key in _memory_cache:
        cached_data, expiration_time = _memory_cache[cache_key]
        if datetime.now() < expiration_time:
            logging.info(f"Cache HIT (memoria): {cache_key}")
            return cached_data
        elif allow_expired:
            logging.warning(f"Cache EXPIRED pero usando datos históricos (memoria): {cache_key}")
            return cached_data
        else:
            logging.info(f"Cache EXPIRED (memoria): {cache_key}")
            del _memory_cache[cache_key]
    
    # Intentar cache en disco
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.pkl")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'rb') as f:
                cached_data, expiration_time = pickle.load(f)
            
            if datetime.now() < expiration_time:
                logging.info(f"Cache HIT (disco): {cache_key}")
                # Cargar en memoria para siguiente acceso
                _memory_cache[cache_key] = (cached_data, expiration_time)
                return cached_data
            elif allow_expired:
                logging.warning(f"Cache EXPIRED pero usando datos históricos (disco): {cache_key}")
                # Cargar en memoria también
                _memory_cache[cache_key] = (cached_data, expiration_time)
                return cached_data
            else:
                logging.info(f"Cache EXPIRED (disco): {cache_key}")
                os.remove(cache_file)
        except Exception as e:
            logging.error(f"Error leyendo cache de disco: {e}")
            if os.path.exists(cache_file):
                os.remove(cache_file)
    
    logging.info(f"Cache MISS: {cache_key}")
    return None

def find_any_cache_for_metric(prefix, metric, entity):
    """
    Buscar CUALQUIER cache para una métrica/entidad, sin importar fechas.
    Útil cuando la API está caída y necesitamos datos históricos.
    
    Args:
        prefix: Prefijo del cache (ej: 'fetch_metric_data')
        metric: Métrica a buscar (ej: 'Gene', 'AporEner')
        entity: Entidad (ej: 'Sistema', 'Recurso')
    
    Returns:
        DataFrame o None si no hay cache
    """
    logging.info(f"Buscando cache alternativo para {metric}/{entity}")
    
    # Buscar en memoria primero
    pattern = f"{prefix}_"
    for cache_key in list(_memory_cache.keys()):
        if cache_key.startswith(pattern):
            try:
                cached_data, _ = _memory_cache[cache_key]
                if isinstance(cached_data, pd.DataFrame) and not cached_data.empty:
                    logging.info(f"Encontrado cache en MEMORIA: {cache_key[:50]}...")
                    return cached_data
            except:
                continue
    
    # Buscar en disco
    try:
        cache_files = [f for f in os.listdir(CACHE_DIR) if f.startswith(prefix) and f.endswith('.pkl')]
        logging.info(f"Encontrados {len(cache_files)} archivos de cache en disco con prefix '{prefix}'")
        if cache_files:
            # Ordenar por fecha de modificación (más reciente primero)
            cache_files.sort(key=lambda x: os.path.getmtime(os.path.join(CACHE_DIR, x)), reverse=True)
            for filename in cache_files:
                cache_file = os.path.join(CACHE_DIR, filename)
                try:
                    with open(cache_file, 'rb') as f:
                        cached_data, expiration_time = pickle.load(f)
                    if isinstance(cached_data, pd.DataFrame) and not cached_data.empty:
                        logging.info(f"Encontrado cache en DISCO: {filename}")
                        # Cargar en memoria
                        cache_key = filename.replace('.pkl', '')
                        _memory_cache[cache_key] = (cached_data, expiration_time)
                        return cached_data
                except Exception as e:
                    logging.error(f"Error leyendo {filename}: {e}")
                    continue
    except Exception as e:
        logging.error(f"Error buscando cache en disco: {e}")
    logging.info(f"No se encontró ningún cache para {metric}/{entity}")
    return None

def save_to_cache(cache_key, data, cache_type='default'):
    """Guardar dato en cache (memoria y disco)"""
    expiration = CACHE_EXPIRATION.get(cache_type, CACHE_EXPIRATION['default'])
    expiration_time = datetime.now() + expiration
    
    # Guardar en memoria
    _memory_cache[cache_key] = (data, expiration_time)
    
    # Guardar en disco para persistencia
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.pkl")
    try:
        with open(cache_file, 'wb') as f:
            pickle.dump((data, expiration_time), f)
        logging.info(f"Guardado en cache: {cache_key} (expira: {expiration})")
    except Exception as e:
        logging.error(f"Error guardando cache en disco: {e}")

def cached_function(cache_type='default'):
    """Decorador para cachear resultados de funciones"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generar clave de cache
            cache_key = get_cache_key(func.__name__, *args, **kwargs)
            
            # Intentar obtener de cache
            cached_result = get_from_cache(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Si no está en cache, ejecutar función
            logging.info(f"Ejecutando función: {func.__name__}")
            result = func(*args, **kwargs)
            
            # Guardar resultado en cache
            if result is not None:
                save_to_cache(cache_key, result, cache_type)
            
            return result
        return wrapper
    return decorator

def clear_cache(cache_type=None):
    """Limpiar cache (todo o por tipo específico)"""
    global _memory_cache
    
    if cache_type is None:
        # Limpiar todo
        _memory_cache.clear()
        for file in os.listdir(CACHE_DIR):
            os.remove(os.path.join(CACHE_DIR, file))
        logging.info("Cache completamente limpiado")
    else:
        # Limpiar por tipo (requeriría metadata adicional)
        logging.info(f"Limpiando cache tipo: {cache_type}")
        keys_to_remove = [k for k in _memory_cache.keys() if k.startswith(cache_type)]
        for key in keys_to_remove:
            del _memory_cache[key]

def get_cache_stats():
    """Obtener estadísticas del cache"""
    memory_items = len(_memory_cache)
    disk_items = len([f for f in os.listdir(CACHE_DIR) if f.endswith('.pkl')])
    
    # Calcular tamaño total
    total_size = 0
    for file in os.listdir(CACHE_DIR):
        total_size += os.path.getsize(os.path.join(CACHE_DIR, file))
    
    return {
        'memory_items': memory_items,
        'disk_items': disk_items,
        'total_size_mb': total_size / (1024 * 1024)
    }

# Función específica para limpiar cache antiguo automáticamente
def cleanup_old_cache():
    """Limpiar archivos de cache expirados (ejecutar periódicamente)"""
    cleaned = 0
    for file in os.listdir(CACHE_DIR):
        if not file.endswith('.pkl'):
            continue
        
        cache_file = os.path.join(CACHE_DIR, file)
        try:
            with open(cache_file, 'rb') as f:
                _, expiration_time = pickle.load(f)
            
            if datetime.now() >= expiration_time:
                os.remove(cache_file)
                cleaned += 1
        except:
            # Si hay error leyendo, eliminar archivo corrupto
            os.remove(cache_file)
            cleaned += 1
    
    if cleaned > 0:
        logging.info(f"Limpiados {cleaned} archivos de cache expirados")
    
    return cleaned
