from dash import dcc, html, Input, Output, State, callback, register_page, dash_table
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
from datetime import date, timedelta, datetime
from io import StringIO
import warnings
import traceback
import logging
import sys
from functools import lru_cache
import hashlib
import signal
from contextlib import contextmanager

# Configurar logging para forzar salida
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr,
    force=True
)
logger = logging.getLogger(__name__)

# Use the installed pydataxm package
try:
    from pydataxm.pydataxm import ReadDB
    PYDATAXM_AVAILABLE = True
except ImportError:
    PYDATAXM_AVAILABLE = False
    print("⚠️ pydataxm no está disponible. Algunos datos pueden no cargarse correctamente.")

# Imports locales
from utils.components import crear_header, crear_navbar, crear_sidebar_universal, crear_boton_regresar
from utils.config import COLORS
from utils.utils_xm import fetch_gene_recurso_chunked
from utils._xm import get_objetoAPI, fetch_metric_data, obtener_datos_desde_sqlite, obtener_datos_inteligente
from utils.cache_manager import get_cache_key, get_from_cache, save_to_cache

warnings.filterwarnings("ignore")

def get_plotly_modules():
    """Importar plotly solo cuando se necesite"""
    import plotly.express as px
    import plotly.graph_objects as go
    return px, go

register_page(
    __name__,
    path="/generacion/fuentes",
    name="Generación por Fuente",
    title="Tablero Generación por Fuente - Ministerio de Minas y Energía de Colombia",
    order=6
)

# ============================================
# TIMEOUT HANDLER PARA API XM LENTA
# ============================================
class TimeoutException(Exception):
    pass

@contextmanager
def timeout_handler(seconds):
    """Context manager para timeout en operaciones bloqueantes
    
    Uso:
        try:
            with timeout_handler(10):
                resultado = operacion_lenta()
        except TimeoutException:
            print("Operación excedió timeout de 10 segundos")
    """
    def timeout_signal_handler(signum, frame):
        raise TimeoutException(f"Operación excedió {seconds} segundos")
    
    # Configurar señal de alarma
    old_handler = signal.signal(signal.SIGALRM, timeout_signal_handler)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        # Restaurar handler y cancelar alarma
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

# Mapeo de tipos de fuente
TIPOS_FUENTE = {
    'HIDRAULICA': {'label': 'Hidráulica', 'icon': 'fa-water', 'color': COLORS.get('energia_hidraulica', '#0d6efd')},
    'EOLICA': {'label': 'Eólica', 'icon': 'fa-wind', 'color': COLORS.get('success', '#28a745')},
    'SOLAR': {'label': 'Solar', 'icon': 'fa-sun', 'color': COLORS.get('warning', '#ffc107')},
    'TERMICA': {'label': 'Térmica', 'icon': 'fa-fire', 'color': COLORS.get('danger', '#dc3545')},
    'BIOMASA': {'label': 'Biomasa', 'icon': 'fa-leaf', 'color': COLORS.get('info', '#17a2b8')}
}

def obtener_listado_recursos(tipo_fuente='EOLICA'):
    """Obtener el listado de recursos para un tipo de fuente específico
    
    ARQUITECTURA v3.0 (2025-11-20): USA SQLITE PRIMERO
    - ✅ SQLite tiene catálogos completos (ListadoRecursos: 1,331 recursos)
    - ✅ Instantáneo (0.003s vs 5-10s API)
    - ✅ No depende de API XM (más confiable)
    """
    from utils.db_manager import get_catalogo
    
    import time as time_module
    with open('/home/admonctrlxm/server/logs/timing.log', 'a') as f:
        f.write(f"[{time_module.strftime('%H:%M:%S')}] Obteniendo ListadoRecursos para {tipo_fuente}...\n")
    logger.info(f"🔍 Obteniendo ListadoRecursos desde SQLite ({tipo_fuente})...")
    
    try:
        # PASO 1: Obtener catálogo completo desde SQLite (devuelve DataFrame)
        df_recursos = get_catalogo('ListadoRecursos')
        
        if df_recursos is None or df_recursos.empty:
            print(f"[ERROR] Catálogo ListadoRecursos vacío!", flush=True)
            logger.warning("⚠️ Catálogo ListadoRecursos vacío en SQLite, intentando API...")
            # Fallback a API solo si SQLite falla
            return obtener_listado_recursos_desde_api(tipo_fuente)
        
        with open('/home/admonctrlxm/server/logs/timing.log', 'a') as f:
            f.write(f"[{time_module.strftime('%H:%M:%S')}] SQLite: {len(df_recursos)} recursos\n")
        logger.info(f"✅ SQLite: {len(df_recursos)} recursos obtenidos")
        
        # Renombrar columnas para compatibilidad con código existente
        # SQLite: codigo, nombre, tipo, region, capacidad
        # API: Values_Code, Values_Name, Values_Type, Values_Region
        df_recursos = df_recursos.rename(columns={
            'codigo': 'Values_Code',
            'nombre': 'Values_Name',
            'tipo': 'Values_Type',
            'region': 'Values_Region',
            'capacidad': 'Values_Capacity'
        })
        
        # Filtrar por tipo de fuente
        if tipo_fuente.upper() != 'TODAS':
            df_filtrado = filtrar_por_tipo_fuente(df_recursos, tipo_fuente)
            logger.info(f"✅ Filtrado {tipo_fuente}: {len(df_filtrado)} recursos")
            return df_filtrado
        
        return df_recursos
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo catálogo desde SQLite: {e}")
        # Fallback a API en caso de error
        return obtener_listado_recursos_desde_api(tipo_fuente)


def obtener_listado_recursos_desde_api(tipo_fuente='EOLICA'):
    """Fallback: obtener listado desde API XM (LENTO - solo si SQLite falla)"""
    cache_key = get_cache_key('listado_recursos', tipo_fuente)
    cached_data = get_from_cache(cache_key, allow_expired=False)
    
    if cached_data is not None:
        logger.info(f"✅ Cache HIT: ListadoRecursos ({tipo_fuente}) - {len(cached_data)} plantas")
        return cached_data
    
    try:
        objetoAPI = get_objetoAPI()
        if objetoAPI is None:
            logger.error("❌ API no disponible")
            return pd.DataFrame()
        
        fecha_fin = date.today() - timedelta(days=14)
        fecha_inicio = fecha_fin - timedelta(days=7)
        
        logger.warning(f"⚠️ Consultando ListadoRecursos API ({tipo_fuente}) - LENTO...")
        
        # Usar fetch_metric_data con cache
        recursos = fetch_metric_data("ListadoRecursos", "Sistema", 
                                     fecha_inicio.strftime('%Y-%m-%d'), 
                                     fecha_fin.strftime('%Y-%m-%d'))
        
        if recursos is not None and not recursos.empty:
            logger.info(f"✅ API: {len(recursos)} recursos obtenidos")
            
            # Guardar en cache para futuras consultas
            save_to_cache(cache_key, recursos, cache_type='listado_recursos')
            
            # Filtrar por tipo
            if tipo_fuente.upper() != 'TODAS':
                return filtrar_por_tipo_fuente(recursos, tipo_fuente)
            return recursos
        
        logger.error("❌ API no devolvió datos")
        return pd.DataFrame()
        
    except Exception as e:
        logger.error(f"❌ Error API: {e}")
        return pd.DataFrame()


def filtrar_por_tipo_fuente(df_recursos, tipo_fuente):
    """Filtrar recursos por tipo de fuente energética
    
    Args:
        df_recursos: DataFrame con columna Values_Type
        tipo_fuente: 'HIDRAULICA', 'EOLICA', 'SOLAR', 'TERMICA', 'BIOMASA'
    
    Returns:
        DataFrame filtrado
    """
    if df_recursos.empty or 'Values_Type' not in df_recursos.columns:
        return df_recursos
    
    # TODAS las fuentes
    if tipo_fuente.upper() == 'TODAS':
        return df_recursos
    
    # Buscar con términos alternativos para biomasa
    if tipo_fuente.upper() == 'BIOMASA':
        terminos_biomasa = ['BIOMASA', 'BIOMAS', 'COGENER', 'BAGAZO', 'RESIDUO']
        plantas = pd.DataFrame()
        for termino in terminos_biomasa:
            plantas_temp = df_recursos[
                df_recursos['Values_Type'].str.contains(termino, na=False, case=False)
            ]
            if not plantas_temp.empty:
                plantas = pd.concat([plantas, plantas_temp], ignore_index=True)
        
        if not plantas.empty:
            plantas = plantas.drop_duplicates(subset=['Values_Code'])
            return plantas
        
        logger.warning(f"⚠️ No se encontraron plantas de Biomasa")
        return pd.DataFrame()
    
    # Otros tipos: buscar coincidencia exacta o parcial
    tipo_upper = tipo_fuente.upper()
    plantas = df_recursos[
        df_recursos['Values_Type'].str.contains(tipo_upper, na=False, case=False)
    ]
    
    if plantas.empty:
        logger.warning(f"⚠️ No se encontraron plantas de {tipo_fuente}")
    
    return plantas



# CÓDIGO DEPRECADO - Mantener por compatibilidad pero ya no se usa
def obtener_listado_recursos_OLD(tipo_fuente='EOLICA'):
    """DEPRECADO: Usa API directamente - reemplazado por versión SQLite"""
    logger.warning("⚠️ Usando función DEPRECADA - debería usar SQLite")
    return obtener_listado_recursos_desde_api(tipo_fuente)

def _detectar_columna_sic(recursos_df: pd.DataFrame, f_ini: date, f_fin: date):
    """Detecta la columna que contiene códigos SIC válidos
    
    OPTIMIZADO: Cache persistente por 30 días - la columna SIC no cambia
    Evita 3-5 consultas API de prueba que tardan 10+ segundos
    """
    # CACHE PERSISTENTE: La estructura de columnas no cambia
    cols_hash = hashlib.md5(str(sorted(recursos_df.columns)).encode()).hexdigest()[:8]
    cache_key = get_cache_key('deteccion_columna_sic', cols_hash)
    cached_col = get_from_cache(cache_key, allow_expired=False)
    
    if cached_col is not None:
        # Verificar que la columna siga existiendo
        if cached_col in recursos_df.columns:
            logger.info(f"✅ Cache HIT: Columna SIC = {cached_col}")
            return cached_col
        else:
            logger.warning(f"⚠️ Cache inválido: columna {cached_col} no existe")
    
    objetoAPI = get_objetoAPI()
    if recursos_df is None or recursos_df.empty or objetoAPI is None:
        return None
    
    logger.info("🔍 Detectando columna SIC (consultando API)...")
    candidatos = ['Values_SIC','Values_Sic','Values_ResourceSIC','Values_ResourceCode','Values_Code']
    cols_str = [c for c in recursos_df.columns if recursos_df[c].dtype == 'object']
    orden = [c for c in candidatos if c in recursos_df.columns] + [c for c in cols_str if c not in candidatos]
    
    def muestra(serie: pd.Series):
        vals = (serie.dropna().astype(str).str.strip()
                .loc[lambda s: s.str.match(r'^[A-Z0-9]{3,6}$', na=False)]
                .unique().tolist())
        return vals[:3]
    
    for col in orden:
        cods = muestra(recursos_df[col])
        if len(cods) < 2:
            continue
        try:
            # ✅ OPTIMIZADO: Usar fetch_metric_data con cache
            prueba = fetch_metric_data("Gene", "Recurso", 
                                       f_ini.strftime('%Y-%m-%d'), 
                                       f_fin.strftime('%Y-%m-%d'))
            if prueba is not None and not prueba.empty:
                if 'Values_code' in prueba.columns and prueba['Values_code'].astype(str).isin(cods).any():
                    logger.info(f"✅ Columna SIC detectada: {col}")
                    # GUARDAR EN CACHE PERSISTENTE (30 días)
                    save_to_cache(cache_key, col, cache_type='deteccion_columna')
                    return col
                logger.info(f"✅ Columna SIC detectada (sin Values_code): {col}")
                save_to_cache(cache_key, col, cache_type='deteccion_columna')
                return col
        except Exception as e:
            print(f"Candidata {col} falló: {e}")
            continue
    
    logger.warning("❌ No fue posible detectar columna SIC")
    return None

# Caché manual para obtener_generacion_plantas (usa fechas Y plantas como key)
_cache_generacion = {}

def obtener_generacion_plantas(fecha_inicio, fecha_fin, plantas_df=None, tipo_fuente='TODAS'):
    """Obtener datos de generación por plantas
    
    IMPORTANTE: Implementa caché manual basado en fechas Y plantas para mejorar performance
    Cache key incluye identificador único de las plantas para evitar conflictos entre tipos de fuente
    
    OPTIMIZACIÓN v2: Usa hash MD5 completo de todos los códigos + tipo_fuente para cache robusto
    """
    try:
        objetoAPI = get_objetoAPI()
        if objetoAPI is None or plantas_df is None or plantas_df.empty:
            return pd.DataFrame(), pd.DataFrame()
        
        col_sic = _detectar_columna_sic(plantas_df, fecha_inicio, fecha_fin)
        if not col_sic:
            return pd.DataFrame(), pd.DataFrame()
        
        # Crear identificador único basado en los códigos de plantas
        # Esto asegura que cada tipo de fuente tenga su propio cache
        codigos = (plantas_df[col_sic].dropna().astype(str).str.strip()
                   .loc[lambda s: s.str.match(r'^[A-Z0-9]{3,6}$', na=False)]
                   .unique().tolist())
        
        if not codigos:
            return pd.DataFrame(), pd.DataFrame()
        
        # OPTIMIZACIÓN: Hash MD5 completo de TODOS los códigos (no solo 3)
        # Incluye tipo_fuente para evitar colisiones entre diferentes tipos
        codigos_str = '|'.join(sorted(codigos))
        plantas_hash = hashlib.md5(codigos_str.encode()).hexdigest()[:12]
        cache_key = f"gen_plantas_{fecha_inicio}_{fecha_fin}_{plantas_hash}_{tipo_fuente}"
        
        # Si está en caché, retornar directamente
        if cache_key in _cache_generacion:
            logger.info(f"⚡ Cache HIT: {tipo_fuente} - {fecha_inicio} a {fecha_fin} ({len(codigos)} plantas)")
            return _cache_generacion[cache_key]
        
        df_generacion = fetch_gene_recurso_chunked(objetoAPI, fecha_inicio, fecha_fin, codigos,
                                                   batch_size=50, chunk_days=30)
        
        if df_generacion is None or df_generacion.empty:
            return pd.DataFrame(), pd.DataFrame()
        
        # Incluir nombre de planta y tipo de fuente
        plantas_min = plantas_df[[col_sic, 'Values_Name', 'Values_Type']].drop_duplicates().rename(
            columns={col_sic:'Codigo', 'Values_Name':'Planta', 'Values_Type':'Tipo_Original'})
        df_generacion = df_generacion.merge(plantas_min, on='Codigo', how='left')
        
        # Clasificar tipo de fuente para visualización
        def categorizar_fuente(tipo_original):
            if pd.isna(tipo_original):
                return 'Térmica'
            tipo_str = str(tipo_original).upper()
            if any(x in tipo_str for x in ['HIDRA', 'HIDRO', 'PCH', 'PEQUEÑA']):
                return 'Hidráulica'
            elif any(x in tipo_str for x in ['EOLIC', 'EÓLIC', 'VIENTO']):
                return 'Eólica'
            elif any(x in tipo_str for x in ['SOLAR', 'FOTOVOL', 'FV']):
                return 'Solar'
            elif any(x in tipo_str for x in ['BIOMASA', 'COGENER', 'BAGAZO', 'BIO']):
                return 'Biomasa'
            else:
                return 'Térmica'
        
        df_generacion['Tipo'] = df_generacion['Tipo_Original'].apply(categorizar_fuente)
        
        participacion_total = df_generacion.groupby('Planta', as_index=False)['Generacion_GWh'].sum()
        total = participacion_total['Generacion_GWh'].sum()
        participacion_total['Participacion_%'] = (
            (participacion_total['Generacion_GWh']/total*100).round(2) if total>0 else 0.0
        )
        participacion_total['Estado'] = participacion_total['Participacion_%'].apply(
            lambda x: 'Alto' if x>=15 else ('Medio' if x>=5 else 'Bajo')
        )
        
        # Guardar en caché antes de retornar
        resultado = (df_generacion, participacion_total)
        _cache_generacion[cache_key] = resultado
        logger.info(f"💾 Cache SAVED: {tipo_fuente} - {fecha_inicio} a {fecha_fin} ({len(codigos)} plantas)")
        
        return resultado
    except Exception as e:
        print(f"Error en obtener_generacion_plantas: {e}")
        traceback.print_exc()
        return pd.DataFrame(), pd.DataFrame()


def obtener_generacion_agregada_por_tipo(fecha_inicio, fecha_fin, tipo_fuente='HIDRAULICA'):
    """
    Consulta generación usando SQLite PRIMERO (5 años de datos), luego API si es necesario.
    
    ARQUITECTURA v3.0 (2025-11-19):
    - ✅ SQLite PRIMERO para datos ≥2020 (instantáneo)
    - ✅ API solo para datos <2020 o si SQLite falla
    - ✅ Filtros de fecha funcionan correctamente (5 años disponibles)
    - ✅ Mapeo automático código→nombre usando catálogo
    
    Args:
        fecha_inicio: Fecha inicial (str formato 'YYYY-MM-DD')
        fecha_fin: Fecha final (str formato 'YYYY-MM-DD')
        tipo_fuente: 'HIDRAULICA', 'TERMICA', 'EOLICA', 'SOLAR', 'BIOMASA'
    
    Returns:
        pd.DataFrame con columnas: ['Fecha', 'Generacion_GWh', 'Tipo', 'Codigo', 'Planta']
    """
    from utils.db_manager import get_metric_data
    import time
    
    start_time = time.time()
    
    with open('/home/admonctrlxm/server/logs/timing.log', 'a') as f:
        f.write(f"\n[{time.strftime('%H:%M:%S')}] === Consultando {tipo_fuente} ({fecha_inicio} → {fecha_fin}) ===\n")
    logger.info(f"🚀 Consultando {tipo_fuente} desde {fecha_inicio} hasta {fecha_fin}")
    
    try:
        # ═══════════════════════════════════════════════════════════════
        # PASO 1: OBTENER LISTADO DE RECURSOS PARA FILTRAR POR TIPO
        # ═══════════════════════════════════════════════════════════════
        t1 = time.time()
        listado = obtener_listado_recursos(tipo_fuente)
        with open('/home/admonctrlxm/server/logs/timing.log', 'a') as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] obtener_listado_recursos: {(time.time()-t1)*1000:.0f}ms\n")
        
        if listado.empty:
            logger.warning(f"⚠️ No se encontraron recursos de tipo {tipo_fuente}")
            return pd.DataFrame()
        
        # OPTIMIZACIÓN: Columna de código siempre es 'Values_Code' desde SQLite
        fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        
        col_sic = 'Values_Code'  # Columna conocida desde SQLite (obtener_listado_recursos)
        
        if col_sic not in listado.columns:
            logger.error(f"❌ Columna {col_sic} no encontrada. Columnas disponibles: {list(listado.columns)}")
            return pd.DataFrame()
        
        # Filtrar códigos válidos (patrón 3-6 caracteres alfanuméricos)
        codigos_tipo = (listado[col_sic].dropna().astype(str).str.strip()
                       .loc[lambda s: s.str.match(r'^[A-Z0-9]{3,6}$', na=False)]
                       .unique().tolist())
        
        logger.info(f"📋 {len(codigos_tipo)} códigos de {tipo_fuente} identificados")
        
        if not codigos_tipo:
            logger.warning(f"⚠️ Sin códigos válidos para {tipo_fuente}")
            return pd.DataFrame()
        
        # ═══════════════════════════════════════════════════════════════
        # PASO 2: CONSULTAR SQLITE PRIMERO (5 años de datos instantáneos)
        # ═══════════════════════════════════════════════════════════════
        with open('/home/admonctrlxm/server/logs/timing.log', 'a') as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] Consultando SQLite con {len(codigos_tipo)} códigos...\n")
        logger.info(f"🔍 Consultando SQLite para {tipo_fuente}...")
        
        t2 = time.time()
        df_gene = get_metric_data(
            'Gene',
            'Recurso',
            fecha_inicio,
            fecha_fin,
            recurso_filter=codigos_tipo  # Filtrar solo códigos de este tipo
        )
        with open('/home/admonctrlxm/server/logs/timing.log', 'a') as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] get_metric_data: {(time.time()-t2)*1000:.0f}ms, {len(df_gene) if df_gene is not None else 0} registros\n")
        
        if df_gene is not None and not df_gene.empty:
            logger.info(f"✅ SQLite: {len(df_gene)} registros obtenidos")
            
            # Renombrar columnas de SQLite a formato esperado
            df_gene = df_gene.rename(columns={
                'fecha': 'Fecha',
                'recurso': 'Codigo',
                'valor_gwh': 'Generacion_GWh'
            })
            
            # Agregar información de tipo
            df_gene['Tipo'] = TIPOS_FUENTE.get(tipo_fuente, {}).get('label', tipo_fuente.capitalize())
            df_gene['Tipo_Original'] = tipo_fuente.upper()
            
            # Agregar nombre de planta desde catálogo
            from utils.db_manager import get_mapeo_codigos
            mapeo_nombres = get_mapeo_codigos('ListadoRecursos')
            
            df_gene['Planta'] = df_gene['Codigo'].map(mapeo_nombres).fillna(df_gene['Codigo'])
            
            # Convertir Fecha a datetime si es string
            if df_gene['Fecha'].dtype == 'object':
                df_gene['Fecha'] = pd.to_datetime(df_gene['Fecha'])
            
            resultado = df_gene[['Fecha', 'Generacion_GWh', 'Tipo', 'Codigo', 'Planta', 'Tipo_Original']].copy()
            
            total_gwh = resultado['Generacion_GWh'].sum()
            elapsed = time.time() - start_time
            logger.info(f"✅ {tipo_fuente}: {len(resultado)} registros, Total: {total_gwh:.2f} GWh en {elapsed:.2f}s")
            
            return resultado
        
        # ═══════════════════════════════════════════════════════════════
        # PASO 3: FALLBACK A API (solo si SQLite no tiene datos)
        # ═══════════════════════════════════════════════════════════════
        logger.warning(f"⚠️ SQLite sin datos para {tipo_fuente}, intentando API...")
        
        objetoAPI = get_objetoAPI()
        if not objetoAPI:
            logger.error("❌ API XM no disponible y SQLite sin datos")
            return pd.DataFrame()
        
        from utils.utils_xm import fetch_gene_recurso_chunked
        
        logger.info(f"🔄 Consultando API con chunking...")
        df_gene = fetch_gene_recurso_chunked(
            objetoAPI,
            fecha_inicio_dt,
            fecha_fin_dt,
            codigos_tipo,
            batch_size=50,
            chunk_days=30
        )
        
        if df_gene is None or df_gene.empty:
            logger.error(f"❌ API sin datos para {tipo_fuente}")
            return pd.DataFrame()
        
        logger.info(f"✅ API: {len(df_gene)} registros obtenidos")
        
        # Agregar información de tipo
        df_gene['Tipo'] = TIPOS_FUENTE.get(tipo_fuente, {}).get('label', tipo_fuente.capitalize())
        df_gene['Tipo_Original'] = tipo_fuente.upper()
        
        # Agregar nombre de planta desde listado
        plantas_info = listado[[col_sic, 'Values_Name']].drop_duplicates()
        plantas_info.columns = ['Codigo', 'Planta']
        df_gene = df_gene.merge(plantas_info, on='Codigo', how='left')
        df_gene['Planta'] = df_gene['Planta'].fillna(df_gene['Codigo'])
        
        # Renombrar columnas
        df_gene.rename(columns={'Date': 'Fecha', 'Value_GWh': 'Generacion_GWh'}, inplace=True)
        
        resultado = df_gene[['Fecha', 'Generacion_GWh', 'Tipo', 'Codigo', 'Planta', 'Tipo_Original']].copy()
        
        total_gwh = resultado['Generacion_GWh'].sum()
        elapsed = time.time() - start_time
        logger.info(f"✅ {tipo_fuente}: {len(resultado)} registros, Total: {total_gwh:.2f} GWh en {elapsed:.2f}s")
        
        return resultado
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo generación de {tipo_fuente}: {e}")
        traceback.print_exc()
        
        # En caso de error, intentar retornar cache antiguo
        cached_data = get_from_cache(cache_key, allow_expired=True, max_age_days=30)
        if cached_data is not None:
            logger.warning(f"⚠️ Usando cache antiguo (por error) para {tipo_fuente}")
            return cached_data
        
        return pd.DataFrame()


def crear_grafica_temporal_negra(df_generacion, planta_seleccionada=None, tipo_fuente='EOLICA'):
    """Gráfica temporal con línea nacional, barras apiladas y áreas por tipo de fuente"""
    px, go = get_plotly_modules()
    from plotly.subplots import make_subplots
    
    if df_generacion.empty:
        return go.Figure().add_annotation(
            text="No hay datos disponibles",
            xref="paper", yref="paper", x=0.5, y=0.5
        )
    
    # Clasificar por tipo de fuente
    def categorizar_fuente(codigo):
        codigo_str = str(codigo).upper()
        if any(x in codigo_str for x in ['H', 'PCH', 'HIDRA']):
            return 'Hidráulica'
        elif 'E' in codigo_str or 'EOL' in codigo_str:
            return 'Eólica'
        elif 'S' in codigo_str or 'SOL' in codigo_str or 'FV' in codigo_str:
            return 'Solar'
        elif 'B' in codigo_str or 'COG' in codigo_str or 'BIO' in codigo_str:
            return 'Biomasa'
        else:
            return 'Térmica'
    
    # Si no tiene columna 'Tipo', crearla
    if 'Tipo' not in df_generacion.columns:
        df_generacion['Tipo'] = df_generacion['Codigo'].apply(categorizar_fuente)
    
    # Colores para cada tipo de fuente
    colores_fuente = {
        'Hidráulica': '#1f77b4',    # Azul
        'Térmica': '#ff7f0e',       # Naranja
        'Eólica': '#2ca02c',        # Verde
        'Solar': '#ffbb33',         # Amarillo
        'Biomasa': '#17becf',       # Cian
    }
    
    # **OPTIMIZACIÓN: Agregar datos inteligentemente según el período**
    # Calcular días del período
    if not df_generacion.empty and 'Fecha' in df_generacion.columns:
        df_generacion['Fecha'] = pd.to_datetime(df_generacion['Fecha'])
        fecha_min = df_generacion['Fecha'].min()
        fecha_max = df_generacion['Fecha'].max()
        dias_periodo = (fecha_max - fecha_min).days
        
        # Aplicar agregación inteligente
        df_generacion = agregar_datos_inteligente(df_generacion, dias_periodo)
    
    # Agrupar por fecha y calcular totales
    df_por_fecha = df_generacion.groupby('Fecha', as_index=False)['Generacion_GWh'].sum().sort_values('Fecha')

    # Determinar columna de agrupación
    # Siempre agrupar por 'Tipo' para mostrar fuentes en barras apiladas
    grouping_col = 'Tipo'

    df_por_fuente = df_generacion.groupby(['Fecha', grouping_col], as_index=False)['Generacion_GWh'].sum().sort_values('Fecha')

    # Calcular porcentaje de participación
    df_por_fuente = df_por_fuente.merge(df_por_fecha[['Fecha', 'Generacion_GWh']], on='Fecha', suffixes=('', '_Total'))
    df_por_fuente['Participacion_%'] = (df_por_fuente['Generacion_GWh'] / df_por_fuente['Generacion_GWh_Total']) * 100

    # Ordenar categorías (Tipos o Plantas) por generación total (mayor a menor)
    generacion_por_categoria = df_generacion.groupby(grouping_col)['Generacion_GWh'].sum().sort_values(ascending=False)
    tipos_ordenados = generacion_por_categoria.index.tolist()

    # Datos para torta (última fecha)
    ultima_fecha = df_por_fecha['Fecha'].max()
    df_torta = df_por_fuente[df_por_fuente['Fecha'] == ultima_fecha].sort_values('Participacion_%', ascending=False)

    # Crear subplots: 2 filas, 1 col (SIN TORTA - ahora es independiente)
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(
            'Generación por Fuente (Barras Apiladas - GWh)' if grouping_col == 'Tipo' else 'Generación por Planta (Barras Apiladas - GWh)',
            'Participación por Fuente (%)' if grouping_col == 'Tipo' else 'Participación por Planta (%)'
        ),
        vertical_spacing=0.12
    )

    # Preparar paleta de colores - siempre usar colores predefinidos para tipos de fuente
    colores_categoria = colores_fuente

    # --- GRÁFICA 1: BARRAS APILADAS (GWh) ---
    for cat in tipos_ordenados:
        df_cat = df_por_fuente[df_por_fuente[grouping_col] == cat]
        if not df_cat.empty:
            fig.add_trace(
                go.Bar(
                    x=df_cat['Fecha'],
                    y=df_cat['Generacion_GWh'],
                    name=str(cat),
                    marker_color=colores_categoria.get(cat, '#666'),
                    hovertemplate=f'<b>{cat}</b><br>Fecha: %{{x}}<br>Generación: %{{y:.2f}} GWh<extra></extra>',
                    legendgroup=str(cat),
                    showlegend=True
                ),
                row=1, col=1
            )

    # Línea negra de total en gráfica 1
    fig.add_trace(
        go.Scatter(
            x=df_por_fecha['Fecha'],
            y=df_por_fecha['Generacion_GWh'],
            mode='lines',
            name='Total Nacional',
            line=dict(color='black', width=2),
            hovertemplate='<b>Total Nacional</b><br>Fecha: %{x}<br>Generación: %{y:.2f} GWh<extra></extra>',
            legendgroup='total',
            showlegend=True
        ),
        row=1, col=1
    )

    # --- GRÁFICA 2: BARRAS APILADAS (PORCENTAJE) ---
    for cat in tipos_ordenados:
        df_cat = df_por_fuente[df_por_fuente[grouping_col] == cat]
        if not df_cat.empty:
            fig.add_trace(
                go.Bar(
                    x=df_cat['Fecha'],
                    y=df_cat['Participacion_%'],
                    name=str(cat),
                    marker_color=colores_categoria.get(cat, '#666'),
                    hovertemplate=f'<b>{cat}</b><br>Fecha: %{{x}}<br>Participación: %{{y:.2f}}%<extra></extra>',
                    legendgroup=str(cat),
                    showlegend=False
                ),
                row=2, col=1
            )

    # Línea de 100% en gráfica 2
    fig.add_trace(
        go.Scatter(
            x=df_por_fecha['Fecha'],
            y=[100] * len(df_por_fecha),
            mode='lines',
            name='Total (100%)',
            line=dict(color='black', width=2, dash='dash'),
            hovertemplate='<b>Total</b><br>Fecha: %{x}<br>Participación: 100%<extra></extra>',
            legendgroup='total',
            showlegend=False
        ),
        row=2, col=1
    )
    
    # Configurar layout
    fig.update_layout(
        height=700,
        hovermode='x unified',
        template='plotly_white',
        barmode='stack',  # Siempre barras apiladas
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Títulos de ejes
    fig.update_xaxes(title_text="Fecha", row=2, col=1)
    fig.update_yaxes(title_text="Generación (GWh)", row=1, col=1)
    fig.update_yaxes(title_text="Participación (%)", row=2, col=1)
    
    return fig

def crear_grafica_torta_fuentes(df_por_fuente, fecha_seleccionada, grouping_col, tipo_fuente):
    """Crea gráfica de torta para una fecha específica"""
    px, go = get_plotly_modules()
    
    if df_por_fuente.empty:
        return go.Figure().add_annotation(
            text="No hay datos disponibles",
            xref="paper", yref="paper", x=0.5, y=0.5
        )
    
    # Colores para cada tipo de fuente
    colores_fuente = {
        'Hidráulica': '#1f77b4',
        'Térmica': '#ff7f0e',
        'Eólica': '#2ca02c',
        'Solar': '#ffbb33',
        'Biomasa': '#17becf',
    }
    
    # Filtrar datos para la fecha seleccionada
    # Normalizar ambas fechas al primer día del mes para comparación
    df_por_fuente_copy = df_por_fuente.copy()
    
    # Convertir fecha seleccionada a datetime para normalización
    if isinstance(fecha_seleccionada, str):
        fecha_sel_dt = pd.to_datetime(fecha_seleccionada)
    elif isinstance(fecha_seleccionada, date) and not isinstance(fecha_seleccionada, datetime):
        fecha_sel_dt = pd.Timestamp(fecha_seleccionada)
    else:
        fecha_sel_dt = pd.to_datetime(fecha_seleccionada)
    
    # Obtener año y mes de la fecha seleccionada
    year_sel = fecha_sel_dt.year
    month_sel = fecha_sel_dt.month
    
    # Convertir fechas del DataFrame a datetime si no lo son
    if 'Fecha' in df_por_fuente_copy.columns:
        df_por_fuente_copy['Fecha'] = pd.to_datetime(df_por_fuente_copy['Fecha'])
        # Agregar columnas de año y mes para comparación
        df_por_fuente_copy['Year'] = df_por_fuente_copy['Fecha'].dt.year
        df_por_fuente_copy['Month'] = df_por_fuente_copy['Fecha'].dt.month
    
    # Filtrar por año y mes (más robusto que comparar fechas exactas)
    df_torta = df_por_fuente_copy[
        (df_por_fuente_copy['Year'] == year_sel) & 
        (df_por_fuente_copy['Month'] == month_sel)
    ].sort_values('Participacion_%', ascending=False)
    
    if df_torta.empty:
        logger.warning(f"No hay datos para {year_sel}/{month_sel:02d}")
        return go.Figure().add_annotation(
            text=f"No hay datos para {fecha_sel_dt.strftime('%m/%Y')}",
            xref="paper", yref="paper", x=0.5, y=0.5
        )
    
    # Preparar colores
    if grouping_col == 'Tipo':
        colores_categoria = colores_fuente
    else:
        try:
            palette = px.colors.qualitative.Plotly
        except Exception:
            palette = ['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3', '#FF6692']
        generacion_por_categoria = df_torta.sort_values('Generacion_GWh', ascending=False)
        categorias = generacion_por_categoria[grouping_col].tolist()
        colores_categoria = {cat: palette[i % len(palette)] for i, cat in enumerate(categorias)}
    
    # Crear figura de torta
    fig = go.Figure()
    fig.add_trace(
        go.Pie(
            labels=df_torta[grouping_col],
            values=df_torta['Participacion_%'],
            marker=dict(colors=[colores_categoria.get(cat, '#666') for cat in df_torta[grouping_col]]),
            textposition='inside',
            textinfo='label+percent',
            hovertemplate='<b>%{label}</b><br>Participación: %{value:.2f}%<extra></extra>'
        )
    )
    
    fig.update_layout(
        height=400,
        template='plotly_white',
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.05
        )
    )
    
    return fig


def crear_tabla_participacion(df_participacion):
    """Crear tabla de participación por planta con paginación estilo XM"""
    if df_participacion.empty:
        return html.P("No hay datos de participación", className="text-muted")
    
    # Ordenar por generación descendente
    df_sorted = df_participacion.sort_values('Generacion_GWh', ascending=False).reset_index(drop=True)
    
    # Calcular totales
    total_generacion = df_sorted['Generacion_GWh'].sum()
    total_participacion = df_sorted['Participacion_%'].sum()
    
    # Formatear columnas para mostrar
    df_display = df_sorted.copy()
    df_display['Generación (GWh)'] = df_display['Generacion_GWh'].apply(lambda x: f"{x:.2f}")
    df_display['Participación (%)'] = df_display['Participacion_%'].apply(lambda x: f"{x:.2f}%")
    
    # Seleccionar columnas finales (sin columna Tipo, solo Fuente)
    columnas_mostrar = ['Planta', 'Fuente', 'Generación (GWh)', 'Participación (%)']
    df_display = df_display[columnas_mostrar]
    
    # Crear DataTable con paginación
    tabla = html.Div([
        dash_table.DataTable(
            data=df_display.to_dict('records'),
            columns=[{"name": col, "id": col} for col in columnas_mostrar],
            
            # PAGINACIÓN - 10 filas por página
            page_size=10,
            page_action='native',
            page_current=0,
            
            # ESTILO de tabla
            style_table={
                'overflowX': 'auto',
                'maxHeight': '500px',  # Altura fija como XM
                'border': '1px solid #dee2e6'
            },
            
            # ESTILO de celdas
            style_cell={
                'textAlign': 'left',
                'padding': '10px',
                'fontFamily': 'Arial, sans-serif',
                'fontSize': '13px',
                'border': '1px solid #dee2e6'
            },
            
            # ESTILO de header
            style_header={
                'backgroundColor': '#6c3fb5',  # Morado como XM
                'color': 'white',
                'fontWeight': 'bold',
                'textAlign': 'center',
                'border': '1px solid #5a2f99'
            },
            
            # ESTILO de datos
            style_data={
                'backgroundColor': 'white',
                'color': 'black'
            },
            
            # ESTILO condicional para filas alternas
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': '#f8f9fa'
                },
                {
                    'if': {'column_id': 'Generación (GWh)'},
                    'textAlign': 'right',
                    'fontWeight': '600'
                },
                {
                    'if': {'column_id': 'Participación (%)'},
                    'textAlign': 'right',
                    'fontWeight': '600'
                }
            ],
            
            # CSS para paginación
            css=[{
                'selector': '.previous-next-container',
                'rule': 'display: flex; justify-content: center; margin-top: 10px;'
            }]
        ),
        
        # FILA DE TOTALES (ajustada para 4 columnas: Planta, Fuente, Generación, Participación)
        html.Div([
            dbc.Row([
                dbc.Col([
                    html.Strong("Total", style={'fontSize': '14px'})
                ], width=3),
                dbc.Col([
                    html.Span("")  # Columna vacía para Fuente
                ], width=3),
                dbc.Col([
                    html.Strong(f"{total_generacion:.2f}", 
                              style={'fontSize': '14px', 'textAlign': 'right', 'display': 'block'})
                ], width=3, style={'textAlign': 'right'}),
                dbc.Col([
                    html.Strong("100.00%",
                              style={'fontSize': '14px', 'textAlign': 'right', 'display': 'block'})
                ], width=3, style={'textAlign': 'right'})
            ], className="py-2 px-3", style={
                'backgroundColor': '#f8f9fa',
                'border': '2px solid #6c3fb5',
                'borderTop': '3px solid #6c3fb5',
                'fontWeight': 'bold'
            })
        ], className="mt-0")
    ])
    
    return tabla

# Función para agregar datos inteligentemente según el período
def agregar_datos_inteligente(df_generacion, dias_periodo):
    """
    Agrupa los datos según el período:
    - <= 60 días: datos diarios (sin cambios)
    - 61-180 días: datos semanales
    - > 180 días: datos mensuales
    """
    if df_generacion.empty:
        return df_generacion
    
    # Asegurar que Fecha sea datetime
    df_generacion['Fecha'] = pd.to_datetime(df_generacion['Fecha'])
    
    # Determinar nivel de agregación
    if dias_periodo <= 60:
        # Datos diarios - no cambiar
        return df_generacion
    elif dias_periodo <= 180:
        # Agrupar por semana
        df_generacion['Periodo'] = df_generacion['Fecha'].dt.to_period('W').dt.start_time
        periodo_label = 'Semana'
    else:
        # Agrupar por mes
        df_generacion['Periodo'] = df_generacion['Fecha'].dt.to_period('M').dt.start_time
        periodo_label = 'Mes'
    
    # Agregar datos
    columnas_grupo = ['Periodo']
    if 'Planta' in df_generacion.columns:
        columnas_grupo.append('Planta')
    if 'Codigo' in df_generacion.columns:
        columnas_grupo.append('Codigo')
    if 'Tipo' in df_generacion.columns:
        columnas_grupo.append('Tipo')
    
    df_agregado = df_generacion.groupby(columnas_grupo, as_index=False).agg({
        'Generacion_GWh': 'sum'
    })
    
    # Renombrar Periodo a Fecha
    df_agregado.rename(columns={'Periodo': 'Fecha'}, inplace=True)
    
    print(f"📊 Datos agregados: {len(df_generacion)} registros → {len(df_agregado)} {periodo_label}s")
    
    return df_agregado

# Función para crear fichas de generación renovable/no renovable según métricas XM
def crear_fichas_generacion_xm():
    """Crear fichas con datos reales de generación renovable y no renovable usando métricas oficiales de XM
    
    Metodología (según recomendación del usuario):
    1. Usar ListadoRecursos para identificar código → nombre de planta + tipo de fuente
    2. Con ese código identificado, sumar las 24 horas por cada planta y convertir a GWh (datos en kWh)
    3. Para generación total: sumar todos los tipos de fuente
    4. Para renovable: sumar solo renovables
    5. Para no renovable: sumar solo no renovables
    """
    # Deshabilitada temporalmente: usamos la versión parametrizada con fechas
    fin = date.today() - timedelta(days=3)
    inicio = fin - timedelta(days=365)
    return crear_fichas_generacion_xm_con_fechas(inicio, fin, 'TODAS')
    '''
        print("\n🚀🚀🚀 INICIANDO crear_fichas_generacion_xm()", flush=True)
        objetoAPI = get_objetoAPI()
        if objetoAPI is None:
            return dbc.Alert("API de XM no disponible", color="danger")
        
        print(f"=" * 80)
        print(f"📅 CONSULTANDO DATOS DEL PERÍODO: {fecha_inicio} al {fecha_fin}")
        print(f"=" * 80)
        
        # PASO 1: Obtener ListadoRecursos para mapear códigos (tolerante a fallas)
        print("\n🔍 PASO 1: Obteniendo ListadoRecursos...")
        codigo_info = {}
        try:
            # ✅ OPTIMIZADO: Usar fetch_metric_data con cache
            recursos_df = fetch_metric_data("ListadoRecursos", "Sistema", 
                                            fecha_inicio.strftime('%Y-%m-%d'), 
                                            fecha_fin.strftime('%Y-%m-%d'))
            if recursos_df is not None and not recursos_df.empty:
                print(f"✅ ListadoRecursos obtenidos: {len(recursos_df)} recursos")
                for _, row in recursos_df.iterrows():
                    codigo = str(row.get('Values_Code', row.get('Values_SIC', '')))
                    if codigo:
                        codigo_info[str(codigo).upper()] = {
                            'nombre': str(row.get('Values_Name', row.get('Values_Resource_Name', codigo))),
                            'tipo': str(row.get('Values_Type', row.get('Values_Recurso', 'TERMICA'))).upper()
                        }
                print(f"✅ Mapeo creado: {len(codigo_info)} códigos")
            else:
                print("⚠️ ListadoRecursos vacío; se usará mapeo heurístico por código.")
                recursos_df = pd.DataFrame()
        except Exception as e:
            print(f"⚠️ Error obteniendo ListadoRecursos, continuo con heurística por código: {e}")
            recursos_df = pd.DataFrame()
        
        # PASO 2: Obtener datos de generación Gene/Recurso
        print("\n🔍 PASO 2: Obteniendo Gene/Recurso...")
        df_gene = objetoAPI.request_data("Gene", "Recurso", fecha_inicio, fecha_fin)
        
        if df_gene is None or df_gene.empty:
            return dbc.Alert("No se obtuvieron datos de generación", color="warning")
        
        print(f"✅ Datos obtenidos: {len(df_gene)} registros")
        
        # PASO 3: Sumar las 24 horas por cada planta y convertir a GWh
        print("\n🔍 PASO 3: Procesando datos horarios...")
        horas_cols = [c for c in df_gene.columns if 'Hour' in str(c)]
        
        if not horas_cols:
            return dbc.Alert("No se encontraron columnas horarias en los datos", color="warning")
        
        print(f"✅ Encontradas {len(horas_cols)} columnas horarias")
        
        # Identificar columna de código
        codigo_col = None
        for col in ['Values_code', 'Values_Code', 'Code']:
            if col in df_gene.columns:
                codigo_col = col
                print(f"Columna SIC detectada: {codigo_col}")
                break
        
        if not codigo_col:
            return dbc.Alert("No se encontró columna de código en los datos", color="warning")
        
        # Sumar 24 horas por cada fila (día) y convertir kWh → GWh
        df_gene['Generacion_Dia_GWh'] = df_gene[horas_cols].fillna(0).sum(axis=1) / 1_000_000
        
        # AGRUPAR por código y sumar TODOS LOS DÍAS del período
        df_agrupado = df_gene.groupby(codigo_col).agg({
            'Generacion_Dia_GWh': 'sum'  # Suma de todos los días
        }).reset_index()
        
        print(f"✅ Datos agrupados: {len(df_agrupado)} plantas únicas")
        print(f"   Total generación (todos los días): {df_agrupado['Generacion_Dia_GWh'].sum():.2f} GWh")
        
        # Renombrar para compatibilidad
        df_agrupado.rename(columns={'Generacion_Dia_GWh': 'Generacion_GWh'}, inplace=True)
        df_gene = df_agrupado  # Reemplazar con datos agrupados
        
        # Mapear códigos a nombres y tipos (con fallback heurístico)
        df_gene['Codigo_Upper'] = df_gene[codigo_col].astype(str).str.upper()
        if codigo_info:
            df_gene['Nombre_Planta'] = df_gene['Codigo_Upper'].map(lambda x: codigo_info.get(x, {}).get('nombre', x))
            df_gene['Tipo_Fuente'] = df_gene['Codigo_Upper'].map(lambda x: codigo_info.get(x, {}).get('tipo', 'TERMICA'))
            print(f"✅ Códigos mapeados con ListadoRecursos")
        else:
            # Heurística básica por prefijo/letra del código XM
            def mapear_basico(codigo):
                cs = str(codigo).upper()
                if cs.startswith('H') or 'PCH' in cs:
                    return 'HIDRAULICA'
                if cs.startswith('E'):
                    return 'EOLICA'
                if cs.startswith('S'):
                    return 'SOLAR'
                if cs.startswith('B') or 'COG' in cs:
                    return 'BIOMASA'
                return 'TERMICA'
            df_gene['Nombre_Planta'] = df_gene['Codigo_Upper']
            df_gene['Tipo_Fuente'] = df_gene['Codigo_Upper'].apply(mapear_basico)
            print("✅ Mapeo heurístico aplicado a códigos XM")
        
        print(f"   Tipos encontrados: {sorted(df_gene['Tipo_Fuente'].unique())}")
        
        # FILTRAR POR TIPO DE FUENTE si no es "TODAS"
        if tipo_fuente != 'TODAS':
            print(f"\n🔍 FILTRANDO por tipo de fuente: {tipo_fuente}")
            df_gene = df_gene[df_gene['Tipo_Fuente'] == tipo_fuente]
            print(f"   Registros después del filtro: {len(df_gene)}")
            
            if df_gene.empty:
                return dbc.Alert(f"No hay datos para el tipo de fuente {tipo_fuente} en el período seleccionado", color="warning")
        
        # PASO 4: Clasificar renovable vs no renovable según XM
        print("\n🔍 PASO 4: Clasificando fuentes renovables...")
        
        def es_renovable_xm(tipo):
            """Clasificación oficial XM de fuentes renovables"""
            tipo_str = str(tipo).upper()
            renovables = ['HIDRAULICA', 'HIDRO', 'PCH', 'EOLICA', 'EOLIC', 
                         'SOLAR', 'FOTOVOLTAICA', 'FV', 'BIOMASA', 'COGENERADOR', 
                         'BAGAZO', 'BIOGAS']
            return any(ren in tipo_str for ren in renovables)
        
        df_gene['Es_Renovable'] = df_gene['Tipo_Fuente'].apply(es_renovable_xm)
        
        # PASO 5: Calcular totales
        print("\n🔍 PASO 5: Calculando totales...")
        
        # Calcular totales en GWh - CONVERSIÓN EXPLÍCITA A FLOAT
        gen_total = float(df_gene['Generacion_GWh'].sum())
        gen_renovable = float(df_gene[df_gene['Es_Renovable'] == True]['Generacion_GWh'].sum())
        gen_no_renovable = float(df_gene[df_gene['Es_Renovable'] == False]['Generacion_GWh'].sum())
        
        # Calcular porcentajes - CONVERSIÓN EXPLÍCITA A FLOAT
        pct_renovable = float((gen_renovable / gen_total * 100) if gen_total > 0 else 0)
        pct_no_renovable = float((gen_no_renovable / gen_total * 100) if gen_total > 0 else 0)
        
        print(f"✅ Totales calculados:")
        print(f"   Generación Total: {gen_total:,.2f} GWh (tipo: {type(gen_total).__name__})")
        print(f"   Renovable: {gen_renovable:,.2f} GWh ({pct_renovable:.1f}%) (tipo: {type(gen_renovable).__name__})")
        print(f"   No Renovable: {gen_no_renovable:,.2f} GWh ({pct_no_renovable:.1f}%) (tipo: {type(gen_no_renovable).__name__})")
        
        # Usar fechas del período consultado
        fecha_dato_inicio = fecha_inicio
        fecha_dato_fin = fecha_fin
        
        # DEBUG: Verificar valores antes de crear HTML
        print(f"\n🎨 Creando fichas HTML con valores:")
        print(f"   gen_total = {gen_total} (tipo: {type(gen_total)})")
        print(f"   gen_renovable = {gen_renovable} (tipo: {type(gen_renovable)})")
        print(f"   gen_no_renovable = {gen_no_renovable} (tipo: {type(gen_no_renovable)})")
        print(f"   Período: {fecha_dato_inicio} al {fecha_dato_fin} (30 días)")
        
        # Formatear valores como strings simples y aplicar fallbacks seguros
        def _fmt(v: float) -> str:
            try:
                s = f"{float(v):.1f}"
                # Evitar mostrar 'nan' o valores vacíos
                if s.lower() == 'nan' or s.strip() == '':
                    return '—'
                return s
            except Exception:
                return '—'

        valor_total = _fmt(gen_total)
        valor_renovable = _fmt(gen_renovable)
        valor_no_renovable = _fmt(gen_no_renovable)
        porcentaje_renovable = _fmt(pct_renovable)
        porcentaje_no_renovable = _fmt(pct_no_renovable)
        
        print(f"\n📝 Strings formateados:")
        print(f"   Total: '{valor_total}'")
        print(f"   Renovable: '{valor_renovable}' ({porcentaje_renovable}%)")
        print(f"   No Renovable: '{valor_no_renovable}' ({porcentaje_no_renovable}%)")
        
        # Formatear fechas como string
        fecha_inicio_str = fecha_dato_inicio.strftime('%d/%m/%Y')
        fecha_fin_str = fecha_dato_fin.strftime('%d/%m/%Y')
        periodo_texto = f"{fecha_inicio_str} - {fecha_fin_str}"
        
        # Determinar título según filtro
        if tipo_fuente == 'TODAS':
            titulo_generacion = "Generación Total SIN"
        else:
            titulo_generacion = f"Generación {TIPOS_FUENTE.get(tipo_fuente, {}).get('label', tipo_fuente)}"
        
    # Crear las fichas HTML estilo SinergoX (texto oscuro para asegurar visibilidad)
        return dbc.Row([
            # Ficha Generación Total
                    dbc.CardBody([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.Div(valor_total, style={'fontWeight': 'bold', 'fontSize': '2.5rem', 'color': '#0b1324', 'lineHeight': '1', 'marginBottom': '0.25rem'}),
                            html.Div("GWh", className="text-muted", style={'fontSize': '1.1rem', 'fontWeight': '500', 'marginBottom': '0.25rem'}),
                            html.H2(valor_total, className="mb-1", style={'fontWeight': 'bold', 'fontSize': '2.5rem', 'color': '#111827'}),
                        ], style={'textAlign': 'center', 'color': '#0b1324'})
                            html.Small(periodo_texto, className="text-muted", style={'fontSize': '0.85rem'})
                        'background': '#ffffff',
                        'borderRadius': '12px',
                        'padding': '1.5rem',
                        'minHeight': '180px',
                        'display': 'flex',
                        'alignItems': 'center',
                        'color': '#0b1324'
                        'minHeight': '180px',
                        'display': 'flex',
                        'alignItems': 'center'
                    })
                ], className="h-100 shadow-sm")
            ], lg=4, md=6, className="mb-4"),

            # Ficha Renovable
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-leaf fa-2x mb-3", style={'color': '#0f172a'}),
                            html.H6("Generación Renovable", className="mb-2", style={'fontWeight': '500', 'color': '#111827'}),
                            html.H2(valor_renovable, className="mb-1", style={'fontWeight': 'bold', 'fontSize': '2.5rem', 'color': '#111827'}),
                            html.P("GWh", className="text-muted mb-1", style={'fontSize': '1.1rem', 'fontWeight': '500'}),
                            html.Span(f"{porcentaje_renovable}% del total", 
                                     className="badge", 
                                     style={
                                         'backgroundColor': 'rgba(15, 23, 42, 0.08)', 
                                         'color': '#111827',
                                         'fontSize': '0.9rem',
                                         'padding': '0.4rem 0.8rem',
                                         'borderRadius': '20px'
                                     })
                        ], style={'textAlign': 'center'})
                    ], style={
                        'background': 'linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%)',
                        'borderRadius': '12px',
                        'padding': '1.5rem',
                        'minHeight': '180px',
                        'display': 'flex',
                        'alignItems': 'center'
                    })
                ], className="h-100 shadow-sm")
            ], lg=4, md=6, className="mb-4"),
            
            # Ficha No Renovable
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-industry fa-2x mb-3", style={'color': '#0f172a'}),
                            html.H6("Generación No Renovable", className="mb-2", style={'fontWeight': '500', 'color': '#111827'}),
                            html.H2(valor_no_renovable, className="mb-1", style={'fontWeight': 'bold', 'fontSize': '2.5rem', 'color': '#111827'}),
                            html.P("GWh", className="text-muted mb-2", style={'fontSize': '1.1rem', 'fontWeight': '500'}),
                            html.Span(f"{porcentaje_no_renovable}% del total", 
                                     className="badge",
                                     style={
                                         'backgroundColor': 'rgba(15, 23, 42, 0.08)', 
                                         'color': '#111827',
                                         'fontSize': '0.9rem',
                                         'padding': '0.4rem 0.8rem',
                                         'borderRadius': '20px'
                                     })
                        ], style={'textAlign': 'center', 'color': '#0b1324'})
                    ], style={
                        'background': '#ffffff',
                        'borderRadius': '12px',
                        'padding': '1.5rem',
                        'minHeight': '180px',
                        'display': 'flex',
                        'alignItems': 'center',
                        'color': '#0b1324'
                    })
                ], className="h-100 shadow-sm")
            ], lg=4, md=6, className="mb-4")
        ])
            
    except Exception as e:
        print(f"❌ ERROR en crear_fichas_generacion_xm: {e}")
        import traceback
        traceback.print_exc()
        return dbc.Alert(f"Error al cargar las fichas de generación: {str(e)}", color="danger")

'''
def crear_grafica_barras_apiladas():
    """Crear gráfica de barras apiladas por fuente de energía como en SinergoX"""
    try:
        px, go = get_plotly_modules()
        from utils._xm import fetch_metric_data
        
        fecha_fin = date.today() - timedelta(days=1)
        fecha_inicio = fecha_fin - timedelta(days=30)  # Últimos 30 días
        
        print(f"🔍 Obteniendo datos para gráfica barras: {fecha_inicio} - {fecha_fin}")
        
        df_gene = fetch_metric_data('Gene', 'Recurso', fecha_inicio, fecha_fin)
        
        if df_gene is None or df_gene.empty:
            return go.Figure().add_annotation(
                text="No hay datos disponibles para la gráfica de barras",
                xref="paper", yref="paper", x=0.5, y=0.5
            )
        
        # Procesar datos horarios correctamente
        df_gene['Date'] = pd.to_datetime(df_gene['Date'])
        horas_cols = [c for c in df_gene.columns if str(c).startswith('Values_Hour')]
        
        if not horas_cols:
            return go.Figure().add_annotation(
                text="No se encontraron datos horarios",
                xref="paper", yref="paper", x=0.5, y=0.5
            )
        
        # Calcular generación total diaria por recurso
        df_gene['Generacion_GWh'] = df_gene[horas_cols].fillna(0).sum(axis=1) / 1000
        
        # El mapeo de 'Tipo' ya se hizo en la sección anterior, no necesitamos hacer nada más aquí
        
        # Categorizar fuentes según clasificación oficial XM
        def categorizar_fuente_xm(tipo):
            tipo_str = str(tipo).upper()
            if any(x in tipo_str for x in ['HIDRAULICA', 'HIDRO', 'PCH', 'PEQUEÑA CENTRAL']):
                return 'Hidráulica'
            elif any(x in tipo_str for x in ['EOLICA', 'EOLIC', 'WIND', 'VIENTO']):
                return 'Eólica'
            elif any(x in tipo_str for x in ['SOLAR', 'FOTOVOLTAICA', 'PHOTOVOLTAIC', 'FV']):
                return 'Solar'
            elif any(x in tipo_str for x in ['TERMICA', 'TERMO', 'GAS', 'CARBON', 'CICLO COMBINADO', 'VAPOR']):
                return 'Térmica'
            elif any(x in tipo_str for x in ['BIOMASA', 'COGENER', 'BAGAZO', 'BIOGAS', 'BIO']):
                return 'Biomasa'
            else:
                return 'Otras'
        
        # Obtener ListadoRecursos para mapear tipos
        objetoAPI = get_objetoAPI()
        if objetoAPI:
            try:
                # ✅ OPTIMIZADO: Usar fetch_metric_data con cache
                recursos_df = fetch_metric_data("ListadoRecursos", "Sistema", 
                                                fecha_inicio.strftime('%Y-%m-%d'), 
                                                fecha_fin.strftime('%Y-%m-%d'))
                if recursos_df is not None and not recursos_df.empty:
                    codigo_tipo = {}
                    for _, row in recursos_df.iterrows():
                        codigo = str(row.get('Values_Code', ''))
                        tipo = str(row.get('Values_Type', 'TERMICA')).upper()
                        if codigo:
                            codigo_tipo[codigo.upper()] = tipo
                    
                    codigo_col = None
                    for col in ['Values_code', 'Values_Code', 'Code']:
                        if col in df_gene.columns:
                            codigo_col = col
                            break
                    
                    if codigo_col:
                        df_gene['Tipo'] = df_gene[codigo_col].astype(str).str.upper().map(codigo_tipo).fillna('TERMICA')
                    else:
                        df_gene['Tipo'] = 'TERMICA'
                else:
                    df_gene['Tipo'] = 'TERMICA'
            except Exception as e:
                print(f"Error obteniendo ListadoRecursos: {e}")
                df_gene['Tipo'] = 'TERMICA'
        else:
            df_gene['Tipo'] = 'TERMICA'
        
        df_gene['Fuente'] = df_gene['Tipo'].apply(categorizar_fuente_xm)
        
        # Agrupar por fecha y fuente
        df_agrupado = df_gene.groupby(['Date', 'Fuente'], as_index=False)['Generacion_GWh'].sum()
        
        # Colores oficiales tipo SinergoX
        colores_xm = {
            'Hidráulica': '#1f77b4',    # Azul
            'Térmica': '#ff7f0e',       # Naranja
            'Eólica': '#2ca02c',        # Verde
            'Solar': '#ffbb33',         # Amarillo
            'Biomasa': '#17becf',       # Cian
            'Otras': '#7f7f7f'          # Gris
        }
        
        # Crear gráfica de barras apiladas
        fig = px.bar(
            df_agrupado, 
            x='Date', 
            y='Generacion_GWh', 
            color='Fuente',
            title="Generación Diaria por Fuente de Energía (SIN)",
            labels={'Generacion_GWh': 'Generación (GWh)', 'Date': 'Fecha', 'Fuente': 'Tipo de Fuente'},
            color_discrete_map=colores_xm,
            hover_data={'Generacion_GWh': ':.2f'}
        )
        
        # Personalizar hover template para mostrar información detallada
        fig.update_traces(
            hovertemplate='<b>%{fullData.name}</b><br>' +
                         'Fecha: %{x|%d/%m/%Y}<br>' +
                         'Generación: %{y:.2f} GWh<br>' +
                         'Fuente de Energía: %{fullData.name}<br>' +
                         '<extra></extra>'
        )
        
        fig.update_layout(
            hovermode='x unified',
            template='plotly_white',
            height=450,
            showlegend=True,
            xaxis_title="Fecha",
            yaxis_title="Generación (GWh)",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        return fig
        
    except Exception as e:
        print(f"Error creando gráfica barras apiladas: {e}")
        return go.Figure().add_annotation(
            text=f"Error: {str(e)}",
            xref="paper", yref="paper", x=0.5, y=0.5
        )

def crear_grafica_area():
    """Crear gráfica de área temporal por fuente como en SinergoX"""
    try:
        px, go = get_plotly_modules()
        from utils._xm import fetch_metric_data
        
        fecha_fin = date.today() - timedelta(days=1)
        fecha_inicio = fecha_fin - timedelta(days=7)  # Últimos 7 días para mejor visualización horaria
        
        print(f"🔍 Obteniendo datos para gráfica área: {fecha_inicio} - {fecha_fin}")
        
        df_gene = fetch_metric_data('Gene', 'Recurso', fecha_inicio, fecha_fin)
        
        if df_gene is None or df_gene.empty:
            return go.Figure().add_annotation(
                text="No hay datos disponibles para la gráfica de área",
                xref="paper", yref="paper", x=0.5, y=0.5
            )
        
        # Procesar datos horarios correctamente
        df_gene['Date'] = pd.to_datetime(df_gene['Date'])
        
        # Mapear códigos XM a tipos de fuente usando listado de recursos
        try:
            recursos_df = obtener_listado_recursos()
            if recursos_df is not None and not recursos_df.empty:
                codigo_tipo_map = {}
                for _, row in recursos_df.iterrows():
                    codigo = row.get('Values_Code', row.get('Values_SIC', ''))
                    tipo = row.get('Values_Type', row.get('Values_Recurso', 'TERMICA'))
                    if codigo and tipo:
                        codigo_tipo_map[str(codigo).upper()] = str(tipo).upper()
                
                df_gene['Tipo'] = df_gene['Values_code'].map(
                    lambda x: codigo_tipo_map.get(str(x).upper(), 'TERMICA')
                )
            else:
                # Mapeo básico por código
                def mapear_basico(codigo):
                    codigo_str = str(codigo).upper()
                    if 'H' in codigo_str or 'PCH' in codigo_str:
                        return 'HIDRAULICA'
                    elif 'E' in codigo_str:
                        return 'EOLICA'
                    elif 'S' in codigo_str:
                        return 'SOLAR'
                    elif 'B' in codigo_str:
                        return 'BIOMASA'
                    else:
                        return 'TERMICA'
                
                df_gene['Tipo'] = df_gene['Values_code'].apply(mapear_basico)
                
        except Exception as e:
            print(f"Error mapeando códigos: {e}")
            return go.Figure().add_annotation(
                text="Error procesando códigos de fuente",
                xref="paper", yref="paper", x=0.5, y=0.5
            )
        
        # Expandir datos horarios con mejor procesamiento
        datos_expandidos = []
        horas_cols = [c for c in df_gene.columns if str(c).startswith('Values_Hour')]
        
        for _, row in df_gene.iterrows():
            for col_hora in horas_cols:
                if col_hora in df_gene.columns and not pd.isna(row[col_hora]) and row[col_hora] > 0:
                    # Extraer número de hora del nombre de columna (Values_Hour01, Values_Hour02, etc.)
                    hora_str = col_hora.replace('Values_Hour', '')
                    hora_num = int(hora_str) - 1  # Ajustar índice (01 -> 0, 02 -> 1, etc.)
                    fecha_hora = row['Date'] + timedelta(hours=hora_num)
                    
                    datos_expandidos.append({
                        'Fecha': fecha_hora,
                        'Tipo': row['Tipo'],
                        'Generacion_MW': row[col_hora]
                    })
        
        if not datos_expandidos:
            # Fallback a datos diarios si no hay horarios
            print("No hay datos horarios, usando datos diarios para área")
            df_gene['Generacion_GWh'] = df_gene[horas_cols].fillna(0).sum(axis=1) / 1000 if horas_cols else df_gene.get('Values_gwh', 0)
            
            def categorizar_fuente_xm(tipo):
                tipo_str = str(tipo).upper()
                if any(x in tipo_str for x in ['HIDRAULICA', 'HIDRO', 'PCH']):
                    return 'Hidráulica'
                elif any(x in tipo_str for x in ['EOLICA', 'EOLIC', 'WIND']):
                    return 'Eólica'
                elif any(x in tipo_str for x in ['SOLAR', 'FOTOVOLTAICA', 'FV']):
                    return 'Solar'
                elif any(x in tipo_str for x in ['TERMICA', 'TERMO', 'GAS', 'CARBON']):
                    return 'Térmica'
                elif any(x in tipo_str for x in ['BIOMASA', 'COGENER', 'BAGAZO']):
                    return 'Biomasa'
                else:
                    return 'Otras'
            
            df_gene['Fuente'] = df_gene['Tipo'].apply(categorizar_fuente_xm)
            df_agrupado = df_gene.groupby(['Date', 'Fuente'], as_index=False)['Generacion_GWh'].sum()
            
            # Colores oficiales tipo SinergoX
            colores_xm = {
                'Hidráulica': '#1f77b4',
                'Térmica': '#ff7f0e', 
                'Eólica': '#2ca02c',
                'Solar': '#ffbb33',
                'Biomasa': '#17becf',
                'Otras': '#7f7f7f'
            }
            
            fig = px.area(
                df_agrupado, 
                x='Date', 
                y='Generacion_GWh', 
                color='Fuente',
                title="Evolución Diaria de la Generación por Fuente (SIN)",
                labels={'Generacion_GWh': 'Generación (GWh)', 'Date': 'Fecha'},
                color_discrete_map=colores_xm,
                hover_data={'Generacion_GWh': ':.2f'}
            )
            
            # Personalizar hover template
            fig.update_traces(
                hovertemplate='<b>%{fullData.name}</b><br>' +
                             'Fecha: %{x|%d/%m/%Y}<br>' +
                             'Generación: %{y:.2f} GWh<br>' +
                             'Tipo: Fuente %{fullData.name}<br>' +
                             '<extra></extra>'
            )
        else:
            # Procesar datos horarios expandidos
            df_expandido = pd.DataFrame(datos_expandidos)
            
            # Categorizar fuentes según clasificación oficial XM
            def categorizar_fuente_xm(tipo):
                tipo_str = str(tipo).upper()
                if any(x in tipo_str for x in ['HIDRAULICA', 'HIDRO', 'PCH']):
                    return 'Hidráulica'
                elif any(x in tipo_str for x in ['EOLICA', 'EOLIC', 'WIND']):
                    return 'Eólica'
                elif any(x in tipo_str for x in ['SOLAR', 'FOTOVOLTAICA', 'FV']):
                    return 'Solar'
                elif any(x in tipo_str for x in ['TERMICA', 'TERMO', 'GAS', 'CARBON']):
                    return 'Térmica'
                elif any(x in tipo_str for x in ['BIOMASA', 'COGENER', 'BAGAZO']):
                    return 'Biomasa'
                else:
                    return 'Otras'
            
            df_expandido['Fuente'] = df_expandido['Tipo'].apply(categorizar_fuente_xm)
            df_agrupado = df_expandido.groupby(['Fecha', 'Fuente'], as_index=False)['Generacion_MW'].sum()
            
            # Colores oficiales tipo SinergoX
            colores_xm = {
                'Hidráulica': '#1f77b4',
                'Térmica': '#ff7f0e',
                'Eólica': '#2ca02c',
                'Solar': '#ffbb33',
                'Biomasa': '#17becf',
                'Otras': '#7f7f7f'
            }
            
            fig = px.area(
                df_agrupado, 
                x='Fecha', 
                y='Generacion_MW', 
                color='Fuente',
                title="Evolución Horaria de la Generación por Fuente (SIN) - Últimos 7 días",
                labels={'Generacion_MW': 'Generación (MW)', 'Fecha': 'Fecha y Hora'},
                color_discrete_map=colores_xm,
                hover_data={'Generacion_MW': ':.1f'}
            )
            
            # Personalizar hover template para datos horarios
            fig.update_traces(
                hovertemplate='<b>%{fullData.name}</b><br>' +
                             'Fecha/Hora: %{x|%d/%m/%Y %H:%M}<br>' +
                             'Generación: %{y:.1f} MW<br>' +
                             'Equivalente: %{customdata:.3f} GWh<br>' +
                             '<extra></extra>',
                customdata=df_agrupado['Generacion_MW'] / 1000  # Convertir MW a GWh para mostrar
            )
        
        fig.update_layout(
            hovermode='x unified',
            template='plotly_white',
            height=450,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            xaxis=dict(
                showgrid=True,
                gridcolor='lightgray'
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='lightgray'
            )
        )
        
        return fig
        
    except Exception as e:
        print(f"Error creando gráfica área: {e}")
        return go.Figure().add_annotation(
            text=f"Error: {str(e)}",
            xref="paper", yref="paper", x=0.5, y=0.5
        )

# FUNCIÓN ELIMINADA - causaba errores

def crear_tabla_resumen_todas_plantas_DISABLED(df, fecha_inicio, fecha_fin):
    """Crear tabla de plantas usando el DataFrame ya cargado del período seleccionado"""
    try:
        if df is None or df.empty:
            return html.Div("No hay datos disponibles", className="alert alert-warning")
        
        # Copiar para no modificar el original
        df_tabla = df.copy()
        
        # Validar columnas necesarias
        columnas_requeridas = ['Codigo', 'Planta', 'Generacion_GWh']
        if not all(col in df_tabla.columns for col in columnas_requeridas):
            return html.Div("Datos incompletos para mostrar la tabla", className="alert alert-warning")
        
        # Determinar columnas de agrupación (incluir Tipo si existe)
        cols_agrupacion = ['Codigo', 'Planta']
        if 'Tipo' in df_tabla.columns:
            cols_agrupacion.append('Tipo')
        
        # Agrupar por planta
        df_resumen = df_tabla.groupby(cols_agrupacion, as_index=False).agg({
            'Generacion_GWh': 'sum'
        })
        
        # Filtrar solo plantas con generación > 0
        df_resumen = df_resumen[df_resumen['Generacion_GWh'] > 0]
        
        # Ordenar por generación descendente
        df_resumen = df_resumen.sort_values('Generacion_GWh', ascending=False)
        
        # Calcular participación
        total_generacion = df_resumen['Generacion_GWh'].sum()
        df_resumen['Participacion'] = (df_resumen['Generacion_GWh'] / total_generacion * 100)
        
        # Agregar posición
        df_resumen.insert(0, 'Posición', range(1, len(df_resumen) + 1))
        
        # Renombrar columnas para display
        rename_dict = {
            'Generacion_GWh': 'Generación (GWh)',
            'Participacion': 'Participación (%)'
        }
        if 'Tipo' in df_resumen.columns:
            rename_dict['Tipo'] = 'Fuente'
        
        df_resumen = df_resumen.rename(columns=rename_dict)
        
        # Formatear valores numéricos
        df_resumen['Generación (GWh)'] = df_resumen['Generación (GWh)'].round(2)
        df_resumen['Participación (%)'] = df_resumen['Participación (%)'].round(2)
        
        # Definir colores por fuente
        color_map = {
            'Hidráulica': '#3498db',
            'Térmica': '#e74c3c',
            'Eólica': '#9b59b6',
            'Solar': '#f39c12',
            'Biomasa': '#27ae60'
        }
        
        # Función para aplicar color por fila
        def get_row_style(fuente):
            color = color_map.get(fuente, '#95a5a6')
            return {
                'backgroundColor': f'{color}15',
                'borderLeft': f'4px solid {color}'
            }
        
        # Definir columnas dinámicamente
        columnas_tabla = [
            {'name': 'Posición', 'id': 'Posición'},
            {'name': 'Planta', 'id': 'Planta'}
        ]
        
        # Agregar columna Fuente solo si existe
        if 'Fuente' in df_resumen.columns:
            columnas_tabla.append({'name': 'Fuente', 'id': 'Fuente'})
        
        columnas_tabla.extend([
            {'name': 'Generación (GWh)', 'id': 'Generación (GWh)', 'type': 'numeric', 'format': {'specifier': '.2f'}},
            {'name': 'Participación (%)', 'id': 'Participación (%)', 'type': 'numeric', 'format': {'specifier': '.2f'}}
        ])
        
        # Crear DataTable con estilos modernos
        tabla = dash_table.DataTable(
            data=df_resumen.to_dict('records'),
            columns=columnas_tabla,
            style_table={
                'overflowX': 'auto',
                'borderRadius': '8px',
                'boxShadow': '0 2px 8px rgba(0,0,0,0.1)'
            },
            style_cell={
                'textAlign': 'left',
                'padding': '12px 16px',
                'fontSize': '14px',
                'fontFamily': '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif',
                'border': 'none',
                'borderBottom': '1px solid #e0e0e0'
            },
            style_header={
                'backgroundColor': '#f8f9fa',
                'color': '#2c3e50',
                'fontWeight': '600',
                'textAlign': 'center',
                'border': 'none',
                'borderBottom': '2px solid #dee2e6',
                'padding': '14px 16px'
            },
            style_data_conditional=[
                {
                    'if': {'filter_query': '{Fuente} = "Hidráulica"'},
                    'backgroundColor': f'{color_map["Hidráulica"]}15',
                    'borderLeft': f'4px solid {color_map["Hidráulica"]}'
                },
                {
                    'if': {'filter_query': '{Fuente} = "Térmica"'},
                    'backgroundColor': f'{color_map["Térmica"]}15',
                    'borderLeft': f'4px solid {color_map["Térmica"]}'
                },
                {
                    'if': {'filter_query': '{Fuente} = "Eólica"'},
                    'backgroundColor': f'{color_map["Eólica"]}15',
                    'borderLeft': f'4px solid {color_map["Eólica"]}'
                },
                {
                    'if': {'filter_query': '{Fuente} = "Solar"'},
                    'backgroundColor': f'{color_map["Solar"]}15',
                    'borderLeft': f'4px solid {color_map["Solar"]}'
                },
                {
                    'if': {'filter_query': '{Fuente} = "Biomasa"'},
                    'backgroundColor': f'{color_map["Biomasa"]}15',
                    'borderLeft': f'4px solid {color_map["Biomasa"]}'
                },
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': '#fafafa'
                }
            ],
            page_size=10,
            sort_action='native',
            filter_action='native',
            style_as_list_view=True
        )
        
        # Formatear fechas para el encabezado (pueden venir como string o date)
        from datetime import date as date_type
        if isinstance(fecha_inicio, str):
            fecha_inicio_str = fecha_inicio
        else:
            fecha_inicio_str = fecha_inicio.strftime('%Y-%m-%d')
            
        if isinstance(fecha_fin, str):
            fecha_fin_str = fecha_fin
        else:
            fecha_fin_str = fecha_fin.strftime('%Y-%m-%d')
        
        return html.Div([
            html.P(
                f"Período: {fecha_inicio_str} a {fecha_fin_str} | Total: {total_generacion:.2f} GWh | {len(df_resumen)} plantas",
                className="text-muted text-center mb-3"
            ),
            tabla
        ])
        
    except Exception as e:
        print(f"Error creando tabla desde DataFrame: {e}")
        import traceback
        traceback.print_exc()
        return html.Div(f"Error generando tabla: {str(e)}", className="alert alert-danger")

def crear_tabla_resumen_todas_plantas():
    """Crear tabla resumen con todas las plantas de todas las fuentes (Top 20 por generación)"""
    try:
        from utils._xm import fetch_metric_data
        
        fecha_fin = date.today() - timedelta(days=1)
        fecha_inicio = fecha_fin - timedelta(days=7)  # Últimos 7 días
        
        print(f"🔍 Obteniendo datos para tabla resumen: {fecha_inicio} - {fecha_fin}")
        
        df_gene = fetch_metric_data('Gene', 'Recurso', fecha_inicio, fecha_fin)
        
        if df_gene is None or df_gene.empty:
            return html.Div([
                dbc.Alert("No hay datos disponibles para la tabla de plantas", color="warning", className="text-center")
            ])
        
        # Procesar datos horarios para obtener generación total
        horas_cols = [c for c in df_gene.columns if str(c).startswith('Values_Hour')]
        
        if horas_cols:
            df_gene['Generacion_GWh'] = df_gene[horas_cols].fillna(0).sum(axis=1) / 1000
        else:
            df_gene['Generacion_GWh'] = df_gene.get('Values_gwh', 0)
        
        # Mapear códigos a tipos y obtener nombres de recursos
        try:
            recursos_df = obtener_listado_recursos()
            if recursos_df is not None and not recursos_df.empty:
                # Crear mapeo de código a tipo y nombre
                codigo_info_map = {}
                for _, row in recursos_df.iterrows():
                    codigo = row.get('Values_Code', row.get('Values_SIC', ''))
                    tipo = row.get('Values_Type', row.get('Values_Recurso', 'TERMICA'))
                    nombre = row.get('Values_Name', row.get('Values_Resource_Name', codigo))
                    if codigo:
                        codigo_info_map[str(codigo).upper()] = {
                            'tipo': str(tipo).upper(),
                            'nombre': str(nombre)
                        }
                
                print(f"📊 Mapeo completo creado: {len(codigo_info_map)} recursos")
                
                # Aplicar mapeo
                df_gene['Tipo'] = df_gene['Values_code'].map(
                    lambda x: codigo_info_map.get(str(x).upper(), {}).get('tipo', 'TERMICA')
                )
                df_gene['Nombre_Recurso'] = df_gene['Values_code'].map(
                    lambda x: codigo_info_map.get(str(x).upper(), {}).get('nombre', str(x))
                )
                
                # Agrupar por código/nombre y tipo
                df_plantas = df_gene.groupby(['Nombre_Recurso', 'Tipo'], as_index=False)['Generacion_GWh'].sum()
                df_plantas.columns = ['Planta', 'Tipo', 'Generacion_GWh']
            else:
                print("⚠️ No se pudo obtener información de recursos, usando códigos directamente")
                # Usar códigos como nombres y mapeo básico para tipos
                def mapear_basico(codigo):
                    codigo_str = str(codigo).upper()
                    if 'H' in codigo_str:
                        return 'HIDRAULICA'
                    elif 'E' in codigo_str:
                        return 'EOLICA'
                    elif 'S' in codigo_str:
                        return 'SOLAR'
                    elif 'B' in codigo_str:
                        return 'BIOMASA'
                    else:
                        return 'TERMICA'
                
                df_gene['Tipo'] = df_gene['Values_code'].apply(mapear_basico)
                df_gene['Nombre_Recurso'] = df_gene['Values_code']  # Usar código como nombre
                
                df_plantas = df_gene.groupby(['Nombre_Recurso', 'Tipo'], as_index=False)['Generacion_GWh'].sum()
                df_plantas.columns = ['Planta', 'Tipo', 'Generacion_GWh']
                
        except Exception as e:
            print(f"❌ Error procesando recursos: {e}")
            return html.Div([
                dbc.Alert("Error procesando información de recursos", color="danger")
            ])
        df_plantas = df_plantas[df_plantas['Generacion_GWh'] > 0]  # Solo plantas con generación
        df_plantas = df_plantas.sort_values('Generacion_GWh', ascending=False)
        
        # Calcular participación
        total_gwh = df_plantas['Generacion_GWh'].sum()
        df_plantas['Participacion_%'] = (df_plantas['Generacion_GWh'] / total_gwh * 100).round(2)
        
        # Categorizar fuente usando clasificación oficial XM
        def categorizar_fuente_xm(tipo):
            tipo_str = str(tipo).upper()
            if any(x in tipo_str for x in ['HIDRAULICA', 'HIDRO', 'PCH']):
                return 'Hidráulica'
            elif any(x in tipo_str for x in ['EOLICA', 'EOLIC', 'WIND']):
                return 'Eólica'
            elif any(x in tipo_str for x in ['SOLAR', 'FOTOVOLTAICA', 'FV']):
                return 'Solar'
            elif any(x in tipo_str for x in ['TERMICA', 'TERMO', 'GAS', 'CARBON']):
                return 'Térmica'
            elif any(x in tipo_str for x in ['BIOMASA', 'COGENER', 'BAGAZO']):
                return 'Biomasa'
            else:
                return 'Otras'
        
        df_plantas['Fuente'] = df_plantas['Tipo'].apply(categorizar_fuente_xm)
        
        # Crear tabla estilo SinergoX
        tabla_data = []
        for i, (_, row) in enumerate(df_plantas.head(20).iterrows(), 1):
            tabla_data.append({
                'Posición': i,
                'Planta': row['Planta'],
                'Tipo': row['Tipo'],
                'Fuente': row['Fuente'],
                'Generación (GWh)': f"{row['Generacion_GWh']:,.2f}",
                'Participación (%)': f"{row['Participacion_%']:.2f}%"
            })
        
        # Crear DataTable con estilo mejorado
        from dash import dash_table
        tabla = dash_table.DataTable(
            data=tabla_data,
            columns=[
                {"name": "Pos.", "id": "Posición", "type": "numeric"},
                {"name": "Planta/Recurso", "id": "Planta", "type": "text"},
                {"name": "Tipo", "id": "Tipo", "type": "text"},
                {"name": "Fuente", "id": "Fuente", "type": "text"},
                {"name": "Generación (GWh)", "id": "Generación (GWh)", "type": "numeric"},
                {"name": "Participación (%)", "id": "Participación (%)", "type": "text"}
            ],
            style_cell={
                'textAlign': 'left',
                'fontFamily': 'Arial, sans-serif',
                'fontSize': '0.9rem',
                'padding': '12px 8px',
                'whiteSpace': 'normal',
                'height': 'auto'
            },
            style_header={
                'backgroundColor': '#f8f9fa',
                'fontWeight': 'bold',
                'textAlign': 'center',
                'border': '1px solid #dee2e6'
            },
            style_data={
                'backgroundColor': 'white',
                'border': '1px solid #dee2e6'
            },
            style_data_conditional=[
                {
                    'if': {'filter_query': '{Fuente} = Hidráulica'},
                    'backgroundColor': '#e3f2fd',
                    'color': 'black',
                },
                {
                    'if': {'filter_query': '{Fuente} = Eólica'},
                    'backgroundColor': '#e8f5e8',
                    'color': 'black',
                },
                {
                    'if': {'filter_query': '{Fuente} = Solar'},
                    'backgroundColor': '#fff8e1',
                    'color': 'black',
                },
                {
                    'if': {'filter_query': '{Fuente} = Térmica'},
                    'backgroundColor': '#ffebee',
                    'color': 'black',
                },
                {
                    'if': {'filter_query': '{Fuente} = Biomasa'},
                    'backgroundColor': '#e0f2f1',
                    'color': 'black',
                }
            ],
            sort_action="native",
            page_size=20,
            style_table={'overflowX': 'auto'}
        )
        
        return html.Div([
            html.H5("Top 20 Plantas por Generación - Últimos 7 días", 
                   className="mb-3 text-center text-primary"),
            tabla,
            html.P(f"Total generación período: {total_gwh:,.2f} GWh", 
                  className="text-muted text-center mt-2 small")
        ])
        
    except Exception as e:
        print(f"❌ Error creando tabla resumen: {e}")
        import traceback
        traceback.print_exc()
        return html.Div([
            dbc.Alert(f"Error generando tabla: {str(e)}", color="danger")
        ])

# Layout como función para ejecutar en cada carga
def layout():
    """Layout dinámico que se ejecuta cada vez que se carga la página"""
    print("📄 📄 📄 Generando layout de la página...", flush=True)
    
    return html.Div([
    # Estilos forzados para asegurar visibilidad de números KPI
    html.Link(rel='stylesheet', href='/assets/kpi-override.css'),
    # Interval que se ejecuta UNA VEZ al cargar para disparar callbacks
    # DESACTIVADO: API XM puede estar lenta - carga manual con botón
    # dcc.Interval(id='interval-carga-inicial', interval=500, n_intervals=0, max_intervals=1),
    
    # Store oculto para tracking
    dcc.Store(id='store-pagina-cargada', data={'loaded': True}),
    
    crear_sidebar_universal(),
    
    # Contenido principal
    dbc.Container([
        crear_header(
            "Generación por Fuente",
            "Análisis unificado de generación por tipo de fuente energética"
        ),
        crear_boton_regresar(),
        
        # ==================================================================
        # TABS DE NAVEGACIÓN
        # ==================================================================
        html.Div([
            html.H5("📊 Selecciona el tipo de análisis:", className="mb-3", 
                   style={'color': '#2c3e50', 'fontWeight': '600'}),
            dbc.Tabs(
                id="tabs-generacion-fuentes",
                active_tab="tab-analisis-general",
                children=[
                    dbc.Tab(label="📊 Análisis General", tab_id="tab-analisis-general"),
                    dbc.Tab(label="📅 Comparación Anual", tab_id="tab-comparacion-anual"),
                ]
            )
        ], style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 
                  'marginBottom': '20px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}),
        
        # ==================================================================
        # CONTENIDO TAB: ANÁLISIS GENERAL (contenido original completo)
        # ==================================================================
        html.Div(id='contenido-analisis-general', children=[
        
        # FILTROS PRINCIPALES (El que ya existía y funcionaba)
        dbc.Card([
            dbc.CardHeader([
                html.H5([
                    html.I(className="fas fa-filter me-2"),
                    "Filtros de Análisis"
                ], className="mb-0")
            ]),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Fuentes a Comparar (Multi-selección):", className="fw-bold"),
                        dcc.Dropdown(
                            id='tipo-fuente-dropdown',
                            options=[
                                {'label': '💧 Hidráulica', 'value': 'HIDRAULICA'},
                                {'label': '🔥 Térmica', 'value': 'TERMICA'},
                                {'label': '💨 Eólica', 'value': 'EOLICA'},
                                {'label': '☀️ Solar', 'value': 'SOLAR'},
                                {'label': '🌿 Biomasa/Cogeneración', 'value': 'BIOMASA'},
                            ],
                            value=['HIDRAULICA', 'TERMICA', 'EOLICA', 'SOLAR', 'BIOMASA'],  # Por defecto: TODAS
                            multi=True,  # MULTI-SELECCIÓN ACTIVADA
                            placeholder="Selecciona una o más fuentes...",
                            style={'width': '100%'}
                        ),
                        html.Small(
                            "💡 Selecciona/deselecciona fuentes para filtrar las barras apiladas",
                            className="text-muted d-block mt-1"
                        )
                    ], md=3),
                    dbc.Col([
                        html.Label("Rango de Fechas:", className="fw-bold"),
                        dcc.DatePickerRange(
                            id='date-range-fuentes',
                            start_date=date.today() - timedelta(days=365),
                            end_date=date.today() - timedelta(days=3),
                            display_format='DD/MM/YYYY',
                            style={'width': '100%'}
                        ),
                        html.Small([
                            "⚡ Datos 2020-2025 instantáneos | ",
                            html.Span("Datos antes de 2020 pueden tardar 30-60s", style={'color': '#ff6b6b', 'fontWeight': '500'})
                        ], className="text-muted d-block mt-1")
                    ], md=6),
                    dbc.Col([
                        html.Br(),
                        dbc.Button(
                            [html.I(className="fas fa-sync-alt me-2"), "🔄 Refrescar"],
                            id="btn-actualizar-fuentes",
                            color="secondary",
                            outline=True,
                            className="w-100",
                            size="lg",
                            title="Los datos se cargan automáticamente. Usa este botón solo para refrescar manualmente."
                        )
                    ], md=3)
                ])
            ])
        ], className="mb-4 shadow"),
        
        # DEBUG: Div para verificar clics en botón
        html.Div(id='debug-clicks', style={'display': 'none'}),
        
        # ==================================================================
        # FICHAS DE INDICADORES (Se cargan automáticamente al inicio)
        # ==================================================================
        html.H5("Indicadores Clave del Sistema", 
               className="text-center mb-4 mt-4",
               style={"color": COLORS['text_primary'], "fontWeight": "600"}),
        
        dcc.Loading(
            id="loading-fichas-generacion",
            type="default",
            children=html.Div(
                id='contenedor-fichas-generacion',
                children=[dbc.Alert([
                    html.I(className="fas fa-hand-pointer me-2"),
                    html.Strong("Cargando indicadores..."),
                    html.Br(),
                    html.Small("(Método optimizado Gene Recurso - carga en 10-15 segundos)")
                ], color="warning", className="text-center")]
            )
        ),
        
        # ==================================================================
        # GRÁFICAS Y ANÁLISIS DETALLADO (Ya existente)
        # ==================================================================
        html.Hr(),
        html.H5("Análisis Detallado por Fuente", 
               className="text-center mb-4",
               style={"color": COLORS['text_primary'], "fontWeight": "600"}),
        
        # Contenedor de resultados (gráfica temporal + tabla)
        dcc.Loading(
            id="loading-fuentes",
            type="circle",
            children=html.Div(id="contenido-fuentes", children=[
                dbc.Alert([
                    html.I(className="fas fa-chart-line me-2"),
                    "Cargando gráficas y tablas..."
                ], color="secondary", className="text-center")
            ])
        ),
        
        ]),  # FIN contenido-analisis-general
        
        # ==================================================================
        # CONTENIDO TAB: COMPARACIÓN ANUAL
        # ==================================================================
        html.Div(id='contenido-comparacion-anual', style={'display': 'none'}, children=[
            html.H4("📅 Comparación de Años Completos", className="text-center mb-4",
                   style={'color': '#2c3e50', 'fontWeight': '600'}),
            
            dbc.Row([
                # COLUMNA AÑO 1
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Año 1", style={'backgroundColor': '#007bff', 'color': 'white', 'textAlign': 'center'}),
                        dbc.CardBody([
                            dcc.Dropdown(
                                id='year-1-dropdown',
                                options=[{'label': str(y), 'value': y} for y in [2025, 2024, 2023, 2022]],
                                value=2025,
                                clearable=False
                            ),
                            html.Hr(),
                            html.Div(id='contenido-year-1', children=[
                                dbc.Alert("Selecciona un año y haz clic en actualizar", color="info")
                            ])
                        ])
                    ])
                ], md=6),
                
                # COLUMNA AÑO 2
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Año 2", style={'backgroundColor': '#28a745', 'color': 'white', 'textAlign': 'center'}),
                        dbc.CardBody([
                            dcc.Dropdown(
                                id='year-2-dropdown',
                                options=[{'label': str(y), 'value': y} for y in [2025, 2024, 2023, 2022]],
                                value=2024,
                                clearable=False
                            ),
                            html.Hr(),
                            html.Div(id='contenido-year-2', children=[
                                dbc.Alert("Selecciona un año y haz clic en actualizar", color="info")
                            ])
                        ])
                    ])
                ], md=6),
            ])
        ]),  # FIN contenido-comparacion-anual
        
    ], fluid=True, className="py-4")
    
    ], style={'backgroundColor': COLORS['bg_main'], 'minHeight': '100vh'})
    
# Fin de la función layout() - Las fichas se generan directamente

# ==================================================================
# CALLBACK PRINCIPAL: Cambiar contenido según tab activo
# ==================================================================
@callback(
    [Output('contenido-analisis-general', 'style'),
     Output('contenido-comparacion-anual', 'style')],
    [Input('tabs-generacion-fuentes', 'active_tab')]
)
def cambiar_contenido_tabs(active_tab):
    """Muestra/oculta contenido según el tab seleccionado"""
    if active_tab == 'tab-comparacion-anual':
        return {'display': 'none'}, {'display': 'block'}
    else:  # tab-analisis-general (por defecto)
        return {'display': 'block'}, {'display': 'none'}

# Callbacks para gráficas principales

@callback(
    Output("grafica-barras-apiladas", "figure"),
    Input("grafica-barras-apiladas", "id"),
    prevent_initial_call=True  # ⚡ NO ejecutar al cargar página
)
def cargar_grafica_barras_apiladas(_):
    """Cargar gráfica de barras apiladas - LAZY LOAD"""
    return crear_grafica_barras_apiladas()

@callback(
    [Output('grafica-torta-fuentes', 'figure'),
     Output('titulo-torta-fuentes', 'children')],
    [Input('grafica-temporal-fuentes', 'clickData')],
    [State('store-datos-fuentes', 'data')],
    prevent_initial_call=True
)
def actualizar_torta_por_click(clickData, stored_data):
    """
    Actualiza el gráfico de torta cuando el usuario hace click en una barra del gráfico apilado.
    Muestra la composición por fuente para el día seleccionado.
    """
    print("[DEBUG] Callback actualizar_torta_por_click ejecutado", flush=True)
    print(f"[DEBUG] clickData: {clickData}", flush=True)
    print(f"[DEBUG] stored_data keys: {stored_data.keys() if stored_data else 'None'}", flush=True)
    
    if not clickData or not stored_data:
        print("[ERROR] No hay clickData o stored_data", flush=True)
        raise PreventUpdate
    
    try:
        # Extraer la fecha del click
        fecha_click_str = clickData['points'][0]['x']
        print(f"[DEBUG] Fecha seleccionada: {fecha_click_str}", flush=True)
        fecha_click = pd.to_datetime(fecha_click_str).date()
        
        # Recuperar datos del store
        df_por_fuente = pd.read_json(StringIO(stored_data['df_por_fuente']), orient='split')
        df_por_fuente['Fecha'] = pd.to_datetime(df_por_fuente['Fecha']).dt.date
        grouping_col = stored_data['grouping_col']
        tipo_fuente = stored_data['tipo_fuente']
        
        print(f"[DEBUG] Datos recuperados: {len(df_por_fuente)} registros", flush=True)
        print(f"[DEBUG] Grouping col: {grouping_col}, Tipo fuente: {tipo_fuente}", flush=True)
        
        # Crear nuevo gráfico de torta para la fecha seleccionada
        nueva_figura = crear_grafica_torta_fuentes(df_por_fuente, fecha_click, grouping_col, tipo_fuente)
        
        # Actualizar título con la fecha seleccionada
        nuevo_titulo = f"Composición por Fuente - {fecha_click.strftime('%d/%m/%Y')}"
        
        print(f"[DEBUG] Gráfico actualizado para {fecha_click}", flush=True)
        return nueva_figura, nuevo_titulo
        
    except Exception as e:
        print(f"[ERROR] Error en actualizar_torta_por_click: {e}", flush=True)
        import traceback
        traceback.print_exc()
        raise PreventUpdate


@callback(
    Output("grafica-area", "figure"),
    Input("grafica-area", "id"),
    prevent_initial_call=True  # ⚡ NO ejecutar al cargar página
)
def cargar_grafica_area(_):
    """Cargar gráfica de área - LAZY LOAD"""
    return crear_grafica_area()

@callback(
    Output("tabla-resumen-todas-plantas", "children"),
    Input("tabla-resumen-todas-plantas", "id"),
    prevent_initial_call=True  # ⚡ NO ejecutar al cargar página
)
def cargar_tabla_resumen(_):
    """Cargar tabla resumen de todas las plantas - LAZY LOAD"""
    return crear_tabla_resumen_todas_plantas()

# Callback - CARGA AUTOMÁTICA al cargar página y al cambiar filtros
@callback(
    Output('contenido-fuentes', 'children'),
    [Input('tipo-fuente-dropdown', 'value'),
     Input('date-range-fuentes', 'start_date'),
     Input('date-range-fuentes', 'end_date'),
     Input('btn-actualizar-fuentes', 'n_clicks')],
    prevent_initial_call=False  # ✅ Se ejecuta automáticamente al cargar
)
def actualizar_tablero_fuentes(n_clicks, tipos_fuente, fecha_inicio, fecha_fin):
    debug_file = "/home/admonctrlxm/server/logs/debug_callback.log"
    with open(debug_file, "a") as f:
        f.write(f"\n{'='*80}\n")
        f.write(f"CALLBACK TABLERO EJECUTADO\n")
        f.write(f"n_clicks={n_clicks}, tipos={tipos_fuente}\n")
        f.write(f"fechas={fecha_inicio} → {fecha_fin}\n")
        f.write(f"{'='*80}\n")
    
    logger.info("="*80)
    logger.info("CALLBACK TABLERO EJECUTADO") 
    logger.info(f"n_clicks={n_clicks}, tipos={tipos_fuente}, fechas={fecha_inicio}-{fecha_fin}")
    logger.info("="*80)
    
    # Validar que tipos_fuente sea una lista
    if not tipos_fuente:
        logger.warning("Sin tipos_fuente")
        return dbc.Alert("⚠️ Selecciona al menos una fuente de energía", color="warning", className="text-center")
    
    # Si es string, convertir a lista
    if isinstance(tipos_fuente, str):
        tipos_fuente = [tipos_fuente]
    
    if not fecha_inicio or not fecha_fin:
        return dbc.Alert("Selecciona un rango de fechas válido", color="info")
    
    try:
        # Convertir fechas
        fecha_inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        fecha_fin_dt = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
        
        # Informar sobre rango grande
        total_days = (fecha_fin_dt - fecha_inicio_dt).days
        if total_days > 180:
            logger.warning(f"⚠️ Rango grande: {total_days} días - puede tardar 30-60s")
        
        logger.info(f"📊 Iniciando carga de datos para: {', '.join(tipos_fuente)}")
        
        # ═══════════════════════════════════════════════════════════════
        # OPTIMIZACIÓN: Usar Gene con entidad Recurso (1 llamada = todas las plantas)
        # ═══════════════════════════════════════════════════════════════
        
        todas_fuentes = ['HIDRAULICA', 'TERMICA', 'EOLICA', 'SOLAR', 'BIOMASA']
        df_generacion_completo = pd.DataFrame()
        errores_api = []
        
        logger.info(f"🚀 Usando método optimizado Gene con entidad Recurso")
        logger.info(f"📅 Rango: {fecha_inicio_dt} a {fecha_fin_dt}")
        
        for fuente in todas_fuentes:
            try:
                logger.info(f"🔄 Procesando {fuente}...")
                # Consulta optimizada: 1 llamada API para todas las plantas del tipo
                df_agregado = obtener_generacion_agregada_por_tipo(
                    fecha_inicio_dt.strftime('%Y-%m-%d'),
                    fecha_fin_dt.strftime('%Y-%m-%d'),
                    fuente
                )
                
                logger.info(f"📊 {fuente}: DataFrame con {len(df_agregado)} filas")
                
                if not df_agregado.empty:
                    logger.info(f"🔍 {fuente} - Columnas: {list(df_agregado.columns)}")
                    logger.info(f"🔍 {fuente} - Tipo único: {df_agregado['Tipo'].unique() if 'Tipo' in df_agregado.columns else 'N/A'}")
                    df_generacion_completo = pd.concat([df_generacion_completo, df_agregado], ignore_index=True)
                    logger.info(f"✅ {fuente}: {df_agregado['Generacion_GWh'].sum():.2f} GWh agregados")
                else:
                    errores_api.append(f"{fuente} (sin datos)")
                    logger.warning(f"⚠️ {fuente}: DataFrame vacío")
                    
            except Exception as e:
                errores_api.append(f"{fuente} (error: {str(e)[:30]})")
                logger.error(f"❌ Error {fuente}: {e}", exc_info=True)
                continue
        
        # Validar que se obtuvieron datos
        if df_generacion_completo.empty:
            logger.error(f"❌ TODAS LAS FUENTES DEVOLVIERON VACÍO")
            logger.error(f"Errores: {errores_api}")
            
            return dbc.Alert([
                html.H5("⚠️ No se encontraron datos", className="mb-3"),
                html.P(f"Período: {fecha_inicio} a {fecha_fin}"),
                html.P(f"Fuentes intentadas: {', '.join(todas_fuentes)}"),
                html.Hr(),
                html.H6("Debug - Errores por fuente:"),
                html.Ul([html.Li(err) for err in errores_api])
            ], color="warning")
        
        # FILTRAR solo las fuentes seleccionadas para las gráficas
        # Convertir códigos a labels
        labels_seleccionadas = [TIPOS_FUENTE.get(tf, {}).get('label', tf) for tf in tipos_fuente]
        df_generacion = df_generacion_completo[df_generacion_completo['Tipo'].isin(labels_seleccionadas)].copy()
        
        if df_generacion.empty:
            return dbc.Alert(
                "No se encontraron datos para las fuentes seleccionadas",
                color="warning"
            )
        
        # NOTA: Con datos agregados, no hay dropdown de plantas individuales
        # (las plantas individuales se consultarían solo si el usuario necesita drill-down)
        # El dropdown de plantas fue eliminado en las mejoras del 19/11/2025
        planta_nombre = None
        
        # Preparar datos para gráficas (igual que en crear_grafica_temporal_negra)
        df_generacion_copy = df_generacion.copy()
        df_generacion_copy['Fecha'] = pd.to_datetime(df_generacion_copy['Fecha'])
        
        # Agrupar por fecha
        df_por_fecha = df_generacion_copy.groupby('Fecha', as_index=False)['Generacion_GWh'].sum().sort_values('Fecha')
        
        # Determinar columna de agrupación
        # Siempre agrupar por 'Tipo' cuando hay múltiples fuentes
        grouping_col = 'Tipo'
        
        # Agrupar por fecha y categoría
        df_por_fuente = df_generacion_copy.groupby(['Fecha', grouping_col], as_index=False)['Generacion_GWh'].sum().sort_values('Fecha')
        df_por_fuente = df_por_fuente.merge(df_por_fecha[['Fecha', 'Generacion_GWh']], on='Fecha', suffixes=('', '_Total'))
        df_por_fuente['Participacion_%'] = (df_por_fuente['Generacion_GWh'] / df_por_fuente['Generacion_GWh_Total']) * 100
        
        # Fecha para torta inicial (última fecha)
        ultima_fecha = df_por_fecha['Fecha'].max()
        
        # Preparar datos agregados por planta para la tabla (detalle de todas las plantas)
        df_tabla_plantas = df_generacion_copy.groupby(['Planta', 'Tipo'], as_index=False)['Generacion_GWh'].sum()
        total_generacion_tabla = df_tabla_plantas['Generacion_GWh'].sum()
        df_tabla_plantas['Participacion_%'] = (df_tabla_plantas['Generacion_GWh'] / total_generacion_tabla) * 100
        df_tabla_plantas = df_tabla_plantas.rename(columns={'Tipo': 'Fuente'})  # Renombrar Tipo a Fuente
        df_tabla_plantas['Estado'] = 'Operando'  # Agregar columna Estado
        # Ordenar por generación descendente
        df_tabla_plantas = df_tabla_plantas.sort_values('Generacion_GWh', ascending=False).reset_index(drop=True)
        
        # Crear contenido - título basado en fuentes seleccionadas
        if len(tipos_fuente) == 5:
            # Todas las fuentes seleccionadas
            titulo_tipo = "Todas las Fuentes"
            icono_tipo = "fa-bolt"
            tipo_fuente = 'TODAS'
        elif len(tipos_fuente) == 1:
            # Una sola fuente
            tipo_fuente = tipos_fuente[0]
            if tipo_fuente in TIPOS_FUENTE:
                info_fuente = TIPOS_FUENTE[tipo_fuente]
                titulo_tipo = info_fuente['label']
                icono_tipo = info_fuente['icon']
            else:
                titulo_tipo = "Generación"
                icono_tipo = "fa-bolt"
        else:
            # Múltiples fuentes seleccionadas (pero no todas)
            titulo_tipo = f"Comparativa ({len(tipos_fuente)} fuentes)"
            icono_tipo = "fa-bolt"
            tipo_fuente = 'MULTIPLES'
        
        contenido = [
            # Encabezado con información del tipo de fuente
            dbc.Alert([
                html.I(className=f"fas {icono_tipo} me-2"),
                html.Strong(f"Tipo de Fuente: {titulo_tipo}")
            ], color="light", className="mb-3"),
            
            # Gráficas lado a lado: Temporal (izquierda) y Torta (derecha)
            dbc.Row([
                # Columna izquierda: Gráfica temporal (70% ancho)
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                                html.I(className="fas fa-chart-line me-2"),
                                f"Evolución Temporal - Generación {titulo_tipo}"
                            ], className="mb-0")
                        ]),
                        dbc.CardBody([
                            dcc.Graph(
                                id='grafica-temporal-fuentes',
                                figure=crear_grafica_temporal_negra(df_generacion, planta_nombre, tipo_fuente),
                                config={'displayModeBar': True}
                            )
                        ])
                    ])
                ], width=8, className="mb-4"),
                
                # Columna derecha: Gráfica de torta interactiva (30% ancho)
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                                html.I(className="fas fa-chart-pie me-2"),
                                html.Span("Composición", id='titulo-torta-fuentes'),
                            ], className="mb-0 text-center"),
                            html.Small("Haz clic en las barras →", className="text-muted d-block text-center mt-1")
                        ]),
                        dbc.CardBody([
                            dcc.Graph(
                                id='grafica-torta-fuentes',
                                figure=crear_grafica_torta_fuentes(df_por_fuente, ultima_fecha, grouping_col, tipo_fuente),
                                config={'displayModeBar': True}
                            ),
                            # Store para guardar los datos necesarios para el callback
                            dcc.Store(id='store-datos-fuentes', data={
                                'df_por_fuente': df_por_fuente.to_json(date_format='iso', orient='split'),
                                'grouping_col': grouping_col,
                                'tipo_fuente': tipo_fuente,  # Puede ser string o 'MULTIPLES'
                                'tipos_fuente': tipos_fuente,  # Lista completa de fuentes seleccionadas
                                'ultima_fecha': ultima_fecha.isoformat()
                            })
                        ])
                    ])
                ], width=4, className="mb-4")
            ], className="mb-4"),
            
            # ==================================================================
            # TABLA DE DETALLE POR PLANTA
            # ==================================================================
            html.Hr(),
            dbc.Card([
                dbc.CardHeader([
                    html.H5([
                        html.I(className="fas fa-table me-2"),
                        "Detalle por Planta"
                    ], className="mb-0"),
                    html.Small(
                        f"Período: {fecha_inicio_dt.strftime('%Y-%m-%d')} a {fecha_fin_dt.strftime('%Y-%m-%d')} | Total: {total_generacion_tabla:.2f} GWh | {len(df_tabla_plantas)} plantas",
                        className="text-muted d-block mt-1"
                    )
                ]),
                dbc.CardBody([
                    crear_tabla_participacion(df_tabla_plantas)
                ])
            ], className="mb-4")
        ]
        
        # Verificar si API retornó menos datos de los solicitados
        if not df_por_fecha.empty:
            fecha_datos_min = df_por_fecha['Fecha'].min().date()
            fecha_datos_max = df_por_fecha['Fecha'].max().date()
            dias_solicitados = (fecha_fin_dt - fecha_inicio_dt).days
            dias_recibidos = (fecha_datos_max - fecha_datos_min).days
            
            if dias_recibidos < (dias_solicitados * 0.5):  # Si recibió menos del 50%
                contenido.insert(0, dbc.Alert([
                    html.I(className="fas fa-info-circle me-2"),
                    html.Strong("ℹ️ Datos limitados de la API XM: "),
                    html.Br(),
                    f"Solicitado: {fecha_inicio_dt.strftime('%d/%m/%Y')} - {fecha_fin_dt.strftime('%d/%m/%Y')} ({dias_solicitados} días)",
                    html.Br(),
                    f"Disponible: {fecha_datos_min.strftime('%d/%m/%Y')} - {fecha_datos_max.strftime('%d/%m/%Y')} ({dias_recibidos} días)",
                    html.Br(),
                    html.Small("La API de XM solo proporciona datos recientes. Esto no es un error del dashboard."),
                ], color="info", className="mb-3"))
        
        # Si hubo errores de API, mostrar advertencia
        if errores_api:
            contenido.insert(0, dbc.Alert([
                html.I(className="fas fa-exclamation-triangle me-2"),
                html.Strong("⚠️ Algunas fuentes no se pudieron cargar: "),
                html.Br(),
                html.Small(", ".join(errores_api)),
                html.Br(),
                html.Small("La API de XM está experimentando lentitud o timeouts. Intenta de nuevo en unos minutos.")
            ], color="warning", className="mb-3"))
        
        logger.info(f"✅ Datos cargados exitosamente para {', '.join(tipos_fuente)}")
        return contenido
        
    except TimeoutException as e:
        logger.error(f"⏱️ TIMEOUT GENERAL: {e}")
        return dbc.Alert([
            html.I(className="fas fa-clock me-2"),
            html.Strong("⏱️ La carga de datos excedió el tiempo límite"),
            html.Br(),
            html.Small("La API de XM está extremadamente lenta en este momento. Por favor intenta:"),
            html.Ul([
                html.Li("Reducir el rango de fechas (30-60 días máximo)"),
                html.Li("Seleccionar menos fuentes de energía"),
                html.Li("Intentar de nuevo en 5-10 minutos")
            ], className="mb-0 mt-2")
        ], color="danger", className="text-start")
    
    except Exception as e:
        logger.exception(f"❌ Error en callback: {e}")
        return dbc.Alert([
            html.I(className="fas fa-exclamation-circle me-2"),
            html.Strong(f"❌ Error al procesar los datos"),
            html.Br(),
            html.Small(f"Detalles técnicos: {str(e)[:200]}")
        ], color="danger")


# Callback para cargar fichas - CARGA AUTOMÁTICA al cambiar fechas O hacer clic
@callback(
    Output('contenedor-fichas-generacion', 'children'),
    [Input('date-range-fuentes', 'start_date'),
     Input('date-range-fuentes', 'end_date'),
     Input('btn-actualizar-fuentes', 'n_clicks')],
    [State('tipo-fuente-dropdown', 'value')]
)
def actualizar_fichas_generacion(start_date, end_date, n_clicks, tipo_fuente_seleccionado):
    """Genera las fichas - SIEMPRE muestra TODAS las fuentes (sin filtrar)"""
    
    logger.info(f"� CALLBACK FICHAS EJECUTADO")
    
    # Si no hay valores, mostrar mensaje de espera
    if start_date is None or end_date is None:
        return dbc.Alert("⏳ Inicializando datos...", color="info")
    
    # Convertir fechas de string a date
    fecha_inicio = pd.to_datetime(start_date).date()
    fecha_fin = pd.to_datetime(end_date).date()
    
    try:
        # ═══════════════════════════════════════════════════════════════
        # OPTIMIZACIÓN: Usar Gene con entidad Recurso (1 llamada para todas las plantas)
        # ═══════════════════════════════════════════════════════════════
        
        todas_fuentes = ['HIDRAULICA', 'TERMICA', 'EOLICA', 'SOLAR', 'BIOMASA']
        df_generacion_completo = pd.DataFrame()
        
        logger.info(f"🚀 Generando fichas con método optimizado (Gene Recurso)")
        
        for fuente in todas_fuentes:
            df_agregado = obtener_generacion_agregada_por_tipo(
                fecha_inicio.strftime('%Y-%m-%d'),
                fecha_fin.strftime('%Y-%m-%d'),
                fuente
            )
            if not df_agregado.empty:
                df_generacion_completo = pd.concat([df_generacion_completo, df_agregado], ignore_index=True)
        
        if not df_generacion_completo.empty:
            logger.info(f"⚡ Generando fichas con datos optimizados")
            return crear_fichas_desde_dataframe(df_generacion_completo, fecha_inicio, fecha_fin, 'TODAS')
        
        # Fallback: usar función original si no hay datos
        logger.warning(f"⚠️ Sin datos optimizados, usando método original")
        return crear_fichas_generacion_xm_con_fechas(fecha_inicio, fecha_fin, 'TODAS')
        
    except Exception as e:
        logger.error(f"Error generando fichas: {e}")
        import traceback
        traceback.print_exc()
        return dbc.Alert(f"Error cargando indicadores: {str(e)}", color="danger")


# Caché manual para fichas de generación
_cache_fichas = {}

def crear_fichas_desde_dataframe(df_generacion, fecha_inicio, fecha_fin, tipo_fuente='TODAS'):
    """
    OPTIMIZACIÓN: Crea fichas directamente desde DataFrame ya cargado (sin consultar API)
    
    Args:
        df_generacion: DataFrame con datos de generación ya procesados
        fecha_inicio: Fecha inicial del período
        fecha_fin: Fecha final del período
        tipo_fuente: Tipo de fuente para título
    
    Returns:
        dbc.Row con las 3 fichas de indicadores
    """
    try:
        if df_generacion.empty:
            return dbc.Alert("No hay datos disponibles para generar fichas", color="warning")
        
        # Clasificar renovable vs no renovable
        def es_renovable(tipo_str):
            tipo_upper = str(tipo_str).upper()
            renovables = ['HIDRÁULICA', 'HIDRAULICA', 'EÓLICA', 'EOLICA', 'SOLAR', 'BIOMASA']
            return any(ren in tipo_upper for ren in renovables)
        
        df_generacion['Es_Renovable'] = df_generacion['Tipo'].apply(es_renovable)
        
        # Calcular totales
        gen_total = float(df_generacion['Generacion_GWh'].sum())
        gen_renovable = float(df_generacion[df_generacion['Es_Renovable'] == True]['Generacion_GWh'].sum())
        gen_no_renovable = float(df_generacion[df_generacion['Es_Renovable'] == False]['Generacion_GWh'].sum())
        
        # Calcular porcentajes
        pct_renovable = float((gen_renovable / gen_total * 100) if gen_total > 0 else 0)
        pct_no_renovable = float((gen_no_renovable / gen_total * 100) if gen_total > 0 else 0)
        
        # Formatear valores
        valor_total = f"{gen_total:.1f}"
        valor_renovable = f"{gen_renovable:.1f}"
        valor_no_renovable = f"{gen_no_renovable:.1f}"
        porcentaje_renovable = f"{pct_renovable:.1f}"
        porcentaje_no_renovable = f"{pct_no_renovable:.1f}"
        
        # Formatear fechas
        fecha_inicio_str = fecha_inicio.strftime('%d/%m/%Y')
        fecha_fin_str = fecha_fin.strftime('%d/%m/%Y')
        periodo_texto = f"{fecha_inicio_str} - {fecha_fin_str}"
        
        # Título según tipo de fuente
        if tipo_fuente == 'TODAS':
            titulo_generacion = "Generación Total SIN"
        else:
            tipo_info = TIPOS_FUENTE.get(tipo_fuente, {})
            titulo_generacion = f"Generación {tipo_info.get('label', tipo_fuente)}"
        
        logger.info(f"✅ Fichas creadas desde DataFrame: {gen_total:.1f} GWh ({len(df_generacion)} registros)")
        
        # Crear fichas HTML
        return dbc.Row([
            # Ficha Generación Total
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-bolt fa-2x mb-3", style={'color': '#0f172a'}),
                            html.H6(titulo_generacion, className="mb-2", style={'fontWeight': '500', 'color': '#111827'}),
                            html.H2(valor_total, className='kpi-number mb-1', 
                                   style={'fontWeight': 'bold', 'fontSize': '2.5rem'}),
                            html.P("GWh", className="text-muted mb-2", style={'fontSize': '1.1rem', 'fontWeight': '500'}),
                            html.Small(periodo_texto, className="text-muted", style={'fontSize': '0.85rem'})
                        ], style={'textAlign': 'center'})
                    ], style={'background': '#ffffff', 'borderRadius': '12px', 'padding': '1.5rem',
                             'minHeight': '180px', 'display': 'flex', 'alignItems': 'center'})
                ], className="h-100 shadow-sm")
            ], lg=4, md=6, className="mb-4"),
            
            # Ficha Renovable
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-leaf fa-2x mb-3", style={'color': '#0f172a'}),
                            html.H6("Generación Renovable", className="mb-2", style={'fontWeight': '500', 'color': '#111827'}),
                            html.H2(valor_renovable, className='kpi-number mb-1',
                                   style={'fontWeight': 'bold', 'fontSize': '2.5rem'}),
                            html.P("GWh", className="text-muted mb-2", style={'fontSize': '1.1rem', 'fontWeight': '500'}),
                            html.Span(f"{porcentaje_renovable}% del total", className="badge",
                                     style={'backgroundColor': 'rgba(15, 23, 42, 0.08)', 'color': '#111827',
                                           'fontSize': '0.9rem', 'padding': '0.4rem 0.8rem', 'borderRadius': '20px'})
                        ], style={'textAlign': 'center'})
                    ], style={'background': 'linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%)',
                             'borderRadius': '12px', 'padding': '1.5rem', 'minHeight': '180px',
                             'display': 'flex', 'alignItems': 'center'})
                ], className="h-100 shadow-sm")
            ], lg=4, md=6, className="mb-4"),
            
            # Ficha No Renovable
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-industry fa-2x mb-3", style={'color': '#0f172a'}),
                            html.H6("Generación No Renovable", className="mb-2", style={'fontWeight': '500', 'color': '#111827'}),
                            html.H2(valor_no_renovable, className='kpi-number mb-1',
                                   style={'fontWeight': 'bold', 'fontSize': '2.5rem'}),
                            html.P("GWh", className="text-muted mb-2", style={'fontSize': '1.1rem', 'fontWeight': '500'}),
                            html.Span(f"{porcentaje_no_renovable}% del total", className="badge",
                                     style={'backgroundColor': 'rgba(15, 23, 42, 0.08)', 'color': '#111827',
                                           'fontSize': '0.9rem', 'padding': '0.4rem 0.8rem', 'borderRadius': '20px'})
                        ], style={'textAlign': 'center'})
                    ], style={'background': 'linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%)',
                             'borderRadius': '12px', 'padding': '1.5rem', 'minHeight': '180px',
                             'display': 'flex', 'alignItems': 'center'})
                ], className="h-100 shadow-sm")
            ], lg=4, md=6, className="mb-4")
        ])
        
    except Exception as e:
        logger.error(f"Error creando fichas desde DataFrame: {e}")
        import traceback
        traceback.print_exc()
        return dbc.Alert(f"Error generando fichas: {str(e)}", color="danger")


# Función auxiliar que recibe las fechas y tipo de fuente como parámetros
def crear_fichas_generacion_xm_con_fechas(fecha_inicio, fecha_fin, tipo_fuente='TODAS'):
    """
    Crea las fichas de generación para el período especificado por el usuario
    
    Args:
        fecha_inicio: Fecha inicial del período
        fecha_fin: Fecha final del período  
        tipo_fuente: 'TODAS' o tipo específico ('HIDRAULICA', 'TERMICA', etc.)
    
    IMPORTANTE: Implementa caché para evitar consultas repetidas a la API
    """
    # Crear key de caché
    cache_key = f"{fecha_inicio}_{fecha_fin}_{tipo_fuente}"
    
    # Si está en caché, retornar directamente
    if cache_key in _cache_fichas:
        print(f"⚡ Usando fichas en caché para {fecha_inicio} a {fecha_fin} - {tipo_fuente}")
        return _cache_fichas[cache_key]
    
    try:
        print(f"\n🚀 INICIANDO crear_fichas_generacion_xm_con_fechas()", flush=True)
        objetoAPI = get_objetoAPI()
        if objetoAPI is None:
            return dbc.Alert("API de XM no disponible", color="danger")
        
        print(f"=" * 80)
        print(f"📅 CONSULTANDO DATOS DEL PERÍODO: {fecha_inicio} al {fecha_fin}")
        print(f"🎯 TIPO DE FUENTE: {tipo_fuente}")
        print(f"=" * 80)
        
        # PASO 1: Obtener ListadoRecursos para mapear códigos
        print("\n🔍 PASO 1: Obteniendo ListadoRecursos...")
        # ✅ OPTIMIZADO: Usar fetch_metric_data con cache (listados siempre actuales)
        recursos_df = fetch_metric_data("ListadoRecursos", "Sistema", 
                                        fecha_inicio.strftime('%Y-%m-%d'), 
                                        fecha_fin.strftime('%Y-%m-%d'))
        
        if recursos_df is None or recursos_df.empty:
            return dbc.Alert("No se pudo obtener ListadoRecursos", color="warning")
        
        print(f"✅ ListadoRecursos obtenidos: {len(recursos_df)} recursos")
        
        # Crear mapeo: código → {nombre, tipo}
        codigo_info = {}
        for _, row in recursos_df.iterrows():
            codigo = str(row.get('Values_Code', ''))
            if codigo:
                codigo_info[codigo.upper()] = {
                    'nombre': str(row.get('Values_Name', codigo)),
                    'tipo': str(row.get('Values_Type', 'TERMICA')).upper()
                }
        
        print(f"✅ Mapeo creado: {len(codigo_info)} códigos")
        
        # PASO 2: Obtener datos de generación Gene/Recurso
        print("\n🔍 PASO 2: Obteniendo Gene/Recurso...")
        # ✅ OPTIMIZADO: Consulta inteligente SQLite (>=2020) vs API (<2020)
        df_gene, warning_msg = obtener_datos_inteligente("Gene", "Recurso", 
                                                          fecha_inicio, 
                                                          fecha_fin)
        
        # Mostrar advertencia si se consultaron datos históricos
        if warning_msg:
            print(f"⚠️ {warning_msg}")
        
        if df_gene is None or df_gene.empty:
            return dbc.Alert("No se obtuvieron datos de generación", color="warning")
        
        print(f"✅ Datos obtenidos: {len(df_gene)} registros")
        
        # PASO 3: Sumar las 24 horas por cada planta y convertir a GWh
        print("\n🔍 PASO 3: Procesando datos horarios...")
        horas_cols = [c for c in df_gene.columns if 'Hour' in str(c)]
        
        if not horas_cols:
            return dbc.Alert("No se encontraron columnas horarias en los datos", color="warning")
        
        print(f"✅ Encontradas {len(horas_cols)} columnas horarias")
        
        # Identificar columna de código
        codigo_col = None
        for col in ['Values_code', 'Values_Code', 'Code']:
            if col in df_gene.columns:
                codigo_col = col
                print(f"Columna SIC detectada: {codigo_col}")
                break
        
        if not codigo_col:
            return dbc.Alert("No se encontró columna de código en los datos", color="warning")
        
        # Sumar 24 horas por cada fila (día) y convertir kWh → GWh
        df_gene['Generacion_Dia_GWh'] = df_gene[horas_cols].fillna(0).sum(axis=1) / 1_000_000
        
        # AGRUPAR por código y sumar TODOS LOS DÍAS del período
        df_agrupado = df_gene.groupby(codigo_col).agg({
            'Generacion_Dia_GWh': 'sum'  # Suma de todos los días
        }).reset_index()
        
        print(f"✅ Datos agrupados: {len(df_agrupado)} plantas únicas")
        print(f"   Total generación (todos los días): {df_agrupado['Generacion_Dia_GWh'].sum():.2f} GWh")
        
        # Renombrar para compatibilidad
        df_agrupado.rename(columns={'Generacion_Dia_GWh': 'Generacion_GWh'}, inplace=True)
        df_gene = df_agrupado  # Reemplazar con datos agrupados
        
        # Mapear códigos a nombres y tipos
        df_gene['Codigo_Upper'] = df_gene[codigo_col].astype(str).str.upper()
        df_gene['Nombre_Planta'] = df_gene['Codigo_Upper'].map(lambda x: codigo_info.get(x, {}).get('nombre', x))
        df_gene['Tipo_Fuente'] = df_gene['Codigo_Upper'].map(lambda x: codigo_info.get(x, {}).get('tipo', 'TERMICA'))
        
        print(f"✅ Códigos mapeados correctamente")
        print(f"   Tipos encontrados: {sorted(df_gene['Tipo_Fuente'].unique())}")
        
        # FILTRAR POR TIPO DE FUENTE si no es "TODAS"
        if tipo_fuente != 'TODAS':
            print(f"\n🔍 FILTRANDO por tipo de fuente: {tipo_fuente}")
            df_gene = df_gene[df_gene['Tipo_Fuente'] == tipo_fuente]
            print(f"   Registros después del filtro: {len(df_gene)}")
            
            if df_gene.empty:
                return dbc.Alert(f"No hay datos para el tipo de fuente {tipo_fuente} en el período seleccionado", color="warning")
        
        # PASO 4: Clasificar renovable vs no renovable según XM
        print("\n🔍 PASO 4: Clasificando fuentes renovables...")
        
        def es_renovable_xm(tipo):
            """Clasificación oficial XM de fuentes renovables"""
            tipo_str = str(tipo).upper()
            renovables = ['HIDRAULICA', 'HIDRO', 'PCH', 'EOLICA', 'EOLIC', 
                         'SOLAR', 'FOTOVOLTAICA', 'FV', 'BIOMASA', 'COGENERADOR', 
                         'BAGAZO', 'BIOGAS']
            return any(ren in tipo_str for ren in renovables)
        
        df_gene['Es_Renovable'] = df_gene['Tipo_Fuente'].apply(es_renovable_xm)
        
        # PASO 5: Calcular totales
        print("\n🔍 PASO 5: Calculando totales...")
        
        # Calcular totales en GWh - CONVERSIÓN EXPLÍCITA A FLOAT
        gen_total = float(df_gene['Generacion_GWh'].sum())
        gen_renovable = float(df_gene[df_gene['Es_Renovable'] == True]['Generacion_GWh'].sum())
        gen_no_renovable = float(df_gene[df_gene['Es_Renovable'] == False]['Generacion_GWh'].sum())
        
        # Calcular porcentajes - CONVERSIÓN EXPLÍCITA A FLOAT
        pct_renovable = float((gen_renovable / gen_total * 100) if gen_total > 0 else 0)
        pct_no_renovable = float((gen_no_renovable / gen_total * 100) if gen_total > 0 else 0)
        
        print(f"✅ Totales calculados:")
        print(f"   Generación Total: {gen_total:,.2f} GWh")
        print(f"   Renovable: {gen_renovable:,.2f} GWh ({pct_renovable:.1f}%)")
        print(f"   No Renovable: {gen_no_renovable:,.2f} GWh ({pct_no_renovable:.1f}%)")
        
        # Formatear valores como strings simples
        valor_total = f"{gen_total:.1f}"
        valor_renovable = f"{gen_renovable:.1f}"
        valor_no_renovable = f"{gen_no_renovable:.1f}"
        porcentaje_renovable = f"{pct_renovable:.1f}"
        porcentaje_no_renovable = f"{pct_no_renovable:.1f}"
        
        print(f"\n📝 Valores formateados para HTML:")
        print(f"   Total: '{valor_total}' (tipo: {type(valor_total).__name__})")
        print(f"   Renovable: '{valor_renovable}' ({porcentaje_renovable}%)")
        print(f"   No Renovable: '{valor_no_renovable}' ({porcentaje_no_renovable}%)")
        
        # Formatear fechas como string
        fecha_inicio_str = fecha_inicio.strftime('%d/%m/%Y')
        fecha_fin_str = fecha_fin.strftime('%d/%m/%Y')
        periodo_texto = f"{fecha_inicio_str} - {fecha_fin_str}"
        
        print(f"   Período: '{periodo_texto}'")
        
        # Determinar título según filtro
        if tipo_fuente == 'TODAS':
            titulo_generacion = "Generación Total SIN"
        else:
            tipo_info = TIPOS_FUENTE.get(tipo_fuente, {})
            titulo_generacion = f"Generación {tipo_info.get('label', tipo_fuente)}"
        
        print(f"   Título: '{titulo_generacion}'")
        print(f"\n🎨 Creando componentes HTML...")
        
        # Crear las fichas HTML estilo SinergoX (texto oscuro para asegurar visibilidad)
        fichas_html = dbc.Row([
            # Ficha Generación Total
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-bolt fa-2x mb-3", style={'color': '#0f172a'}),
                            html.H6(titulo_generacion, className="mb-2", style={'fontWeight': '500', 'color': '#111827'}),
                            # Número grande
                            html.H2(
                                valor_total,
                                className='kpi-number mb-1',
                                style={
                                    'fontWeight': 'bold',
                                    'fontSize': '2.5rem'
                                }
                            ),
                            html.P("GWh", className="text-muted mb-2", style={'fontSize': '1.1rem', 'fontWeight': '500'}),
                            html.Small(periodo_texto, className="text-muted", style={'fontSize': '0.85rem'})
                        ], style={'textAlign': 'center'})
                    ], style={
                        'background': '#ffffff',
                        'borderRadius': '12px',
                        'padding': '1.5rem',
                        'minHeight': '180px',
                        'display': 'flex',
                        'alignItems': 'center'
                    })
                ], className="h-100 shadow-sm")
            ], lg=4, md=6, className="mb-4"),

            # Ficha Renovable
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-leaf fa-2x mb-3", style={'color': '#0f172a'}),
                            html.H6("Generación Renovable", className="mb-2", style={'fontWeight': '500', 'color': '#111827'}),
                            html.H2(
                                valor_renovable,
                                className='kpi-number mb-1',
                                style={
                                    'fontWeight': 'bold',
                                    'fontSize': '2.5rem'
                                }
                            ),
                            html.P("GWh", className="text-muted mb-2", style={'fontSize': '1.1rem', 'fontWeight': '500'}),
                            html.Span(f"{porcentaje_renovable}% del total", 
                                     className="badge", 
                                     style={
                                         'backgroundColor': 'rgba(15, 23, 42, 0.08)', 
                                         'color': '#111827',
                                         'fontSize': '0.9rem',
                                         'padding': '0.4rem 0.8rem',
                                         'borderRadius': '20px'
                                     })
                        ], style={'textAlign': 'center'})
                    ], style={
                        'background': 'linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%)',
                        'borderRadius': '12px',
                        'padding': '1.5rem',
                        'minHeight': '180px',
                        'display': 'flex',
                        'alignItems': 'center'
                    })
                ], className="h-100 shadow-sm")
            ], lg=4, md=6, className="mb-4"),
            
            # Ficha No Renovable
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-industry fa-2x mb-3", style={'color': '#0f172a'}),
                            html.H6("Generación No Renovable", className="mb-2", style={'fontWeight': '500', 'color': '#111827'}),
                            html.H2(
                                valor_no_renovable,
                                className='kpi-number mb-1',
                                style={
                                    'fontWeight': 'bold',
                                    'fontSize': '2.5rem'
                                }
                            ),
                            html.P("GWh", className="text-muted mb-2", style={'fontSize': '1.1rem', 'fontWeight': '500'}),
                            html.Span(f"{porcentaje_no_renovable}% del total", 
                                     className="badge",
                                     style={
                                         'backgroundColor': 'rgba(15, 23, 42, 0.08)', 
                                         'color': '#111827',
                                         'fontSize': '0.9rem',
                                         'padding': '0.4rem 0.8rem',
                                         'borderRadius': '20px'
                                     })
                        ], style={'textAlign': 'center'})
                    ], style={
                        'background': 'linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%)',
                        'borderRadius': '12px',
                        'padding': '1.5rem',
                        'minHeight': '180px',
                        'display': 'flex',
                        'alignItems': 'center'
                    })
                ], className="h-100 shadow-sm")
            ], lg=4, md=6, className="mb-4")
    ])

        print(f"✅ Fichas HTML creadas exitosamente\n")
        
        # Guardar en caché antes de retornar
        _cache_fichas[cache_key] = fichas_html
        print(f"💾 Fichas guardadas en caché para {fecha_inicio} a {fecha_fin} - {tipo_fuente}")
        
        return fichas_html
            
    except Exception as e:
        print(f"❌ ERROR en crear_fichas_generacion_xm_con_fechas: {e}")
        import traceback
        traceback.print_exc()
        return dbc.Alert(f"Error al cargar las fichas de generación: {str(e)}", color="danger")
