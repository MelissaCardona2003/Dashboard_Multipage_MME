from dash import dcc, html, Input, Output, State, dash_table, ALL, callback, register_page
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import datetime as dt
from datetime import date, timedelta
import warnings
import sys
import os
import time
import traceback
from flask import Flask, jsonify
import dash
# Use the installed pydataxm package instead of local module
from pydataxm.pydataxm import ReadDB

# Imports locales para componentes uniformes
from .components import crear_header, crear_navbar, crear_sidebar_universal
from .config import COLORS

warnings.filterwarnings("ignore")

register_page(
    __name__,
    path="/hidrologia",
    name="Hidrologia",
    title="Dashboard Hidrológico - Ministerio de Minas y Energía de Colombia",
    order=3
)

# --- NUEVO: Fecha/hora de última actualización del código ---
LAST_UPDATE = time.strftime('%Y-%m-%d %H:%M:%S')

# Funciones auxiliares para formateo de datos
def format_number(value):
    """Formatear números con separadores de miles usando puntos"""
    if pd.isna(value) or not isinstance(value, (int, float)):
        return value
    
    # Formatear con separador de miles usando puntos (formato colombiano)
    return f"{value:,.2f}".replace(",", ".")

def format_date(date_value):
    """Formatear fechas para mostrar solo la fecha sin hora"""
    if pd.isna(date_value):
        return date_value
    
    if isinstance(date_value, str):
        try:
            # Intentar convertir string a datetime
            dt_value = pd.to_datetime(date_value)
            return dt_value.strftime('%Y-%m-%d')
        except Exception:
            return date_value
    elif hasattr(date_value, 'strftime'):
        return date_value.strftime('%Y-%m-%d')
    else:
        return date_value


# Inicializar API XM
import traceback
try:
    objetoAPI = ReadDB()
    print("API XM inicializada correctamente")
except Exception as e:
    print(f"Error al inicializar API XM: {e}")
    traceback.print_exc()
    objetoAPI = None


# --- VALIDACIÓN DE FECHAS Y MANEJO DE ERRORES ---
def validar_rango_fechas(start_date, end_date):
    """
    Valida que el rango de fechas sea válido para la API de XM.
    La API de XM tiene limitaciones temporales hacia atrás.
    """
    from datetime import datetime, timedelta
    
    if not start_date or not end_date:
        return False, "Debe seleccionar fechas de inicio y fin."
    
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d') if isinstance(start_date, str) else start_date
        end_dt = datetime.strptime(end_date, '%Y-%m-%d') if isinstance(end_date, str) else end_date
        
        # Fecha mínima permitida (aproximadamente 2 años hacia atrás para datos hidrológicos)
        fecha_minima = datetime.now() - timedelta(days=730)
        fecha_maxima = datetime.now()
        
        if start_dt < fecha_minima:
            return False, f"⚠️ La fecha de inicio es muy antigua. La API de XM solo permite consultas desde {fecha_minima.strftime('%Y-%m-%d')} aproximadamente. Para datos históricos más antiguos, contacte directamente a XM."
        
        if end_dt > fecha_maxima:
            return False, f"⚠️ La fecha final no puede ser futura. Fecha máxima permitida: {fecha_maxima.strftime('%Y-%m-%d')}"
        
        if start_dt > end_dt:
            return False, "⚠️ La fecha de inicio debe ser anterior a la fecha final."
        
        # Validar que el rango no sea demasiado amplio (más de 1 año)
        dias_diferencia = (end_dt - start_dt).days
        if dias_diferencia > 365:
            return False, "⚠️ El rango de fechas es muy amplio. Por favor, seleccione un período de máximo 1 año para optimizar el rendimiento."
        
        return True, "Rango de fechas válido"
        
    except Exception as e:
        return False, f"Error validando fechas: {str(e)}"

def manejar_error_api(error, operacion="consulta"):
    """
    Maneja errores específicos de la API de XM y proporciona mensajes útiles.
    """
    error_str = str(error).lower()
    
    if "400" in error_str and "json" in error_str and "text/plain" in error_str:
        return f"🔄 La API de XM retornó un error para esta {operacion}. Esto suele ocurrir cuando:\n\n• Las fechas seleccionadas están fuera del rango disponible\n• Los datos para el período solicitado no están disponibles\n• Hay mantenimiento en los servidores de XM\n\n💡 Recomendaciones:\n• Intente con fechas más recientes (últimos 6 meses)\n• Reduzca el rango de fechas\n• Verifique el estado de la API de XM en www.xm.com.co"
    
    elif "timeout" in error_str or "connection" in error_str:
        return f"🌐 Error de conexión con la API de XM. Verifique su conexión a internet y vuelva a intentar."
    
    elif "unauthorized" in error_str or "403" in error_str:
        return f"🔐 Error de autorización con la API de XM. Contacte al administrador del sistema."
    
    else:
        return f"❌ Error inesperado en la {operacion}: {str(error)[:200]}..."



# Obtener la relación río-región directamente desde la API XM
def get_rio_region_dict():
    try:
        df = objetoAPI.request_data('ListadoRios', 'Sistema', '2024-01-01', '2024-01-02')
        if 'Values_Name' in df.columns and 'Values_HydroRegion' in df.columns:
            # Normalizar nombres igual que antes
            df['Values_Name'] = df['Values_Name'].str.strip().str.upper()
            df['Values_HydroRegion'] = df['Values_HydroRegion'].str.strip().str.title()
            return dict(sorted(zip(df['Values_Name'], df['Values_HydroRegion'])))
        else:
            return {}
    except Exception as e:
        print(f"Error obteniendo relación río-región desde la API: {e}")
        return {}

RIO_REGION = get_rio_region_dict()

def get_region_options():
    """
    Obtiene las regiones que tienen ríos con datos de caudal activos.
    Filtra regiones que no tienen datos para evitar confusión al usuario.
    """
    try:
        # Obtener ríos con datos de caudal recientes
        df = objetoAPI.request_data('AporCaudal', 'Rio', (date.today() - timedelta(days=30)).strftime('%Y-%m-%d'), date.today().strftime('%Y-%m-%d'))
        if 'Name' in df.columns:
            rios_con_datos = set(df['Name'].unique())
            # Filtrar solo regiones que tienen ríos con datos
            regiones_con_datos = set()
            for rio, region in RIO_REGION.items():
                if rio in rios_con_datos:
                    regiones_con_datos.add(region)
            return sorted(regiones_con_datos)
        else:
            return sorted(set(RIO_REGION.values()))
    except Exception as e:
        print(f"Error filtrando regiones con datos: {e}")
        return sorted(set(RIO_REGION.values()))






# --- NUEVO: Función para obtener todos los ríos únicos desde la API ---
def get_all_rios_api():
    if objetoAPI is None:
        return []
    try:
        df = objetoAPI.request_data('AporCaudal', 'Rio', '2000-01-01', date.today().strftime('%Y-%m-%d'))
        if 'Name' in df.columns:
            rios = sorted(df['Name'].dropna().unique())
            return rios
        else:
            return []
    except Exception:
        return []

def get_rio_options(region=None):
    if objetoAPI is None:
        print("API XM no inicializada")
        return []
    try:
        df = objetoAPI.request_data('AporCaudal', 'Rio', (date.today() - timedelta(days=30)).strftime('%Y-%m-%d'), date.today().strftime('%Y-%m-%d'))
        if 'Name' in df.columns:
            rios = sorted(df['Name'].dropna().unique())
            if region:
                rios = [r for r in rios if RIO_REGION.get(r) == region]
            return rios
        else:
            return []
    except Exception as e:
        print(f"Error obteniendo opciones de Río: {e}")
        return []

regiones = []  # Se cargarán dinámicamente
rios = []      # Se cargarán dinámicamente

layout = html.Div([
    # Sidebar desplegable
    crear_sidebar_universal(),
    
    # Header uniforme
    # Header dinámico específico para hidrología
    crear_header(
        titulo_pagina="Análisis Hidrológico y Recursos Hídricos",
        descripcion_pagina="Monitoreo integral del potencial hídrico para generación hidroeléctrica",
        icono_pagina="fas fa-tint",
        informacion_adicional="Sistema de seguimiento de caudales, análisis de tendencias climáticas y evaluación del impacto hídrico en la matriz energética nacional",
        color_tema="#007bff"
    ),
    # Barra de navegación eliminada
    
    # Container principal
    dbc.Container([
        dbc.Row([
            # Contenido principal (ahora ocupa todo el ancho)
            dbc.Col([
                # Panel de controles en tabs
                dbc.Tabs([
                    dbc.Tab(label="🌊 Consulta de Caudales", tab_id="tab-consulta"),
                    dbc.Tab(label="📊 Análisis Hidrológico", tab_id="tab-analisis"),
                    dbc.Tab(label="📈 Tendencias Climáticas", tab_id="tab-tendencias"),
                ], id="hidro-tabs", active_tab="tab-consulta", className="mb-4"),
                
                # Contenido dinámico
                html.Div(id="hidrologia-tab-content")
            ], width=12)  # Ahora ocupa todo el ancho
        ])
    ], fluid=True)
], style={'backgroundColor': COLORS['bg_main'], 'minHeight': '100vh'})

# Modal global para tablas de datos
modal_rio_table = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle(id="modal-title-dynamic", children="Detalle de datos hidrológicos"), close_button=True),
    dbc.ModalBody([
        html.Div(id="modal-description", className="mb-3", style={"fontSize": "0.9rem", "color": "#666"}),
        html.Div(id="modal-table-content")
    ]),
], id="modal-rio-table", is_open=False, size="xl", backdrop=True, centered=True, style={"zIndex": 2000})

# Agregar modal al layout final
layout_with_modal = html.Div([layout, modal_rio_table])
layout = layout_with_modal

# Layout del panel de controles (lo que antes estaba en el layout principal)
def crear_panel_controles():
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.I(className="fas fa-sliders-h me-2", style={"color": COLORS['primary']}),
                html.Strong("Panel de Consulta de Caudales", style={"fontSize": "1.1rem", "color": COLORS['text_primary']})
            ], className="mb-3 d-flex align-items-center"),
            
            dbc.Alert([
                html.I(className="fas fa-exclamation-circle me-2"),
                html.Strong("📅 Limitaciones de fechas: "),
                "La API de XM funciona mejor con fechas recientes (últimos 2 años). Fechas muy antiguas pueden generar errores o no tener datos disponibles."
            ], color="info", className="mb-3", style={"fontSize": "0.85rem"}),
            
            dbc.Row([
                dbc.Col([
                    html.Label([
                        html.I(className="fas fa-map-marked-alt me-2"),
                        "Región Hidrológica"
                    ], className="fw-bold mb-2 d-flex align-items-center"),
                    dcc.Dropdown(
                        id="region-dropdown",
                        options=[{"label": "🌍 Todas las regiones", "value": "__ALL_REGIONS__"}],
                        placeholder="Selecciona una región hidrológica...",
                        className="form-control-modern mb-0",
                        style={"fontSize": "0.95rem"}
                    )
                ], lg=3, md=6, sm=12),
                
                dbc.Col([
                    html.Label([
                        html.I(className="fas fa-water me-2"),
                        "Río para Análisis"
                    ], className="fw-bold mb-2 d-flex align-items-center"),
                    dcc.Dropdown(
                        id="rio-dropdown",
                        options=[],  # Se cargarán dinámicamente según la región
                        placeholder="Selecciona un río para consultar...",
                        className="form-control-modern mb-0",
                        style={"fontSize": "0.95rem"}
                    )
                ], lg=3, md=6, sm=12),
                
                dbc.Col([
                    html.Label([
                        html.I(className="fas fa-calendar-alt me-2"),
                        "Fecha de Inicio"
                    ], className="fw-bold mb-2 d-flex align-items-center"),
                    dcc.DatePickerSingle(
                        id="start-date",
                        date=date.today() - timedelta(days=30),
                        display_format="DD/MM/YYYY",
                        className="form-control-modern",
                        style={"width": "100%"}
                    )
                ], lg=2, md=6, sm=12),
                
                dbc.Col([
                    html.Label([
                        html.I(className="fas fa-calendar-check me-2"),
                        "Fecha Final"
                    ], className="fw-bold mb-2 d-flex align-items-center"),
                    dcc.DatePickerSingle(
                        id="end-date",
                        date=date.today(),
                        display_format="DD/MM/YYYY",
                        className="form-control-modern",
                        style={"width": "100%"}
                    )
                ], lg=2, md=6, sm=12),
                
                dbc.Col([
                    html.Label("\u00A0", className="d-block"),
                    dbc.Button([
                        html.I(className="fas fa-chart-line me-2"),
                        "Consultar Caudales"
                    ],
                    id="query-button",
                    color="primary",
                    className="w-100 btn-modern",
                    style={"marginTop": "0.5rem", "background": f"linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%)", "border": "none"}
                    ),
                    # Mensaje informativo sobre tiempo de carga
                    html.Small([
                        html.I(className="fas fa-info-circle me-1"),
                        "La consulta puede tomar unos segundos dependiendo del rango de fechas"
                    ], className="text-muted d-block mt-1", style={"fontSize": "0.75rem"})
                ], lg=2, md=12, sm=12)
            ], className="g-3 align-items-end")
        ], className="p-4")
    ], className="shadow-sm")

# Callback para manejar tabs
@callback(
    Output("hidrologia-tab-content", "children"),
    Input("hidro-tabs", "active_tab")
)
def render_hidro_tab_content(active_tab):
    if active_tab == "tab-consulta":
        return html.Div([
            crear_panel_controles(),
            # Loading indicator con mensaje personalizado
            dcc.Loading(
                id="loading-hidro",
                type="circle",
                children=html.Div(id="hidro-results-content", className="mt-4"),
                color=COLORS['primary'],
                loading_state={'is_loading': False}
            )
        ])
    elif active_tab == "tab-analisis":
        return html.Div([
            dbc.Card([
                dbc.CardBody([
                    html.H4([
                        html.I(className="fas fa-chart-area me-2", style={"color": COLORS['primary']}),
                        "Análisis Hidrológico Avanzado"
                    ], className="mb-4"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("📊 Análisis de Variabilidad", className="mb-3"),
                                    html.P("Análisis estadístico de variabilidad de caudales por región y temporada.", className="text-muted")
                                ])
                            ], className="h-100")
                        ], md=6),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("⚡ Correlaciones Energéticas", className="mb-3"),
                                    html.P("Relación entre caudales y generación hidroeléctrica en Colombia.", className="text-muted")
                                ])
                            ], className="h-100")
                        ], md=6)
                    ])
                ])
            ], className="shadow-sm")
        ])
    elif active_tab == "tab-tendencias":
        return html.Div([
            dbc.Card([
                dbc.CardBody([
                    html.H4([
                        html.I(className="fas fa-trending-up me-2", style={"color": COLORS['primary']}),
                        "Tendencias Climáticas e Hidrológicas"
                    ], className="mb-4"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("🌡️ Variabilidad Climática", className="mb-3"),
                                    html.P("Análisis de patrones climáticos y su impacto en los recursos hídricos.", className="text-muted")
                                ])
                            ], className="h-100")
                        ], md=6),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("📈 Proyecciones Futuras", className="mb-3"),
                                    html.P("Modelos predictivos para planificación de recursos hídricos.", className="text-muted")
                                ])
                            ], className="h-100")
                        ], md=6)
                    ])
                ])
            ], className="shadow-sm")
        ])
    else:
        return html.Div([
            crear_panel_controles(),
            html.Div(id="hidro-results-content", className="mt-4")
        ])

# Callback para actualizar ríos según región seleccionada
@callback(
    Output("rio-dropdown", "options"),
    [Input("region-dropdown", "value")]
)
def update_rio_options(region):
    # Si se selecciona "Todas las regiones", mostrar todos los ríos disponibles
    if region == "__ALL_REGIONS__":
        rios_region = get_rio_options()  # Obtener todos los ríos sin filtro de región
    else:
        rios_region = get_rio_options(region)
    
    options = [{"label": "Todos los ríos", "value": "__ALL__"}]
    options += [{"label": r, "value": r} for r in rios_region]
    return options
def update_rio_options(region):
    # Si se selecciona "Todas las regiones", mostrar todos los ríos disponibles
    if region == "__ALL_REGIONS__":
        rios_region = get_rio_options()  # Obtener todos los ríos sin filtro de región
    else:
        rios_region = get_rio_options(region)
    
    options = [{"label": "Todos los ríos", "value": "__ALL__"}]
    options += [{"label": r, "value": r} for r in rios_region]
    return options


# Callback principal para consultar y mostrar datos filtrando por río y fechas
@callback(
    Output("hidro-results-content", "children"),
    [Input("query-button", "n_clicks")],
    [State("rio-dropdown", "value"),
     State("start-date", "date"),
     State("end-date", "date"),
     State("region-dropdown", "value")]
)
def update_content(n_clicks, rio, start_date, end_date, region):
    # Debug básico del callback
    if n_clicks and n_clicks > 0:
        print(f"� Consultando datos: región={region}, río={rio}, fechas={start_date} a {end_date}")
    
    # Función auxiliar para mostrar la vista por defecto (panorámica nacional)
    def show_default_view(start_date, end_date):
        # Validar rango de fechas
        es_valido, mensaje = validar_rango_fechas(start_date, end_date)
        if not es_valido:
            return dbc.Alert([
                html.H6("Fechas no válidas", className="alert-heading"),
                html.P(mensaje),
                html.Hr(),
                html.P("Ajuste el rango de fechas y vuelva a intentar.", className="mb-0")
            ], color="warning", className="text-start")
        
        try:
            data = objetoAPI.request_data('AporCaudal', 'Rio', start_date, end_date)
            if data is None or data.empty:
                return dbc.Alert([
                    html.H6("Sin datos", className="alert-heading"),
                    html.P(f"No hay datos disponibles para el período {start_date} a {end_date}."),
                    html.Hr(),
                    html.P("Intente con fechas más recientes.", className="mb-0")
                ], color="warning", className="text-start")
            
            # Agregar información de región
            data['Region'] = data['Name'].map(RIO_REGION)
            
            # Mostrar contribución total por región (todas las regiones)
            if 'Name' in data.columns and 'Value' in data.columns:
                # Agrupar por región y fecha para crear series temporales
                region_df = data.groupby(['Region', 'Date'])['Value'].sum().reset_index()
                region_df = region_df[region_df['Region'].notna()]  # Filtrar regiones válidas
                
                # Obtener datos de embalses para todas las regiones con estructura jerárquica
                regiones_totales, df_completo_embalses = get_tabla_regiones_embalses()
                
                return html.Div([
                    html.H5("🇨🇴 Contribución Energética por Región Hidrológica de Colombia", className="text-center mb-2"),
                    html.P("Vista panorámica nacional: Series temporales comparativas de aportes de caudal por región hidrológica. Haga clic en cualquier punto para ver el detalle agregado diario de la región. Los datos incluyen todos los ríos monitoreados en el período seleccionado, agrupados por región para análisis comparativo nacional.", className="text-center text-muted mb-3", style={"fontSize": "0.9rem"}),
                    dbc.Row([
                        dbc.Col([
                            create_porcapor_kpi(start_date, end_date, region="__ALL_REGIONS__")
                        ], md=6, className="mx-auto")
                    ], className="mb-4 justify-content-center"),
                    dbc.Row([
                        dbc.Col([
                            create_total_timeline_chart(data, "Aportes totales nacionales")
                        ], md=12)
                    ]),
                    dcc.Store(id="region-data-store", data=data.to_dict('records')),
                    dcc.Store(id="embalses-completo-data", data=df_completo_embalses.to_dict('records')),
                    html.Hr(),
                    html.H5("⚡ Capacidad Útil Diaria de Energía por Región Hidrológica", className="text-center mt-4 mb-2"),
                    html.P("📋 Interfaz jerárquica expandible: Haga clic en cualquier región para desplegar sus embalses. Cada región muestra dos tablas lado a lado con participación porcentual y capacidad detallada en GWh. Los datos están ordenados de mayor a menor valor. Los símbolos ⊞ indican regiones contraídas y ⊟ regiones expandidas.", className="text-center text-muted mb-3", style={"fontSize": "0.9rem"}),
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader([
                                    html.I(className="bi bi-pie-chart me-2", style={"color": "#667eea"}),
                                    html.Strong("📊 Participación Porcentual por Región")
                                ], style={"background": "linear-gradient(135deg, #e3f2fd 0%, #f3f4f6 100%)",
                                         "border": "none", "borderRadius": "8px 8px 0 0"}),
                                dbc.CardBody([
                                    html.P("Distribución porcentual de la capacidad energética entre regiones y sus embalses. Haga clic en los botones [+]/[-] para expandir/contraer cada región.", 
                                          className="text-muted mb-3", style={"fontSize": "0.85rem"}),
                                    html.Div([
                                        # Botones superpuestos para cada región
                                        html.Div(id="participacion-toggle-buttons", style={
                                            'position': 'absolute', 
                                            'zIndex': 10, 
                                            'pointerEvents': 'none'
                                        }),
                                        # Tabla principal
                                        html.Div(id="tabla-participacion-jerarquica-container", children=[
                                            html.Div("Cargando datos...", className="text-center text-muted")
                                        ])
                                    ], style={'position': 'relative'})
                                ], className="p-3")
                            ], className="card-modern h-100")
                        ], md=6),
                        
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader([
                                    html.I(className="bi bi-battery-full me-2", style={"color": "#28a745"}),
                                    html.Strong("🏭 Capacidad Detallada por Región")
                                ], style={"background": "linear-gradient(135deg, #e8f5e8 0%, #f3f4f6 100%)",
                                         "border": "none", "borderRadius": "8px 8px 0 0"}),
                                dbc.CardBody([
                                    html.P("Valores específicos de capacidad útil diaria en GWh y porcentaje de volumen útil por región y embalses. La columna 'Volumen Útil (%)' indica la disponibilidad energética como porcentaje del volumen almacenado por encima del Nivel Mínimo Técnico. Haga clic en los botones [+]/[-] para expandir/contraer cada región.", 
                                          className="text-muted mb-3", style={"fontSize": "0.85rem"}),
                                    html.Div([
                                        # Botones superpuestos para cada región
                                        html.Div(id="capacidad-toggle-buttons", style={
                                            'position': 'absolute', 
                                            'zIndex': 10, 
                                            'pointerEvents': 'none'
                                        }),
                                        # Tabla principal
                                        html.Div(id="tabla-capacidad-jerarquica-container", children=[
                                            html.Div("Cargando datos...", className="text-center text-muted")
                                        ])
                                    ], style={'position': 'relative'})
                                ], className="p-3")
                            ], className="card-modern h-100")
                        ], md=6)
                    ], className="g-3"),
                    
                    # Stores para manejar los datos jerárquicos y estados de expansión
                    dcc.Store(id="participacion-jerarquica-data", data=[]),
                    dcc.Store(id="capacidad-jerarquica-data", data=[]),
                    dcc.Store(id="regiones-expandidas", data=[])
                ])
            else:
                return dbc.Alert("No se pueden procesar los datos obtenidos.", color="warning")
        except Exception as e:
            error_message = manejar_error_api(e, "consulta de vista general")
            return dbc.Alert([
                html.H6("Error en vista general", className="alert-heading"),
                html.Pre(error_message, style={"white-space": "pre-wrap", "font-family": "inherit"}),
                html.Hr(),
                html.P("Intente con un rango de fechas más reciente.", className="mb-0")
            ], color="danger", className="text-start")
    
    # Verificar si los filtros están vacíos o en valores por defecto
    filtros_vacios = (
        (region is None or region == "__ALL_REGIONS__") and 
        (rio is None or rio == "__ALL__")
    )
    
    # Si no se ha hecho clic, o faltan fechas, o todos los filtros están vacíos pero hay fechas
    if not n_clicks or not start_date or not end_date:
        # Mostrar datos por defecto de todas las regiones al cargar la página
        if start_date and end_date and not n_clicks:
            return show_default_view(start_date, end_date)
        else:
            return dbc.Alert("Selecciona una región, fechas y/o río, luego haz clic en Consultar.", color="info", className="text-center")
    
    # Si se hizo clic pero todos los filtros están vacíos, mostrar vista por defecto
    if filtros_vacios:
        return show_default_view(start_date, end_date)
    
    # Validar fechas antes de proceder
    es_valido, mensaje = validar_rango_fechas(start_date, end_date)
    if not es_valido:
        return dbc.Alert([
            html.H6("Fechas no válidas", className="alert-heading"),
            html.P(mensaje),
            html.Hr(),
            html.P("Corrija las fechas y vuelva a intentar.", className="mb-0")
        ], color="warning", className="text-start")

    try:
        data = objetoAPI.request_data('AporCaudal', 'Rio', start_date, end_date)
        
        if data is None or data.empty:
            return dbc.Alert([
                html.H6("Sin datos disponibles", className="alert-heading"),
                html.P(f"No hay datos para el período {start_date} a {end_date} con los filtros seleccionados."),
                html.Hr(),
                html.P("Intente con fechas más recientes o diferentes filtros.", className="mb-0")
            ], color="warning", className="text-start")

        # Si hay un río específico seleccionado (y no es 'Todos los ríos'), mostrar la serie temporal diaria de ese río
        if rio and rio != "__ALL__":
            data_rio = data[data['Name'] == rio]
            if data_rio.empty:
                return dbc.Alert("No se encontraron datos para el río seleccionado.", color="warning")
            plot_df = data_rio.copy()
            if 'Date' in plot_df.columns and 'Value' in plot_df.columns:
                plot_df = plot_df[['Date', 'Value']].rename(columns={'Date': 'Fecha', 'Value': 'GWh'})
            return html.Div([
                html.H5(f"🌊 Río {rio} - Serie Temporal Completa de Aportes de Caudal", className="text-center mb-2"),
                html.P(f"Análisis detallado del río {rio} incluyendo gráfico de tendencias temporales y tabla de datos diarios con participación porcentual. Los valores están expresados en Gigavatios-hora (GWh) y representan la energía potencial aprovechable del caudal.", className="text-center text-muted mb-3", style={"fontSize": "0.9rem"}),
                dbc.Row([
                    dbc.Col([
                        html.H6("📈 Evolución Temporal", className="text-center mb-2"),
                        dbc.Row([
                            dbc.Col([
                                create_porcapor_kpi(start_date, end_date, region=region, rio=rio)
                            ], md=6, className="mx-auto")
                        ], className="mb-4 justify-content-center"),
                        create_line_chart(plot_df)
                    ], md=7),
                    dbc.Col([
                        html.H6("📊 Datos Detallados", className="text-center mb-2"),
                        create_data_table(plot_df)
                    ], md=5)
                ])
            ])

        # Si no hay río seleccionado o es 'Todos los ríos', mostrar barra de contribución total por río
        # Si hay región seleccionada, filtrar por región, si no, mostrar todas las regiones
        data['Region'] = data['Name'].map(RIO_REGION)
        
        if region and region != "__ALL_REGIONS__":
            data_filtered = data[data['Region'] == region]
            title_suffix = f"en la región {region}"
            # Obtener datos frescos de embalses con la nueva columna
            embalses_df_fresh = get_embalses_capacidad(region)
            
            # Aplicar formateo de números a la capacidad y porcentaje
            if not embalses_df_fresh.empty and 'Capacidad Útil Diaria (GWh)' in embalses_df_fresh.columns:
                embalses_df_formatted = embalses_df_fresh.copy()
                embalses_df_formatted['Capacidad Útil Diaria (GWh)'] = embalses_df_fresh['Capacidad Útil Diaria (GWh)'].apply(format_number)
                
                # Formatear porcentaje de volumen útil si existe
                if 'Volumen Útil (%)' in embalses_df_fresh.columns:
                    embalses_df_formatted['Volumen Útil (%)'] = embalses_df_fresh['Volumen Útil (%)'].apply(
                        lambda x: f"{x:.1f}%" if pd.notna(x) else "N/D"
                    )
                
                # Agregar fila TOTAL para capacidad de embalses
                if not embalses_df_formatted.empty:
                    total_capacity = embalses_df_fresh['Capacidad Útil Diaria (GWh)'].sum()
                    
                    # Calcular promedio ponderado del porcentaje de volumen útil
                    avg_volume_pct = None
                    if 'Volumen Útil (%)' in embalses_df_fresh.columns:
                        valid_data = embalses_df_fresh[embalses_df_fresh['Volumen Útil (%)'].notna()]
                        if not valid_data.empty:
                            avg_volume_pct = valid_data['Volumen Útil (%)'].mean()
                    
                    total_row_data = {
                        'Embalse': ['TOTAL'],
                        'Capacidad Útil Diaria (GWh)': [format_number(total_capacity)]
                    }
                    
                    if 'Volumen Útil (%)' in embalses_df_fresh.columns:
                        total_row_data['Volumen Útil (%)'] = [f"{avg_volume_pct:.1f}%" if avg_volume_pct is not None else "N/D"]
                    
                    total_row = pd.DataFrame(total_row_data)
                    embalses_df_formatted = pd.concat([embalses_df_formatted, total_row], ignore_index=True)
            else:
                embalses_df_formatted = embalses_df_fresh
                # DEBUG: Imprimir datos formateados para la tabla REGIÓN
                print(f"🔍 DEBUG TABLA REGION: Columnas en embalses_df_formatted: {list(embalses_df_formatted.columns)}")
                print(f"🔍 DEBUG TABLA REGION: Shape: {embalses_df_formatted.shape}")
                if not embalses_df_formatted.empty:
                    print(f"🔍 DEBUG TABLA REGION: Primeras 2 filas:")
                    print(embalses_df_formatted.head(2).to_string())
            # Obtener embalses de la región específica
            try:
                embalses_info = objetoAPI.request_data('ListadoEmbalses','Sistema','2024-01-01','2024-01-02')
                embalses_info['Values_Name'] = embalses_info['Values_Name'].str.strip().str.upper()
                embalses_info['Values_HydroRegion'] = embalses_info['Values_HydroRegion'].str.strip().str.title()
                embalses_region = embalses_info[embalses_info['Values_HydroRegion'] == region]['Values_Name'].sort_values().unique()
            except Exception as e:
                print(f"Error obteniendo embalses para el filtro: {e}")
                embalses_region = []
        else:
            # Si no hay región específica o es "Todas las regiones", mostrar vista nacional
            if region == "__ALL_REGIONS__":
                # Mostrar la vista panorámica nacional igual que al cargar la página
                region_df = data.groupby(['Region', 'Date'])['Value'].sum().reset_index()
                region_df = region_df[region_df['Region'].notna()]  # Filtrar regiones válidas
                
                return html.Div([
                    html.H5("🇨🇴 Contribución Energética por Región Hidrológica de Colombia", className="text-center mb-2"),
                    html.P("Vista panorámica nacional: Series temporales comparativas de aportes de caudal por región hidrológica. Haga clic en cualquier punto para ver el detalle agregado diario de la región. Los datos incluyen todos los ríos monitoreados en el período seleccionado, agrupados por región para análisis comparativo nacional.", className="text-center text-muted mb-3", style={"fontSize": "0.9rem"}),
                    dbc.Row([
                        dbc.Col([
                            create_porcapor_kpi(start_date, end_date, region="__ALL_REGIONS__")
                        ], md=6, className="mx-auto")
                    ], className="mb-4 justify-content-center"),
                    dbc.Row([
                        dbc.Col([
                            create_total_timeline_chart(data, "Aportes totales nacionales")
                        ], md=12)
                    ]),
                    dcc.Store(id="region-data-store", data=data.to_dict('records')),
                    html.Hr(),
                ])
            
            data_filtered = data
            title_suffix = "- Todas las regiones"
            # Obtener datos frescos de embalses con la nueva columna  
            embalses_df_fresh = get_embalses_capacidad()
            # Aplicar formateo de números a la capacidad y porcentaje
            if not embalses_df_fresh.empty and 'Capacidad Útil Diaria (GWh)' in embalses_df_fresh.columns:
                embalses_df_formatted = embalses_df_fresh.copy()
                embalses_df_formatted['Capacidad Útil Diaria (GWh)'] = embalses_df_fresh['Capacidad Útil Diaria (GWh)'].apply(format_number)
                
                # Formatear porcentaje de volumen útil si existe
                if 'Volumen Útil (%)' in embalses_df_fresh.columns:
                    embalses_df_formatted['Volumen Útil (%)'] = embalses_df_fresh['Volumen Útil (%)'].apply(
                        lambda x: f"{x:.1f}%" if pd.notna(x) else "N/D"
                    )
                
                # Agregar fila TOTAL para capacidad de embalses
                if not embalses_df_formatted.empty:
                    total_capacity = embalses_df_fresh['Capacidad Útil Diaria (GWh)'].sum()
                    
                    # Calcular promedio ponderado del porcentaje de volumen útil
                    avg_volume_pct = None
                    if 'Volumen Útil (%)' in embalses_df_fresh.columns:
                        valid_data = embalses_df_fresh[embalses_df_fresh['Volumen Útil (%)'].notna()]
                        if not valid_data.empty:
                            avg_volume_pct = valid_data['Volumen Útil (%)'].mean()
                    
                    total_row_data = {
                        'Embalse': ['TOTAL'],
                        'Capacidad Útil Diaria (GWh)': [format_number(total_capacity)]
                    }
                    
                    if 'Volumen Útil (%)' in embalses_df_fresh.columns:
                        total_row_data['Volumen Útil (%)'] = [f"{avg_volume_pct:.1f}%" if avg_volume_pct is not None else "N/D"]
                    
                    total_row = pd.DataFrame(total_row_data)
                    embalses_df_formatted = pd.concat([embalses_df_formatted, total_row], ignore_index=True)
            else:
                embalses_df_formatted = embalses_df_fresh
                # DEBUG: Imprimir datos formateados para la tabla NACIONAL
                print(f"🔍 DEBUG TABLA NACIONAL: Columnas en embalses_df_formatted: {list(embalses_df_formatted.columns)}")
                print(f"🔍 DEBUG TABLA NACIONAL: Shape: {embalses_df_formatted.shape}")
                if not embalses_df_formatted.empty:
                    print(f"🔍 DEBUG TABLA NACIONAL: Primeras 2 filas:")
                    print(embalses_df_formatted.head(2).to_string())
            embalses_region = embalses_df['Embalse'].unique() if not embalses_df.empty else []

        if data_filtered.empty:
            return dbc.Alert("No se encontraron datos para la región seleccionada." if region else "No se encontraron datos.", color="warning")
        
        # Asegurar que embalses_df_formatted esté definido para todos los casos
        if 'embalses_df_formatted' not in locals():
            if not embalses_df.empty and 'Capacidad Útil Diaria (GWh)' in embalses_df.columns:
                embalses_df_formatted = embalses_df_fresh.copy()
                embalses_df_formatted['Capacidad Útil Diaria (GWh)'] = embalses_df['Capacidad Útil Diaria (GWh)'].apply(format_number)
                
                # Agregar fila TOTAL para capacidad de embalses
                if not embalses_df_formatted.empty:
                    total_capacity = embalses_df_fresh['Capacidad Útil Diaria (GWh)'].sum()
                    total_row = pd.DataFrame({
                        'Embalse': ['TOTAL'],
                        'Capacidad Útil Diaria (GWh)': [format_number(total_capacity)]
                    })
                    embalses_df_formatted = pd.concat([embalses_df_formatted, total_row], ignore_index=True)
            else:
                embalses_df_formatted = embalses_df_fresh
            
        if 'Name' in data_filtered.columns and 'Value' in data_filtered.columns:
            # Para región específica, crear gráfica temporal de esa región
            if region and region != "__ALL_REGIONS__":
                # Crear gráfica temporal para la región específica
                region_temporal_data = data_filtered.groupby('Date')['Value'].sum().reset_index()
                region_temporal_data['Region'] = region
                
                return html.Div([
                    html.H5(f"🏞️ Evolución Temporal de Aportes Energéticos - Región {region}", className="text-center mb-2"),
                    html.P(f"Serie temporal de aportes de caudal para la región {region}. La gráfica muestra la evolución diaria de los aportes energéticos de todos los ríos de esta región durante el período seleccionado.", className="text-center text-muted mb-3", style={"fontSize": "0.9rem"}),
                    dbc.Row([
                        dbc.Col([
                            create_porcapor_kpi(start_date, end_date, region=region)
                        ], md=6, className="mx-auto")
                    ], className="mb-4 justify-content-center"),
                    dbc.Row([
                        dbc.Col([
                            create_total_timeline_chart(region_temporal_data, f"Aportes región {region}")
                        ], md=12)
                    ]),
                    dcc.Store(id="region-data-store", data=data_filtered.to_dict('records')),
                    html.Hr(),
                    html.H5(f"⚡ Capacidad Útil y Volumen por Embalse {title_suffix}", className="text-center mt-4 mb-2"),
                    html.P(f"Análisis detallado de la capacidad energética por embalse. Los datos muestran la energía disponible en GWh que puede ser generada diariamente por cada embalse. Incluye participación porcentual y filtros interactivos.", className="text-center text-muted mb-3", style={"fontSize": "0.9rem"}),
                    dbc.Row([
                        dbc.Col([
                            html.H6("📊 Participación Porcentual por Embalse", className="text-center mb-2"),
                            html.P("Distribución porcentual de la capacidad energética entre embalses. La tabla incluye una fila TOTAL que suma exactamente 100%.", className="text-muted mb-2", style={"fontSize": "0.8rem"}),
                            dash_table.DataTable(
                                id="tabla-participacion-embalse",
                                data=get_participacion_embalses(embalses_df_fresh).to_dict('records'),
                                columns=[
                                    {"name": "Embalse", "id": "Embalse"},
                                    {"name": "Participación (%)", "id": "Participación (%)"}
                                ],
                                style_cell={'textAlign': 'left', 'padding': '6px', 'fontFamily': 'Arial', 'fontSize': 14},
                                style_header={'backgroundColor': '#e3e3e3', 'fontWeight': 'bold'},
                                style_data={'backgroundColor': '#f8f8f8'},
                                style_data_conditional=[
                                    {
                                        'if': {'filter_query': '{Embalse} = "TOTAL"'},
                                        'backgroundColor': '#007bff',
                                        'color': 'white',
                                        'fontWeight': 'bold'
                                    }
                                ],
                                page_action="none"
                            ),
                        ], md=4),
                        dbc.Col([
                            html.H6("🏭 Capacidad Detallada por Embalse", className="text-center mb-2"),
                            html.P("Valores específicos de capacidad útil diaria en GWh. Use el filtro para buscar embalses específicos.", className="text-muted mb-2", style={"fontSize": "0.8rem"}),
                            dcc.Dropdown(
                                id="embalse-cap-dropdown",
                                options=[{"label": e.title(), "value": e} for e in embalses_region],
                                placeholder="🔍 Buscar embalse específico...",
                                className="mb-2"
                            ),
                            dash_table.DataTable(
                                id="tabla-capacidad-embalse",
                                data=get_embalses_data_for_table(region),
                                columns=[
                                    {"name": "Embalse", "id": "Embalse"},
                                    {"name": "Capacidad Útil Diaria (GWh)", "id": "Capacidad Útil Diaria (GWh)"},
                                    {"name": "Volumen Útil (%)", "id": "Volumen Útil (%)"}
                                ],
                                style_cell={"textAlign": "left", "padding": "6px", "fontFamily": "Arial", "fontSize": 14},
                                style_header={"backgroundColor": "#e3e3e3", "fontWeight": "bold"},
                                style_data={"backgroundColor": "#f8f8f8"},
                                style_data_conditional=[
                                    {
                                        "if": {"filter_query": "{Embalse} = \"TOTAL\""}, 
                                        "backgroundColor": "#007bff",
                                        "color": "white",
                                        "fontWeight": "bold"
                                    }
                                ],
                                page_action="none"
                            ),
                        ], md=8)
                    ]),
                    dcc.Store(id="embalse-cap-data", data=embalses_df_formatted.to_dict('records')),
                    dcc.Store(id="participacion-data", data=get_participacion_embalses(embalses_df_fresh).to_dict('records'))
                ])
            else:
                # Para caso sin región específica o vista general, mostrar también gráfica temporal
                national_temporal_data = data_filtered.groupby('Date')['Value'].sum().reset_index()
                national_temporal_data['Region'] = 'Nacional'
                
                return html.Div([
                    html.H5(f"🇨🇴 Evolución Temporal de Aportes Energéticos Nacionales", className="text-center mb-2"),
                    html.P(f"Serie temporal agregada de aportes de caudal a nivel nacional. La gráfica muestra la evolución diaria de los aportes energéticos de todas las regiones de Colombia durante el período seleccionado.", className="text-center text-muted mb-3", style={"fontSize": "0.9rem"}),
                    dbc.Row([
                        dbc.Col([
                            create_porcapor_kpi(start_date, end_date, region=None)
                        ], md=6, className="mx-auto")
                    ], className="mb-4 justify-content-center"),
                    dbc.Row([
                        dbc.Col([
                            create_total_timeline_chart(national_temporal_data, "Aportes nacionales")
                        ], md=12)
                    ]),
                    dcc.Store(id="region-data-store", data=data_filtered.to_dict('records')),
                    html.Hr(),
                    html.H5(f"⚡ Capacidad Útil Diaria de Energía - Embalses Nacionales", className="text-center mt-4 mb-2"),
                    html.P(f"Análisis detallado de la capacidad energética por embalse a nivel nacional. Los datos muestran la energía disponible en GWh que puede ser generada diariamente por cada embalse. Incluye participación porcentual y filtros interactivos.", className="text-center text-muted mb-3", style={"fontSize": "0.9rem"}),
                    dbc.Row([
                        dbc.Col([
                            html.H6("📊 Participación Porcentual por Embalse", className="text-center mb-2"),
                            html.P("Distribución porcentual de la capacidad energética entre embalses. La tabla incluye una fila TOTAL que suma exactamente 100%.", className="text-muted mb-2", style={"fontSize": "0.8rem"}),
                            dash_table.DataTable(
                                id="tabla-participacion-embalse",
                                data=get_participacion_embalses(embalses_df_fresh).to_dict('records'),
                                columns=[
                                    {"name": "Embalse", "id": "Embalse"},
                                    {"name": "Participación (%)", "id": "Participación (%)"}
                                ],
                                style_cell={'textAlign': 'left', 'padding': '6px', 'fontFamily': 'Arial', 'fontSize': 14},
                                style_header={'backgroundColor': '#e3e3e3', 'fontWeight': 'bold'},
                                style_data={'backgroundColor': '#f8f8f8'},
                                style_data_conditional=[
                                    {
                                        'if': {'filter_query': '{Embalse} = "TOTAL"'},
                                        'backgroundColor': '#007bff',
                                        'color': 'white',
                                        'fontWeight': 'bold'
                                    }
                                ],
                                page_action="none"
                            ),
                        ], md=4),
                        dbc.Col([
                            html.H6("🏭 Capacidad Detallada por Embalse", className="text-center mb-2"),
                            html.P("Valores específicos de capacidad útil diaria en GWh. Use el filtro para buscar embalses específicos.", className="text-muted mb-2", style={"fontSize": "0.8rem"}),
                            dcc.Dropdown(
                                id="embalse-cap-dropdown",
                                options=[{"label": e.title(), "value": e} for e in embalses_region],
                                placeholder="🔍 Buscar embalse específico...",
                                className="mb-2"
                            ),
                            dash_table.DataTable(
                                id="tabla-capacidad-embalse-2",
                                data=get_embalses_data_for_table(),
                                columns=[
                                    {"name": "Embalse", "id": "Embalse"},
                                    {"name": "Capacidad Útil Diaria (GWh)", "id": "Capacidad Útil Diaria (GWh)"},
                                    {"name": "Volumen Útil (%)", "id": "Volumen Útil (%)"}
                                ],
                                style_cell={"textAlign": "left", "padding": "6px", "fontFamily": "Arial", "fontSize": 14},
                                style_header={"backgroundColor": "#e3e3e3", "fontWeight": "bold"},
                                style_data={"backgroundColor": "#f8f8f8"},
                                style_data_conditional=[
                                    {
                                        "if": {"filter_query": "{Embalse} = \"TOTAL\""}, 
                                        "backgroundColor": "#007bff",
                                        "color": "white",
                                        "fontWeight": "bold"
                                    }
                                ],
                                page_action="none"
                            ),
                        ], md=8)
                    ]),
                    dcc.Store(id="embalse-cap-data", data=embalses_df_formatted.to_dict('records')),
                    dcc.Store(id="participacion-data", data=get_participacion_embalses(embalses_df_fresh).to_dict('records'))
                ])
        else:
            return dbc.Alert("No se pueden graficar los datos de la región." if region else "No se pueden graficar los datos.", color="warning")
    except Exception as e:
        error_message = manejar_error_api(e, "consulta de datos hidrológicos")
        return dbc.Alert([
            html.H6("Error en consulta", className="alert-heading"),
            html.Pre(error_message, style={"white-space": "pre-wrap", "font-family": "inherit"}),
            html.Hr(),
            html.P("Revise los parámetros de consulta e intente nuevamente.", className="mb-0")
        ], color="danger", className="text-start")

# Callback para inicializar las tablas jerárquicas al cargar la página
@callback(
    [Output("participacion-jerarquica-data", "data"),
     Output("capacidad-jerarquica-data", "data")],
    [Input("start-date", "date"), Input("end-date", "date")],
    prevent_initial_call=False
)
def initialize_hierarchical_tables(start_date, end_date):
    """Inicializar las tablas jerárquicas con datos de regiones al cargar la página"""
    try:
        regiones_totales, df_completo_embalses = get_tabla_regiones_embalses()
        
        if regiones_totales.empty:
            return [], [], [], []
        
        # Crear datos para tabla de participación (solo regiones inicialmente)
        participacion_data = []
        capacidad_data = []
        
        for _, row in regiones_totales.iterrows():
            # Datos de participación
            participacion_data.append({
                'nombre': f"▶️ {row['Región']}",  # Flecha indicando que se puede expandir
                'participacion': f"{row['Participación (%)']}%",
                'tipo': 'region',
                'region_name': row['Región'],
                'expandida': False,
                'id': f"region_{row['Región']}"
            })
            
            # Datos de capacidad
            capacidad_data.append({
                'nombre': f"▶️ {row['Región']}",  # Flecha indicando que se puede expandir
                'capacidad': f"{format_number(row['Total (GWh)'])} GWh",
                'tipo': 'region',
                'region_name': row['Región'],
                'expandida': False,
                'id': f"region_{row['Región']}"
            })
        
        # Agregar fila TOTAL al final
        participacion_data.append({
            'nombre': 'TOTAL SISTEMA',
            'participacion': '100.0%',
            'tipo': 'total',
            'region_name': '',
            'expandida': False,
            'id': 'total'
        })
        
        total_sistema = regiones_totales['Total (GWh)'].sum()
        capacidad_data.append({
            'nombre': 'TOTAL SISTEMA',
            'capacidad': f"{format_number(total_sistema)} GWh",
            'tipo': 'total',
            'region_name': '',
            'expandida': False,
            'id': 'total'
        })
        
        # Datos completos para los stores (incluye embalses)
        participacion_completa = participacion_data.copy()
        capacidad_completa = capacidad_data.copy()
        
        # Agregar datos de embalses a los stores completos
        for region_name in regiones_totales['Región'].unique():
            embalses_region = get_embalses_by_region(region_name, df_completo_embalses)
            
            if not embalses_region.empty:
                for _, embalse_row in embalses_region.iterrows():
                    embalse_name = embalse_row['Región'].replace('    └─ ', '')
                    
                    # Datos de participación para embalses
                    participacion_completa.append({
                        'nombre': f"    └─ {embalse_name}",
                        'participacion': f"{embalse_row['Participación (%)']}%",
                        'tipo': 'embalse',
                        'region_name': region_name,
                        'expandida': False,
                        'id': f"embalse_{region_name}_{embalse_name}"
                    })
                    
                    # Datos de capacidad para embalses  
                    capacidad_completa.append({
                        'nombre': f"    └─ {embalse_name}",
                        'capacidad': f"{format_number(embalse_row['Total (GWh)'])} GWh",
                        'tipo': 'embalse',
                        'region_name': region_name,
                        'expandida': False,
                        'id': f"embalse_{region_name}_{embalse_name}"
                    })
        
        # Retornar: datos completos para stores
        return participacion_completa, capacidad_completa
        
    except Exception as e:
        print(f"Error inicializando tablas jerárquicas: {e}")
        return [], []

def build_hierarchical_table_view(data_complete, expanded_regions, view_type="participacion"):
    """Construir vista de tabla jerárquica con botones integrados en la primera columna"""
    if not data_complete:
        return dash_table.DataTable(
            data=[],
            columns=[
                {"name": "Región / Embalse", "id": "nombre"},
                {"name": "Participación (%)" if view_type == "participacion" else "Capacidad (GWh)", "id": "valor"}
            ]
        )
    
    table_data = []
    processed_regions = set()
    
    # Obtener todas las regiones únicas
    all_regions = set()
    for item in data_complete:
        if item.get('tipo') == 'region':
            region_name = item.get('region_name')
            if region_name:
                all_regions.add(region_name)
    
    # Crear lista de regiones con sus valores para ordenar de mayor a menor
    region_items = []
    for item in data_complete:
        if item.get('tipo') == 'region':
            region_name = item.get('region_name')
            if region_name and region_name not in processed_regions:
                # Obtener el valor para ordenar
                valor_str = item.get('participacion', item.get('capacidad', '0'))
                try:
                    # Extraer valor numérico del string (ej: "25.5%" -> 25.5)
                    if isinstance(valor_str, str):
                        valor_num = float(valor_str.replace('%', '').replace(',', '').strip())
                    else:
                        valor_num = float(valor_str) if valor_str else 0
                except:
                    valor_num = 0
                
                region_items.append({
                    'item': item,
                    'region_name': region_name,
                    'valor_num': valor_num
                })
                processed_regions.add(region_name)
    
    # Ordenar regiones por valor de mayor a menor
    region_items.sort(key=lambda x: x['valor_num'], reverse=True)
    
    # Procesar cada región en orden descendente
    for region_data in region_items:
        region_item = region_data['item']
        region_name = region_data['region_name']
        
        is_expanded = region_name in expanded_regions
        
        # Fila de región con botón integrado en el nombre
        button_icon = "⊟" if is_expanded else "⊞"  # Símbolos más elegantes
        table_data.append({
            "nombre": f"{button_icon} {region_name}",
            "valor": region_item.get('participacion', region_item.get('capacidad', '')),
            "tipo": "region",
            "region_name": region_name,
            "id": f"region_{region_name}",
            "clickable": True  # Marcar como clickeable
        })
        
        # Si está expandida, agregar embalses ordenados de mayor a menor
        if is_expanded:
            embalses = []
            processed_embalses = set()
            
            for item in data_complete:
                if (item.get('tipo') == 'embalse' and 
                    item.get('region_name') == region_name):
                    embalse_id = item.get('id', '')
                    if embalse_id not in processed_embalses:
                        processed_embalses.add(embalse_id)
                        # Agregar valor numérico para ordenar
                        valor_str = item.get('participacion', item.get('capacidad', '0'))
                        try:
                            if isinstance(valor_str, str):
                                valor_num = float(valor_str.replace('%', '').replace(',', '').strip())
                            else:
                                valor_num = float(valor_str) if valor_str else 0
                        except:
                            valor_num = 0
                        item['valor_num'] = valor_num
                        embalses.append(item)
            
            # Ordenar embalses de mayor a menor
            embalses.sort(key=lambda x: x.get('valor_num', 0), reverse=True)
            
            for embalse in embalses:
                        embalse_name = embalse.get('nombre', '').replace('    └─ ', '')
                        table_data.append({
                            "nombre": f"    └─ {embalse_name}",
                            "valor": embalse.get('participacion', embalse.get('capacidad', '')),
                            "tipo": "embalse",
                            "region_name": region_name,
                            "id": embalse.get('id', f"embalse_{region_name}_{embalse_name}"),
                            "clickable": False  # Embalses no son clickeables
                        })
    
    # Agregar fila TOTAL
    total_item = None
    for item in data_complete:
        if item.get('tipo') == 'total':
            total_item = item
            break
    
    if total_item:
        table_data.append({
            "nombre": "TOTAL SISTEMA",
            "valor": total_item.get('participacion', total_item.get('capacidad', '')),
            "tipo": "total",
            "region_name": "",
            "id": "total",
            "clickable": False
        })
    
    # Crear tabla con estructura de 2 columnas
    return dash_table.DataTable(
        id=f"tabla-{view_type}-jerarquica-display",
        data=table_data,
        columns=[
            {"name": "Región / Embalse", "id": "nombre"},
            {"name": "Participación (%)" if view_type == "participacion" else "Capacidad (GWh)", "id": "valor"}
        ],
        style_cell={
            'textAlign': 'left',
            'padding': '8px',
            'fontFamily': 'Inter, Arial, sans-serif',
            'fontSize': 13,
            'backgroundColor': '#f8f9fa',
            'border': '1px solid #dee2e6'
        },
        style_header={
            'backgroundColor': '#667eea' if view_type == 'participacion' else '#28a745',
            'color': 'white',
            'fontWeight': 'bold',
            'fontSize': 14,
            'textAlign': 'center',
            'border': f'1px solid {"#5a6cf0" if view_type == "participacion" else "#218838"}'
        },
        style_data_conditional=[
            {
                'if': {'filter_query': '{tipo} = "region"'},
                'backgroundColor': '#e3f2fd' if view_type == 'participacion' else '#e8f5e8',
                'fontWeight': 'bold',
                'cursor': 'pointer',
                'border': f'2px solid {"#2196f3" if view_type == "participacion" else "#28a745"}'
            },
            {
                'if': {'filter_query': '{tipo} = "embalse"'},
                'backgroundColor': '#f8f9fa',
                'fontStyle': 'italic'
            },
            {
                'if': {'filter_query': '{tipo} = "total"'},
                'backgroundColor': '#007bff',
                'color': 'white',
                'fontWeight': 'bold'
            }
        ],
        page_action="none"
    )

# Callback para manejar clics en las regiones y expandir/colapsar embalses
@callback(
    [Output("tabla-participacion-jerarquica-container", "children"),
     Output("tabla-capacidad-jerarquica-container", "children"),
     Output("regiones-expandidas", "data")],
    [Input("tabla-participacion-jerarquica-display", "active_cell"),
     Input("tabla-capacidad-jerarquica-display", "active_cell")],
    [State("participacion-jerarquica-data", "data"),
     State("capacidad-jerarquica-data", "data"),
     State("regiones-expandidas", "data")],
    prevent_initial_call=True
)
def toggle_region_from_table(active_cell_part, active_cell_cap, participacion_complete, capacidad_complete, regiones_expandidas):
    """Manejar clics en los nombres de región con botones integrados"""
    try:
        if not participacion_complete or not capacidad_complete:
            return dash.no_update, dash.no_update, regiones_expandidas or []
        
        if regiones_expandidas is None:
            regiones_expandidas = []
        
        # Obtener el clic activo
        active_cell = active_cell_part or active_cell_cap
        if not active_cell:
            return dash.no_update, dash.no_update, regiones_expandidas
        
        # Solo responder a clics en la columna "nombre"
        if active_cell.get('column_id') != 'nombre':
            return dash.no_update, dash.no_update, regiones_expandidas
        
        # Obtener el nombre de la celda clicada directamente de la tabla
        # Construir la tabla actual para obtener los datos exactos
        current_table = build_hierarchical_table_view(participacion_complete, regiones_expandidas, "participacion")
        
        # Obtener los datos de la tabla actual
        table_data = current_table.data if hasattr(current_table, 'data') else []
        
        # Verificar qué fila se clicó
        row_id = active_cell['row']
        if row_id < len(table_data):
            clicked_row = table_data[row_id]
            clicked_name = clicked_row.get('nombre', '')
            
            # Extraer el nombre de la región del texto (remover símbolos ⊞/⊟)
            region_name = clicked_name.replace('⊞ ', '').replace('⊟ ', '').strip()
            
            # Verificar si es una fila de región (no embalse ni total)
            if clicked_row.get('tipo') == 'region' and region_name:
                # Toggle la región
                if region_name in regiones_expandidas:
                    regiones_expandidas.remove(region_name)
                else:
                    regiones_expandidas.append(region_name)
        
        # Reconstruir las vistas
        participacion_view = build_hierarchical_table_view(participacion_complete, regiones_expandidas, "participacion")
        capacidad_view = build_hierarchical_table_view(capacidad_complete, regiones_expandidas, "capacidad")
        
        return participacion_view, capacidad_view, regiones_expandidas
        
    except Exception as e:
        print(f"Error en toggle_region_from_table: {e}")
        import traceback
        traceback.print_exc()
        return dash.no_update, dash.no_update, regiones_expandidas or []

# Callback para inicializar las vistas HTML desde los stores
@callback(
    [Output("tabla-participacion-jerarquica-container", "children", allow_duplicate=True),
     Output("tabla-capacidad-jerarquica-container", "children", allow_duplicate=True)],
    [Input("participacion-jerarquica-data", "data"),
     Input("capacidad-jerarquica-data", "data")],
    [State("regiones-expandidas", "data")],
    prevent_initial_call='initial_duplicate'
)
def update_html_tables_from_stores(participacion_complete, capacidad_complete, regiones_expandidas):
    """Actualizar las vistas HTML basándose en los stores"""
    try:
        if not participacion_complete or not capacidad_complete:
            return (
                html.Div("No hay datos de participación disponibles", className="text-center text-muted p-3"),
                html.Div("No hay datos de capacidad disponibles", className="text-center text-muted p-3")
            )
        
        if not regiones_expandidas:
            regiones_expandidas = []
        
        # Construir vistas de tabla iniciales (todas las regiones colapsadas)
        participacion_view = build_hierarchical_table_view(participacion_complete, regiones_expandidas, "participacion")
        capacidad_view = build_hierarchical_table_view(capacidad_complete, regiones_expandidas, "capacidad")
        
        return participacion_view, capacidad_view
        
    except Exception as e:
        print(f"Error en update_html_tables_from_stores: {e}")
        return (
            html.Div("Error al cargar datos de participación", className="text-center text-danger p-3"),
            html.Div("Error al cargar datos de capacidad", className="text-center text-danger p-3")
        )
        
    except Exception as e:
        print(f"Error en update_tables_from_stores: {e}")
        import traceback
        traceback.print_exc()
        return [], []

# Callback adicional para cargar datos por defecto al iniciar la página
@callback(
    Output("hidro-results-content", "children", allow_duplicate=True),
    [Input("start-date", "date"), Input("end-date", "date")],
    prevent_initial_call='initial_duplicate'
)
def load_default_data(start_date, end_date):
    """Cargar datos por defecto al inicializar la página"""
    if start_date and end_date:
        # Validar rango de fechas antes de hacer la consulta
        es_valido, mensaje = validar_rango_fechas(start_date, end_date)
        if not es_valido:
            return dbc.Alert([
                html.H6("Rango de fechas no válido", className="alert-heading"),
                html.P(mensaje),
                html.Hr(),
                html.P("Ajuste las fechas y vuelva a intentar.", className="mb-0")
            ], color="warning", className="text-start")
        
        # Verificar que la API esté disponible
        if objetoAPI is None:
            return dbc.Alert([
                html.H6("API XM no disponible", className="alert-heading"),
                html.P("La conexión con la API de XM no está activa."),
                html.Hr(),
                html.P("Reinicie la aplicación o contacte al administrador.", className="mb-0")
            ], color="danger", className="text-start")
        
        try:
            # Realizar consulta con manejo mejorado de errores
            data = objetoAPI.request_data('AporCaudal', 'Rio', start_date, end_date)
            
            if data is None or data.empty:
                return dbc.Alert([
                    html.H6("Sin datos disponibles", className="alert-heading"),
                    html.P(f"No se encontraron datos de caudales para el período {start_date} a {end_date}."),
                    html.Hr(),
                    html.P("Intente con un rango de fechas diferente o más reciente.", className="mb-0")
                ], color="warning", className="text-start")
            
            # Agregar información de región
            data['Region'] = data['Name'].map(RIO_REGION)
            
            # Mostrar contribución total por región (todas las regiones)
            if 'Name' in data.columns and 'Value' in data.columns:
                # Agrupar por región y fecha para crear series temporales
                region_df = data.groupby(['Region', 'Date'])['Value'].sum().reset_index()
                region_df = region_df[region_df['Region'].notna()]  # Filtrar regiones válidas
                
                return html.Div([
                    html.H5("🇨🇴 Contribución Energética por Región Hidrológica de Colombia", className="text-center mb-2"),
                    html.P("Vista panorámica nacional: Timeline del total nacional de aportes de caudal. Haga clic en cualquier punto para ver el desglose detallado por región para esa fecha específica. Los datos incluyen todos los ríos monitoreados en el período seleccionado, agregados por día.", className="text-center text-muted mb-3", style={"fontSize": "0.9rem"}),
                    dbc.Row([
                        dbc.Col([
                            create_porcapor_kpi(start_date, end_date, region="__ALL_REGIONS__")
                        ], md=6, className="mx-auto")
                    ], className="mb-4 justify-content-center"),
                    dbc.Row([
                        dbc.Col([
                            create_total_timeline_chart(data, "Aportes totales nacionales")
                        ], md=12)
                    ]),
                    dcc.Store(id="region-data-store", data=data.to_dict('records')),
                    html.Hr(),
                ])
            else:
                return dbc.Alert([
                    html.H6("Error de formato de datos", className="alert-heading"),
                    html.P("Los datos obtenidos no tienen el formato esperado."),
                    html.Hr(),
                    html.P("Contacte al administrador del sistema.", className="mb-0")
                ], color="warning", className="text-start")
                
        except Exception as e:
            error_message = manejar_error_api(e, "carga de datos iniciales")
            return dbc.Alert([
                html.H6("Error al cargar datos", className="alert-heading"),
                html.Pre(error_message, style={"white-space": "pre-wrap", "font-family": "inherit"}),
                html.Hr(),
                html.P("Si el problema persiste, contacte al equipo técnico.", className="mb-0")
            ], color="danger", className="text-start")
    
    return dbc.Alert([
        html.H6("Inicializando...", className="alert-heading"),
        html.P("Cargando datos iniciales del sistema hidrológico..."),
        html.Hr(),
        html.P("Seleccione un rango de fechas para comenzar.", className="mb-0")
    ], color="info", className="text-start")

# --- Función para calcular participación porcentual de embalses ---
def get_participacion_embalses(df_embalses):
    """
    Calcula la participación porcentual de cada embalse respecto al total.
    """
    if df_embalses.empty or 'Capacidad Útil Diaria (GWh)' not in df_embalses.columns:
        return pd.DataFrame(columns=['Embalse', 'Participación (%)'])
    
    df_participacion = df_embalses.copy()
    total = df_participacion['Capacidad Útil Diaria (GWh)'].sum()
    
    if total > 0:
        # Calcular porcentajes sin redondear primero
        porcentajes = (df_participacion['Capacidad Útil Diaria (GWh)'] / total * 100)
        
        # Ajustar el último valor para que la suma sea exactamente 100%
        porcentajes_redondeados = porcentajes.round(2)
        diferencia = 100 - porcentajes_redondeados.sum()
        
        # Si hay diferencia por redondeo, ajustar el valor más grande
        if abs(diferencia) > 0.001:
            idx_max = porcentajes_redondeados.idxmax()
            porcentajes_redondeados.loc[idx_max] += diferencia
            
        df_participacion['Participación (%)'] = porcentajes_redondeados.round(2)
    else:
        df_participacion['Participación (%)'] = 0
    
    # Ordenar de mayor a menor por participación
    df_participacion = df_participacion.sort_values('Participación (%)', ascending=False)
    
    # Solo devolver las columnas necesarias
    df_final = df_participacion[['Embalse', 'Participación (%)']].reset_index(drop=True)
    
    # Agregar fila TOTAL
    total_row = pd.DataFrame({
        'Embalse': ['TOTAL'],
        'Participación (%)': [100.0]
    })
    
    df_final = pd.concat([df_final, total_row], ignore_index=True)
    
    return df_final

# --- Función para crear tabla con capacidad y participación combinadas ---
def get_tabla_con_participacion(df_embalses):
    """
    Crea una tabla que combina la capacidad útil con la participación porcentual.
    """
    if df_embalses.empty or 'Capacidad Útil Diaria (GWh)' not in df_embalses.columns:
        return pd.DataFrame(columns=['Embalse', 'Capacidad Útil Diaria (GWh)', 'Participación (%)'])
    
    df_resultado = df_embalses.copy()
    total = df_resultado['Capacidad Útil Diaria (GWh)'].sum()
    
    if total > 0:
        # Calcular porcentajes sin redondear primero
        porcentajes = (df_resultado['Capacidad Útil Diaria (GWh)'] / total * 100)
        
        # Ajustar el último valor para que la suma sea exactamente 100%
        porcentajes_redondeados = porcentajes.round(2)
        diferencia = 100 - porcentajes_redondeados.sum()
        
        # Si hay diferencia por redondeo, ajustar el valor más grande
        if abs(diferencia) > 0.001:
            idx_max = porcentajes_redondeados.idxmax()
            porcentajes_redondeados.loc[idx_max] += diferencia
            
        df_resultado['Participación (%)'] = porcentajes_redondeados.round(2)
    else:
        df_resultado['Participación (%)'] = 0
    
    # Formatear números en la capacidad
    df_resultado['Capacidad Útil Diaria (GWh)'] = df_resultado['Capacidad Útil Diaria (GWh)'].apply(format_number)
    
    # Ordenar de mayor a menor por participación
    df_resultado = df_resultado.sort_values('Participación (%)', ascending=False)
    
    return df_resultado[['Embalse', 'Capacidad Útil Diaria (GWh)', 'Participación (%)']].reset_index(drop=True)

# --- Función para crear tabla jerárquica de regiones con embalses ---
def get_tabla_regiones_embalses():
    """
    Crea una tabla jerárquica que muestra primero las regiones y permite expandir para ver embalses.
    """
    try:
        # Obtener todos los embalses con su información de región
        embalses_info = objetoAPI.request_data('ListadoEmbalses','Sistema','2024-01-01','2024-01-02')
        embalses_info['Values_Name'] = embalses_info['Values_Name'].str.strip().str.upper()
        embalses_info['Values_HydroRegion'] = embalses_info['Values_HydroRegion'].str.strip().str.title()
        
        # Obtener capacidades por embalse
        embalses_capacidad = get_embalses_capacidad()
        
        # Combinar información de región con capacidades
        df_completo = embalses_capacidad.merge(
            embalses_info[['Values_Name', 'Values_HydroRegion']], 
            left_on='Embalse', 
            right_on='Values_Name', 
            how='left'
        )
        
        # Agrupar por región
        regiones_totales = df_completo.groupby('Values_HydroRegion')['Capacidad Útil Diaria (GWh)'].sum().reset_index()
        regiones_totales = regiones_totales.rename(columns={'Values_HydroRegion': 'Región', 'Capacidad Útil Diaria (GWh)': 'Total (GWh)'})
        regiones_totales = regiones_totales.sort_values('Total (GWh)', ascending=False)
        
        # Calcular participación porcentual de regiones
        total_general = regiones_totales['Total (GWh)'].sum()
        if total_general > 0:
            regiones_totales['Participación (%)'] = (regiones_totales['Total (GWh)'] / total_general * 100).round(2)
            # Ajustar para que sume exactamente 100%
            diferencia = 100 - regiones_totales['Participación (%)'].sum()
            if abs(diferencia) > 0.001:
                idx_max = regiones_totales['Participación (%)'].idxmax()
                regiones_totales.loc[idx_max, 'Participación (%)'] += diferencia
                regiones_totales['Participación (%)'] = regiones_totales['Participación (%)'].round(2)
        else:
            regiones_totales['Participación (%)'] = 0
        
        # Agregar identificador de tipo
        regiones_totales['Tipo'] = 'region'
        regiones_totales['ID'] = range(len(regiones_totales))
        
        return regiones_totales, df_completo
        
    except Exception as e:
        print(f"Error creando tabla de regiones: {e}")
        return pd.DataFrame(), pd.DataFrame()

def create_collapsible_regions_table():
    """
    Crea una tabla expandible elegante con regiones que se pueden plegar/desplegar para ver embalses.
    """
    try:
        regiones_totales, df_completo_embalses = get_tabla_regiones_embalses()
        
        if regiones_totales.empty:
            return dbc.Alert("No se encontraron datos de regiones.", color="warning", className="text-center")
        
        # Crear componentes colapsables elegantes para cada región
        region_components = []
        
        for idx, region_row in regiones_totales.iterrows():
            region_name = region_row['Región']
            total_gwh = region_row['Total (GWh)']
            participacion = region_row['Participación (%)']
            
            # Obtener embalses de la región
            embalses_region = get_embalses_by_region(region_name, df_completo_embalses)
            
            # Contar embalses para mostrar en el header
            num_embalses = len(embalses_region) if not embalses_region.empty else 0
            
            # Crear contenido de embalses con las dos tablas lado a lado
            if not embalses_region.empty:
                # Preparar datos para las tablas con formateo
                embalses_data_formatted = []
                embalses_data_raw = []  # Para cálculos
                for _, embalse_row in embalses_region.iterrows():
                    embalse_name = embalse_row['Región'].replace('    └─ ', '')
                    embalse_capacidad = embalse_row['Total (GWh)']
                    embalse_participacion = embalse_row['Participación (%)']
                    
                    embalses_data_formatted.append({
                        'Embalse': embalse_name,
                        'Capacidad Útil Diaria (GWh)': format_number(embalse_capacidad),  # Formatear números
                        'Participación (%)': embalse_participacion
                    })
                    
                    embalses_data_raw.append({
                        'Embalse': embalse_name,
                        'Capacidad Útil Diaria (GWh)': embalse_capacidad,  # Sin formatear para cálculos
                        'Participación (%)': embalse_participacion
                    })
                
                # Calcular total para la tabla de capacidad
                total_capacidad = sum([row['Capacidad Útil Diaria (GWh)'] for row in embalses_data_raw])
                
                # Crear tabla de participación porcentual
                tabla_participacion = dash_table.DataTable(
                    data=[{
                        'Embalse': row['Embalse'],
                        'Participación (%)': row['Participación (%)']
                    } for row in embalses_data_formatted] + [{'Embalse': 'TOTAL', 'Participación (%)': '100.0%'}],
                    columns=[
                        {"name": "Embalse", "id": "Embalse"},
                        {"name": "Participación (%)", "id": "Participación (%)"}
                    ],
                    style_cell={
                        'textAlign': 'left',
                        'padding': '8px',
                        'fontFamily': 'Inter, Arial, sans-serif',
                        'fontSize': 13,
                        'backgroundColor': '#f8f9fa',
                        'border': '1px solid #dee2e6'
                    },
                    style_header={
                        'backgroundColor': '#667eea',
                        'color': 'white',
                        'fontWeight': 'bold',
                        'fontSize': 14,
                        'textAlign': 'center',
                        'border': '1px solid #5a6cf0'
                    },
                    style_data_conditional=[
                        {
                            'if': {'filter_query': '{Embalse} = "TOTAL"'},
                            'backgroundColor': '#007bff',
                            'color': 'white',
                            'fontWeight': 'bold'
                        }
                    ],
                    page_action="none"
                )
                
                # Crear tabla de capacidad detallada
                tabla_capacidad = dash_table.DataTable(
                    data=embalses_data_formatted + [{
                        'Embalse': 'TOTAL',
                        'Capacidad Útil Diaria (GWh)': format_number(total_capacidad),
                        'Participación (%)': ''
                    }],
                    columns=create_embalse_table_columns(embalses_df_formatted),
                    style_cell={
                        'textAlign': 'left',
                        'padding': '8px',
                        'fontFamily': 'Inter, Arial, sans-serif',
                        'fontSize': 13,
                        'backgroundColor': '#f8f9fa',
                        'border': '1px solid #dee2e6'
                    },
                    style_header={
                        'backgroundColor': '#28a745',
                        'color': 'white',
                        'fontWeight': 'bold',
                        'fontSize': 14,
                        'textAlign': 'center',
                        'border': '1px solid #218838'
                    },
                    style_data_conditional=[
                        {
                            'if': {'filter_query': '{Embalse} = "TOTAL"'},
                            'backgroundColor': '#007bff',
                            'color': 'white',
                            'fontWeight': 'bold'
                        }
                    ],
                    page_action="none"
                )
                
                embalses_content = html.Div([
                    html.Div([
                        html.I(className="bi bi-building me-2", style={"color": "#28a745"}),
                        html.Strong(f"Análisis Detallado - {region_name}", 
                                  className="text-success", style={"fontSize": "1.1rem"})
                    ], className="mb-4 d-flex align-items-center"),
                    
                    # Las dos tablas lado a lado
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader([
                                    html.I(className="bi bi-pie-chart me-2", style={"color": "#667eea"}),
                                    html.Strong("📊 Participación Porcentual por Embalse")
                                ], style={"background": "linear-gradient(135deg, #e3f2fd 0%, #f3f4f6 100%)",
                                         "border": "none", "borderRadius": "8px 8px 0 0"}),
                                dbc.CardBody([
                                    html.P("Distribución porcentual de la capacidad energética entre embalses. La tabla incluye una fila TOTAL que suma exactamente 100%.", 
                                          className="text-muted mb-3", style={"fontSize": "0.85rem"}),
                                    tabla_participacion
                                ], className="p-3")
                            ], className="card-modern h-100")
                        ], md=6),
                        
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader([
                                    html.I(className="bi bi-battery-full me-2", style={"color": "#28a745"}),
                                    html.Strong("🏭 Capacidad Detallada por Embalse")
                                ], style={"background": "linear-gradient(135deg, #e8f5e8 0%, #f3f4f6 100%)",
                                         "border": "none", "borderRadius": "8px 8px 0 0"}),
                                dbc.CardBody([
                                    html.P(f"Valores específicos de capacidad útil diaria en GWh para los {num_embalses} embalses de la región.", 
                                          className="text-muted mb-3", style={"fontSize": "0.85rem"}),
                                    tabla_capacidad
                                ], className="p-3")
                            ], className="card-modern h-100")
                        ], md=6)
                    ], className="g-3")
                ])
            else:
                embalses_content = dbc.Alert([
                    html.I(className="bi bi-exclamation-triangle me-2"),
                    f"No se encontraron embalses para la región {region_name}."
                ], color="light", className="text-center my-3 alert-modern")
            
            # Crear card principal elegante para la región
            region_card = dbc.Card([
                # Header clickeable de la región
                dbc.CardHeader([
                    dbc.Button([
                        html.Div([
                            html.Div([
                                html.I(className="bi bi-chevron-right me-3", 
                                       id={"type": "chevron-region", "index": idx},
                                       style={"fontSize": "1.1rem", "color": "#007bff", "transition": "transform 0.3s ease"}),
                                html.I(className="bi bi-geo-alt-fill me-2", style={"color": "#28a745"}),
                                html.Strong(region_name, style={"fontSize": "1.1rem", "color": "#2d3748"})
                            ], className="d-flex align-items-center"),
                            html.Div([
                                dbc.Badge(f"{format_number(total_gwh)} GWh", color="primary", className="me-2 px-2 py-1"),
                                dbc.Badge(f"{participacion}%", color="success", className="px-2 py-1"),
                                html.Small(f" • {num_embalses} embalse{'s' if num_embalses != 1 else ''}", 
                                         className="text-muted ms-2")
                            ], className="d-flex align-items-center mt-1")
                        ], className="d-flex justify-content-between align-items-start w-100")
                    ], 
                    id={"type": "toggle-region", "index": idx},
                    className="w-100 text-start border-0 bg-transparent p-0",
                    style={"background": "transparent !important"}
                    )
                ], className="border-0 bg-gradient", 
                style={
                    "background": f"linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)",
                    "borderRadius": "12px 12px 0 0",
                    "padding": "1rem"
                }),
                
                # Contenido colapsable
                dbc.Collapse([
                    dbc.CardBody([
                        html.Hr(className="mt-0 mb-3", style={"borderColor": "#dee2e6"}),
                        embalses_content
                    ], className="pt-0", style={"backgroundColor": "#fdfdfe"})
                ],
                id={"type": "collapse-region", "index": idx},
                is_open=False
                )
            ], className="mb-3 shadow-sm",
            style={
                "border": "1px solid #e3e6f0",
                "borderRadius": "12px",
                "transition": "all 0.3s ease",
                "overflow": "hidden"
            })
            
            region_components.append(region_card)
        
        return html.Div([
            # Header explicativo elegante
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="bi bi-info-circle-fill me-2", style={"color": "#0d6efd"}),
                        html.Strong("⚡ Capacidad Útil Diaria de Energía por Región Hidrológica", style={"fontSize": "1.2rem"})
                    ], className="d-flex align-items-center mb-2"),
                    html.P([
                        "Haz clic en cualquier región para expandir y ver sus tablas detalladas. ",
                        html.Strong("Cada región muestra dos tablas lado a lado:", className="text-primary"),
                        " participación porcentual de embalses y capacidad energética detallada en GWh."
                    ], className="mb-0 text-dark", style={"fontSize": "0.95rem"})
                ], className="py-3")
            ], className="mb-4", 
            style={
                "background": "linear-gradient(135deg, #e3f2fd 0%, #f3f4f6 100%)",
                "border": "1px solid #bbdefb",
                "borderRadius": "12px"
            }),
            
            # Container de regiones
            html.Div(region_components, id="regions-container")
        ])
        
    except Exception as e:
        print(f"Error creando tabla colapsable: {e}")
        return dbc.Alert(f"Error al crear tabla: {str(e)}", color="danger")


# Callback elegante para manejar el pliegue/despliegue de regiones
@callback(
    [Output({"type": "collapse-region", "index": dash.dependencies.MATCH}, "is_open"),
     Output({"type": "chevron-region", "index": dash.dependencies.MATCH}, "className")],
    [Input({"type": "toggle-region", "index": dash.dependencies.MATCH}, "n_clicks")],
    [State({"type": "collapse-region", "index": dash.dependencies.MATCH}, "is_open")]
)
def toggle_region_collapse(n_clicks, is_open):
    """
    Callback elegante para manejar el toggle de una región específica usando pattern-matching
    """
    if not n_clicks:
        return False, "bi bi-chevron-right me-3"
    
    new_state = not is_open
    if new_state:
        # Expandido - rotar chevron hacia abajo
        return True, "bi bi-chevron-down me-3"
    else:
        # Contraído - chevron hacia la derecha
        return False, "bi bi-chevron-right me-3"


def get_embalses_by_region(region, df_completo):
    """
    Obtiene los embalses de una región específica con participación dentro de esa región.
    """
    embalses_region = df_completo[df_completo['Values_HydroRegion'] == region].copy()
    if embalses_region.empty:
        return pd.DataFrame()
    
    total_region = embalses_region['Capacidad Útil Diaria (GWh)'].sum()
    if total_region > 0:
        embalses_region['Participación (%)'] = (embalses_region['Capacidad Útil Diaria (GWh)'] / total_region * 100).round(2)
        # Ajustar para que sume exactamente 100%
        diferencia = 100 - embalses_region['Participación (%)'].sum()
        if abs(diferencia) > 0.001:
            idx_max = embalses_region['Participación (%)'].idxmax()
            embalses_region.loc[idx_max, 'Participación (%)'] += diferencia
            embalses_region['Participación (%)'] = embalses_region['Participación (%)'].round(2)
    else:
        embalses_region['Participación (%)'] = 0
    
    # Formatear para mostrar como sub-elementos - usar la columna correcta 'Embalse'
    if 'Embalse' in embalses_region.columns:
        resultado = embalses_region[['Embalse', 'Capacidad Útil Diaria (GWh)', 'Participación (%)']].copy()
        resultado = resultado.rename(columns={'Embalse': 'Región', 'Capacidad Útil Diaria (GWh)': 'Total (GWh)'})
        resultado['Región'] = '    └─ ' + resultado['Región'].astype(str)  # Identar embalses
        resultado['Tipo'] = 'embalse'
        return resultado
    else:
        print(f"Warning: Columnas disponibles en df_completo: {embalses_region.columns.tolist()}")
        return pd.DataFrame()
def get_embalses_data_for_table(region=None):
    """
    Función simple que obtiene datos de embalses con 3 columnas formateados para la tabla.
    Garantiza que siempre devuelve las 3 columnas correctamente formateadas.
    """
    try:
        # Obtener datos frescos con las 3 columnas
        df_fresh = get_embalses_capacidad(region)
        
        if df_fresh.empty:
            return []
        
        # Crear datos formateados para la tabla
        table_data = []
        
        for _, row in df_fresh.iterrows():
            formatted_row = {
                'Embalse': row['Embalse'],
                'Capacidad Útil Diaria (GWh)': format_number(row['Capacidad Útil Diaria (GWh)']),
                'Volumen Útil (%)': f"{row['Volumen Útil (%)']:.1f}%" if pd.notna(row['Volumen Útil (%)']) else "N/D"
            }
            table_data.append(formatted_row)
        
        # Agregar fila TOTAL
        total_capacity = df_fresh['Capacidad Útil Diaria (GWh)'].sum()
        valid_volume_data = df_fresh[df_fresh['Volumen Útil (%)'].notna()]
        avg_volume = valid_volume_data['Volumen Útil (%)'].mean() if not valid_volume_data.empty else None
        
        total_row = {
            'Embalse': 'TOTAL',
            'Capacidad Útil Diaria (GWh)': format_number(total_capacity),
            'Volumen Útil (%)': f"{avg_volume:.1f}%" if avg_volume is not None else "N/D"
        }
        table_data.append(total_row)
        
        print(f"✅ DATOS TABLA PREPARADOS: {len(table_data)} filas con 3 columnas")
        return table_data
        
    except Exception as e:
        print(f"❌ Error en get_embalses_data_for_table: {e}")
        return []

def get_embalses_capacidad(region=None):
    """
    Obtiene la capacidad útil diaria de energía por embalse desde la API XM (CapaUtilDiarEner) 
    y el porcentaje de volumen útil diario (PorcVoluUtilDiar).
    Si se pasa una región, filtra los embalses de esa región.
    Solo incluye embalses que tienen datos de capacidad activos.
    """
    try:
        # Obtener datos de capacidad útil diaria de energía
        df_capacidad = objetoAPI.request_data('CapaUtilDiarEner','Embalse','2024-01-01','2024-01-02')
        
        # Obtener datos de porcentaje de volumen útil diario
        df_porcentaje = objetoAPI.request_data('PorcVoluUtilDiar','Embalse','2024-01-01','2024-01-02')
        print(f"📊 Datos de capacidad útil: {len(df_capacidad)} registros")
        print(f"💧 Datos de porcentaje de volumen útil: {len(df_porcentaje)} registros")
        
        if 'Name' in df_capacidad.columns and 'Value' in df_capacidad.columns:
            # Obtener información de región para embalses
            embalses_info = objetoAPI.request_data('ListadoEmbalses','Sistema','2024-01-01','2024-01-02')
            embalses_info['Values_Name'] = embalses_info['Values_Name'].str.strip().str.upper()
            embalses_info['Values_HydroRegion'] = embalses_info['Values_HydroRegion'].str.strip().str.title()
            embalse_region_dict = dict(zip(embalses_info['Values_Name'], embalses_info['Values_HydroRegion']))
            
            # Solo incluir embalses que tienen datos de capacidad
            embalses_con_datos = set(df_capacidad['Name'].unique())
            embalse_region_dict_filtrado = {
                embalse: region for embalse, region in embalse_region_dict.items() 
                if embalse in embalses_con_datos
            }
            
            # Procesar datos de capacidad
            df_capacidad['Region'] = df_capacidad['Name'].map(embalse_region_dict_filtrado)
            if region:
                df_capacidad = df_capacidad[df_capacidad['Region'] == region]
            df_capacidad_grouped = df_capacidad.groupby('Name')['Value'].sum().reset_index()
            df_capacidad_grouped = df_capacidad_grouped.rename(columns={'Name': 'Embalse', 'Value': 'Capacidad Útil Diaria (GWh)'})
            
            # Procesar datos de porcentaje de volumen útil
            df_porcentaje_final = pd.DataFrame()
            if not df_porcentaje.empty and 'Name' in df_porcentaje.columns and 'Value' in df_porcentaje.columns:
                df_porcentaje['Region'] = df_porcentaje['Name'].map(embalse_region_dict_filtrado)
                if region:
                    df_porcentaje = df_porcentaje[df_porcentaje['Region'] == region]
                df_porcentaje_grouped = df_porcentaje.groupby('Name')['Value'].mean().reset_index()
                df_porcentaje_grouped = df_porcentaje_grouped.rename(columns={'Name': 'Embalse', 'Value': 'Volumen Útil (%)'})
                df_porcentaje_final = df_porcentaje_grouped
            
            # Combinar ambos datasets
            if not df_porcentaje_final.empty:
                df_final = pd.merge(df_capacidad_grouped, df_porcentaje_final, on='Embalse', how='left')
                print(f"📊 Merge exitoso - Columnas finales: {list(df_final.columns)}")
                print(f"📊 Primeras filas del DataFrame final:")
                print(df_final.head())
            else:
                df_final = df_capacidad_grouped.copy()
                df_final['Volumen Útil (%)'] = None
                print("⚠️ No hay datos de porcentaje - columna creada con valores None")
                print(f"📊 Columnas finales: {list(df_final.columns)}")
                
            return df_final.sort_values('Embalse')
        else:
            return pd.DataFrame(columns=['Embalse', 'Capacidad Útil Diaria (GWh)', 'Volumen Útil (%)'])
    except Exception as e:
        print(f"Error obteniendo datos de embalses: {e}")
        return pd.DataFrame(columns=['Embalse', 'Capacidad Útil Diaria (GWh)', 'Volumen Útil (%)'])

def create_embalse_table_columns(df):
    """Crea las columnas para la tabla de embalses dinámicamente según las columnas disponibles"""
    columns = []
    print(f"🔧 Creando columnas para tabla - DataFrame tiene: {list(df.columns) if not df.empty else 'VACÍO'}")
    if not df.empty:
        for col in df.columns:
            if col == "Embalse":
                columns.append({"name": "Embalse", "id": "Embalse"})
                print(f"✅ Agregada columna: Embalse")
            elif col == "Capacidad Útil Diaria (GWh)":
                columns.append({"name": "Capacidad Útil Diaria (GWh)", "id": "Capacidad Útil Diaria (GWh)"})
                print(f"✅ Agregada columna: Capacidad Útil Diaria (GWh)")
            elif col == "Volumen Útil (%)":
                columns.append({"name": "Volumen Útil (%)", "id": "Volumen Útil (%)"})
                print(f"✅ Agregada columna: Volumen Útil (%)")
    print(f"🔧 Total de columnas creadas: {len(columns)}")
    return columns

def create_initial_embalse_table():
    """Crea la tabla inicial de embalses con la nueva columna"""
    try:
        print("🚀 CREANDO TABLA INICIAL DE EMBALSES...")
        
        # Obtener datos directamente
        df = get_embalses_capacidad()
        print(f"📊 Datos iniciales obtenidos: {df.shape[0]} filas, columnas: {list(df.columns)}")
        
        if df.empty:
            return dbc.Alert("No hay datos de embalses para mostrar.", color="warning")
        
        # Formatear datos
        df_formatted = df.copy()
        df_formatted['Capacidad Útil Diaria (GWh)'] = df['Capacidad Útil Diaria (GWh)'].apply(format_number)
        
        if 'Volumen Útil (%)' in df.columns:
            df_formatted['Volumen Útil (%)'] = df['Volumen Útil (%)'].apply(
                lambda x: f"{x:.1f}%" if pd.notna(x) else "N/D"
            )
            print("✅ Columna 'Volumen Útil (%)' formateada en tabla inicial")
        
        # Agregar fila TOTAL
        total_capacity = df['Capacidad Útil Diaria (GWh)'].sum()
        total_row_data = {
            'Embalse': ['TOTAL'],
            'Capacidad Útil Diaria (GWh)': [format_number(total_capacity)]
        }
        
        if 'Volumen Útil (%)' in df.columns:
            valid_data = df[df['Volumen Útil (%)'].notna()]
            avg_volume_pct = valid_data['Volumen Útil (%)'].mean() if not valid_data.empty else None
            total_row_data['Volumen Útil (%)'] = [f"{avg_volume_pct:.1f}%" if avg_volume_pct is not None else "N/D"]
        
        total_row = pd.DataFrame(total_row_data)
        df_formatted = pd.concat([df_formatted, total_row], ignore_index=True)
        
        print(f"📊 DataFrame final para tabla inicial: {df_formatted.shape[0]} filas, columnas: {list(df_formatted.columns)}")
        
        return create_dynamic_embalse_table(df_formatted)
        
    except Exception as e:
        print(f"❌ Error creando tabla inicial: {e}")
        import traceback
        traceback.print_exc()
        return dbc.Alert(f"Error: {str(e)}", color="danger")

def create_dynamic_embalse_table(df_formatted):
    """Crea una tabla de embalses dinámicamente con todas las columnas disponibles"""
    print(f"🏗️ INICIO create_dynamic_embalse_table - DataFrame: {df_formatted.shape if not df_formatted.empty else 'VACÍO'}")
    
    if df_formatted.empty:
        print("⚠️ DataFrame vacío - retornando alerta")
        return dbc.Alert("No hay datos de embalses para mostrar.", color="warning")
    
    print(f"🏗️ Creando tabla dinámica de embalses con {len(df_formatted)} filas y columnas: {list(df_formatted.columns)}")
    
    # Crear columnas dinámicamente
    columns = create_embalse_table_columns(df_formatted)
    print(f"🔧 Columnas creadas: {len(columns)}")
    
    # Crear la tabla
    table = dash_table.DataTable(
        id="tabla-capacidad-embalse",
        data=df_formatted.to_dict('records'),
        columns=columns,
        style_cell={'textAlign': 'left', 'padding': '6px', 'fontFamily': 'Arial', 'fontSize': 14},
        style_header={'backgroundColor': '#e3e3e3', 'fontWeight': 'bold'},
        style_data={'backgroundColor': '#f8f8f8'},
        style_data_conditional=[
            {
                'if': {'filter_query': '{Embalse} = "TOTAL"'},
                'backgroundColor': '#007bff',
                'color': 'white',
                'fontWeight': 'bold'
            }
        ],
        page_action="none"
    )
    
    print(f"✅ Tabla DataTable creada exitosamente con ID: {table.id}")
    return table
    
def create_data_table(data):
    """Tabla simple de datos de caudal con participación porcentual"""
    if data is None or data.empty:
        return dbc.Alert("No hay datos para mostrar en la tabla.", color="warning")
    
    # Crear una copia del dataframe para modificar
    df_with_participation = data.copy()
    
    # Formatear fechas si existe columna de fecha
    date_columns = [col for col in df_with_participation.columns if 'fecha' in col.lower() or 'date' in col.lower()]
    for col in date_columns:
        df_with_participation[col] = df_with_participation[col].apply(format_date)
    
    # Si tiene columna 'GWh', calcular participación
    if 'GWh' in df_with_participation.columns:
        # Filtrar filas que no sean TOTAL para calcular el porcentaje
        df_no_total = df_with_participation[df_with_participation['GWh'] != 'TOTAL'].copy()
        if not df_no_total.empty:
            # Asegurar que los valores son numéricos
            df_no_total['GWh'] = pd.to_numeric(df_no_total['GWh'], errors='coerce')
            total = df_no_total['GWh'].sum()
            
            if total > 0:
                # Calcular porcentajes
                porcentajes = (df_no_total['GWh'] / total * 100).round(2)
                
                # Ajustar para que sume exactamente 100%
                diferencia = 100 - porcentajes.sum()
                if abs(diferencia) > 0.001 and len(porcentajes) > 0:
                    idx_max = porcentajes.idxmax()
                    porcentajes.loc[idx_max] += diferencia
                
                # Agregar la columna de participación
                df_with_participation.loc[df_no_total.index, 'Participación (%)'] = porcentajes.round(2)
                
                # Agregar fila TOTAL si no existe
                has_total_row = any(df_with_participation.iloc[:, 0] == 'TOTAL')
                if not has_total_row:
                    # Crear fila total
                    total_row = {}
                    for col in df_with_participation.columns:
                        if col == df_with_participation.columns[0]:  # Primera columna (normalmente 'Fecha')
                            total_row[col] = 'TOTAL'
                        elif col == 'GWh':
                            total_row[col] = format_number(total)
                        elif col == 'Participación (%)':
                            total_row[col] = '100.0%'
                        else:
                            total_row[col] = ''
                    
                    # Agregar la fila total al dataframe
                    df_with_participation = pd.concat([df_with_participation, pd.DataFrame([total_row])], ignore_index=True)
            else:
                df_with_participation['Participación (%)'] = 0
        else:
            df_with_participation['Participación (%)'] = 0
    
    # Formatear columnas numéricas (GWh, capacidades, etc.)
    numeric_columns = [col for col in df_with_participation.columns 
                      if any(keyword in col.lower() for keyword in ['gwh', 'capacidad', 'caudal', 'valor', 'value'])]
    
    for col in numeric_columns:
        if col != 'Participación (%)':  # No formatear porcentajes
            df_with_participation[col] = df_with_participation[col].apply(
                lambda x: format_number(x) if pd.notnull(x) and x != 'TOTAL' else x
            )
    
    # Detectar si hay columna de totales
    style_data_conditional = []
    if 'TOTAL' in df_with_participation.values:
        # Buscar la columna que contiene el total
        for col in df_with_participation.columns:
            if any(df_with_participation[col] == 'TOTAL'):
                style_data_conditional.append({
                    'if': {'filter_query': f'{{{col}}} = "TOTAL"'},
                    'backgroundColor': '#007bff',
                    'color': 'white',
                    'fontWeight': 'bold'
                })
    
    return dash_table.DataTable(
        data=df_with_participation.head(1000).to_dict('records'),
        columns=[{"name": i, "id": i} for i in df_with_participation.columns],
        style_cell={'textAlign': 'left', 'padding': '6px', 'fontFamily': 'Arial', 'fontSize': 14},
        style_header={'backgroundColor': '#e3e3e3', 'fontWeight': 'bold'},
        style_data={'backgroundColor': '#f8f8f8'},
        style_data_conditional=style_data_conditional,
        page_action="none",
        export_format="xlsx",
        export_headers="display"
    )

def create_line_chart(data):
    """Gráfico de líneas moderno de caudal"""
    if data is None or data.empty:
        return dbc.Alert("No se pueden crear gráficos con estos datos.", color="warning", className="alert-modern")
    
    # Esperar columnas 'Fecha' y 'GWh' tras el renombrado
    if 'Fecha' in data.columns and 'GWh' in data.columns:
        fig = px.line(data, x='Fecha', y='GWh', 
                     labels={'GWh': "Energía (GWh)", 'Fecha': "Fecha"}, 
                     markers=True)
        
        # Aplicar tema moderno
        fig.update_layout(
            height=400,
            margin=dict(l=20, r=20, t=40, b=20),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Inter, Arial, sans-serif", size=12),
            title_font_size=16,
            xaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128,128,128,0.2)',
                showline=True,
                linewidth=2,
                linecolor='rgba(128,128,128,0.3)'
            ),
            yaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128,128,128,0.2)',
                showline=True,
                linewidth=2,
                linecolor='rgba(128,128,128,0.3)'
            )
        )
        
        # Estilo moderno de la línea
        fig.update_traces(
            line=dict(width=3, color='#667eea'),
            marker=dict(size=8, color='#764ba2', 
                       line=dict(width=2, color='white')),
            hovertemplate='<b>Fecha:</b> %{x}<br><b>Energía:</b> %{y:.2f} GWh<extra></extra>'
        )
        
        return dbc.Card([
            dbc.CardHeader([
                html.I(className="bi bi-graph-up-arrow me-2", style={"color": "#667eea"}),
                html.Strong("Evolución Temporal", style={"fontSize": "1.1rem"})
            ]),
            dbc.CardBody([
                dcc.Graph(figure=fig)
            ], className="p-2")
        ], className="card-modern chart-container")
    else:
        return dbc.Alert("No se pueden crear gráficos con estos datos.", color="warning", className="alert-modern")

def create_bar_chart(data, metric_name):
    """Crear gráfico de líneas moderno por región o río"""
    # Detectar columnas categóricas y numéricas
    cat_cols = [col for col in data.columns if data[col].dtype == 'object']
    num_cols = [col for col in data.columns if data[col].dtype in ['float64', 'int64']]
    
    if not cat_cols or not num_cols:
        return dbc.Alert("No se pueden crear gráficos de líneas con estos datos.", 
                        color="warning", className="alert-modern")
    
    cat_col = cat_cols[0]
    num_col = num_cols[0]
    
    # Si los datos tienen información de región, crear líneas por región
    if 'Region' in data.columns:
        # Agrupar por región y fecha para crear series temporales por región
        if 'Date' in data.columns:
            # Datos diarios por región - series temporales
            fig = px.line(
                data,
                x='Date',
                y='Value', 
                color='Region',
                title="Aportes Energéticos por Región Hidrológica",
                labels={'Value': "Energía (GWh)", 'Date': "Fecha", 'Region': "Región"},
                markers=True,
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            # Asegurar que cada línea tenga información de región para el click
            fig.for_each_trace(lambda t: t.update(legendgroup=t.name, customdata=[t.name] * len(t.x)))
        else:
            # Datos agregados por región - convertir a líneas también
            region_data = data.groupby('Region')[num_col].sum().reset_index()
            region_data = region_data.sort_values(by=num_col, ascending=False)
            
            fig = px.line(
                region_data,
                x='Region',
                y=num_col,
                title="Contribución Total por Región Hidrológica",
                labels={num_col: "Energía (GWh)", 'Region': "Región"},
                markers=True,
                color_discrete_sequence=['#667eea']
            )
    else:
        # Agrupar y ordenar datos de mayor a menor - usar líneas en lugar de barras
        grouped_data = data.groupby(cat_col)[num_col].sum().reset_index()
        grouped_data = grouped_data.sort_values(by=num_col, ascending=False)
        
        fig = px.line(
            grouped_data.head(15),  # Top 15 para mejor visualización
            x=cat_col,
            y=num_col,
            title="Aportes Energéticos por Río",
            labels={num_col: "Energía (GWh)", cat_col: "Río"},
            markers=True,
            color_discrete_sequence=['#667eea']
        )
    
    # Aplicar estilo moderno
    fig.update_layout(
        height=550,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter, Arial, sans-serif", size=12),
        title=dict(
            font_size=16,
            x=0.5,
            xanchor='center',
            font_color='#2d3748'
        ),
        xaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(128,128,128,0.2)',
            showline=True,
            linewidth=2,
            linecolor='rgba(128,128,128,0.3)',
            tickangle=-45
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(128,128,128,0.2)',
            showline=True,
            linewidth=2,
            linecolor='rgba(128,128,128,0.3)'
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Mejorar el estilo para todos los gráficos de líneas
    fig.update_traces(
        marker=dict(size=10, line=dict(width=2, color='white')),
        line=dict(width=4),
        hovertemplate='<b>%{fullData.name}</b><br>Valor: %{y:.2f} GWh<extra></extra>'
    )
    
    chart_title = "Aportes de Energía por Región" if 'Region' in data.columns else "Aportes de Energía por Río"
    
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.I(className="bi bi-graph-up me-2", style={"color": "#667eea"}),
                html.Strong(chart_title, style={"fontSize": "1.2rem"})
            ], className="d-flex align-items-center"),
            html.Small("Haz clic en cualquier punto para ver detalles", className="text-muted")
        ]),
        dbc.CardBody([
            dcc.Graph(id="rio-detail-graph", figure=fig, clear_on_unhover=True)
        ], className="p-2")
    ], className="card-modern chart-container shadow-lg")

def create_latest_value_kpi(data, metric_name):
    """Crear card KPI que muestra el valor más reciente de la serie temporal"""
    if data is None or data.empty:
        return dbc.Alert("No hay datos disponibles", color="warning", className="mb-3")
    
    # Verificar que tengamos las columnas necesarias
    if 'Date' not in data.columns or 'Value' not in data.columns:
        return dbc.Alert("Faltan columnas necesarias", color="warning", className="mb-3")
    
    # Agrupar por fecha y sumar todos los valores
    daily_totals = data.groupby('Date')['Value'].sum().reset_index()
    daily_totals = daily_totals.sort_values('Date')
    
    if daily_totals.empty:
        return dbc.Alert("No hay datos procesados", color="warning", className="mb-3")
    
    # Obtener el valor más reciente
    latest_date = daily_totals['Date'].iloc[-1]
    latest_value = daily_totals['Value'].iloc[-1]
    
    # Formatear fecha
    if hasattr(latest_date, 'strftime'):
        formatted_date = latest_date.strftime('%d/%m/%Y')
    else:
        formatted_date = str(latest_date)
    
    # Formatear valor
    formatted_value = f"{latest_value:,.0f}".replace(",", ".")
    
    # Calcular tendencia si hay datos suficientes
    trend_icon = ""
    trend_color = "#6c757d"
    trend_text = ""
    trend_bg = "#f8f9fa"
    
    if len(daily_totals) >= 2:
        previous_value = daily_totals['Value'].iloc[-2]
        if previous_value != 0:  # Evitar división por cero
            change = latest_value - previous_value
            change_pct = (change / abs(previous_value) * 100)  # Usar valor absoluto para evitar negativos extraños
            
            if change > 0:
                trend_icon = "bi bi-arrow-up-circle-fill"
                trend_color = "#28a745"
                trend_text = f"+{change_pct:.1f}%"
                trend_bg = "#d4edda"
            elif change < 0:
                trend_icon = "bi bi-arrow-down-circle-fill"
                trend_color = "#dc3545"
                trend_text = f"{change_pct:.1f}%"
                trend_bg = "#f8d7da"
            else:
                trend_icon = "bi bi-dash-circle-fill"
                trend_color = "#6c757d"
                trend_text = "0.0%"
                trend_bg = "#e2e3e5"
        else:
            trend_icon = "bi bi-info-circle-fill"
            trend_color = "#17a2b8"
            trend_text = "N/A"
            trend_bg = "#d1ecf1"
    
    return dbc.Card([
        dbc.CardBody([
            # Contenedor principal centrado
            html.Div([
                # Encabezado con ícono
                html.Div([
                    html.I(className="bi bi-lightning-charge-fill me-2", 
                           style={"fontSize": "1.8rem", "color": "#007bff"}),
                    html.H5("Último Registro", className="text-dark mb-0", 
                            style={"fontSize": "1.1rem", "fontWeight": "600"})
                ], className="d-flex align-items-center justify-content-center mb-4"),
                
                # Contenedor principal con valor y tendencia lado a lado
                dbc.Row([
                    dbc.Col([
                        # Valor principal y unidad
                        html.Div([
                            html.H1(f"{formatted_value}", 
                                    className="mb-1", 
                                    style={
                                        "fontWeight": "800", 
                                        "color": "#2d3748", 
                                        "fontSize": "3.5rem",
                                        "lineHeight": "1",
                                        "textAlign": "center"
                                    }),
                            
                            # Unidad centrada
                            html.P("GWh", 
                                   className="text-primary mb-0", 
                                   style={
                                       "fontSize": "1.3rem", 
                                       "fontWeight": "500",
                                       "textAlign": "center"
                                   }),
                        ], className="text-center")
                    ], md=8),
                    
                    dbc.Col([
                        # Indicador de tendencia al lado
                        html.Div([
                            html.Div([
                                html.I(className=trend_icon, 
                                       style={
                                           "fontSize": "2rem", 
                                           "color": trend_color,
                                           "marginBottom": "5px"
                                       }) if trend_icon else None,
                                html.H5(trend_text, 
                                        className="mb-1", 
                                        style={
                                            "color": trend_color, 
                                            "fontWeight": "700",
                                            "fontSize": "1.2rem"
                                        }) if trend_text else None,
                                html.Small("vs anterior",
                                         className="text-muted",
                                         style={"fontSize": "0.75rem"})
                            ], className="text-center p-2 rounded-3",
                               style={
                                   "backgroundColor": trend_bg,
                                   "border": f"2px solid {trend_color}20"
                               })
                        ], className="d-flex align-items-center justify-content-center h-100")
                    ], md=4)
                ], className="mb-3", align="center"),
                
                # Fecha centrada abajo
                html.Div([
                    html.I(className="bi bi-calendar-date me-2", 
                           style={"color": "#6c757d", "fontSize": "1.1rem"}),
                    html.Span(formatted_date, 
                             style={"fontSize": "1rem", "color": "#6c757d"})
                ], className="d-flex align-items-center justify-content-center")
                
            ], className="px-3")
        ], className="py-4 px-4")
    ], className="shadow border-0 mb-4 mx-auto", 
       style={
           "background": "linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%)",
           "borderRadius": "20px",
           "border": "1px solid #e9ecef",
           "maxWidth": "500px",
           "minHeight": "200px"
       })

def get_porcapor_data(fecha_inicio, fecha_fin):
    """Obtener datos de la métrica PorcApor - Aportes % por río"""
    try:
        print(f"🔍 Consultando PorcApor desde {fecha_inicio} hasta {fecha_fin}")
        data = objetoAPI.request_data('PorcApor', 'Rio', fecha_inicio, fecha_fin)
        if not data.empty:
            print(f"✅ Datos PorcApor obtenidos: {len(data)} registros")
            return data
        else:
            print("⚠️ No se encontraron datos de PorcApor")
            return pd.DataFrame()
    except Exception as e:
        print(f"❌ Error obteniendo datos PorcApor: {e}")
        return pd.DataFrame()

def create_porcapor_kpi(fecha_inicio, fecha_fin, region=None, rio=None):
    """Crear tarjeta KPI específica para la métrica PorcApor (Aportes % por río)
    
    Args:
        fecha_inicio: Fecha de inicio del rango
        fecha_fin: Fecha de fin del rango  
        region: Región para filtrar (opcional)
        rio: Río para filtrar (opcional)
    """
    data = get_porcapor_data(fecha_inicio, fecha_fin)
    
    if data is None or data.empty:
        return dbc.Alert("No hay datos de PorcApor disponibles", color="warning", className="mb-3")
    
    # DEBUG: Mostrar las columnas que se recibieron
    print(f"🔍 DEBUG KPI: Columnas recibidas de PorcApor: {list(data.columns)}")
    print(f"🔍 DEBUG KPI: Shape de datos: {data.shape}")
    if not data.empty:
        print(f"🔍 DEBUG KPI: Primeras 2 filas:")
        print(data.head(2).to_string())
    
    # Verificar que tengamos las columnas necesarias
    if 'Date' not in data.columns or 'Value' not in data.columns:
        print(f"❌ DEBUG KPI: Faltan columnas - Date: {'Date' in data.columns}, Value: {'Value' in data.columns}")
        return dbc.Alert(f"Faltan columnas necesarias en PorcApor. Columnas disponibles: {list(data.columns)}", color="warning", className="mb-3")
    
    # Filtrar por río específico si se especifica
    if rio and rio != "__ALL__":
        print(f"🔍 DEBUG KPI: Filtrando por río específico: {rio}")
        data_filtered = data[data['Name'] == rio]
        print(f"🔍 DEBUG KPI: Datos filtrados para {rio}: {len(data_filtered)} registros")
        if data_filtered.empty:
            print(f"❌ DEBUG KPI: No hay datos para el río {rio}")
            available_rios = data['Name'].unique()
            print(f"🔍 DEBUG KPI: Ríos disponibles: {sorted(available_rios)[:10]}...")
            return dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.H6("📊 Aportes % por Sistema", className="text-center mb-2"),
                        html.Hr(),
                        html.P(f"No hay datos de participación porcentual para el río {rio} en este período.", 
                               className="text-center text-muted mb-2"),
                        html.P("Este río puede estar temporalmente fuera de operación o en mantenimiento.", 
                               className="text-center text-muted small mb-2"),
                        html.P("💡 Selecciona otro río con datos activos como DESV. BATATAS, DESV. CHIVOR, etc.", 
                               className="text-center text-info small")
                    ])
                ])
            ], className="text-center shadow-sm mb-3")
        title_suffix = f" - {rio}"
    else:
        # Filtrar por región si se especifica y no es "todas las regiones"
        if region and region != "__ALL_REGIONS__":
            # Agregar información de región usando el mapeo RIO_REGION
            data['Region'] = data['Name'].map(RIO_REGION) 
            data_filtered = data[data['Region'] == region]
            if data_filtered.empty:
                return dbc.Alert(f"No hay datos de PorcApor para la región {region}", color="warning", className="mb-3")
            title_suffix = f" - {region}"
        else:
            data_filtered = data
            title_suffix = ""
    
    # Agrupar por fecha y calcular promedio de los ríos filtrados
    daily_avg = data_filtered.groupby('Date')['Value'].mean().reset_index()
    daily_avg = daily_avg.sort_values('Date')
    
    if daily_avg.empty:
        return dbc.Alert("No hay datos procesados de PorcApor", color="warning", className="mb-3")
    
    # Obtener el valor más reciente
    latest_date = daily_avg['Date'].iloc[-1]
    latest_value = daily_avg['Value'].iloc[-1]
    formatted_date = pd.to_datetime(latest_date).strftime('%d/%m/%Y')
    
    # Formatear el valor como porcentaje
    formatted_value = f"{latest_value:.1f}"
    
    # Calcular tendencia si hay al menos 2 registros
    if len(daily_avg) >= 2:
        previous_value = daily_avg['Value'].iloc[-2]
        change_percent = ((latest_value - previous_value) / previous_value) * 100
        
        if change_percent > 0:
            trend_icon = "bi bi-arrow-up-circle-fill"
            trend_color = "#28a745"
            trend_text = f"+{change_percent:.1f}%"
            trend_bg = "#d4edda"
        elif change_percent < 0:
            trend_icon = "bi bi-arrow-down-circle-fill"
            trend_color = "#dc3545"
            trend_text = f"{change_percent:.1f}%"
            trend_bg = "#f8d7da"
        else:
            trend_icon = "bi bi-dash-circle-fill"
            trend_color = "#ffc107"
            trend_text = "0.0%"
            trend_bg = "#fff3cd"
    else:
        trend_icon = "bi bi-info-circle-fill"
        trend_color = "#17a2b8"
        trend_text = "N/A"
        trend_bg = "#d1ecf1"

    return dbc.Card([
        dbc.CardBody([
            # Contenedor principal centrado
            html.Div([
                # Encabezado con ícono
                html.Div([
                    html.I(className="bi bi-percent me-2", 
                           style={"fontSize": "1.8rem", "color": "#28a745"}),
                    html.H5(f"Aportes % por Sistema{title_suffix}", className="text-dark mb-0", 
                            style={"fontSize": "1.1rem", "fontWeight": "600"})
                ], className="d-flex align-items-center justify-content-center mb-4"),
                
                # Contenedor principal con valor y tendencia lado a lado
                dbc.Row([
                    dbc.Col([
                        # Valor principal y unidad
                        html.Div([
                            html.H1(f"{formatted_value}", 
                                    className="mb-1", 
                                    style={
                                        "fontWeight": "800", 
                                        "color": "#2d3748", 
                                        "fontSize": "3.5rem",
                                        "lineHeight": "1",
                                        "textAlign": "center"
                                    }),
                            
                            # Unidad centrada
                            html.P("%", 
                                   className="text-success mb-0", 
                                   style={
                                       "fontSize": "1.3rem", 
                                       "fontWeight": "500",
                                       "textAlign": "center"
                                   }),
                        ], className="text-center")
                    ], md=8),
                    
                    dbc.Col([
                        # Indicador de tendencia al lado
                        html.Div([
                            html.Div([
                                html.I(className=trend_icon, 
                                       style={
                                           "fontSize": "2rem", 
                                           "color": trend_color,
                                           "marginBottom": "5px"
                                       }) if trend_icon else None,
                                html.H5(trend_text, 
                                        className="mb-1", 
                                        style={
                                            "color": trend_color, 
                                            "fontWeight": "700",
                                            "fontSize": "1.2rem"
                                        }) if trend_text else None,
                                html.Small("vs anterior",
                                         className="text-muted",
                                         style={"fontSize": "0.75rem"})
                            ], className="text-center p-2 rounded-3",
                               style={
                                   "backgroundColor": trend_bg,
                                   "border": f"2px solid {trend_color}20"
                               })
                        ], className="d-flex align-items-center justify-content-center h-100")
                    ], md=4)
                ], className="mb-3", align="center"),
                
                # Fecha centrada abajo
                html.Div([
                    html.I(className="bi bi-calendar-date me-2", 
                           style={"color": "#6c757d", "fontSize": "1.1rem"}),
                    html.Span(formatted_date, 
                             style={"fontSize": "1rem", "color": "#6c757d"})
                ], className="d-flex align-items-center justify-content-center")
                
            ], className="px-3")
        ], className="py-4 px-4")
    ], className="shadow border-0 mb-4 mx-auto", 
       style={
           "background": "linear-gradient(135deg, #e8f5e8 0%, #f0f8f0 100%)",
           "borderRadius": "20px",
           "border": "1px solid #28a745",
           "maxWidth": "500px",
           "minHeight": "200px"
       })

def create_total_timeline_chart(data, metric_name):
    """Crear gráfico de línea temporal con total nacional por día"""
    if data is None or data.empty:
        return dbc.Alert("No se pueden crear gráficos con estos datos.", 
                        color="warning", className="alert-modern")
    
    # Verificar que tengamos las columnas necesarias
    if 'Date' not in data.columns or 'Value' not in data.columns:
        return dbc.Alert("No se encuentran las columnas necesarias (Date, Value).", 
                        color="warning", className="alert-modern")
    
    # Agrupar por fecha y sumar todos los valores de todas las regiones
    daily_totals = data.groupby('Date')['Value'].sum().reset_index()
    daily_totals = daily_totals.sort_values('Date')
    
    # Crear gráfico de línea con una sola línea negra
    fig = px.line(
        daily_totals,
        x='Date',
        y='Value',
        title="Total Nacional de Aportes de Caudal por Día",
        labels={'Value': "Total Energía (GWh)", 'Date': "Fecha"},
        markers=True
    )
    
    # Estilo moderno con línea negra
    fig.update_layout(
        height=500,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter, Arial, sans-serif", size=12),
        title=dict(
            font_size=16,
            x=0.5,
            xanchor='center',
            font_color='#2d3748'
        ),
        xaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(128,128,128,0.2)',
            showline=True,
            linewidth=2,
            linecolor='rgba(128,128,128,0.3)',
            title="Fecha"
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(128,128,128,0.2)',
            showline=True,
            linewidth=2,
            linecolor='rgba(128,128,128,0.3)',
            title="Total Energía (GWh)"
        ),
        showlegend=False
    )
    
    # Aplicar línea negra con marcadores
    fig.update_traces(
        line=dict(width=3, color='black'),
        marker=dict(size=8, color='black', 
                   line=dict(width=2, color='white')),
        hovertemplate='<b>Fecha:</b> %{x}<br><b>Total Nacional:</b> %{y:.2f} GWh<extra></extra>'
    )
    
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.I(className="bi bi-graph-up me-2", style={"color": "#000"}),
                html.Strong("Total Nacional por Día", style={"fontSize": "1.2rem"})
            ], className="d-flex align-items-center"),
            html.Small("Haz clic en cualquier punto para ver detalles por región", className="text-muted")
        ]),
        dbc.CardBody([
            dcc.Graph(id="total-timeline-graph", figure=fig, clear_on_unhover=True)
        ], className="p-2")
    ], className="card-modern chart-container shadow-lg")
# Callback para mostrar el modal con la tabla diaria al hacer click en un punto de la línea
@callback(
    [Output("modal-rio-table", "is_open"), Output("modal-table-content", "children"), 
     Output("modal-title-dynamic", "children"), Output("modal-description", "children")],
    [Input("total-timeline-graph", "clickData"), Input("modal-rio-table", "is_open")],
    [State("region-data-store", "data")],
    prevent_initial_call=True
)
def show_modal_table(timeline_clickData, is_open, region_data):
    ctx = dash.callback_context
    
    print(f"🚀 CALLBACK EJECUTADO! Triggered: {[prop['prop_id'] for prop in ctx.triggered]}")
    print(f" Timeline click data: {timeline_clickData}")
    
    # Determinar qué fue clicado
    clickData = None
    graph_type = None
    
    if ctx.triggered:
        trigger_id = ctx.triggered[0]["prop_id"]
        print(f"🔍 DEBUG: Callback triggered - trigger_id: {trigger_id}")
        
        if trigger_id.startswith("total-timeline-graph") and timeline_clickData:
            clickData = timeline_clickData
            graph_type = "timeline"
            print(f"🎯 DEBUG: Timeline click detected! clickData: {clickData}")
        elif trigger_id.startswith("modal-rio-table"):
            print(f"❌ DEBUG: Modal close triggered")
            return False, None, "", ""
    
    # Si se hace click en un punto del timeline, mostrar el modal con la tabla
    if clickData and graph_type == "timeline":
        point_data = clickData["points"][0]
        print(f"🔍 DEBUG: point_data extraído: {point_data}")
        
        df = pd.DataFrame(region_data) if region_data else pd.DataFrame()
        print(f"📊 DEBUG: region_data recibido: {type(region_data)}, length: {len(region_data) if region_data else 'None'}")
        print(f"📈 DEBUG: DataFrame creado - shape: {df.shape}, columns: {df.columns.tolist() if not df.empty else 'DataFrame vacío'}")
        
        if df.empty:
            print(f"❌ DEBUG: DataFrame está vacío - retornando mensaje de error")
            return False, None, "Sin datos", "No hay información disponible para mostrar."
        
        # Obtener la fecha clicada
        selected_date = point_data['x']
        total_value = point_data['y']
        print(f"📅 DEBUG: Fecha seleccionada: {selected_date}, Total: {total_value}")
        print(f"📅 DEBUG: Tipo de fecha seleccionada: {type(selected_date)}")
        
        # Ver qué fechas están disponibles en el DataFrame
        unique_dates = df['Date'].unique()[:10]  # Primeras 10 fechas únicas
        print(f"📆 DEBUG: Primeras fechas disponibles en DataFrame: {unique_dates}")
        print(f"📆 DEBUG: Tipo de fechas en DataFrame: {type(df['Date'].iloc[0]) if not df.empty else 'N/A'}")
        
        # Filtrar datos de esa fecha específica
        df_date = df[df['Date'] == selected_date].copy()
        print(f"🗓️ DEBUG: Datos filtrados por fecha - shape: {df_date.shape}")
        
        # Si no hay datos, intentar convertir la fecha a diferentes formatos
        if df_date.empty:
            print(f"🔄 DEBUG: Intentando conversiones de fecha...")
            # Intentar convertir la fecha seleccionada a datetime
            try:
                from datetime import datetime
                if isinstance(selected_date, str):
                    selected_date_dt = pd.to_datetime(selected_date)
                    print(f"🔄 DEBUG: Fecha convertida a datetime: {selected_date_dt}")
                    # Intentar filtrar con la fecha convertida
                    df_date = df[df['Date'] == selected_date_dt].copy()
                    print(f"🔄 DEBUG: Datos filtrados con fecha convertida - shape: {df_date.shape}")
                
                # Si aún no hay datos, intentar convertir las fechas del DataFrame
                if df_date.empty:
                    print(f"🔄 DEBUG: Convirtiendo fechas del DataFrame...")
                    df['Date'] = pd.to_datetime(df['Date'])
                    df_date = df[df['Date'] == selected_date_dt].copy()
                    print(f"🔄 DEBUG: Datos filtrados después de conversión DF - shape: {df_date.shape}")
                    
            except Exception as e:
                print(f"❌ DEBUG: Error en conversión de fechas: {e}")
        
        print(f"🔍 DEBUG: Primeras filas de df_date: {df_date.head(3).to_dict() if not df_date.empty else 'No hay datos'}")
        
        if df_date.empty:
            print(f"❌ DEBUG: No hay datos para la fecha {selected_date}")
            return False, None, f"Sin datos para {selected_date}", f"No se encontraron datos para la fecha {selected_date}."
        
        # Agrupar por región para esa fecha
        region_summary = df_date.groupby('Region')['Value'].sum().reset_index()
        region_summary = region_summary.sort_values('Value', ascending=False)
        region_summary = region_summary.rename(columns={'Region': 'Región', 'Value': 'Caudal (GWh)'})
        print(f"📊 DEBUG: region_summary creado - shape: {region_summary.shape}")
        print(f"📈 DEBUG: region_summary contenido: {region_summary.to_dict() if not region_summary.empty else 'Vacío'}")
        
        # Calcular participación porcentual
        total = region_summary['Caudal (GWh)'].sum()
        print(f"💰 DEBUG: Total calculado: {total}")
        
        if total > 0:
            region_summary['Participación (%)'] = (region_summary['Caudal (GWh)'] / total * 100).round(2)
            # Ajustar para que sume exactamente 100%
            diferencia = 100 - region_summary['Participación (%)'].sum()
            if abs(diferencia) > 0.001:
                idx_max = region_summary['Participación (%)'].idxmax()
                region_summary.loc[idx_max, 'Participación (%)'] += diferencia
                region_summary['Participación (%)'] = region_summary['Participación (%)'].round(2)
        else:
            region_summary['Participación (%)'] = 0
        
        # Formatear números
        region_summary['Caudal (GWh)'] = region_summary['Caudal (GWh)'].apply(format_number)
        
        # Agregar fila total
        total_row = {
            'Región': 'TOTAL',
            'Caudal (GWh)': format_number(total),
            'Participación (%)': '100.0%'
        }
        
        data_with_total = region_summary.to_dict('records') + [total_row]
        
        # Crear tabla
        table = dash_table.DataTable(
            data=data_with_total,
            columns=[
                {"name": "Región", "id": "Región"},
                {"name": "Caudal (GWh)", "id": "Caudal (GWh)"},
                {"name": "Participación (%)", "id": "Participación (%)"}
            ],
            style_cell={'textAlign': 'left', 'padding': '8px', 'fontFamily': 'Inter, Arial', 'fontSize': 14},
            style_header={'backgroundColor': '#1e40af', 'color': 'white', 'fontWeight': 'bold'},
            style_data={'backgroundColor': '#f8f9fa'},
            style_data_conditional=[
                {
                    'if': {'filter_query': '{Región} = "TOTAL"'},
                    'backgroundColor': '#2563eb',
                    'color': 'white',
                    'fontWeight': 'bold'
                }
            ],
            page_action="none",
            export_format="xlsx",
            export_headers="display"
        )
        
        # Crear título y descripción
        formatted_date = format_date(selected_date)
        total_regions = len(region_summary) - 1 if len(region_summary) > 0 else 0
        title = f"📅 Detalles del {formatted_date} - Total Nacional: {format_number(total_value)} GWh"
        description = f"Detalle por región hidrológica para el día {formatted_date}. Se muestran los aportes de caudal de {total_regions} regiones que registraron actividad en esta fecha, con su respectiva participación porcentual sobre el total nacional de {format_number(total_value)} GWh."
        
        print(f"✅ DEBUG: Título: {title}")
        print(f"✅ DEBUG: Descripción: {description}")
        print(f"✅ DEBUG: Retornando modal abierto con tabla de {len(data_with_total)} filas")
        
        return True, table, title, description
    
    # Si se cierra el modal
    elif ctx.triggered and ctx.triggered[0]["prop_id"].startswith("modal-rio-table"):
        return False, None, "", ""
    
    # Por defecto, modal cerrado
    print(f"⚠️ DEBUG: No se detectó ningún click válido - modal cerrado por defecto")
    return False, None, "", ""

def create_stats_summary(data):
    """Crear resumen estadístico"""
    numeric_data = data.select_dtypes(include=['float64', 'int64'])
    
    if numeric_data.empty:
        return dbc.Alert("No hay datos numéricos para análisis estadístico.", color="warning")
    
    stats = numeric_data.describe()
    
    return dbc.Card([
        dbc.CardHeader([
            html.H6([
                html.I(className="bi bi-calculator me-2"),
                "Resumen Estadístico"
            ], className="mb-0")
        ]),
        dbc.CardBody([
            dash_table.DataTable(
                data=stats.round(2).reset_index().to_dict('records'),
                columns=[{"name": i, "id": i} for i in stats.reset_index().columns],
                style_cell={
                    'textAlign': 'center',
                    'padding': '10px',
                    'fontFamily': 'Arial'
                },
                style_header={
                    'backgroundColor': '#3498db',
                    'color': 'white',
                    'fontWeight': 'bold'
                },
                style_data={'backgroundColor': '#f8f9fa'},
            )
        ])
    ])

# NOTA: Los callbacks de tabla de embalses fueron eliminados para implementación directa en layout

# Callback para cargar opciones de regiones dinámicamente
@callback(
    Output('region-dropdown', 'options'),
    Input('region-dropdown', 'id')  # Se ejecuta al cargar la página
)
def load_region_options(_):
    """Carga las opciones de regiones dinámicamente para evitar bloqueos durante la importación."""
    try:
        regiones_disponibles = get_region_options()
        options = [{"label": "🌍 Todas las regiones", "value": "__ALL_REGIONS__"}]
        options += [{"label": f"🏔️ {r}", "value": r} for r in regiones_disponibles]
        return options
    except Exception as e:
        print(f"Error cargando opciones de regiones: {e}")
        return [{"label": "🌍 Todas las regiones", "value": "__ALL_REGIONS__"}]