
def get_plotly_modules():
    """Importar plotly solo cuando se necesite"""
    import plotly.express as px
    import plotly.graph_objects as go
    return px, go

from dash import dcc, html, Input, Output, State, callback, register_page
import dash_bootstrap_components as dbc
import pandas as pd
from datetime import date, timedelta, datetime
import warnings
import traceback

# Use the installed pydataxm package
try:
    from pydataxm.pydataxm import ReadDB
    PYDATAXM_AVAILABLE = True
except ImportError:
    PYDATAXM_AVAILABLE = False
    print("⚠️ pydataxm no está disponible. Algunos datos pueden no cargarse correctamente.")

# Imports locales
from .components import crear_header, crear_navbar, crear_sidebar_universal, crear_boton_regresar
from .config import COLORS
from .utils_xm import fetch_gene_recurso_chunked
from ._xm import get_objetoAPI

warnings.filterwarnings("ignore")

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
                plantas = recursos[
                    recursos['Values_Type'].str.contains(tipo_fuente, na=False, case=False)
                ].copy()
                return plantas
            else:
                print("No se encontró la columna 'Values_Type' en recursos")
        print(f"No se obtuvieron recursos de tipo {tipo_fuente}")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error obteniendo listado de recursos {tipo_fuente}: {e}")
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
        
        plantas_min = plantas_df[[col_sic,'Values_Name']].drop_duplicates().rename(
            columns={col_sic:'Codigo','Values_Name':'Planta'})
        df_generacion = df_generacion.merge(plantas_min, on='Codigo', how='left')
        
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
    """Gráfica temporal con serie nacional y opcionalmente una planta seleccionada"""
    px, go = get_plotly_modules()
    
    if df_generacion.empty:
        return go.Figure().add_annotation(
            text="No hay datos disponibles",
            xref="paper", yref="paper", x=0.5, y=0.5
        )
    
    nacional = (df_generacion.groupby('Fecha', as_index=False)['Generacion_GWh']
                .sum().sort_values('Fecha'))
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=nacional['Fecha'],
        y=nacional['Generacion_GWh'],
        mode='lines+markers',
        name='Nacional',
        line=dict(color='black', width=2),
        marker=dict(color='black', size=5),
        hovertemplate='Fecha: %{x}<br>Generación: %{y:.2f} GWh<extra></extra>'
    ))
    
    if planta_seleccionada:
        df_p = df_generacion[df_generacion['Planta'] == planta_seleccionada]
        df_p = df_p.groupby('Fecha', as_index=False)['Generacion_GWh'].sum().sort_values('Fecha')
        if not df_p.empty:
            fig.add_trace(go.Scatter(
                x=df_p['Fecha'],
                y=df_p['Generacion_GWh'],
                mode='lines+markers',
                name=planta_seleccionada,
                line=dict(color='black', width=2, dash='dot'),
                marker=dict(color='black', size=5),
                hovertemplate=f'Fecha: %{{x}}<br>Generación: %{{y:.2f}} GWh<extra></extra>'
            ))
    
    fig.update_layout(
        title=f"Evolución Temporal - Generación {TIPOS_FUENTE.get(tipo_fuente, {}).get('label', tipo_fuente)}",
        xaxis_title="Fecha",
        yaxis_title="Generación (GWh)",
        hovermode='x unified',
        template='plotly_white',
        height=400
    )
    
    return fig

def crear_tabla_participacion(df_participacion):
    """Crear tabla de participación por planta"""
    if df_participacion.empty:
        return html.P("No hay datos de participación", className="text-muted")
    
    df_sorted = df_participacion.sort_values('Generacion_GWh', ascending=False)
    
    def color_estado(estado):
        if estado == 'Alto':
            return 'success'
        elif estado == 'Medio':
            return 'warning'
        return 'secondary'
    
    tabla_rows = []
    for _, row in df_sorted.iterrows():
        tabla_rows.append(
            html.Tr([
                html.Td(row['Planta']),
                html.Td(f"{row['Generacion_GWh']:.2f}", className="text-end"),
                html.Td(f"{row['Participacion_%']:.2f}%", className="text-end"),
                html.Td([
                    dbc.Badge(row['Estado'], color=color_estado(row['Estado']))
                ])
            ])
        )
    
    tabla = dbc.Table([
        html.Thead([
            html.Tr([
                html.Th("Planta"),
                html.Th("Generación (GWh)", className="text-end"),
                html.Th("Participación (%)", className="text-end"),
                html.Th("Estado")
            ])
        ]),
        html.Tbody(tabla_rows)
    ], striped=True, bordered=True, hover=True, responsive=True, className="table-sm")
    
    return tabla

# Layout
layout = html.Div([
    crear_sidebar_universal(),
    
    # Contenido principal
    dbc.Container([
        crear_header(
            "Generación por Fuente",
            "Análisis unificado de generación por tipo de fuente energética"
        ),
        crear_boton_regresar(),
        
        # Controles
        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Tipo de Fuente:", className="fw-bold"),
                        dcc.Dropdown(
                            id='tipo-fuente-dropdown',
                            options=[
                                {'label': f"{info['icon']} {info['label']}", 'value': tipo}
                                for tipo, info in TIPOS_FUENTE.items()
                            ],
                            value='EOLICA',
                            clearable=False,
                            style={'width': '100%'}
                        )
                    ], md=3),
                    dbc.Col([
                        html.Label("Rango de Fechas:", className="fw-bold"),
                        dcc.DatePickerRange(
                            id='date-range-fuentes',
                            start_date=date.today() - timedelta(days=7),
                            end_date=date.today(),
                            display_format='DD/MM/YYYY',
                            style={'width': '100%'}
                        )
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
                            "Actualizar Datos",
                            id="btn-actualizar-fuentes",
                            color="primary",
                            className="w-100"
                        )
                    ], md=2)
                ])
            ])
        ], className="mb-4"),
        
        # Contenedor de resultados
        dcc.Loading(
            id="loading-fuentes",
            type="circle",
            children=html.Div(id="contenido-fuentes")
        ),
        
    ], fluid=True, className="py-4")
    
], style={'backgroundColor': COLORS['bg_main'], 'minHeight': '100vh'})

# Callbacks
@callback(
    [Output('planta-dropdown-fuentes', 'options'),
     Output('contenido-fuentes', 'children')],
    [Input('btn-actualizar-fuentes', 'n_clicks'),
     Input('tipo-fuente-dropdown', 'value'),
     Input('date-range-fuentes', 'start_date'),
     Input('date-range-fuentes', 'end_date')],
    [State('planta-dropdown-fuentes', 'value')]
)
def actualizar_tablero_fuentes(n_clicks, tipo_fuente, fecha_inicio, fecha_fin, planta_seleccionada):
    if not fecha_inicio or not fecha_fin or not tipo_fuente:
        return [], dbc.Alert("Selecciona un tipo de fuente y rango de fechas válido", color="info")
    
    try:
        # Convertir fechas
        fecha_inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        fecha_fin_dt = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
        
        # Obtener listado de plantas del tipo seleccionado
        plantas_df = obtener_listado_recursos(tipo_fuente)
        
        if plantas_df.empty:
            return [], dbc.Alert(
                f"No se pudieron obtener datos de plantas {TIPOS_FUENTE[tipo_fuente]['label'].lower()}",
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
        info_fuente = TIPOS_FUENTE[tipo_fuente]
        contenido = [
            # Encabezado con información del tipo de fuente
            dbc.Alert([
                html.I(className=f"fas {info_fuente['icon']} me-2"),
                html.Strong(f"Tipo de Fuente: {info_fuente['label']}")
            ], color="light", className="mb-3"),
            
            # Gráfica temporal
            dbc.Card([
                dbc.CardHeader([
                    html.H5([
                        html.I(className="fas fa-chart-line me-2"),
                        f"Evolución Temporal - Generación {info_fuente['label']}"
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
                        f"Participación por Planta {info_fuente['label']}"
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
