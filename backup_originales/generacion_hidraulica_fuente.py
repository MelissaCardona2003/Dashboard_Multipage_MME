from dash import dcc, html, Input, Output, State, dash_table, ALL, callback, register_page
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
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
try:
    from pydataxm.pydataxm import ReadDB
    PYDATAXM_AVAILABLE = True
except ImportError:
    PYDATAXM_AVAILABLE = False
    print("⚠️ pydataxm no está disponible. Algunos datos pueden no cargarse correctamente.")

# Imports locales para componentes uniformes
from .components import crear_header, crear_navbar, crear_sidebar_universal, crear_boton_regresar
from .config import COLORS

warnings.filterwarnings("ignore")

register_page(
    __name__,
    path="/generacion/hidraulica/fuente",
    name="Fuente Hidráulica",
    title="Tablero Fuente Hidráulica - Ministerio de Minas y Energía de Colombia",
    order=5
)

# Inicializar API XM
objetoAPI = None
if PYDATAXM_AVAILABLE:
    try:
        objetoAPI = ReadDB()
        print("✅ API XM inicializada correctamente en fuente hidráulica")
    except Exception as e:
        print(f"❌ Error al inicializar API XM en fuente hidráulica: {e}")
        objetoAPI = None

def obtener_listado_recursos():
    """Obtener el listado de recursos para identificar plantas hidráulicas"""
    try:
        if objetoAPI is None:
            return pd.DataFrame()
        
        # Obtener listado de recursos
        recursos = objetoAPI.request_data("ListadoRecursos", "Sistema", 
                                        date.today() - timedelta(days=1), 
                                        date.today())
        
        if recursos is not None and not recursos.empty:
            # Filtrar solo plantas hidráulicas (tipo HIDRA, MENOR_HIDRA)
            plantas_hidraulicas = recursos[
                recursos['Values_tiporecurso'].str.contains('HIDRA', na=False, case=False)
            ].copy()
            
            return plantas_hidraulicas
            
    except Exception as e:
        print(f"Error obteniendo listado de recursos: {e}")
        return pd.DataFrame()
    
    return pd.DataFrame()

def obtener_generacion_plantas(fecha_inicio, fecha_fin, plantas_df=None):
    """Obtener datos de generación por plantas hidráulicas"""
    try:
        if objetoAPI is None or plantas_df is None or plantas_df.empty:
            return pd.DataFrame(), pd.DataFrame()
        
        datos_generacion = []
        
        # Obtener generación para cada planta
        for _, planta in plantas_df.iterrows():
            codigo_planta = planta['Values_codigo']
            nombre_planta = planta['Values_nombre']
            
            try:
                # Solicitar datos de generación
                gen_data = objetoAPI.request_data("Gene", codigo_planta, fecha_inicio, fecha_fin)
                
                if gen_data is not None and not gen_data.empty:
                    # Procesar datos horarios y convertir a GWh
                    for _, row in gen_data.iterrows():
                        fecha = row['Date']
                        
                        # Sumar todas las horas del día y convertir kWh a GWh
                        horas_cols = [col for col in gen_data.columns if 'Values_Hour' in col]
                        generacion_diaria_kwh = sum([row[col] for col in horas_cols if pd.notna(row[col])])
                        generacion_diaria_gwh = generacion_diaria_kwh / 1_000_000  # kWh a GWh
                        
                        datos_generacion.append({
                            'Fecha': fecha,
                            'Planta': nombre_planta,
                            'Codigo': codigo_planta,
                            'Generacion_GWh': generacion_diaria_gwh
                        })
                        
            except Exception as e:
                print(f"Error obteniendo datos para planta {codigo_planta}: {e}")
                continue
        
        if datos_generacion:
            df_generacion = pd.DataFrame(datos_generacion)
            
            # Crear tabla de participación
            participacion_total = df_generacion.groupby('Planta')['Generacion_GWh'].sum().reset_index()
            total_generacion = participacion_total['Generacion_GWh'].sum()
            participacion_total['Participacion_%'] = (participacion_total['Generacion_GWh'] / total_generacion * 100).round(2)
            
            # Añadir lógica del semáforo
            participacion_total['Estado'] = participacion_total['Participacion_%'].apply(
                lambda x: 'Alto' if x >= 20 else 'Medio' if x >= 5 else 'Bajo'
            )
            
            return df_generacion, participacion_total
            
    except Exception as e:
        print(f"Error en obtener_generacion_plantas: {e}")
        traceback.print_exc()
    
    return pd.DataFrame(), pd.DataFrame()

def crear_grafica_temporal(df_generacion):
    """Crear gráfica de línea temporal de generación"""
    if df_generacion.empty:
        return go.Figure().add_annotation(text="No hay datos disponibles", 
                                        xref="paper", yref="paper", x=0.5, y=0.5)
    
    fig = go.Figure()
    
    # Agregar línea por cada planta
    plantas = df_generacion['Planta'].unique()
    colores = px.colors.qualitative.Set3
    
    for i, planta in enumerate(plantas):
        datos_planta = df_generacion[df_generacion['Planta'] == planta]
        
        fig.add_trace(go.Scatter(
            x=datos_planta['Fecha'],
            y=datos_planta['Generacion_GWh'],
            mode='lines+markers',
            name=planta,
            line=dict(color=colores[i % len(colores)], width=2),
            hovertemplate='<b>%{fullData.name}</b><br>' +
                         'Fecha: %{x}<br>' +
                         'Generación: %{y:.2f} GWh<extra></extra>'
        ))
    
    fig.update_layout(
        title='Evolución Temporal de Generación Hidráulica',
        xaxis_title='Fecha',
        yaxis_title='Generación (GWh)',
        hovermode='x unified',
        showlegend=True,
        height=500,
        template='plotly_white'
    )
    
    return fig

def crear_tabla_participacion(df_participacion):
    """Crear tabla de participación con semáforo"""
    if df_participacion.empty:
        return html.Div("No hay datos de participación disponibles")
    
    # Definir colores del semáforo
    def get_color_semaforo(estado):
        if estado == 'Alto':
            return '#28a745'  # Verde
        elif estado == 'Medio':
            return '#ffc107'  # Amarillo
        else:
            return '#dc3545'  # Rojo
    
    # Preparar datos para la tabla
    tabla_data = []
    for _, row in df_participacion.iterrows():
        tabla_data.append({
            'Planta': row['Planta'],
            'Generacion_GWh': f"{row['Generacion_GWh']:.2f}",
            'Participacion_%': f"{row['Participacion_%']:.2f}%",
            'Estado': row['Estado']
        })
    
    return dash_table.DataTable(
        data=tabla_data,
        columns=[
            {"name": "Planta", "id": "Planta"},
            {"name": "Generación (GWh)", "id": "Generacion_GWh"},
            {"name": "Participación (%)", "id": "Participacion_%"},
            {"name": "Estado", "id": "Estado"}
        ],
        style_cell={
            'textAlign': 'left',
            'padding': '10px',
            'fontFamily': 'Arial',
            'fontSize': '14px'
        },
        style_header={
            'backgroundColor': COLORS['primary'],
            'color': 'white',
            'fontWeight': 'bold'
        },
        style_data_conditional=[
            {
                'if': {'filter_query': '{Estado} = Alto'},
                'backgroundColor': '#d4edda',
                'color': '#155724'
            },
            {
                'if': {'filter_query': '{Estado} = Medio'},
                'backgroundColor': '#fff3cd',
                'color': '#856404'
            },
            {
                'if': {'filter_query': '{Estado} = Bajo'},
                'backgroundColor': '#f8d7da',
                'color': '#721c24'
            }
        ],
        sort_action="native",
        page_action="native",
        page_current=0,
        page_size=15
    )

# Layout principal
layout = html.Div([
    # Sidebar universal
    crear_sidebar_universal(),
    
    # Header
    crear_header(
        titulo_pagina="Fuente Hidráulica",
        descripcion_pagina="Tablero de plantas hidráulicas con generación y participación del Sistema Interconectado Nacional",
        icono_pagina="fas fa-water",
        color_tema=COLORS['energia_hidraulica']
    ),
    
    # Container principal
    dbc.Container([
        # Botón de regreso
        crear_boton_regresar(),
        
        # Título de la página
        html.Div([
            html.H2([
                html.I(className="fas fa-water me-3", 
                      style={"color": COLORS['energia_hidraulica']}),
                "Tablero Fuente Hidráulica"
            ], className="mb-3", style={"color": COLORS['text_primary']}),
            html.P("Análisis detallado de generación por plantas hidráulicas del sistema eléctrico colombiano", 
                  className="lead", style={"color": COLORS['text_secondary']})
        ], className="text-center mb-5"),
        
        # Controles de filtro
        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Rango de Fechas:", className="fw-bold"),
                        dcc.DatePickerRange(
                            id='date-range-hidraulica',
                            start_date=date.today() - timedelta(days=7),
                            end_date=date.today(),
                            display_format='DD/MM/YYYY',
                            style={'width': '100%'}
                        )
                    ], md=4),
                    dbc.Col([
                        html.Label("Planta (Opcional):", className="fw-bold"),
                        dcc.Dropdown(
                            id='planta-dropdown-hidraulica',
                            placeholder="Todas las plantas",
                            multi=True
                        )
                    ], md=6),
                    dbc.Col([
                        html.Br(),
                        dbc.Button(
                            "Actualizar Datos",
                            id="btn-actualizar-hidraulica",
                            color="primary",
                            className="w-100"
                        )
                    ], md=2)
                ])
            ])
        ], className="mb-4"),
        
        # Contenedor de resultados
        html.Div(id="contenido-hidraulica"),
        
    ], fluid=True, className="py-4")
    
], style={'backgroundColor': COLORS['bg_main'], 'minHeight': '100vh'})

# Callbacks
@callback(
    [Output('planta-dropdown-hidraulica', 'options'),
     Output('contenido-hidraulica', 'children')],
    [Input('btn-actualizar-hidraulica', 'n_clicks')],
    [State('date-range-hidraulica', 'start_date'),
     State('date-range-hidraulica', 'end_date'),
     State('planta-dropdown-hidraulica', 'value')]
)
def actualizar_tablero_hidraulica(n_clicks, fecha_inicio, fecha_fin, plantas_seleccionadas):
    if not n_clicks:
        return [], html.Div("Haz clic en 'Actualizar Datos' para cargar la información")
    
    try:
        # Convertir fechas
        fecha_inicio_dt = dt.datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        fecha_fin_dt = dt.datetime.strptime(fecha_fin, "%Y-%m-%d").date()
        
        # Obtener listado de plantas hidráulicas
        plantas_df = obtener_listado_recursos()
        
        if plantas_df.empty:
            return [], dbc.Alert("No se pudieron obtener los datos de plantas hidráulicas", color="warning")
        
        # Opciones para el dropdown
        opciones_plantas = [{'label': row['Values_nombre'], 'value': row['Values_codigo']} 
                           for _, row in plantas_df.iterrows()]
        
        # Obtener datos de generación
        df_generacion, df_participacion = obtener_generacion_plantas(fecha_inicio_dt, fecha_fin_dt, plantas_df)
        
        if df_generacion.empty:
            return opciones_plantas, dbc.Alert("No se encontraron datos de generación para el período seleccionado", color="info")
        
        # Filtrar por plantas seleccionadas si las hay
        if plantas_seleccionadas:
            df_generacion = df_generacion[df_generacion['Codigo'].isin(plantas_seleccionadas)]
            df_participacion = df_participacion[df_participacion['Planta'].isin(
                df_generacion['Planta'].unique()
            )]
        
        # Crear contenido
        contenido = [
            # Gráfica temporal
            dbc.Card([
                dbc.CardHeader([
                    html.H5([
                        html.I(className="fas fa-chart-line me-2"),
                        "Evolución Temporal de Generación Hidráulica"
                    ], className="mb-0")
                ]),
                dbc.CardBody([
                    dcc.Graph(
                        figure=crear_grafica_temporal(df_generacion),
                        config={'displayModeBar': True}
                    )
                ])
            ], className="mb-4"),
            
            # Tabla de participación
            dbc.Card([
                dbc.CardHeader([
                    html.H5([
                        html.I(className="fas fa-table me-2"),
                        "Participación por Planta Hidráulica"
                    ], className="mb-0")
                ]),
                dbc.CardBody([
                    crear_tabla_participacion(df_participacion)
                ])
            ])
        ]
        
        return opciones_plantas, contenido
        
    except Exception as e:
        print(f"Error en callback hidráulica: {e}")
        traceback.print_exc()
        return [], dbc.Alert(f"Error al procesar los datos: {str(e)}", color="danger")
