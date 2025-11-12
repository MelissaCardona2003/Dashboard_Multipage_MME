"""Helper ligero para inicializar la conexión a pydataxm de forma perezosa (lazy).

Los módulos de la carpeta `pages` deben llamar a `get_objetoAPI()` cuando necesiten
usar la API en vez de inicializar al importar el módulo. Esto evita que imports largos
bloqueen el arranque del servidor Dash.

Incluye sistema de caché para optimizar consultas repetidas.
"""
from typing import Optional
import logging
from datetime import date
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

# Importar sistema de cache
from utils.cache_manager import cached_function, get_cache_key, get_from_cache, save_to_cache, find_any_cache_for_metric

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
    Función para obtener datos de métricas desde XM API con cache INTELIGENTE y seguro.
    
    ESTRATEGIA INTELIGENTE:
    1. Datos HISTÓRICOS (>7 días en el pasado) → Cache LARGO (7 días OK, datos inmutables)
    2. Datos RECIENTES (<7 días) → Cache CORTO (24h, datos pueden actualizarse)
    3. Validación de estructura → Prevenir cache corrupto
    4. API solo cuando necesario
    
    PERIODICIDAD XM:
    - Gene, DemaCome: Actualización DIARIA (antes del mediodía)
    - ListadoRecursos: Actualización SEMANAL/MENSUAL
    - Aportes, Volumen: Actualización DIARIA
    
    Args:
        metric: Nombre de la métrica (ej: 'Gene', 'VolEmbalDiar', 'AporEner')
        entity: Entidad (ej: 'Sistema', 'Recurso')
        start_date: Fecha de inicio
        end_date: Fecha de fin
    
    Returns:
        DataFrame con los datos o None si hay error
    """
    logger = logging.getLogger('xm_helper')
    from datetime import datetime, timedelta
    
    # Determinar si son datos HISTÓRICOS (inmutables) o RECIENTES (actualizables)
    today = datetime.now().date()
    days_old = (today - end_date).days if isinstance(end_date, date) else (today - datetime.strptime(end_date, '%Y-%m-%d').date()).days
    
    is_historical = days_old > 7  # Datos de hace más de 7 días son INMUTABLES
    max_cache_age = 7 if is_historical else 1  # Históricos: 7 días OK, Recientes: 1 día máximo
    
    # PASO 1: Intentar cache válido primero
    cache_key = get_cache_key('fetch_metric_data', metric, entity, start_date, end_date)
    cached_data = get_from_cache(cache_key, allow_expired=False)
    if cached_data is not None:
        logger.info(f'✅ Cache válido para {metric}/{entity}')
        return cached_data
    
    # PASO 2: ESTRATEGIA INTELIGENTE - Cache expirado según antigüedad de datos
    historical_data = get_from_cache(cache_key, allow_expired=True, max_age_days=max_cache_age)
    if historical_data is not None:
        if is_historical:
            logger.info(f'⚡ Cache HISTÓRICO (datos >{days_old}d viejos, inmutables) para {metric}/{entity}')
        else:
            logger.info(f'⚡ Cache RECIENTE (datos <7d, max 24h cache) para {metric}/{entity}')
        return historical_data
    
    # Buscar cualquier cache alternativo para esta métrica
    any_cache = find_any_cache_for_metric('fetch_metric_data', metric, entity)
    if any_cache is not None:
        logger.info(f'📊 Usando cache alternativo para {metric}/{entity}')
        return any_cache
    
    # Solo si NO hay ningún cache, intentar API
    objetoAPI = get_objetoAPI()
    
    if objetoAPI is None:
        logger.warning(f'❌ API no disponible y no hay cache para {metric}/{entity}')
        return None
    
    # API disponible, intentar consultar
    try:
        logger.info(f'🔍 Consultando {metric}/{entity} desde {start_date} hasta {end_date}')
        
        # OPTIMIZACIÓN: Detectar queries grandes y dividirlas en batches
        # MEJORA DE PERFORMANCE: Aumentar MAX_DAYS_PER_QUERY para reducir overhead
        MAX_DAYS_PER_QUERY = 60  # Aumentado de 14 a 60 días por consulta
        
        # Convertir fechas a datetime para calcular días
        if isinstance(start_date, str):
            start_dt = pd.to_datetime(start_date).date()
        else:
            start_dt = start_date if isinstance(start_date, date) else start_date.date()
            
        if isinstance(end_date, str):
            end_dt = pd.to_datetime(end_date).date()
        else:
            end_dt = end_date if isinstance(end_date, date) else end_date.date()
        
        days_span = (end_dt - start_dt).days
        
        # Si la query es muy grande, dividirla en batches (solo métricas realmente pesadas)
        # MEJORA: Removida 'Gene' de HEAVY_METRICS - ya tiene chunking propio en fetch_gene_recurso_chunked
        HEAVY_METRICS = ['DemaCome', 'CapaEfecNeta']
        if days_span > MAX_DAYS_PER_QUERY and metric in HEAVY_METRICS:
            logger.info(f'📦 BATCHING: Dividiendo {metric} ({days_span} días) en chunks de {MAX_DAYS_PER_QUERY}d')
            
            all_data = []
            current_start = start_dt
            
            while current_start <= end_dt:
                current_end = min(current_start + timedelta(days=MAX_DAYS_PER_QUERY), end_dt)
                
                logger.info(f'  📦 Batch: {current_start} a {current_end}')
                
                batch_data = objetoAPI.request_data(
                    metric, entity, 
                    current_start.strftime('%Y-%m-%d'), 
                    current_end.strftime('%Y-%m-%d')
                )
                
                if batch_data is not None and not batch_data.empty:
                    all_data.append(batch_data)
                
                current_start = current_end + timedelta(days=1)
            
            # Combinar todos los batches
            if all_data:
                data = pd.concat(all_data, ignore_index=True)
                logger.info(f'✅ Batches combinados: {len(data)} registros totales')
            else:
                data = None
        else:
            # Query normal con timeout
            def _fetch_data():
                return objetoAPI.request_data(metric, entity, start_date, end_date)
            
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(_fetch_data)
                    data = future.result(timeout=300)  # 300 segundos (5 minutos) - aumentado por queries grandes
            except FutureTimeoutError:
                logger.warning(f'⏱️ Timeout (300s) consultando {metric}/{entity} - usando cache histórico')
                # En caso de timeout, usar cache histórico
                historical_data = get_from_cache(cache_key, allow_expired=True)
                if historical_data is not None:
                    logger.info(f'📊 Usando datos históricos (por timeout) para {metric}/{entity}')
                    return historical_data
                
                any_cache = find_any_cache_for_metric('fetch_metric_data', metric, entity)
                if any_cache is not None:
                    logger.info(f'📊 Usando cache alternativo (por timeout) para {metric}/{entity}')
                    return any_cache
                
                return None
        
        if data is not None and not data.empty:
            # 🔧 CONVERSIÓN AUTOMÁTICA DE UNIDADES ANTES DE CACHEAR
            # Asegurar que métricas de energía siempre se cacheen en GWh
            if metric in ['AporEner', 'AporEnerMediHist'] and 'Value' in data.columns:
                valor_promedio = data['Value'].mean()
                if valor_promedio > 1000:  # Valores en kWh, convertir a GWh
                    data = data.copy()  # Evitar modificar original
                    data['Value'] = data['Value'] / 1_000_000
                    logger.info(f'✅ {metric} convertido: kWh → GWh (promedio: {valor_promedio/1e6:.2f} GWh)')
                elif valor_promedio < 0.001:
                    logger.warning(f'⚠️ {metric} valores sospechosamente pequeños (promedio={valor_promedio:.6f})')
                else:
                    logger.info(f'✅ {metric} ya en GWh (promedio: {valor_promedio:.2f} GWh)')
            
            logger.info(f'✅ Obtenidos {len(data)} registros de {metric}/{entity}')
            # Guardar en cache con validación de unidades (ahora siempre en GWh para métricas de energía)
            save_to_cache(cache_key, data, cache_type='default', metric_name=metric)
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

def fetch_multiple_metrics_parallel(metrics_requests, max_workers=5):
    """
    Consultar múltiples métricas en paralelo para optimizar rendimiento.
    
    Args:
        metrics_requests: Lista de tuplas (metric, entity, start_date, end_date, key_name)
                         Ejemplo: [
                             ('Gene', 'Recurso', '2025-01-01', '2025-12-31', 'generacion'),
                             ('AporEner', 'Rio', '2025-01-01', '2025-12-31', 'aportes'),
                         ]
        max_workers: Número máximo de consultas simultáneas (default: 5)
    
    Returns:
        Dict con resultados: {'generacion': DataFrame, 'aportes': DataFrame, ...}
    
    Ejemplo de uso:
        metrics = [
            ('Gene', 'Recurso', start_date, end_date, 'gene'),
            ('AporEner', 'Sistema', start_date, end_date, 'apor_sistema'),
            ('AporEnerMediHist', 'Sistema', start_hist, end_hist, 'media_hist'),
        ]
        results = fetch_multiple_metrics_parallel(metrics)
        df_gene = results['gene']
        df_apor = results['apor_sistema']
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import time
    
    logger = logging.getLogger('xm_helper')
    results = {}
    
    start_time = time.time()
    logger.info(f"⚡ Consultando {len(metrics_requests)} métricas en paralelo (max {max_workers} workers)...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Enviar todas las consultas
        future_to_metric = {}
        for metric_req in metrics_requests:
            metric, entity, start_date, end_date, key_name = metric_req
            future = executor.submit(fetch_metric_data, metric, entity, start_date, end_date)
            future_to_metric[future] = (key_name, metric, entity)
        
        # Recolectar resultados conforme se completan
        for future in as_completed(future_to_metric):
            key_name, metric, entity = future_to_metric[future]
            try:
                result = future.result()
                results[key_name] = result
                if result is not None and not result.empty:
                    logger.info(f"✅ {key_name} ({metric}/{entity}): {len(result)} filas")
                else:
                    logger.warning(f"⚠️ {key_name} ({metric}/{entity}): Sin datos")
            except Exception as e:
                logger.error(f"❌ Error en {key_name} ({metric}/{entity}): {e}")
                results[key_name] = None
    
    elapsed = time.time() - start_time
    logger.info(f"⚡ Consultas paralelas completadas en {elapsed:.2f} segundos")
    
    return results
