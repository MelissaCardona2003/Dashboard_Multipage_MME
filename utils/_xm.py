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
    
    # PASO 2: Cache expirado (pero SOLO si es para las fechas solicitadas)
    # NO retornar cache de fechas diferentes - genera datos incorrectos
    historical_data = get_from_cache(cache_key, allow_expired=True, max_age_days=30)
    if historical_data is not None:
        logger.info(f'⚡ Cache disponible (hasta 30 días) para {metric}/{entity}')
        return historical_data
    
    # NO buscar cache alternativo - retornar None para que dashboard pruebe fechas anteriores
    # Esto previene mostrar datos corruptos de fechas incorrectas
    
    # Solo si NO hay ningún cache, intentar API
    objetoAPI = get_objetoAPI()
    
    if objetoAPI is None:
        logger.warning(f'❌ API no disponible y no hay cache para {metric}/{entity}')
        return None
    
    # API disponible, intentar consultar
    try:
        logger.info(f'🔍 Consultando {metric}/{entity} desde {start_date} hasta {end_date}')
        
        # OPTIMIZACIÓN: Detectar queries grandes y dividirlas en batches
        # MEJORA DE PERFORMANCE: Máximo 14 días para evitar timeouts con Gene/Recurso
        MAX_DAYS_PER_QUERY = 14  # Reducido a 14 días para evitar sobrecarga API
        
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
                    data = future.result(timeout=10)  # 10 segundos - timeout agresivo para evitar bloqueos largos
            except FutureTimeoutError:
                logger.warning(f'⏱️ Timeout (10s) consultando {metric}/{entity} - usando cache histórico')
                # En caso de timeout, SOLO usar cache de las fechas exactas solicitadas (máx 30 días)
                historical_data = get_from_cache(cache_key, allow_expired=True, max_age_days=30)
                if historical_data is not None:
                    logger.info(f'✅ Usando cache histórico para {metric}/{entity}')
                    return historical_data
                
                # NO buscar cache alternativo - previene datos de fechas incorrectas
                logger.error(f'❌ No hay cache disponible para {metric}/{entity}')
                return None
        
        if data is not None and not data.empty:
            # ⚠️ REDISEÑO 2025-11-19: Conversiones movidas a precalentar_cache_inteligente.py
            # fetch_metric_data() SOLO consulta API y cachea datos RAW
            # Dashboard espera recibir datos YA CONVERTIDOS desde precalentamiento
            
            logger.info(f'✅ Obtenidos {len(data)} registros de {metric}/{entity}')
            
            # Guardar en cache (si viene de API, guardar RAW; si viene de precalentamiento, ya está convertido)
            save_to_cache(cache_key, data, cache_type='default', metric_name=metric, units_converted=False)
            return data
        else:
            logger.warning(f'⚠️ No hay datos para {metric}/{entity}')
            
            # Si no hay datos nuevos, SOLO usar cache de fechas exactas
            historical_data = get_from_cache(cache_key, allow_expired=True)
            if historical_data is not None:
                logger.info(f'📊 Usando datos históricos (no hay nuevos) para {metric}/{entity}')
                return historical_data
            
            # NO buscar cache alternativo - previene datos de fechas incorrectas
            return None
            
    except Exception as e:
        logger.error(f'❌ Error consultando {metric}/{entity}: {e}')
        
        # En caso de error, SOLO intentar cache de fechas exactas
        historical_data = get_from_cache(cache_key, allow_expired=True)
        if historical_data is not None:
            logger.info(f'📊 Usando datos históricos (por error) para {metric}/{entity}')
            return historical_data
        
        # NO buscar cache alternativo - previene datos de fechas incorrectas
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


def obtener_datos_con_fallback(metric: str, entity: str, fecha_fin: date, dias_busqueda: int = 7):
    """
    Buscar datos hacia atrás hasta encontrar fecha válida.
    
    Esta función implementa la estrategia CORRECTA para el sistema cache-precalentamiento:
    - Si no hay datos para fecha exacta → buscar hacia atrás
    - NO usar cache de fechas incorrectas (previene datos corruptos)
    - Retornar None si no hay datos en ventana de búsqueda
    
    Args:
        metric: Métrica XM (ej: 'Gene', 'AporEner', 'VoluUtilDiarEner')
        entity: Entidad (ej: 'Sistema', 'Embalse', 'Rio', 'Recurso')
        fecha_fin: Fecha inicial de búsqueda (normalmente datetime.now().date())
        dias_busqueda: Cuántos días buscar hacia atrás (default: 7)
    
    Returns:
        tuple: (DataFrame con datos, date de fecha encontrada) o (None, None)
    
    Ejemplo:
        from datetime import datetime
        from utils._xm import obtener_datos_con_fallback
        
        # Buscar últimos datos de reservas (hasta 7 días atrás)
        df_vol, fecha = obtener_datos_con_fallback(
            'VoluUtilDiarEner', 
            'Embalse', 
            datetime.now().date()
        )
        
        if df_vol is not None:
            print(f"Datos encontrados para {fecha}")
            # Procesar datos...
        else:
            print("No hay datos disponibles")
    """
    from datetime import timedelta
    
    logger = logging.getLogger('xm_helper')
    
    for dias_atras in range(dias_busqueda):
        fecha_prueba = fecha_fin - timedelta(days=dias_atras)
        fecha_str = fecha_prueba.strftime('%Y-%m-%d')
        
        df = fetch_metric_data(metric, entity, fecha_str, fecha_str)
        
        if df is not None and not df.empty:
            if dias_atras > 0:
                logger.info(f"✅ Datos encontrados para {metric}/{entity} en {fecha_str} ({dias_atras} días atrás)")
            else:
                logger.info(f"✅ Datos encontrados para {metric}/{entity} en {fecha_str} (hoy)")
            return df, fecha_prueba
    
    logger.warning(f"❌ No hay datos para {metric}/{entity} en últimos {dias_busqueda} días")
    return None, None


def obtener_datos_desde_sqlite(metric: str, entity: str, fecha_fin, dias_busqueda: int = 7, recurso: str = None):
    """
    Consultar datos desde SQLite con fallback automático hacia atrás.
    
    Reemplaza obtener_datos_con_fallback() para usar SQLite en lugar de cache.
    Busca datos hacia atrás hasta encontrar registros válidos.
    
    Args:
        metric: Métrica XM (ej: 'Gene', 'AporEner', 'VoluUtilDiarEner')
        entity: Entidad (ej: 'Sistema', 'Embalse', 'Rio', 'Recurso')
        fecha_fin: Fecha inicial de búsqueda (str 'YYYY-MM-DD' o date/datetime object)
        dias_busqueda: Cuántos días buscar hacia atrás (default: 7)
        recurso: Filtro opcional por recurso (ej: 'SOLAR', 'EOLICA')
    
    Returns:
        tuple: (DataFrame con datos, date de fecha encontrada) o (None, None)
    
    Ejemplo:
        # Buscar últimos datos de reservas
        df_vol, fecha = obtener_datos_desde_sqlite(
            'VoluUtilDiarEner', 
            'Embalse', 
            datetime.now().date()
        )
    """
    from datetime import timedelta, datetime
    from utils import db_manager
    
    logger = logging.getLogger('xm_helper')
    
    # Convertir fecha_fin a date si es string o datetime
    if isinstance(fecha_fin, str):
        fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
    elif isinstance(fecha_fin, datetime):
        fecha_fin = fecha_fin.date()
    
    for dias_atras in range(dias_busqueda):
        fecha_inicio = fecha_fin - timedelta(days=dias_atras)
        fecha_str = fecha_inicio.strftime('%Y-%m-%d')
        
        # Consultar SQLite
        df = db_manager.get_metric_data(
            metrica=metric,
            entidad=entity,
            fecha_inicio=fecha_str,
            fecha_fin=fecha_str,
            recurso=recurso
        )
        
        if df is not None and not df.empty:
            if dias_atras > 0:
                logger.info(f"✅ [SQLite] Datos encontrados para {metric}/{entity} en {fecha_str} ({dias_atras} días atrás)")
            else:
                logger.info(f"✅ [SQLite] Datos encontrados para {metric}/{entity} en {fecha_str} (hoy)")
            
            # Renombrar columnas para compatibilidad con código existente
            # SQLite retorna: fecha, metrica, entidad, recurso, valor_gwh, unidad
            # Código espera: Date, Value, (opcionalmente Resources/Embalse/Rio)
            if 'valor_gwh' in df.columns:
                df = df.rename(columns={'valor_gwh': 'Value', 'fecha': 'Date'})
            
            if 'recurso' in df.columns and df['recurso'].notna().any():
                # Detectar nombre correcto de columna según entidad
                if entity == 'Embalse':
                    df = df.rename(columns={'recurso': 'Embalse'})
                elif entity == 'Rio':
                    df = df.rename(columns={'recurso': 'Rio'})
                elif entity == 'Recurso':
                    df = df.rename(columns={'recurso': 'Resources'})
                elif entity == 'Agente':
                    df = df.rename(columns={'recurso': 'Agente'})
            
            return df, fecha_inicio
    
    logger.warning(f"❌ [SQLite] No hay datos para {metric}/{entity} en últimos {dias_busqueda} días")
    return None, None


def obtener_datos_inteligente(metric: str, entity: str, fecha_inicio, fecha_fin, recurso: str = None):
    """
    Consulta inteligente de datos: SQLite (>=2020, rápido) vs API XM (<2020, lento con advertencia).
    
    Esta función decide automáticamente la fuente de datos basándose en el rango de fechas:
    - Si fecha_inicio >= 2020-01-01: Consulta SQLite (rápido, <5s)
    - Si fecha_inicio < 2020-01-01: Consulta API XM directo (lento, 30-60s, muestra advertencia)
    
    Args:
        metric: Métrica XM (ej: 'Gene', 'AporEner', 'VoluUtilDiarEner')
        entity: Entidad (ej: 'Sistema', 'Embalse', 'Rio', 'Recurso')
        fecha_inicio: Fecha inicial del rango (str 'YYYY-MM-DD' o date/datetime object)
        fecha_fin: Fecha final del rango (str 'YYYY-MM-DD' o date/datetime object)
        recurso: Filtro opcional por recurso (ej: 'SOLAR', 'EOLICA')
    
    Returns:
        tuple: (DataFrame con datos, str mensaje de advertencia o None)
    
    Ejemplos:
        # Consulta reciente (>= 2020) - Usa SQLite
        df, warning = obtener_datos_inteligente('Gene', 'Sistema', '2023-01-01', '2024-01-01')
        # warning = None, consulta rápida
        
        # Consulta histórica (< 2020) - Usa API XM
        df, warning = obtener_datos_inteligente('Gene', 'Sistema', '2015-01-01', '2016-01-01')
        # warning = "⚠️ Consultando datos históricos (antes de 2020) directamente..."
    """
    from datetime import datetime, date
    from utils import db_manager
    
    logger = logging.getLogger('xm_helper')
    
    # Fecha límite: datos antes del 2020 no están en SQLite
    FECHA_LIMITE_SQLITE = date(2020, 1, 1)
    
    # Convertir fechas a objetos date
    if isinstance(fecha_inicio, str):
        fecha_inicio_date = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
    elif isinstance(fecha_inicio, datetime):
        fecha_inicio_date = fecha_inicio.date()
    else:
        fecha_inicio_date = fecha_inicio
    
    if isinstance(fecha_fin, str):
        fecha_fin_date = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
    elif isinstance(fecha_fin, datetime):
        fecha_fin_date = fecha_fin.date()
    else:
        fecha_fin_date = fecha_fin
    
    # Convertir a strings para las consultas
    fecha_inicio_str = fecha_inicio_date.strftime('%Y-%m-%d')
    fecha_fin_str = fecha_fin_date.strftime('%Y-%m-%d')
    
    # Decisión: SQLite vs API XM
    if fecha_inicio_date >= FECHA_LIMITE_SQLITE:
        # CASO 1: Datos recientes (>= 2020) - Usar SQLite (rápido)
        logger.info(f"📊 [SQLite] Consultando {metric}/{entity} desde {fecha_inicio_str} hasta {fecha_fin_str}")
        
        df = db_manager.get_metric_data(
            metrica=metric,
            entidad=entity,
            fecha_inicio=fecha_inicio_str,
            fecha_fin=fecha_fin_str,
            recurso=recurso
        )
        
        if df is not None and not df.empty:
            # Renombrar columnas para compatibilidad con código existente
            # SQLite: fecha, metrica, entidad, recurso, valor_gwh, unidad
            # API XM: Date, Name, Value, Id
            
            if 'valor_gwh' in df.columns:
                df = df.rename(columns={'valor_gwh': 'Value'})
            
            if 'fecha' in df.columns:
                df = df.rename(columns={'fecha': 'Date'})
            
            # MAPEO DE CÓDIGOS A NOMBRES usando tabla catalogos
            if 'recurso' in df.columns:
                # Intentar mapear códigos a nombres desde catálogos
                catalogo_nombre = None
                if entity == 'Recurso':
                    catalogo_nombre = 'ListadoRecursos'
                elif entity == 'Embalse':
                    catalogo_nombre = 'ListadoEmbalses'
                elif entity == 'Rio':
                    catalogo_nombre = 'ListadoRios'
                elif entity == 'Agente':
                    catalogo_nombre = 'ListadoAgentes'
                
                if catalogo_nombre:
                    try:
                        # Obtener mapeo código → nombre
                        mapeo = db_manager.get_mapeo_codigos(catalogo_nombre)
                        if mapeo:
                            # Aplicar mapeo: si el código existe en catálogo, usar nombre; si no, mantener código
                            df['Name'] = df['recurso'].apply(lambda x: mapeo.get(str(x).upper(), x) if pd.notna(x) else x)
                            logger.info(f"✅ [Mapeo] {len(mapeo)} códigos mapeados desde {catalogo_nombre}")
                        else:
                            # Sin mapeo, usar código tal cual
                            df['Name'] = df['recurso']
                            logger.warning(f"⚠️ [Mapeo] {catalogo_nombre} vacío, usando códigos directamente")
                    except Exception as e:
                        logger.warning(f"⚠️ [Mapeo] Error obteniendo {catalogo_nombre}: {e}")
                        df['Name'] = df['recurso']
                else:
                    # Sin catálogo, renombrar directamente
                    df['Name'] = df['recurso']
                
                # Crear alias según entidad (para compatibilidad legacy)
                if entity == 'Embalse' and 'Name' in df.columns:
                    df['Embalse'] = df['Name']
                elif entity == 'Rio' and 'Name' in df.columns:
                    df['Rio'] = df['Name']
                elif entity == 'Recurso' and 'Name' in df.columns:
                    df['Resources'] = df['Name']
                elif entity == 'Agente' and 'Name' in df.columns:
                    df['Agente'] = df['Name']
            
            # VERIFICAR: Si todos los valores de Name son None, usar API como fallback
            if 'Name' in df.columns and df['Name'].isna().all():
                logger.warning(f"⚠️ [SQLite] Columna 'Name' vacía, fallback a API XM")
                # No retornar estos datos vacíos, dejar que consulte API
                df = None
            
            if df is not None:
                logger.info(f"✅ [SQLite] {len(df)} registros obtenidos con nombres mapeados")
                return df, None  # Sin advertencia
        
        # Si no hay datos en SQLite o están incompletos, usar API XM
        logger.info(f"📡 [Fallback] Consultando API XM para {metric}/{entity}")
    
    # CASO 2: Datos históricos (< 2020) o fallback desde SQLite
    mensaje_advertencia = None
    if fecha_inicio_date < FECHA_LIMITE_SQLITE:
        mensaje_advertencia = (
            f"⚠️ **Consultando datos históricos** (antes de 2020) directamente desde API XM. "
            f"Esta operación puede tardar 30-60 segundos..."
        )
        logger.warning(f"🐌 [API XM] Consultando datos históricos {metric}/{entity} desde {fecha_inicio_str}")
    else:
        logger.info(f"📡 [API XM] Fallback desde SQLite, consultando {metric}/{entity}")
    
    try:
        df = fetch_metric_data(
            metric=metric,
            entity=entity,
            start_date=fecha_inicio_str,
            end_date=fecha_fin_str
        )
        
        if df is not None and not df.empty:
            logger.info(f"✅ [API XM] {len(df)} registros obtenidos")
            return df, mensaje_advertencia
        else:
            logger.warning(f"⚠️ [API XM] No hay datos para {metric}/{entity} en el rango solicitado")
            return None, mensaje_advertencia
    
    except Exception as e:
        logger.error(f"❌ [API XM] Error al consultar datos: {e}")
        return None, f"❌ Error al consultar datos: {str(e)}"
