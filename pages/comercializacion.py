"""
Página de Comercialización - Portal Energético MME
Análisis de precios de bolsa y escasez del mercado eléctrico colombiano
"""

import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
from datetime import date, timedelta
import pandas as pd
import traceback
import logging

from utils.config import COLORS
from utils.components import crear_header, crear_sidebar_universal, crear_boton_regresar
from utils._xm import fetch_metric_data

def get_plotly_modules():
    """Importación diferida de Plotly para optimizar carga inicial"""
    import plotly.express as px
    import plotly.graph_objects as go
    return px, go

# Configurar logging
logger = logging.getLogger(__name__)

# Registrar la página
dash.register_page(__name__, path='/comercializacion', name='Comercialización', title='Comercialización - Portal MME')

# ==================== FUNCIONES DE DATOS ====================

def obtener_precio_bolsa(fecha_inicio, fecha_fin):
    """Obtener datos de Precio Bolsa Nacional (datos horarios)"""
    try:
        df = fetch_metric_data('PrecBolsNaci', 'Sistema', fecha_inicio, fecha_fin)
        
        if df is None or df.empty:
            logger.warning("No se obtuvieron datos de PrecBolsNaci")
            return pd.DataFrame()
        
        # Transformar de formato ancho (24 columnas) a formato largo
        # Calcular promedio diario
        hour_cols = [c for c in df.columns if 'Hour' in c]
        df['Promedio_Diario'] = df[hour_cols].mean(axis=1)
        df['Metrica'] = 'Precio Bolsa Nacional'
        
        # Crear DataFrame con formato consistente
        df_result = pd.DataFrame({
            'Date': pd.to_datetime(df['Date']),
            'Value': df['Promedio_Diario'],
            'Metrica': df['Metrica']
        })
        
        # Guardar datos completos para el modal (con las 24 horas)
        df_result['Datos_Horarios'] = df[['Date'] + hour_cols].to_dict('records')
        
        logger.info(f"✅ PrecBolsNaci: {len(df_result)} días obtenidos")
        return df_result
        
    except Exception as e:
        logger.error(f"Error obteniendo PrecBolsNaci: {e}")
        traceback.print_exc()
        return pd.DataFrame()

def obtener_precio_escasez(fecha_inicio, fecha_fin):
    """Obtener datos de Precio Escasez (datos diarios)"""
    try:
        df = fetch_metric_data('PrecEsca', 'Sistema', fecha_inicio, fecha_fin)
        
        if df is None or df.empty:
            logger.warning("No se obtuvieron datos de PrecEsca")
            return pd.DataFrame()
        
        df['Date'] = pd.to_datetime(df['Date'])
        df['Metrica'] = 'Precio Escasez'
        
        logger.info(f"✅ PrecEsca: {len(df)} días obtenidos")
        return df[['Date', 'Value', 'Metrica']]
        
    except Exception as e:
        logger.error(f"Error obteniendo PrecEsca: {e}")
        traceback.print_exc()
        return pd.DataFrame()

def obtener_precio_escasez_activacion(fecha_inicio, fecha_fin):
    """Obtener datos de Precio Escasez Activación (datos diarios)"""
    try:
        df = fetch_metric_data('PrecEscaAct', 'Sistema', fecha_inicio, fecha_fin)
        
        if df is None or df.empty:
            logger.warning("⚠️ PrecEscaAct: No hay datos disponibles en la API XM")
            return pd.DataFrame()
        
        df['Date'] = pd.to_datetime(df['Date'])
        df['Metrica'] = 'Precio Escasez Activación'
        
        logger.info(f"✅ PrecEscaAct: {len(df)} días obtenidos")
        return df[['Date', 'Value', 'Metrica']]
        
    except Exception as e:
        logger.error(f"Error obteniendo PrecEscaAct: {e}")
        traceback.print_exc()
        return pd.DataFrame()

# ==================== FUNCIONES DE VISUALIZACIÓN ====================

def crear_grafica_precios(df_bolsa, df_escasez, df_escasez_act):
    """Crear gráfica de líneas con los tres precios"""
    px, go = get_plotly_modules()
    
    if df_bolsa.empty and df_escasez.empty and df_escasez_act.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No hay datos disponibles para el rango de fechas seleccionado",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        fig.update_layout(height=500)
        return fig
    
    # Combinar datos de las tres métricas disponibles
    dfs_to_concat = []
    if not df_bolsa.empty:
        dfs_to_concat.append(df_bolsa[['Date', 'Value', 'Metrica']])
    if not df_escasez.empty:
        dfs_to_concat.append(df_escasez[['Date', 'Value', 'Metrica']])
    if not df_escasez_act.empty:
        dfs_to_concat.append(df_escasez_act[['Date', 'Value', 'Metrica']])
    
    df_combinado = pd.concat(dfs_to_concat, ignore_index=True)
    
    # Crear gráfica
    fig = px.line(
        df_combinado,
        x='Date',
        y='Value',
        color='Metrica',
        title='Evolución de Precios del Mercado Eléctrico',
        labels={'Date': 'Fecha', 'Value': 'Precio ($/kWh)', 'Metrica': 'Métrica'},
        color_discrete_map={
            'Precio Bolsa Nacional': '#FFB800',  # Amarillo/Naranja brillante
            'Precio Escasez': '#DC3545',  # Rojo
            'Precio Escasez Activación': '#28A745'  # Verde
        }
    )
    
    fig.update_traces(mode='lines+markers', marker=dict(size=8), line=dict(width=2))
    
    fig.update_layout(
        height=500,
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family='Arial', size=12),
        xaxis=dict(
            showgrid=True,
            gridcolor='lightgray',
            title_font=dict(size=14, color='black')
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='lightgray',
            title_font=dict(size=14, color='black')
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig

def crear_tabla_horaria(datos_hora, fecha_seleccionada):
    """Crear tabla con datos horarios de un día específico"""
    if not datos_hora or not isinstance(datos_hora, dict):
        return html.Div("No hay datos horarios disponibles", 
                       className="alert alert-warning")
    
    # Extraer valores de cada hora
    horas = []
    valores = []
    
    for i in range(1, 25):
        col_name = f'Values_Hour{i:02d}'
        if col_name in datos_hora:
            horas.append(f"Hora {i:02d}")
            valores.append(f"${datos_hora[col_name]:.2f}")
    
    if not horas:
        return html.Div("No hay datos horarios disponibles", 
                       className="alert alert-warning")
    
    # Crear DataFrame para la tabla
    df_tabla = pd.DataFrame({
        'Hora': horas,
        'Precio ($/kWh)': valores
    })
    
    # Dividir en 3 columnas para mejor visualización
    n = len(horas)
    tercio = n // 3
    
    col1 = df_tabla.iloc[:tercio]
    col2 = df_tabla.iloc[tercio:tercio*2]
    col3 = df_tabla.iloc[tercio*2:]
    
    def crear_mini_tabla(df_mini):
        return html.Table([
            html.Thead(html.Tr([
                html.Th("Hora", style={'padding': '8px', 'borderBottom': '2px solid #dee2e6'}),
                html.Th("Precio", style={'padding': '8px', 'borderBottom': '2px solid #dee2e6', 'textAlign': 'right'})
            ])),
            html.Tbody([
                html.Tr([
                    html.Td(row['Hora'], style={'padding': '6px'}),
                    html.Td(row['Precio ($/kWh)'], style={'padding': '6px', 'textAlign': 'right', 'fontWeight': 'bold'})
                ]) for _, row in df_mini.iterrows()
            ])
        ], className="table table-sm table-hover", style={'marginBottom': '0'})
    
    return html.Div([
        dbc.Row([
            dbc.Col(crear_mini_tabla(col1), md=4),
            dbc.Col(crear_mini_tabla(col2), md=4),
            dbc.Col(crear_mini_tabla(col3), md=4)
        ])
    ])

# ==================== LAYOUT ====================

def layout(**kwargs):
    """Layout principal de la página de comercialización"""
    
    # Configurar valores por defecto
    fecha_fin = date.today() - timedelta(days=1)
    fecha_inicio = fecha_fin - timedelta(days=365)  # Último año completo por defecto
    precio_promedio_bolsa = 0.0
    precio_max_bolsa = 0.0
    precio_escasez_actual = 0.0
    
    # Obtener datos iniciales de las tres métricas
    try:
        df_bolsa = obtener_precio_bolsa(fecha_inicio, fecha_fin)
        df_escasez = obtener_precio_escasez(fecha_inicio, fecha_fin)
        df_escasez_act = obtener_precio_escasez_activacion(fecha_inicio, fecha_fin)
        
        fig_precios = crear_grafica_precios(df_bolsa, df_escasez, df_escasez_act)
        
        # Calcular estadísticas para las fichas
        if not df_bolsa.empty:
            precio_promedio_bolsa = float(df_bolsa['Value'].mean())
            precio_max_bolsa = float(df_bolsa['Value'].max())
        
        if not df_escasez.empty:
            precio_escasez_actual = float(df_escasez['Value'].iloc[-1])
        
    except Exception as e:
        logger.error(f"Error cargando datos iniciales: {e}")
        traceback.print_exc()
        px, go = get_plotly_modules()
        fig_precios = go.Figure()
        fig_precios.add_annotation(
            text="Error al cargar datos. Por favor, actualice la página.",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="red")
        )
    
    return html.Div([
        crear_sidebar_universal(),
        crear_boton_regresar(),
        
        dbc.Container([
            # Header
            crear_header(
                "⚡ COMERCIALIZACIÓN",
                "Análisis de precios del mercado eléctrico colombiano"
            ),
            
            # Información importante sobre las métricas
            dbc.Alert([
                html.I(className="fas fa-info-circle me-2"),
                html.Strong("Métricas implementadas: "),
                html.Br(),
                "📊 ", html.Strong("Precio Bolsa Nacional"), " (PrecBolsNaci): Promedio diario de 24 horas. Click en punto para ver detalle horario.",
                html.Br(),
                "⚠️ ", html.Strong("Precio Escasez"), " (PrecEsca): Precio diario de escasez del sistema.",
                html.Br(),
                "🔶 ", html.Strong("Precio Escasez Activación"), " (PrecEscaAct): Precio de activación de escasez."
            ], color="info", className="mb-4"),
            
            # Controles de filtro
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            dbc.Row([
                                # Selector de rango de fechas
                                dbc.Col([
                                    html.Label("Rango de Fechas:", 
                                             style={'fontWeight': 'bold', 'marginBottom': '8px'}),
                                    dcc.DatePickerRange(
                                        id='selector-fechas-comercializacion',
                                        start_date=fecha_inicio,
                                        end_date=fecha_fin,
                                        display_format='YYYY-MM-DD',
                                        max_date_allowed=date.today(),
                                        style={'width': '100%'}
                                    )
                                ], md=8, className="mb-3"),
                                
                                # Botón de actualizar
                                dbc.Col([
                                    html.Label("\u00A0", style={'display': 'block'}),  # Espaciador
                                    dbc.Button(
                                        [html.I(className="fas fa-sync-alt me-2"), "Actualizar Datos"],
                                        id='btn-actualizar-comercializacion',
                                        color="primary",
                                        className="w-100"
                                    )
                                ], md=4)
                            ])
                        ])
                    ], className="mb-4 shadow-sm")
                ])
            ]),
            
            # Fichas KPI
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("💰 Precio Promedio Bolsa", className="text-muted mb-2"),
                            html.H3(f"${precio_promedio_bolsa:.2f}", 
                                   id='ficha-precio-promedio',
                                   style={'color': COLORS.get('primary', '#0d6efd')}),
                            html.Small("$/kWh", className="text-muted")
                        ])
                    ], className="shadow-sm mb-4")
                ], md=4),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("📈 Precio Máximo Bolsa", className="text-muted mb-2"),
                            html.H3(f"${precio_max_bolsa:.2f}", 
                                   id='ficha-precio-max',
                                   style={'color': COLORS.get('warning', '#ffc107')}),
                            html.Small("$/kWh", className="text-muted")
                        ])
                    ], className="shadow-sm mb-4")
                ], md=4),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("⚠️ Precio Escasez Actual", className="text-muted mb-2"),
                            html.H3(f"${precio_escasez_actual:.2f}", 
                                   id='ficha-precio-escasez',
                                   style={'color': COLORS.get('danger', '#dc3545')}),
                            html.Small("$/kWh", className="text-muted")
                        ])
                    ], className="shadow-sm mb-4")
                ], md=4)
            ]),
            
            # Gráfica principal
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("📊 Evolución de Precios", className="mb-0")),
                        dbc.CardBody([
                            dcc.Loading(
                                dcc.Graph(
                                    id='grafica-precios-comercializacion',
                                    figure=fig_precios,
                                    config={'displayModeBar': True, 'displaylogo': False}
                                )
                            )
                        ])
                    ], className="shadow-sm mb-4")
                ])
            ]),
            
            # Store para datos
            dcc.Store(id='store-comercializacion', data=None),
            
            # Modal para detalle horario
            dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle(id='modal-titulo-comercializacion')),
                dbc.ModalBody(id='modal-contenido-comercializacion'),
                dbc.ModalFooter(
                    dbc.Button("Cerrar", id='modal-cerrar-comercializacion', className="ms-auto")
                )
            ], id='modal-detalle-comercializacion', size='xl', is_open=False)
            
        ], fluid=True, className="p-4")
    ])

# ==================== CALLBACKS ====================

@callback(
    [Output('grafica-precios-comercializacion', 'figure'),
     Output('store-comercializacion', 'data'),
     Output('ficha-precio-promedio', 'children'),
     Output('ficha-precio-max', 'children'),
     Output('ficha-precio-escasez', 'children')],
    [Input('btn-actualizar-comercializacion', 'n_clicks')],
    [State('selector-fechas-comercializacion', 'start_date'),
     State('selector-fechas-comercializacion', 'end_date')],
    prevent_initial_call=True
)
def actualizar_datos_comercializacion(n_clicks, fecha_inicio_str, fecha_fin_str):
    """Callback para actualizar la gráfica y fichas según las fechas seleccionadas"""
    
    px, go = get_plotly_modules()
    
    try:
        # Convertir fechas
        fecha_inicio = pd.to_datetime(fecha_inicio_str).date()
        fecha_fin = pd.to_datetime(fecha_fin_str).date()
        
        # Validar rango
        if (fecha_fin - fecha_inicio).days > 365:
            fig_error = go.Figure().add_annotation(
                text="Por favor seleccione un rango menor a 365 días",
                xref="paper", yref="paper", x=0.5, y=0.5,
                showarrow=False, font=dict(size=16, color="red")
            )
            return fig_error, None, "$0.00", "$0.00", "$0.00"
        
        # Obtener datos de las tres métricas
        df_bolsa = obtener_precio_bolsa(fecha_inicio, fecha_fin)
        df_escasez = obtener_precio_escasez(fecha_inicio, fecha_fin)
        df_escasez_act = obtener_precio_escasez_activacion(fecha_inicio, fecha_fin)
        
        # Crear gráfica con las tres métricas
        fig = crear_grafica_precios(df_bolsa, df_escasez, df_escasez_act)
        
        # Calcular estadísticas
        precio_promedio = df_bolsa['Value'].mean() if not df_bolsa.empty else 0.0
        precio_max = df_bolsa['Value'].max() if not df_bolsa.empty else 0.0
        precio_escasez = df_escasez['Value'].iloc[-1] if not df_escasez.empty else 0.0
        
        # Guardar datos en store (las tres métricas)
        store_data = {
            'bolsa': df_bolsa.to_json(date_format='iso', orient='split') if not df_bolsa.empty else None,
            'escasez': df_escasez.to_json(date_format='iso', orient='split') if not df_escasez.empty else None,
            'escasez_act': df_escasez_act.to_json(date_format='iso', orient='split') if not df_escasez_act.empty else None
        }
        
        return (
            fig, 
            store_data,
            f"${precio_promedio:.2f}",
            f"${precio_max:.2f}",
            f"${precio_escasez:.2f}"
        )
        
    except Exception as e:
        logger.error(f"Error en actualizar_datos_comercializacion: {e}")
        traceback.print_exc()
        
        fig_error = go.Figure().add_annotation(
            text=f"Error al cargar datos: {str(e)[:100]}",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=14, color="red")
        )
        
        return fig_error, None, "$0.00", "$0.00", "$0.00"

@callback(
    [Output('modal-detalle-comercializacion', 'is_open'),
     Output('modal-titulo-comercializacion', 'children'),
     Output('modal-contenido-comercializacion', 'children')],
    [Input('grafica-precios-comercializacion', 'clickData'),
     Input('modal-cerrar-comercializacion', 'n_clicks')],
    [State('store-comercializacion', 'data'),
     State('modal-detalle-comercializacion', 'is_open')],
    prevent_initial_call=True
)
def toggle_modal_detalle(clickData, close_clicks, store_data, is_open):
    """Abrir/cerrar modal con detalle horario al hacer clic en la gráfica"""
    
    from dash import callback_context as ctx
    
    if not ctx.triggered:
        return False, "", ""
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Cerrar modal
    if trigger_id == 'modal-cerrar-comercializacion':
        return False, "", ""
    
    # Abrir modal con datos
    if trigger_id == 'grafica-precios-comercializacion' and clickData:
        try:
            # Extraer información del click
            punto = clickData['points'][0]
            fecha_click = pd.to_datetime(punto['x']).date()
            metrica = punto['data']['name']
            
            # Solo mostrar detalle horario para Precio Bolsa Nacional
            if metrica != 'Precio Bolsa Nacional':
                return False, "", ""
            
            if not store_data or not store_data.get('bolsa'):
                return False, "", ""
            
            # Cargar datos
            df_bolsa = pd.read_json(store_data['bolsa'], orient='split')
            df_bolsa['Date'] = pd.to_datetime(df_bolsa['Date']).dt.date
            
            # Buscar datos de ese día
            df_dia = df_bolsa[df_bolsa['Date'] == fecha_click]
            
            if df_dia.empty or 'Datos_Horarios' not in df_dia.columns:
                return True, f"Detalle del {fecha_click}", html.Div(
                    "No hay datos horarios disponibles para esta fecha",
                    className="alert alert-warning"
                )
            
            datos_horarios = df_dia.iloc[0]['Datos_Horarios']
            tabla = crear_tabla_horaria(datos_horarios, fecha_click)
            
            titulo = f"📊 Detalle Horario - Precio Bolsa Nacional - {fecha_click}"
            
            return True, titulo, tabla
            
        except Exception as e:
            logger.error(f"Error mostrando detalle: {e}")
            traceback.print_exc()
            return True, "Error", html.Div(
                f"Error al cargar datos: {str(e)}",
                className="alert alert-danger"
            )
    
    return is_open, "", ""
