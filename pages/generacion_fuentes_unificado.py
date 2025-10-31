from dash import dcc, html, Input, Output, State, callback, register_page, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
from datetime import date, timedelta, datetime
import warnings
import traceback
import logging
import sys
from functools import lru_cache
import hashlib

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
from utils._xm import get_objetoAPI

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

# Mapeo de tipos de fuente
TIPOS_FUENTE = {
    'HIDRAULICA': {'label': 'Hidráulica', 'icon': 'fa-water', 'color': COLORS.get('energia_hidraulica', '#0d6efd')},
    'EOLICA': {'label': 'Eólica', 'icon': 'fa-wind', 'color': COLORS.get('success', '#28a745')},
    'SOLAR': {'label': 'Solar', 'icon': 'fa-sun', 'color': COLORS.get('warning', '#ffc107')},
    'TERMICA': {'label': 'Térmica', 'icon': 'fa-fire', 'color': COLORS.get('danger', '#dc3545')},
    'BIOMASA': {'label': 'Biomasa', 'icon': 'fa-leaf', 'color': COLORS.get('info', '#17a2b8')}
}

def obtener_listado_recursos(tipo_fuente='EOLICA'):
    """Obtener el listado de recursos para un tipo de fuente específico"""
    try:
        objetoAPI = get_objetoAPI()
        if objetoAPI is None:
            print("API no disponible - retornando DataFrame vacío")
            return pd.DataFrame()
        
        fecha_fin = date.today() - timedelta(days=14)
        fecha_inicio = fecha_fin - timedelta(days=7)
        recursos = objetoAPI.request_data("ListadoRecursos", "Sistema", fecha_inicio, fecha_fin)
        
        if recursos is not None and not recursos.empty:
            if 'Values_Type' in recursos.columns:
                # Debug: mostrar tipos únicos disponibles
                tipos_unicos = recursos['Values_Type'].dropna().unique()
                print(f"🔍 Tipos de fuente disponibles: {sorted(tipos_unicos)}")
                
                # Si es TODAS, retornar todas las plantas
                if tipo_fuente.upper() == 'TODAS':
                    plantas = recursos.copy()
                    print(f"📊 Total plantas (TODAS): {len(plantas)}")
                    return plantas
                
                # Buscar con términos alternativos para biomasa
                elif tipo_fuente.upper() == 'BIOMASA':
                    # Intentar diferentes términos para biomasa
                    terminos_biomasa = ['BIOMASA', 'BIOMAS', 'COGENER', 'BAGAZO', 'RESIDUO']
                    plantas = pd.DataFrame()
                    for termino in terminos_biomasa:
                        plantas_temp = recursos[
                            recursos['Values_Type'].str.contains(termino, na=False, case=False)
                        ].copy()
                        if not plantas_temp.empty:
                            plantas = pd.concat([plantas, plantas_temp]).drop_duplicates()
                            print(f"✅ Encontradas plantas con término '{termino}': {len(plantas_temp)}")
                else:
                    plantas = recursos[
                        recursos['Values_Type'].str.contains(tipo_fuente, na=False, case=False)
                    ].copy()
                
                print(f"📊 Total plantas encontradas para {tipo_fuente}: {len(plantas)}")
                return plantas
            else:
                print("No se encontró la columna 'Values_Type' en recursos")
        print(f"No se obtuvieron recursos de tipo {tipo_fuente}")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error obteniendo listado de recursos {tipo_fuente}: {e}")
        import traceback
        traceback.print_exc()
    return pd.DataFrame()

def _detectar_columna_sic(recursos_df: pd.DataFrame, f_ini: date, f_fin: date):
    """Detecta la columna que contiene códigos SIC válidos"""
    objetoAPI = get_objetoAPI()
    if recursos_df is None or recursos_df.empty or objetoAPI is None:
        return None
    
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
            prueba = objetoAPI.request_data("Gene", "Recurso", f_ini, f_fin, cods)
            if prueba is not None and not prueba.empty:
                if 'Values_code' in prueba.columns and prueba['Values_code'].astype(str).isin(cods).any():
                    print(f"Columna SIC detectada: {col}")
                    return col
                print(f"Columna SIC detectada (sin Values_code): {col}")
                return col
        except Exception as e:
            print(f"Candidata {col} falló: {e}")
            continue
    
    print("No fue posible detectar columna SIC")
    return None

def obtener_generacion_plantas(fecha_inicio, fecha_fin, plantas_df=None):
    """Obtener datos de generación por plantas"""
    try:
        objetoAPI = get_objetoAPI()
        if objetoAPI is None or plantas_df is None or plantas_df.empty:
            return pd.DataFrame(), pd.DataFrame()
        
        col_sic = _detectar_columna_sic(plantas_df, fecha_inicio, fecha_fin)
        if not col_sic:
            return pd.DataFrame(), pd.DataFrame()
        
        codigos = (plantas_df[col_sic].dropna().astype(str).str.strip()
                   .loc[lambda s: s.str.match(r'^[A-Z0-9]{3,6}$', na=False)]
                   .unique().tolist())
        
        if not codigos:
            return pd.DataFrame(), pd.DataFrame()
        
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
        
        return df_generacion, participacion_total
    except Exception as e:
        print(f"Error en obtener_generacion_plantas: {e}")
        traceback.print_exc()
        return pd.DataFrame(), pd.DataFrame()

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
    df_por_fuente = df_generacion.groupby(['Fecha', 'Tipo'], as_index=False)['Generacion_GWh'].sum().sort_values('Fecha')
    
    # Crear subplots: 2 filas
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(
            'Generación por Fuente (Barras Apiladas)',
            'Generación por Fuente (Áreas Apiladas)'
        ),
        vertical_spacing=0.15,
        specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
    )
    
    # --- GRÁFICA 1: BARRAS APILADAS ---
    tipos_ordenados = ['Hidráulica', 'Térmica', 'Eólica', 'Solar', 'Biomasa']
    for tipo in tipos_ordenados:
        df_tipo = df_por_fuente[df_por_fuente['Tipo'] == tipo]
        if not df_tipo.empty:
            fig.add_trace(
                go.Bar(
                    x=df_tipo['Fecha'],
                    y=df_tipo['Generacion_GWh'],
                    name=tipo,
                    marker_color=colores_fuente.get(tipo, '#666'),
                    hovertemplate=f'<b>{tipo}</b><br>Fecha: %{{x}}<br>Generación: %{{y:.2f}} GWh<extra></extra>',
                    legendgroup=tipo,
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
    
    # --- GRÁFICA 2: ÁREAS APILADAS ---
    for tipo in tipos_ordenados:
        df_tipo = df_por_fuente[df_por_fuente['Tipo'] == tipo]
        if not df_tipo.empty:
            fig.add_trace(
                go.Scatter(
                    x=df_tipo['Fecha'],
                    y=df_tipo['Generacion_GWh'],
                    name=tipo,
                    mode='lines',
                    stackgroup='one',
                    fillcolor=colores_fuente.get(tipo, '#666'),
                    line=dict(width=0.5, color=colores_fuente.get(tipo, '#666')),
                    hovertemplate=f'<b>{tipo}</b><br>Fecha: %{{x}}<br>Generación: %{{y:.2f}} GWh<extra></extra>',
                    legendgroup=tipo,
                    showlegend=False  # Ya se muestra en la primera gráfica
                ),
                row=2, col=1
            )
    
    # Línea negra de total en gráfica 2
    fig.add_trace(
        go.Scatter(
            x=df_por_fecha['Fecha'],
            y=df_por_fecha['Generacion_GWh'],
            mode='lines',
            name='Total Nacional',
            line=dict(color='black', width=2),
            hovertemplate='<b>Total Nacional</b><br>Fecha: %{x}<br>Generación: %{y:.2f} GWh<extra></extra>',
            legendgroup='total',
            showlegend=False  # Ya se muestra en la primera gráfica
        ),
        row=2, col=1
    )
    
    # Configurar layout
    fig.update_layout(
        height=900,
        hovermode='x unified',
        template='plotly_white',
        barmode='stack',
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
    fig.update_yaxes(title_text="Generación (GWh)", row=2, col=1)
    
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
    
    # Seleccionar columnas finales
    columnas_mostrar = ['Planta', 'Generación (GWh)', 'Participación (%)', 'Estado']
    df_display = df_display[columnas_mostrar]
    
    # Crear DataTable con paginación
    tabla = html.Div([
        dash_table.DataTable(
            data=df_display.to_dict('records'),
            columns=[{"name": col, "id": col} for col in columnas_mostrar],
            
            # PAGINACIÓN estilo XM
            page_size=15,  # 15 filas por página
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
        
        # FILA DE TOTALES (como XM)
        # Nota: La participación siempre debe ser 100% (los decimales pueden no sumar exactamente debido a redondeos)
        html.Div([
            dbc.Row([
                dbc.Col([
                    html.Strong("Total", style={'fontSize': '14px'})
                ], width=3),
                dbc.Col([
                    html.Strong(f"{total_generacion:.2f}", 
                              style={'fontSize': '14px', 'textAlign': 'right', 'display': 'block'})
                ], width=3, style={'textAlign': 'right'}),
                dbc.Col([
                    html.Strong("100.00%",  # Siempre 100% (los redondeos pueden causar pequeñas diferencias)
                              style={'fontSize': '14px', 'textAlign': 'right', 'display': 'block'})
                ], width=3, style={'textAlign': 'right'}),
                dbc.Col([
                    html.Span("")  # Columna vacía para Estado
                ], width=3)
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
            recursos_df = objetoAPI.request_data("ListadoRecursos", "Sistema", fecha_inicio, fecha_fin)
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
                            html.Div(valor_renovable, style={'fontWeight': 'bold', 'fontSize': '2.5rem', 'color': '#0b1324', 'lineHeight': '1', 'marginBottom': '0.25rem'}),
                            html.Div("GWh", className="text-muted", style={'fontSize': '1.1rem', 'fontWeight': '500', 'marginBottom': '0.25rem'}),
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
    dcc.Interval(id='interval-carga-inicial', interval=500, n_intervals=0, max_intervals=1),
    
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
        # FILTROS PRINCIPALES (El que ya existía y funcionaba)
        # ==================================================================
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
                        html.Label("Tipo de Fuente:", className="fw-bold"),
                        dcc.Dropdown(
                            id='tipo-fuente-dropdown',
                            options=[
                                {'label': 'Todas las Fuentes', 'value': 'TODAS'},
                                {'label': '💧 Hidráulica', 'value': 'HIDRAULICA'},
                                {'label': '🔥 Térmica', 'value': 'TERMICA'},
                                {'label': '💨 Eólica', 'value': 'EOLICA'},
                                {'label': '☀️ Solar', 'value': 'SOLAR'},
                                {'label': '🌿 Biomasa/Cogeneración', 'value': 'BIOMASA'},
                            ],
                            value='TODAS',
                            clearable=False,
                            style={'width': '100%'}
                        )
                    ], md=3),
                    dbc.Col([
                        html.Label("Rango de Fechas:", className="fw-bold"),
                        dcc.DatePickerRange(
                            id='date-range-fuentes',
                            start_date=date.today() - timedelta(days=33),
                            end_date=date.today() - timedelta(days=3),
                            display_format='DD/MM/YYYY',
                            style={'width': '100%'}
                        ),
                        html.Small([
                            "⚡ Por defecto: 30 días | ",
                            html.Span("Períodos largos se agrupan automáticamente", style={'color': '#28a745'})
                        ], className="text-muted d-block mt-1")
                    ], md=4),
                    dbc.Col([
                        html.Label("Planta (opcional):", className="fw-bold"),
                        dcc.Dropdown(
                            id='planta-dropdown-fuentes',
                            placeholder="Selecciona una planta (opcional)",
                            multi=False
                        )
                    ], md=3),
                    dbc.Col([
                        html.Br(),
                        dbc.Button(
                            [html.I(className="fas fa-sync-alt me-2"), "Actualizar Datos"],
                            id="btn-actualizar-fuentes",
                            color="primary",
                            className="w-100",
                            size="lg"
                        )
                    ], md=2)
                ])
            ])
        ], className="mb-4 shadow"),
        
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
                children=[dbc.Alert("Cargando indicadores...", color="info", className="text-center")]
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
            children=html.Div(id="contenido-fuentes")
        ),
        
    ], fluid=True, className="py-4")
    
    ], style={'backgroundColor': COLORS['bg_main'], 'minHeight': '100vh'})
    
# Fin de la función layout() - Las fichas se generan directamente

# Callbacks para gráficas principales

@callback(
    Output("grafica-barras-apiladas", "figure"),
    Input("grafica-barras-apiladas", "id")
)
def cargar_grafica_barras_apiladas(_):
    """Cargar gráfica de barras apiladas"""
    return crear_grafica_barras_apiladas()

@callback(
    Output("grafica-area", "figure"),
    Input("grafica-area", "id")
)
def cargar_grafica_area(_):
    """Cargar gráfica de área"""
    return crear_grafica_area()

@callback(
    Output("tabla-resumen-todas-plantas", "children"),
    Input("tabla-resumen-todas-plantas", "id")
)
def cargar_tabla_resumen(_):
    """Cargar tabla resumen de todas las plantas"""
    return crear_tabla_resumen_todas_plantas()

# Callbacks - Se ejecuta automáticamente al cargar y cuando cambian los filtros
@callback(
    [Output('planta-dropdown-fuentes', 'options'),
     Output('contenido-fuentes', 'children')],
    [Input('tipo-fuente-dropdown', 'value'),
     Input('date-range-fuentes', 'start_date'),
     Input('date-range-fuentes', 'end_date'),
     Input('btn-actualizar-fuentes', 'n_clicks'),
     Input('interval-carga-inicial', 'n_intervals')],  # Trigger automático en carga
    [State('planta-dropdown-fuentes', 'value')],
    prevent_initial_call=False  # SE EJECUTA AL CARGAR LA PÁGINA
)
def actualizar_tablero_fuentes(tipo_fuente, fecha_inicio, fecha_fin, n_clicks, n_intervals, planta_seleccionada):
    if not fecha_inicio or not fecha_fin or not tipo_fuente:
        return [], dbc.Alert("Selecciona un tipo de fuente y rango de fechas válido", color="info")
    
    try:
        # Convertir fechas
        fecha_inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        fecha_fin_dt = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
        
        # Obtener listado de plantas del tipo seleccionado
        plantas_df = obtener_listado_recursos(tipo_fuente)
        
        if plantas_df.empty:
            tipo_label = TIPOS_FUENTE[tipo_fuente]['label'].lower() if tipo_fuente in TIPOS_FUENTE else "todas las fuentes"
            return [], dbc.Alert(
                f"No se pudieron obtener datos de plantas {tipo_label}",
                color="warning"
            )
        
        # Opciones para el dropdown
        col_sic = _detectar_columna_sic(plantas_df, fecha_inicio_dt, fecha_fin_dt)
        opciones_plantas = []
        if col_sic:
            opciones_plantas = [
                {'label': f"{row['Values_Name']}", 'value': row[col_sic]}
                for _, row in plantas_df.iterrows() if pd.notna(row.get(col_sic))
            ]
        
        # Obtener datos de generación
        df_generacion, df_participacion = obtener_generacion_plantas(
            fecha_inicio_dt, fecha_fin_dt, plantas_df
        )
        
        if df_generacion.empty:
            return opciones_plantas, dbc.Alert(
                "No se encontraron datos de generación para el período seleccionado",
                color="info"
            )
        
        # Determinar planta seleccionada
        planta_nombre = None
        if planta_seleccionada:
            cod_sel = planta_seleccionada
            if isinstance(cod_sel, list):
                cod_sel = cod_sel[0] if cod_sel else None
            if cod_sel is not None:
                nombre = df_generacion.loc[df_generacion['Codigo'] == cod_sel, 'Planta']
                planta_nombre = nombre.iloc[0] if not nombre.empty else None
        
        # Crear contenido
        if tipo_fuente in TIPOS_FUENTE:
            info_fuente = TIPOS_FUENTE[tipo_fuente]
            titulo_tipo = info_fuente['label']
            icono_tipo = info_fuente['icon']
        else:
            # Para 'TODAS' u otros casos
            titulo_tipo = "Todas las Fuentes"
            icono_tipo = "fa-bolt"
        
        contenido = [
            # Encabezado con información del tipo de fuente
            dbc.Alert([
                html.I(className=f"fas {icono_tipo} me-2"),
                html.Strong(f"Tipo de Fuente: {titulo_tipo}")
            ], color="light", className="mb-3"),
            
            # Gráfica temporal
            dbc.Card([
                dbc.CardHeader([
                    html.H5([
                        html.I(className="fas fa-chart-line me-2"),
                        f"Evolución Temporal - Generación {titulo_tipo}"
                    ], className="mb-0")
                ]),
                dbc.CardBody([
                    dcc.Graph(
                        figure=crear_grafica_temporal_negra(df_generacion, planta_nombre, tipo_fuente),
                        config={'displayModeBar': True}
                    )
                ])
            ], className="mb-4"),
            
            # Tabla de participación
            dbc.Card([
                dbc.CardHeader([
                    html.H5([
                        html.I(className="fas fa-table me-2"),
                        f"Participación por Planta {titulo_tipo}"
                    ], className="mb-0")
                ]),
                dbc.CardBody([
                    crear_tabla_participacion(df_participacion)
                ])
            ])
        ]
        
        return opciones_plantas, contenido
        
    except Exception as e:
        print(f"Error en callback fuentes: {e}")
        traceback.print_exc()
        return [], dbc.Alert(f"Error al procesar los datos: {str(e)}", color="danger")


# Callback para cargar fichas (se ejecuta al cargar y cuando cambian los filtros)
@callback(
    Output('contenedor-fichas-generacion', 'children'),
    [Input('date-range-fuentes', 'start_date'),
     Input('date-range-fuentes', 'end_date'),
     Input('tipo-fuente-dropdown', 'value'),
     Input('btn-actualizar-fuentes', 'n_clicks'),
     Input('interval-carga-inicial', 'n_intervals')],  # Trigger automático en carga
    prevent_initial_call=False  # SE EJECUTA AL CARGAR LA PÁGINA
)
def actualizar_fichas_generacion(start_date, end_date, tipo_fuente, n_clicks, n_intervals):
    """Genera las fichas al cargar la página y cuando el usuario presiona 'Actualizar Datos'"""
    
    print(f"\n🎯 Callback de fichas ejecutado", flush=True)
    print(f"   start_date: {start_date}, end_date: {end_date}, tipo_fuente: {tipo_fuente}", flush=True)
    
    # Si no hay valores, mostrar mensaje de espera
    if start_date is None or end_date is None or tipo_fuente is None:
        return dbc.Alert("⏳ Inicializando datos...", color="info")
    
    # Convertir fechas de string a date
    fecha_inicio = pd.to_datetime(start_date).date()
    fecha_fin = pd.to_datetime(end_date).date()
    
    try:
        print(f"  🔄 Generando fichas XM para {fecha_inicio} a {fecha_fin}...", flush=True)
        fichas_html = crear_fichas_generacion_xm_con_fechas(fecha_inicio, fecha_fin, tipo_fuente)
        print(f"  ✅ Fichas generadas correctamente", flush=True)
        print(f"  🔍 Tipo de retorno: {type(fichas_html)}", flush=True)
        print(f"  🔍 Contenido: {str(fichas_html)[:200]}...", flush=True)
        return fichas_html
    except Exception as e:
        print(f"  ❌ Error generando fichas: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return dbc.Alert(f"Error cargando indicadores: {str(e)}", color="danger")


# Función auxiliar que recibe las fechas y tipo de fuente como parámetros
def crear_fichas_generacion_xm_con_fechas(fecha_inicio, fecha_fin, tipo_fuente='TODAS'):
    """
    Crea las fichas de generación para el período especificado por el usuario
    
    Args:
        fecha_inicio: Fecha inicial del período
        fecha_fin: Fecha final del período  
        tipo_fuente: 'TODAS' o tipo específico ('HIDRAULICA', 'TERMICA', etc.)
    """
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
        recursos_df = objetoAPI.request_data("ListadoRecursos", "Sistema", fecha_inicio, fecha_fin)
        
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
        return fichas_html
            
    except Exception as e:
        print(f"❌ ERROR en crear_fichas_generacion_xm_con_fechas: {e}")
        import traceback
        traceback.print_exc()
        return dbc.Alert(f"Error al cargar las fichas de generación: {str(e)}", color="danger")
