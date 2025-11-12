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
# OPTIMIZADO: Reducido a 6h para métricas críticas (evitar datos obsoletos)
CACHE_EXPIRATION = {
    'metricas_hidricas': timedelta(hours=6),      # Reservas, aportes - 6h (actualización diaria XM, validar más seguido)
    'generacion_xm': timedelta(hours=6),          # Datos de XM - 6h (actualización diaria, validar antes de mediodía)
    'generacion_plantas': timedelta(hours=6),     # Generación por plantas - 6h
    'gene_recurso': timedelta(hours=6),           # Gene/Recurso - 6h (generación por código SIC)
    'listado_recursos': timedelta(days=7),        # Listado de recursos (cambia poco) - 7 días
    'deteccion_columna': timedelta(days=30),      # Detección de columnas SIC - 30 días (estructura estable)
    'precios': timedelta(hours=3),                # Precios de bolsa - 3h (más volátil)
    'default': timedelta(hours=6)                 # Por defecto 6h (balance rendimiento/actualidad)
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

def get_from_cache(cache_key, allow_expired=False, max_age_days=7):
    """
    Obtener dato del cache (primero memoria, luego disco)
    
    OPTIMIZACIÓN: Si allow_expired=True, acepta cache de hasta max_age_days días de antigüedad
    
    Args:
        cache_key: Clave del cache
        allow_expired: Si True, retorna datos expirados si no hay alternativa
        max_age_days: Máxima antigüedad en días para cache expirado (default: 7 días)
    """
    # Intentar cache en memoria primero
    if cache_key in _memory_cache:
        cached_data, expiration_time = _memory_cache[cache_key]
        age_days = (datetime.now() - expiration_time).days
        
        if datetime.now() < expiration_time:
            logging.info(f"Cache HIT (memoria): {cache_key}")
            return cached_data
        elif allow_expired and age_days <= max_age_days:
            logging.warning(f"⚡ Cache EXPIRADO ({age_days}d) pero ACEPTABLE (memoria): {cache_key}")
            return cached_data
        else:
            if allow_expired:
                logging.info(f"Cache MUY VIEJO ({age_days}d > {max_age_days}d) - descartado (memoria)")
            else:
                logging.info(f"Cache EXPIRED (memoria): {cache_key}")
            del _memory_cache[cache_key]
    
    # Intentar cache en disco
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.pkl")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'rb') as f:
                cached_data, expiration_time = pickle.load(f)
            
            # VALIDACIÓN CRÍTICA: Verificar que NO esté corrupto
            if cached_data is None:
                logging.error(f"🚨 CACHE CORRUPTO (None): {cache_key} - ELIMINANDO")
                os.remove(cache_file)
                return None
            
            if not hasattr(cached_data, 'columns'):
                logging.error(f"🚨 CACHE CORRUPTO (no es DataFrame): {cache_key} tipo={type(cached_data)} - ELIMINANDO")
                os.remove(cache_file)
                return None
            
            age_days = (datetime.now() - expiration_time).days
            
            if datetime.now() < expiration_time:
                logging.info(f"Cache HIT (disco): {cache_key}")
                # Cargar en memoria para siguiente acceso
                _memory_cache[cache_key] = (cached_data, expiration_time)
                return cached_data
            elif allow_expired and age_days <= max_age_days:
                logging.warning(f"⚡ Cache EXPIRADO ({age_days}d) pero ACEPTABLE (disco): {cache_key}")
                # Cargar en memoria también
                _memory_cache[cache_key] = (cached_data, expiration_time)
                return cached_data
            else:
                if allow_expired:
                    logging.info(f"Cache MUY VIEJO ({age_days}d > {max_age_days}d) - eliminado (disco)")
                else:
                    logging.info(f"Cache EXPIRED (disco): {cache_key}")
                os.remove(cache_file)
        except (pickle.UnpicklingError, EOFError, AttributeError) as e:
            logging.error(f"🚨 CACHE CORRUPTO (pickle): {cache_key} - {e} - ELIMINANDO")
            if os.path.exists(cache_file):
                os.remove(cache_file)
        except Exception as e:
            logging.error(f"🚨 Error leyendo cache de disco: {cache_key} - {e} - ELIMINANDO")
            if os.path.exists(cache_file):
                os.remove(cache_file)
    
    logging.info(f"Cache MISS: {cache_key}")
    return None

def _validate_cache_date_range(df):
    """
    Validar que el cache no contenga datos de fechas futuras (indicador de cache incompleto).
    
    Args:
        df: DataFrame a validar
    
    Returns:
        bool: True si las fechas son válidas, False si hay fechas futuras o error
    """
    try:
        if df is None or df.empty:
            logging.warning("⚠️ Cache vacío o None - rechazando")
            return False
        
        # Verificar que sea DataFrame válido
        if not hasattr(df, 'columns'):
            logging.error(f"🚨 CACHE CORRUPTO: No es DataFrame válido (tipo: {type(df)})")
            return False
        
        # Buscar columna de fecha
        date_col = None
        for col in ['Date', 'date', 'Fecha', 'fecha']:
            if col in df.columns:
                date_col = col
                break
        
        if date_col:
            try:
                import pandas as pd
                df_dates = pd.to_datetime(df[date_col], errors='coerce')
                
                # Verificar que no todas las fechas sean NaT (corrupción)
                if df_dates.isna().all():
                    logging.error(f"🚨 CACHE CORRUPTO: Todas las fechas son NaT en columna '{date_col}'")
                    return False
                
                max_date = df_dates.max()
                today = pd.Timestamp.now()
                
                if pd.isna(max_date):
                    logging.error(f"🚨 CACHE CORRUPTO: max_date es NaT")
                    return False
                
                if max_date > today:
                    logging.warning(f"⚠️ Cache tiene fechas FUTURAS (max: {max_date.date()}, hoy: {today.date()})")
                    return False
            except Exception as e:
                logging.error(f"🚨 Error validando fechas (cache corrupto?): {e}")
                return False
        
        return True
        
    except Exception as e:
        logging.error(f"🚨 EXCEPCIÓN en _validate_cache_date_range: {e} - RECHAZANDO cache por seguridad")
        return False

def _validate_cache_structure(df, metric, entity):
    """
    Validar que un DataFrame de cache tenga la estructura correcta para la métrica solicitada.
    
    VALIDACIONES:
    1. Tipo de dato correcto (DataFrame)
    2. Fechas no futuras (prevenir cache incompleto)
    3. Estructura de columnas según métrica
    
    Args:
        df: DataFrame a validar
        metric: Métrica esperada (ej: 'Gene', 'ListadoEmbalses', 'AporEner')
        entity: Entidad esperada (ej: 'Sistema', 'Recurso', 'Embalse')
    
    Returns:
        bool: True si el DataFrame tiene la estructura esperada, False si no
    """
    try:
        if df is None or df.empty:
            logging.debug(f"Cache vacío para {metric}/{entity}")
            return False
        
        # VALIDACIÓN 0: Verificar que sea DataFrame válido
        if not hasattr(df, 'columns') or not hasattr(df, 'shape'):
            logging.error(f"🚨 CACHE CORRUPTO: No es DataFrame válido para {metric}/{entity} (tipo: {type(df)})")
            return False
        
        # VALIDACIÓN 1: Fechas no futuras
        if not _validate_cache_date_range(df):
            logging.warning(f"⚠️ Cache rechazado: fechas inválidas para {metric}/{entity}")
            return False
            
    except Exception as e:
        logging.error(f"🚨 EXCEPCIÓN en _validate_cache_structure: {e} - RECHAZANDO cache por seguridad")
        return False
    
    # Definir columnas requeridas por métrica/entidad
    REQUIRED_COLUMNS = {
        'ListadoEmbalses': ['Values_Name', 'Values_Code', 'Values_HydroRegion'],
        'ListadoAgentes': ['Values_Code', 'Values_Name'],
        'Gene': ['Date', 'Value'],
        'AporEner': ['Date', 'Value', 'Name'],
        'AporEnerMediHist': ['Date', 'Value', 'Name'],
        'DemaCome': ['Date', 'Values_code'],
        'DemaReal': ['Date', 'Values_code'],
        'VoluUtilDiarEner': ['Date', 'Value'],
        'CapaUtilDiarEner': ['Date', 'Value'],
    }
    
    # Verificar si tenemos columnas requeridas para esta métrica
    if metric in REQUIRED_COLUMNS:
        required = REQUIRED_COLUMNS[metric]
        # Verificar que TODAS las columnas requeridas existan
        for col in required:
            if col not in df.columns:
                logging.warning(f"⚠️ Cache inválido: falta columna '{col}' para métrica '{metric}'")
                logging.warning(f"   Columnas disponibles: {list(df.columns)}")
                return False
        logging.debug(f"✅ Cache válido: tiene todas las columnas requeridas para '{metric}'")
        return True
    else:
        # Si no conocemos la métrica, hacer validación básica
        # Al menos debe tener columnas 'Date' o 'Value' o 'Values_*'
        basic_cols = ['Date', 'Value', 'Name']
        values_cols = [col for col in df.columns if col.startswith('Values_')]
        
        if any(col in df.columns for col in basic_cols) or len(values_cols) > 0:
            logging.debug(f"✅ Cache válido (validación básica) para métrica desconocida '{metric}'")
            return True
        else:
            logging.warning(f"⚠️ Cache inválido: no tiene columnas básicas para métrica '{metric}'")
            logging.warning(f"   Columnas disponibles: {list(df.columns)}")
            return False

def find_any_cache_for_metric(prefix, metric, entity):
    """
    Buscar cache para una métrica/entidad específica, sin importar fechas.
    Útil cuando la API está caída y necesitamos datos históricos.
    
    VALIDACIÓN ESTRICTA: Solo devuelve cache que corresponda a la métrica/entidad solicitada.
    
    Args:
        prefix: Prefijo del cache (ej: 'fetch_metric_data')
        metric: Métrica a buscar (ej: 'Gene', 'AporEner')
        entity: Entidad (ej: 'Sistema', 'Recurso')
    
    Returns:
        DataFrame o None si no hay cache
    """
    logging.info(f"Buscando cache alternativo para {metric}/{entity}")
    
    # Crear identificador único de métrica/entidad para validar cache
    metric_id = f"{metric}_{entity}".lower()
    
    # Buscar en memoria primero
    pattern = f"{prefix}_"
    for cache_key in list(_memory_cache.keys()):
        if cache_key.startswith(pattern):
            try:
                # VALIDACIÓN: verificar que el cache_key contenga la métrica y entidad
                if metric.lower() in cache_key.lower() and entity.lower() in cache_key.lower():
                    cached_data, expiration_time = _memory_cache[cache_key]
                    if isinstance(cached_data, pd.DataFrame) and not cached_data.empty:
                        # Validar que el DataFrame tenga las columnas esperadas según la métrica
                        if _validate_cache_structure(cached_data, metric, entity):
                            logging.info(f"✅ Cache VÁLIDO en MEMORIA: {cache_key[:60]}...")
                            return cached_data
                        else:
                            logging.warning(f"⚠️ Cache en memoria tiene estructura incorrecta: {cache_key[:60]}")
            except Exception as e:
                logging.error(f"Error validando cache en memoria: {e}")
                continue
    
    # Buscar en disco
    try:
        cache_files = [f for f in os.listdir(CACHE_DIR) if f.startswith(prefix) and f.endswith('.pkl')]
        logging.info(f"Encontrados {len(cache_files)} archivos de cache en disco con prefix '{prefix}'")
        if cache_files:
            # Ordenar por fecha de modificación (más reciente primero)
            cache_files.sort(key=lambda x: os.path.getmtime(os.path.join(CACHE_DIR, x)), reverse=True)
            for filename in cache_files:
                # VALIDACIÓN: verificar que el filename contenga la métrica y entidad
                if metric.lower() not in filename.lower() or entity.lower() not in filename.lower():
                    continue  # Skip cache que no corresponde a esta métrica/entidad
                
                cache_file = os.path.join(CACHE_DIR, filename)
                try:
                    with open(cache_file, 'rb') as f:
                        cached_data, expiration_time = pickle.load(f)
                    if isinstance(cached_data, pd.DataFrame) and not cached_data.empty:
                        # Validar que el DataFrame tenga las columnas esperadas
                        if _validate_cache_structure(cached_data, metric, entity):
                            logging.info(f"✅ Cache VÁLIDO en DISCO: {filename}")
                            # Cargar en memoria
                            cache_key = filename.replace('.pkl', '')
                            _memory_cache[cache_key] = (cached_data, expiration_time)
                            return cached_data
                        else:
                            logging.warning(f"⚠️ Cache en disco tiene estructura incorrecta: {filename}")
                except Exception as e:
                    logging.error(f"Error leyendo {filename}: {e}")
                    continue
    except Exception as e:
        logging.error(f"Error buscando cache en disco: {e}")
    logging.info(f"❌ No se encontró ningún cache VÁLIDO para {metric}/{entity}")
    return None

def save_to_cache(cache_key, data, cache_type='default', metric_name=None):
    """Guardar dato en cache (memoria y disco) con validaciones anti-corrupción"""
    try:
        # VALIDACIÓN CRÍTICA: No guardar datos None o vacíos
        if data is None:
            logging.warning(f"⚠️ Intento de guardar cache None: {cache_key} - RECHAZADO")
            return
        
        if hasattr(data, 'empty') and data.empty:
            logging.warning(f"⚠️ Intento de guardar DataFrame vacío: {cache_key} - RECHAZADO")
            return
        
        # VALIDACIÓN: Verificar que sea DataFrame válido
        if not hasattr(data, 'columns') or not hasattr(data, 'shape'):
            logging.error(f"🚨 Intento de guardar dato NO DataFrame: {cache_key} tipo={type(data)} - RECHAZADO")
            return
        
        # VALIDACIÓN DE UNIDADES: Prevenir caches con kWh en lugar de GWh
        if metric_name in ['AporEner', 'AporEnerMediHist'] and 'Value' in data.columns:
            promedio = data['Value'].mean()
            if promedio > 1000:  # Valores en kWh, NO en GWh
                logging.error(f"🚨 VALIDACIÓN FALLIDA: {metric_name} tiene valores en kWh (promedio={promedio:.0f})")
                logging.error(f"🚨 Se esperaban valores en GWh. Cache NO guardado para prevenir error.")
                logging.error(f"🚨 Verifique que la conversión kWh→GWh se aplique ANTES de guardar.")
                return
            elif promedio < 0.001 and promedio > 0:
                logging.warning(f"⚠️ VALIDACIÓN SOSPECHOSA: {metric_name} tiene valores muy pequeños (promedio={promedio:.6f})")
                logging.warning(f"⚠️ Posible sobre-conversión. Revise lógica de unidades.")
        
        expiration = CACHE_EXPIRATION.get(cache_type, CACHE_EXPIRATION['default'])
        expiration_time = datetime.now() + expiration
        
        # Guardar en memoria
        _memory_cache[cache_key] = (data, expiration_time)
        
        # Guardar en disco para persistencia
        cache_file = os.path.join(CACHE_DIR, f"{cache_key}.pkl")
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump((data, expiration_time), f)
            
            # Log detallado del tamaño y contenido
            size_kb = os.path.getsize(cache_file) / 1024
            rows, cols = data.shape
            logging.info(f"💾 Cache guardado: {cache_key} | {rows} filas × {cols} cols | {size_kb:.1f}KB | expira en {expiration}")
        except Exception as e:
            logging.error(f"🚨 Error guardando cache en disco: {cache_key} - {e}")
            # Eliminar cache parcial si existe
            if os.path.exists(cache_file):
                os.remove(cache_file)
                
    except Exception as e:
        logging.error(f"🚨 EXCEPCIÓN en save_to_cache: {cache_key} - {e}")

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
        except (OSError, PermissionError, EOFError, pickle.UnpicklingError) as e:
            # Si hay error leyendo o eliminando, eliminar archivo corrupto
            try:
                os.remove(cache_file)
                cleaned += 1
                logging.debug(f"Archivo de cache corrupto eliminado: {cache_file} - {e}")
            except OSError:
                logging.warning(f"No se pudo eliminar cache corrupto: {cache_file}")
    
    if cleaned > 0:
        logging.info(f"Limpiados {cleaned} archivos de cache expirados")
    
    return cleaned

def cleanup_corrupted_cache():
    """
    Limpiar cache corrupto al inicio de la aplicación.
    Verifica que cada archivo de cache contenga un DataFrame válido.
    """
    cleaned = 0
    corrupted = 0
    
    logging.info("🧹 Iniciando limpieza de cache corrupto...")
    
    for file in os.listdir(CACHE_DIR):
        if not file.endswith('.pkl'):
            continue
        
        cache_file = os.path.join(CACHE_DIR, file)
        try:
            with open(cache_file, 'rb') as f:
                cached_data, expiration_time = pickle.load(f)
            
            # Verificar que sea un DataFrame válido
            if not isinstance(cached_data, pd.DataFrame):
                logging.warning(f"⚠️ Cache corrupto (no es DataFrame): {file}")
                os.remove(cache_file)
                corrupted += 1
            elif cached_data.empty:
                logging.warning(f"⚠️ Cache vacío: {file}")
                os.remove(cache_file)
                cleaned += 1
            else:
                # Cache válido
                logging.debug(f"✅ Cache válido: {file}")
        except Exception as e:
            # Si hay error leyendo, eliminar archivo corrupto
            logging.error(f"❌ Error leyendo cache {file}: {e}")
            try:
                os.remove(cache_file)
                corrupted += 1
            except (OSError, PermissionError) as remove_error:
                logging.warning(f"No se pudo eliminar cache corrupto {file}: {remove_error}")
    
    if cleaned > 0 or corrupted > 0:
        logging.info(f"🧹 Limpieza completada: {cleaned} archivos vacíos, {corrupted} archivos corruptos eliminados")
    else:
        logging.info(f"✅ No se encontró cache corrupto")
    
    return cleaned + corrupted
