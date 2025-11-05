
def get_plotly_modules():
    """Importar plotly solo cuando se necesite"""
    import plotly.express as px
    import plotly.graph_objects as go
    return px, go

import dash
from dash import dcc, html, Input, Output, State, callback, register_page, dash_table
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime
from io import StringIO
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
from utils.components import crear_header, crear_navbar, crear_sidebar_universal, crear_boton_regresar
from utils.config import COLORS
from utils._xm import get_objetoAPI

warnings.filterwarnings("ignore")

register_page(
    __name__,
    path="/distribucion/demanda",
    name="Demanda por Agente",
    title="Tablero Demanda por Agente - Ministerio de Minas y Energía de Colombia",
    order=11
)

def obtener_listado_agentes():
    """Obtener el listado de agentes del sistema"""
    try:
        objetoAPI = get_objetoAPI()
        if objetoAPI is None:
            print("API no disponible - retornando DataFrame vacío")
            return pd.DataFrame()
        
        fecha_fin = date.today() - timedelta(days=1)
        fecha_inicio = fecha_fin - timedelta(days=7)
        agentes = objetoAPI.request_data("ListadoAgentes", "Sistema", fecha_inicio, fecha_fin)
        
        if agentes is not None and not agentes.empty:
            # Filtrar solo agentes activos
            if 'Values_State' in agentes.columns:
                agentes = agentes[agentes['Values_State'] == 'OPERACION'].copy()
            return agentes
        print("No se obtuvieron agentes")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error obteniendo listado de agentes: {e}")
        traceback.print_exc()
    return pd.DataFrame()

def obtener_demanda_comercial(fecha_inicio, fecha_fin, codigos_agentes=None):
    """Obtener datos de demanda comercial (DemaCome) por agente"""
    try:
        objetoAPI = get_objetoAPI()
        if objetoAPI is None:
            return pd.DataFrame()
        
        # Obtener DemaCome por Agente
        df = objetoAPI.request_data('DemaCome', 'Agente', fecha_inicio, fecha_fin)
        
        if df is None or df.empty:
            print("No se obtuvieron datos de DemaCome")
            return pd.DataFrame()
        
        # Filtrar por códigos si se proporcionan
        if codigos_agentes:
            df = df[df['Values_code'].isin(codigos_agentes)].copy()
        
        # Procesar datos horarios
        df_procesado = procesar_datos_horarios(df, 'DemaCome')
        
        return df_procesado
        
    except Exception as e:
        print(f"Error obteniendo demanda comercial: {e}")
        traceback.print_exc()
        return pd.DataFrame()

def obtener_demanda_real(fecha_inicio, fecha_fin, codigos_agentes=None):
    """Obtener datos de demanda real por agente"""
    try:
        objetoAPI = get_objetoAPI()
        if objetoAPI is None:
            return pd.DataFrame()
        
        # Obtener DemaReal por Agente
        df = objetoAPI.request_data('DemaReal', 'Agente', fecha_inicio, fecha_fin)
        
        if df is None or df.empty:
            print("No se obtuvieron datos de DemaReal")
            return pd.DataFrame()
        
        # Filtrar por códigos si se proporcionan
        if codigos_agentes:
            df = df[df['Values_code'].isin(codigos_agentes)].copy()
        
        # Procesar datos horarios
        df_procesado = procesar_datos_horarios(df, 'DemaReal')
        
        return df_procesado
        
    except Exception as e:
        print(f"Error obteniendo demanda real: {e}")
        traceback.print_exc()
        return pd.DataFrame()

def procesar_datos_horarios(df, tipo_metrica):
    """
    Procesar datos horarios: sumar las 24 horas y convertir de kWh a GWh
    
    Args:
        df: DataFrame con columnas Values_Hour01 a Values_Hour24
        tipo_metrica: 'DemaCome' o 'DemaReal'
    
    Returns:
        DataFrame con columnas: Fecha, Codigo_Agente, Demanda_GWh, Tipo
    """
    if df.empty:
        return pd.DataFrame()
    
    # Identificar columnas de horas
    cols_horas = [col for col in df.columns if 'Hour' in col]
    
    # Reemplazar NaN con 0
    df[cols_horas] = df[cols_horas].fillna(0)
    
    # Sumar las 24 horas para obtener total diario en kWh
    df['Total_kWh'] = df[cols_horas].sum(axis=1)
    
    # Convertir de kWh a GWh
    df['Demanda_GWh'] = df['Total_kWh'] / 1_000_000
    
    # Preparar DataFrame resultado
    df_resultado = pd.DataFrame({
        'Fecha': pd.to_datetime(df['Date']),
        'Codigo_Agente': df['Values_code'],
        'Demanda_GWh': df['Demanda_GWh'],
        'Tipo': tipo_metrica
    })
    
    return df_resultado

def obtener_demanda_no_atendida(fecha_inicio, fecha_fin):
    """Obtener datos de Demanda No Atendida Programada por Área"""
    try:
        objetoAPI = get_objetoAPI()
        if objetoAPI is None:
            return pd.DataFrame()
        
        # Obtener DemaNoAtenProg por Area
        df = objetoAPI.request_data('DemaNoAtenProg', 'Area', fecha_inicio, fecha_fin)
        
        if df is None or df.empty:
            print("No se obtuvieron datos de Demanda No Atendida")
            return pd.DataFrame()
        
        # Renombrar columnas para mayor claridad
        df_resultado = pd.DataFrame({
            'Fecha': pd.to_datetime(df['Date']),
            'Area': df['Name'],
            'Demanda_No_Atendida_kWh': df['Value']
        })
        
        # Convertir a GWh
        df_resultado['Demanda_No_Atendida_GWh'] = df_resultado['Demanda_No_Atendida_kWh'] / 1_000_000
        
        # Ordenar por fecha descendente
        df_resultado = df_resultado.sort_values('Fecha', ascending=False)
        
        return df_resultado
        
    except Exception as e:
        print(f"Error obteniendo demanda no atendida: {e}")
        traceback.print_exc()
        return pd.DataFrame()

def crear_grafica_lineas_demanda(df_demanda_come, df_demanda_real, agente_nombre=None):
    """
    Crear gráfica de líneas comparando DemaCome y DemaReal
    
    Args:
        df_demanda_come: DataFrame con demanda comercial
        df_demanda_real: DataFrame con demanda real
        agente_nombre: Nombre del agente para el título
    """
    px, go = get_plotly_modules()
    
    fig = go.Figure()
    
    # Agregar línea de Demanda Comercial
    if not df_demanda_come.empty:
        df_come_agg = df_demanda_come.groupby('Fecha', as_index=False)['Demanda_GWh'].sum()
        df_come_agg = df_come_agg.sort_values('Fecha')
        
        fig.add_trace(go.Scatter(
            x=df_come_agg['Fecha'],
            y=df_come_agg['Demanda_GWh'],
            mode='lines+markers',
            name='Demanda Comercial',
            line=dict(color=COLORS.get('primary', '#0d6efd'), width=2),
            marker=dict(size=6),
            hovertemplate='<b>Demanda Comercial</b><br>Fecha: %{x}<br>Demanda: %{y:.4f} GWh<extra></extra>'
        ))
    
    # Agregar línea de Demanda Real
    if not df_demanda_real.empty:
        df_real_agg = df_demanda_real.groupby('Fecha', as_index=False)['Demanda_GWh'].sum()
        df_real_agg = df_real_agg.sort_values('Fecha')
        
        fig.add_trace(go.Scatter(
            x=df_real_agg['Fecha'],
            y=df_real_agg['Demanda_GWh'],
            mode='lines+markers',
            name='Demanda Real',
            line=dict(color=COLORS.get('success', '#28a745'), width=2, dash='dot'),
            marker=dict(size=6),
            hovertemplate='<b>Demanda Real</b><br>Fecha: %{x}<br>Demanda: %{y:.4f} GWh<extra></extra>'
        ))
    
    titulo = "Evolución Temporal - Demanda por Agente"
    if agente_nombre:
        titulo = f"Evolución Temporal - {agente_nombre}"
    
    fig.update_layout(
        title=titulo,
        xaxis_title="Fecha",
        yaxis_title="Demanda (GWh)",
        hovermode='x unified',
        template='plotly_white',
        height=450,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig

def crear_tabla_demanda_no_atendida(df_dna, page_current=0, page_size=10):
    """
    Crear tabla de Demanda No Atendida Programada con paginación
    
    Args:
        df_dna: DataFrame con demanda no atendida
        page_current: Página actual (0-indexed)
        page_size: Número de filas por página
    """
    if df_dna.empty:
        return html.Div([
            html.P("No hay datos de Demanda No Atendida disponibles", 
                   className="text-muted text-center")
        ])
    
    # Formatear datos para la tabla
    df_tabla = df_dna.copy()
    df_tabla['Fecha'] = df_tabla['Fecha'].dt.strftime('%Y-%m-%d')
    df_tabla['Demanda_No_Atendida_GWh'] = df_tabla['Demanda_No_Atendida_GWh'].apply(
        lambda x: f"{x:.4f}"
    )
    
    # Renombrar columnas para display
    df_tabla = df_tabla[['Fecha', 'Area', 'Demanda_No_Atendida_GWh']]
    df_tabla.columns = ['Fecha', 'Área', 'Demanda No Atendida (GWh)']
    
    # Calcular total
    total_gwh = df_dna['Demanda_No_Atendida_GWh'].sum()
    
    tabla = dash_table.DataTable(
        id='tabla-demanda-no-atendida',
        columns=[{"name": col, "id": col} for col in df_tabla.columns],
        data=df_tabla.to_dict('records'),
        page_current=page_current,
        page_size=page_size,
        page_action='native',
        style_table={'overflowX': 'auto'},
        style_cell={
            'textAlign': 'left',
            'padding': '12px',
            'fontFamily': 'Arial, sans-serif',
            'fontSize': '14px'
        },
        style_header={
            'backgroundColor': COLORS.get('primary', '#0d6efd'),
            'color': 'white',
            'fontWeight': 'bold',
            'textAlign': 'center'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#f8f9fa'
            }
        ]
    )
    
    # Fila de total
    total_row = html.Div([
        html.Strong("Total Demanda No Atendida: "),
        html.Span(f"{total_gwh:.4f} GWh", 
                 style={'color': COLORS.get('danger', '#dc3545'), 'fontSize': '1.1rem'})
    ], className="mt-3 text-end", style={'padding': '10px'})
    
    return html.Div([tabla, total_row])

# ==================== LAYOUT ====================

def layout(**kwargs):
    """Layout principal de la página de distribución"""
    
    # Obtener datos iniciales
    try:
        fecha_fin = date.today() - timedelta(days=1)
        fecha_inicio = fecha_fin - timedelta(days=30)
        
        # Obtener listado de agentes
        agentes_df = obtener_listado_agentes()
        
        # Opciones para el dropdown
        if not agentes_df.empty and 'Values_Code' in agentes_df.columns and 'Values_Name' in agentes_df.columns:
            opciones_agentes = [
                {'label': f"{row['Values_Code']} - {row['Values_Name']}", 
                 'value': row['Values_Code']}
                for _, row in agentes_df.iterrows()
            ]
            # Agregar opción "Todos"
            opciones_agentes.insert(0, {'label': 'TODOS LOS AGENTES', 'value': 'TODOS'})
        else:
            opciones_agentes = [{'label': 'No hay agentes disponibles', 'value': None}]
        
        # Obtener datos de demanda para todos los agentes inicialmente
        df_demanda_come = obtener_demanda_comercial(fecha_inicio, fecha_fin)
        df_demanda_real = obtener_demanda_real(fecha_inicio, fecha_fin)
        df_dna = obtener_demanda_no_atendida(fecha_inicio, fecha_fin)
        
        # Crear gráfica inicial
        fig_lineas = crear_grafica_lineas_demanda(df_demanda_come, df_demanda_real)
        
        # Crear tabla inicial
        tabla_dna = crear_tabla_demanda_no_atendida(df_dna)
        
    except Exception as e:
        print(f"Error cargando datos iniciales: {e}")
        traceback.print_exc()
        opciones_agentes = []
        fig_lineas = get_plotly_modules()[1].Figure()
        tabla_dna = html.Div("Error cargando datos")
    
    return html.Div([
        # Sidebar desplegable
        crear_sidebar_universal(),
        
        # Header específico
        crear_header(
            titulo_pagina="Demanda por Agente",
            descripcion_pagina="Análisis de demanda comercial y real por agente del sistema",
            icono_pagina="fas fa-bolt",
            color_tema=COLORS.get('distribucion', '#3F51B5')
        ),
        
        # Container principal
        dbc.Container([
            # Botón de regreso
            crear_boton_regresar(),
            
            # Título de la sección
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.I(className="fas fa-bolt", 
                              style={"fontSize": "3rem", "color": "#3F51B5", "marginRight": "1rem"}),
                        html.H2("DEMANDA POR AGENTE", 
                               style={"color": COLORS['text_primary'], "fontWeight": "700", 
                                      "display": "inline-block"})
                    ], className="text-center mb-4")
                ])
            ]),
            
            # Controles de filtro
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            dbc.Row([
                                # Selector de agente
                                dbc.Col([
                                    html.Label("Seleccionar Agente:", 
                                             style={'fontWeight': 'bold', 'marginBottom': '8px'}),
                                    dcc.Dropdown(
                                        id='selector-agente-distribucion',
                                        options=opciones_agentes,
                                        value='TODOS',
                                        placeholder="Seleccione un agente",
                                        clearable=False,
                                        style={'width': '100%'}
                                    )
                                ], md=6, className="mb-3"),
                                
                                # Selector de rango de fechas
                                dbc.Col([
                                    html.Label("Rango de Fechas:", 
                                             style={'fontWeight': 'bold', 'marginBottom': '8px'}),
                                    dcc.DatePickerRange(
                                        id='selector-fechas-distribucion',
                                        start_date=fecha_inicio,
                                        end_date=fecha_fin,
                                        display_format='YYYY-MM-DD',
                                        max_date_allowed=date.today(),
                                        style={'width': '100%'}
                                    )
                                ], md=6, className="mb-3")
                            ]),
                            
                            # Botón de actualizar
                            dbc.Row([
                                dbc.Col([
                                    dbc.Button(
                                        [html.I(className="fas fa-sync-alt me-2"), "Actualizar Datos"],
                                        id='btn-actualizar-distribucion',
                                        color="primary",
                                        className="w-100"
                                    )
                                ], md=12)
                            ])
                        ])
                    ], className="mb-4 shadow-sm")
                ])
            ]),
            
            # Gráfica de líneas
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                                html.I(className="fas fa-chart-line me-2"),
                                "Evolución Temporal - Demanda Comercial vs Demanda Real"
                            ], className="mb-0")
                        ]),
                        dbc.CardBody([
                            dcc.Loading(
                                id="loading-grafica-distribucion",
                                type="default",
                                children=[
                                    dcc.Graph(
                                        id='grafica-lineas-demanda',
                                        figure=fig_lineas,
                                        config={'displayModeBar': True}
                                    )
                                ]
                            )
                        ])
                    ], className="mb-4 shadow-sm")
                ])
            ]),
            
            # Tabla de Demanda No Atendida
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                                html.I(className="fas fa-table me-2"),
                                "Demanda No Atendida Programada por Área"
                            ], className="mb-0")
                        ]),
                        dbc.CardBody([
                            dcc.Loading(
                                id="loading-tabla-dna",
                                type="default",
                                children=[
                                    html.Div(
                                        id='contenedor-tabla-dna',
                                        children=tabla_dna
                                    )
                                ]
                            )
                        ])
                    ], className="mb-4 shadow-sm")
                ])
            ]),
            
            # Store para guardar datos
            dcc.Store(id='store-datos-distribucion'),
            dcc.Store(id='store-agentes-distribucion', data=agentes_df.to_json(date_format='iso', orient='split') if not agentes_df.empty else None),
            
            # Modal para mostrar detalle al hacer click en la gráfica
            dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle(id="modal-title-demanda")),
                dbc.ModalBody([
                    html.P(id="modal-description-demanda", className="mb-3"),
                    html.Div(id="modal-table-content-demanda")
                ]),
                dbc.ModalFooter(
                    dbc.Button("Cerrar", id="close-modal-demanda", className="ms-auto", n_clicks=0)
                )
            ], id="modal-detalle-demanda", is_open=False, size="xl")
            
        ], fluid=True, className="py-4")
    ])

# ==================== CALLBACKS ====================

@callback(
    [Output('grafica-lineas-demanda', 'figure'),
     Output('contenedor-tabla-dna', 'children'),
     Output('store-datos-distribucion', 'data')],
    [Input('btn-actualizar-distribucion', 'n_clicks')],
    [State('selector-agente-distribucion', 'value'),
     State('selector-fechas-distribucion', 'start_date'),
     State('selector-fechas-distribucion', 'end_date'),
     State('store-agentes-distribucion', 'data')]
)
def actualizar_datos_distribucion(n_clicks, codigo_agente, fecha_inicio_str, fecha_fin_str, agentes_json):
    """Callback para actualizar la gráfica y tabla según los filtros seleccionados"""
    
    px, go = get_plotly_modules()
    
    try:
        # Convertir fechas
        fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
        fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
        
        # Validar rango de fechas
        if (fecha_fin - fecha_inicio).days > 365:
            fig_error = go.Figure().add_annotation(
                text="Por favor seleccione un rango menor a 365 días",
                xref="paper", yref="paper", x=0.5, y=0.5,
                showarrow=False, font=dict(size=16, color="red")
            )
            return fig_error, html.Div("Rango de fechas demasiado amplio"), None
        
        # Determinar códigos de agentes a consultar
        codigos_agentes = None
        agente_nombre = "Todos los Agentes"
        
        if codigo_agente and codigo_agente != 'TODOS':
            codigos_agentes = [codigo_agente]
            
            # Obtener nombre del agente
            if agentes_json:
                agentes_df = pd.read_json(StringIO(agentes_json), orient='split')
                agente_row = agentes_df[agentes_df['Values_Code'] == codigo_agente]
                if not agente_row.empty:
                    agente_nombre = agente_row.iloc[0]['Values_Name']
        
        # Obtener datos
        df_demanda_come = obtener_demanda_comercial(fecha_inicio, fecha_fin, codigos_agentes)
        df_demanda_real = obtener_demanda_real(fecha_inicio, fecha_fin, codigos_agentes)
        df_dna = obtener_demanda_no_atendida(fecha_inicio, fecha_fin)
        
        # Crear gráfica
        fig_lineas = crear_grafica_lineas_demanda(df_demanda_come, df_demanda_real, agente_nombre)
        
        # Crear tabla
        tabla_dna = crear_tabla_demanda_no_atendida(df_dna)
        
        # Guardar datos en store
        store_data = {
            'demanda_come': df_demanda_come.to_json(date_format='iso', orient='split') if not df_demanda_come.empty else None,
            'demanda_real': df_demanda_real.to_json(date_format='iso', orient='split') if not df_demanda_real.empty else None,
            'dna': df_dna.to_json(date_format='iso', orient='split') if not df_dna.empty else None
        }
        
        return fig_lineas, tabla_dna, store_data
        
    except Exception as e:
        print(f"Error en actualizar_datos_distribucion: {e}")
        traceback.print_exc()
        
        fig_error = go.Figure().add_annotation(
            text=f"Error al cargar datos: {str(e)[:100]}",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=14, color="red")
        )
        
        return fig_error, html.Div(f"Error: {str(e)[:200]}"), None

@callback(
    [Output('modal-detalle-demanda', 'is_open'),
     Output('modal-table-content-demanda', 'children'),
     Output('modal-title-demanda', 'children'),
     Output('modal-description-demanda', 'children')],
    [Input('grafica-lineas-demanda', 'clickData'),
     Input('close-modal-demanda', 'n_clicks')],
    [State('store-datos-distribucion', 'data'),
     State('store-agentes-distribucion', 'data'),
     State('modal-detalle-demanda', 'is_open')],
    prevent_initial_call=True
)
def mostrar_detalle_por_agente(clickData, n_clicks_close, datos_store, agentes_json, is_open):
    """
    Callback para mostrar tabla detallada por agente al hacer click en un punto de la gráfica
    
    La tabla muestra:
    - Agente (código y nombre)
    - Demanda Comercial (GWh)
    - Demanda Real (GWh)
    - Participación (%)
    - Diferencia (Real - Comercial) en GWh
    """
    
    import dash
    ctx = dash.callback_context
    
    if not ctx.triggered:
        raise PreventUpdate
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Si se cerró el modal
    if trigger_id == 'close-modal-demanda':
        return False, None, "", ""
    
    # Si se hizo click en la gráfica
    if trigger_id == 'grafica-lineas-demanda' and clickData:
        try:
            # Obtener datos del punto clickeado
            point_data = clickData['points'][0]
            fecha_seleccionada = point_data['x']
            curve_number = point_data.get('curveNumber', 0)
            
            print(f"🎯 Click en gráfica - Fecha: {fecha_seleccionada}, Curva: {curve_number}")
            
            # Verificar que hay datos en el store
            if not datos_store:
                return False, html.Div("No hay datos disponibles"), "Sin datos", ""
            
            # Cargar datos del store
            df_demanda_come = pd.read_json(StringIO(datos_store['demanda_come']), orient='split') if datos_store.get('demanda_come') else pd.DataFrame()
            df_demanda_real = pd.read_json(StringIO(datos_store['demanda_real']), orient='split') if datos_store.get('demanda_real') else pd.DataFrame()
            
            if df_demanda_come.empty and df_demanda_real.empty:
                return False, html.Div("No hay datos para esta fecha"), "Sin datos", ""
            
            # Convertir fecha seleccionada a datetime
            fecha_dt = pd.to_datetime(fecha_seleccionada)
            
            # Filtrar datos por fecha
            df_come_fecha = df_demanda_come[pd.to_datetime(df_demanda_come['Fecha']) == fecha_dt].copy() if not df_demanda_come.empty else pd.DataFrame()
            df_real_fecha = df_demanda_real[pd.to_datetime(df_demanda_real['Fecha']) == fecha_dt].copy() if not df_demanda_real.empty else pd.DataFrame()
            
            print(f"📊 Datos filtrados - DemaCome: {len(df_come_fecha)}, DemaReal: {len(df_real_fecha)}")
            
            if df_come_fecha.empty and df_real_fecha.empty:
                return False, html.Div("No hay datos para esta fecha"), "Sin datos", ""
            
            # Cargar listado de agentes para obtener nombres
            agentes_df = pd.read_json(StringIO(agentes_json), orient='split') if agentes_json else pd.DataFrame()
            
            # Combinar datos de demanda comercial y real
            if not df_come_fecha.empty:
                df_combined = df_come_fecha.groupby('Codigo_Agente', as_index=False)['Demanda_GWh'].sum()
                df_combined = df_combined.rename(columns={'Demanda_GWh': 'Demanda_Comercial_GWh'})
            else:
                df_combined = pd.DataFrame(columns=['Codigo_Agente', 'Demanda_Comercial_GWh'])
            
            if not df_real_fecha.empty:
                df_real_agg = df_real_fecha.groupby('Codigo_Agente', as_index=False)['Demanda_GWh'].sum()
                df_real_agg = df_real_agg.rename(columns={'Demanda_GWh': 'Demanda_Real_GWh'})
                
                if df_combined.empty:
                    df_combined = df_real_agg
                else:
                    df_combined = df_combined.merge(df_real_agg, on='Codigo_Agente', how='outer')
            
            # Rellenar NaN con 0
            df_combined['Demanda_Comercial_GWh'] = df_combined.get('Demanda_Comercial_GWh', 0).fillna(0)
            df_combined['Demanda_Real_GWh'] = df_combined.get('Demanda_Real_GWh', 0).fillna(0)
            
            # Calcular diferencia
            df_combined['Diferencia_GWh'] = df_combined['Demanda_Real_GWh'] - df_combined['Demanda_Comercial_GWh']
            
            # Calcular participación basada en demanda comercial (o real si no hay comercial)
            total_comercial = df_combined['Demanda_Comercial_GWh'].sum()
            total_real = df_combined['Demanda_Real_GWh'].sum()
            
            if total_comercial > 0:
                df_combined['Participacion_%'] = (df_combined['Demanda_Comercial_GWh'] / total_comercial * 100).round(2)
            elif total_real > 0:
                df_combined['Participacion_%'] = (df_combined['Demanda_Real_GWh'] / total_real * 100).round(2)
            else:
                df_combined['Participacion_%'] = 0
            
            # Agregar nombres de agentes
            if not agentes_df.empty:
                agentes_nombres = agentes_df[['Values_Code', 'Values_Name']].drop_duplicates()
                agentes_nombres = agentes_nombres.rename(columns={'Values_Code': 'Codigo_Agente', 'Values_Name': 'Nombre_Agente'})
                df_combined = df_combined.merge(agentes_nombres, on='Codigo_Agente', how='left')
                df_combined['Agente'] = df_combined['Codigo_Agente'] + ' - ' + df_combined['Nombre_Agente'].fillna('Desconocido')
            else:
                df_combined['Agente'] = df_combined['Codigo_Agente']
            
            # Ordenar por participación descendente
            df_combined = df_combined.sort_values('Participacion_%', ascending=False)
            
            # Formatear para la tabla
            df_tabla = df_combined[[
                'Agente', 
                'Demanda_Comercial_GWh', 
                'Demanda_Real_GWh', 
                'Participacion_%', 
                'Diferencia_GWh'
            ]].copy()
            
            # Formatear números
            df_tabla['Demanda_Comercial_GWh'] = df_tabla['Demanda_Comercial_GWh'].apply(lambda x: f"{x:.4f}")
            df_tabla['Demanda_Real_GWh'] = df_tabla['Demanda_Real_GWh'].apply(lambda x: f"{x:.4f}")
            df_tabla['Diferencia_GWh'] = df_tabla['Diferencia_GWh'].apply(lambda x: f"{x:+.4f}")
            df_tabla['Participacion_%'] = df_tabla['Participacion_%'].apply(lambda x: f"{x:.2f}%")
            
            # Renombrar columnas para display
            df_tabla.columns = [
                'Agente',
                'Demanda Comercial (GWh)',
                'Demanda Real (GWh)',
                'Participación (%)',
                'Diferencia (GWh)'
            ]
            
            # Agregar fila de totales
            total_row = {
                'Agente': 'TOTAL',
                'Demanda Comercial (GWh)': f"{total_comercial:.4f}",
                'Demanda Real (GWh)': f"{total_real:.4f}",
                'Participación (%)': '100.00%',
                'Diferencia (GWh)': f"{total_real - total_comercial:+.4f}"
            }
            
            data_with_total = df_tabla.to_dict('records') + [total_row]
            
            # Crear tabla
            tabla = dash_table.DataTable(
                data=data_with_total,
                columns=[{"name": col, "id": col} for col in df_tabla.columns],
                style_cell={
                    'textAlign': 'left',
                    'padding': '12px',
                    'fontFamily': 'Arial, sans-serif',
                    'fontSize': '14px',
                    'whiteSpace': 'normal',
                    'height': 'auto'
                },
                style_header={
                    'backgroundColor': COLORS.get('primary', '#0d6efd'),
                    'color': 'white',
                    'fontWeight': 'bold',
                    'textAlign': 'center'
                },
                style_data={
                    'backgroundColor': '#f8f9fa'
                },
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': 'white'
                    },
                    {
                        'if': {'filter_query': '{Agente} = "TOTAL"'},
                        'backgroundColor': COLORS.get('primary', '#0d6efd'),
                        'color': 'white',
                        'fontWeight': 'bold'
                    },
                    {
                        'if': {
                            'filter_query': '{Diferencia (GWh)} contains "+"',
                            'column_id': 'Diferencia (GWh)'
                        },
                        'color': COLORS.get('success', '#28a745')
                    },
                    {
                        'if': {
                            'filter_query': '{Diferencia (GWh)} contains "-"',
                            'column_id': 'Diferencia (GWh)'
                        },
                        'color': COLORS.get('danger', '#dc3545')
                    }
                ],
                page_size=15,
                page_action='native',
                sort_action='native',
                filter_action='native',
                export_format='xlsx',
                export_headers='display'
            )
            
            # Título y descripción
            fecha_formateada = pd.to_datetime(fecha_seleccionada).strftime('%d/%m/%Y')
            tipo_demanda = "Demanda Comercial" if curve_number == 0 else "Demanda Real"
            
            titulo = f"📊 Detalle por Agente - {fecha_formateada}"
            descripcion = f"Detalle de demanda por agente para el día {fecha_formateada}. Se muestran {len(df_tabla)} agentes con sus respectivas demandas comercial y real, participación porcentual y la diferencia entre ambas."
            
            return True, tabla, titulo, descripcion
            
        except Exception as e:
            print(f"❌ Error en mostrar_detalle_por_agente: {e}")
            traceback.print_exc()
            return False, html.Div(f"Error: {str(e)[:200]}"), "Error", ""
    
    raise PreventUpdate
