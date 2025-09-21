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
    path="/generacion/biomasa",
    name="Generacion Biomasa",
    title="Dashboard Generación Biomasa - Ministerio de Minas y Energía de Colombia",
    order=6
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
            date_obj = pd.to_datetime(date_value)
            return date_obj.strftime('%Y-%m-%d')
        except:
            return date_value
    elif hasattr(date_value, 'strftime'):
        return date_value.strftime('%Y-%m-%d')
    else:
        return date_value

# Métricas específicas para generación biomasa (usando códigos de la API XM)
METRICAS_BIOMASA = [
    "GeneBio_1", "GeneBio_2", "GeneBio_3", "GeneBio_4",  # Métricas de generación biomasa
    "CapaInstBio_1", "CapaInstBio_2",  # Capacidad instalada biomasa
    "PronBio_1", "PronBio_2",  # Pronósticos biomasa
    "ComBio_1", "ComBio_2"  # Combustible biomasa
]

# --- FUNCIONES PARA MANEJO DE DATOS ---
def conectar_api_xm():
    """Conectar a la API de XM"""
    try:
        objetoapi = ReadDB()
        print("API XM inicializada correctamente para generación biomasa")
        return objetoapi
    except Exception as e:
        print(f"Error al conectar con la API de XM: {e}")
        return None

def obtener_metricas_disponibles():
    """Obtener lista de métricas disponibles en la API XM"""
    try:
        api = conectar_api_xm()
        if api:
            metricas = api.request_data()
            print(f"Métricas disponibles: {len(metricas)}")
            return metricas
        return pd.DataFrame()
    except Exception as e:
        print(f"Error al obtener métricas: {e}")
        return pd.DataFrame()

def obtener_datos_biomasa(metrica, fecha_inicio, fecha_fin):
    """Obtener datos de generación biomasa específicos"""
    try:
        api = conectar_api_xm()
        if not api:
            return pd.DataFrame()
        
        # Obtener datos específicos para la métrica biomasa
        datos = api.request_data(
            metrica=metrica,
            start_date=fecha_inicio,
            end_date=fecha_fin
        )
        
        if datos.empty:
            print(f"No hay datos para la métrica {metrica} en el período solicitado")
            return pd.DataFrame()
        
        # Procesamiento específico para datos biomasa
        if 'fecha' in datos.columns:
            datos['fecha'] = pd.to_datetime(datos['fecha'])
            datos = datos.sort_values('fecha')
        
        return datos
        
    except Exception as e:
        print(f"Error al obtener datos biomasa: {e}")
        traceback.print_exc()
        return pd.DataFrame()

# --- LAYOUT PRINCIPAL ---
def layout():
    """Layout principal del dashboard de generación biomasa"""
    
    return html.Div([
        # Componente de carga
        dcc.Loading(
            id="loading-biomasa",
            type="default",
            children=[
                html.Div([
                    # Sidebar universal
                    crear_sidebar_universal(),
                    
                    # Contenido principal
                    html.Div([
                        # Header
                        # Header dinámico específico para generación por biomasa
                        crear_header(
                            titulo_pagina="Generación por Biomasa",
                            descripcion_pagina="Análisis de energía renovable a partir de biomasa y residuos orgánicos",
                            icono_pagina="fas fa-leaf",
                            color_tema=COLORS['energia_biomasa']
                        ),
                        
                        # Container principal
                        dbc.Container([
                            # Botón de regreso
                            crear_boton_regresar(),
                            
                            # Título específico de la página
                            html.Div([
                                html.H2([
                                    html.I(className="fas fa-leaf me-3", style={"color": "#228B22"}),
                                    "Dashboard de Generación Biomasa"
                                ], className="mb-3", style={"color": COLORS['text_primary']}),
                                html.P("Análisis detallado de la generación de energía biomasa en Colombia", 
                                      className="lead", style={"color": COLORS['text_secondary']})
                            ], className="text-center mb-4"),
                            
                            # Controles de fecha
                            dbc.Row([
                                dbc.Col([
                                    dbc.Card([
                                        dbc.CardBody([
                                            html.H5("📅 Selección de Período", className="card-title"),
                                            dbc.Row([
                                                dbc.Col([
                                                    html.Label("Fecha de inicio:", className="form-label"),
                                                    dcc.DatePickerSingle(
                                                        id='fecha-inicio-biomasa',
                                                        date=date.today() - timedelta(days=30),
                                                        display_format='YYYY-MM-DD',
                                                        style={'width': '100%'}
                                                    )
                                                ], md=6),
                                                dbc.Col([
                                                    html.Label("Fecha de fin:", className="form-label"),
                                                    dcc.DatePickerSingle(
                                                        id='fecha-fin-biomasa',
                                                        date=date.today(),
                                                        display_format='YYYY-MM-DD',
                                                        style={'width': '100%'}
                                                    )
                                                ], md=6),
                                            ]),
                                            html.Br(),
                                            dbc.Row([
                                                dbc.Col([
                                                    html.Label("Métrica biomasa:", className="form-label"),
                                                    dcc.Dropdown(
                                                        id='dropdown-metrica-biomasa',
                                                        options=[
                                                            {'label': 'Generación Biomasa Total', 'value': 'GeneBio_1'},
                                                            {'label': 'Capacidad Instalada Biomasa', 'value': 'CapaInstBio_1'},
                                                            {'label': 'Pronóstico Biomasa', 'value': 'PronBio_1'},
                                                            {'label': 'Combustible Biomasa', 'value': 'ComBio_1'}
                                                        ],
                                                        value='GeneBio_1',
                                                        placeholder="Selecciona una métrica biomasa"
                                                    )
                                                ], md=12),
                                            ]),
                                            html.Br(),
                                            dbc.Button(
                                                "🔄 Actualizar Datos", 
                                                id="btn-actualizar-biomasa",
                                                color="primary",
                                                className="w-100"
                                            )
                                        ])
                                    ])
                                ], md=12)
                            ], className="mb-4"),
                            
                            # Contenedor para gráficos y datos
                            html.Div(id="contenido-biomasa-principal"),
                            
                            # Footer con información
                            html.Hr(),
                            html.Div([
                                html.P([
                                    "🌿 Dashboard de Generación Biomasa - ",
                                    html.Strong("Ministerio de Minas y Energía de Colombia"),
                                    " | Última actualización: ", LAST_UPDATE
                                ], className="text-center text-muted mb-0")
                            ])
                            
                        ], fluid=True, className="py-4")
                        
                    ], className="main-content", style={'marginLeft': '0px', 'transition': 'margin-left 0.3s ease-in-out'})
                ])
            ]
        ),
        
        # Stores para datos
        dcc.Store(id='store-datos-biomasa'),
        dcc.Store(id='store-metricas-biomasa'),
    ])

# --- CALLBACKS ---
@callback(
    Output('contenido-biomasa-principal', 'children'),
    [Input('btn-actualizar-biomasa', 'n_clicks')],
    [State('fecha-inicio-biomasa', 'date'),
     State('fecha-fin-biomasa', 'date'),
     State('dropdown-metrica-biomasa', 'value')]
)
def actualizar_dashboard_biomasa(n_clicks, fecha_inicio, fecha_fin, metrica):
    """Actualizar el dashboard de generación biomasa"""
    if not n_clicks:
        return html.Div([
            dbc.Alert([
                html.H4("🌿 Bienvenido al Dashboard de Generación Biomasa", className="alert-heading"),
                html.P("Haz clic en 'Actualizar Datos' para cargar la información de generación biomasa."),
                html.Hr(),
                html.P("Este dashboard muestra análisis detallados de la generación de energía biomasa en Colombia.", className="mb-0")
            ], color="info", className="text-center")
        ])
    
    try:
        # Obtener datos biomasa
        datos = obtener_datos_biomasa(metrica, fecha_inicio, fecha_fin)
        
        if datos.empty:
            return dbc.Alert([
                html.H4("⚠️ Sin Datos", className="alert-heading"),
                html.P("No se encontraron datos para el período y métrica seleccionados."),
                html.P("Por favor, verifica las fechas y la métrica biomasa seleccionada.", className="mb-0")
            ], color="warning", className="text-center")
        
        # Crear contenido del dashboard (similar estructura a hidrología)
        return crear_contenido_dashboard_biomasa(datos, metrica)
        
    except Exception as e:
        print(f"Error en callback de generación biomasa: {e}")
        traceback.print_exc()
        return dbc.Alert([
            html.H4("❌ Error", className="alert-heading"),
            html.P(f"Error al procesar los datos: {str(e)}"),
            html.P("Por favor, intenta nuevamente o contacta al administrador.", className="mb-0")
        ], color="danger", className="text-center")

def crear_contenido_dashboard_biomasa(datos, metrica):
    """Crear el contenido principal del dashboard biomasa"""
    try:
        # Análisis estadístico básico
        total_registros = len(datos)
        fecha_min = datos['fecha'].min() if 'fecha' in datos.columns else 'N/A'
        fecha_max = datos['fecha'].max() if 'fecha' in datos.columns else 'N/A'
        
        # Determinar columna numérica principal
        columnas_numericas = datos.select_dtypes(include=['float64', 'int64']).columns
        columna_principal = columnas_numericas[0] if len(columnas_numericas) > 0 else None
        
        if columna_principal:
            valor_promedio = datos[columna_principal].mean()
            valor_max = datos[columna_principal].max()
            valor_min = datos[columna_principal].min()
        else:
            valor_promedio = valor_max = valor_min = 0
        
        # Layout del contenido
        return html.Div([
            # Métricas principales
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4(format_number(total_registros), className="text-primary"),
                            html.P("Total Registros", className="card-text")
                        ])
                    ])
                ], md=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4(format_number(valor_promedio), className="text-success"),
                            html.P("Promedio Biomasa", className="card-text")
                        ])
                    ])
                ], md=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4(format_number(valor_max), className="text-warning"),
                            html.P("Máximo Biomasa", className="card-text")
                        ])
                    ])
                ], md=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4(format_number(valor_min), className="text-info"),
                            html.P("Mínimo Biomasa", className="card-text")
                        ])
                    ])
                ], md=3),
            ], className="mb-4"),
            
            # Gráfico principal
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                                html.I(className="fas fa-chart-line me-2"),
                                f"Evolución de {metrica} - Generación Biomasa"
                            ])
                        ]),
                        dbc.CardBody([
                            dcc.Graph(
                                figure=crear_grafico_biomasa(datos, metrica),
                                style={'height': '400px'}
                            )
                        ])
                    ])
                ], md=12)
            ], className="mb-4"),
            
            # Tabla de datos
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                                html.I(className="fas fa-table me-2"),
                                "Datos Detallados - Generación Biomasa"
                            ])
                        ]),
                        dbc.CardBody([
                            crear_tabla_biomasa(datos)
                        ])
                    ])
                ], md=12)
            ])
        ])
        
    except Exception as e:
        print(f"Error al crear contenido del dashboard biomasa: {e}")
        traceback.print_exc()
        return dbc.Alert(f"Error al crear el dashboard: {str(e)}", color="danger")

def crear_grafico_biomasa(datos, metrica):
    """Crear gráfico de líneas para datos biomasa"""
    try:
        if datos.empty:
            return px.line(title="No hay datos para mostrar")
        
        # Determinar columnas para el gráfico
        if 'fecha' in datos.columns:
            x_col = 'fecha'
        else:
            x_col = datos.columns[0]
        
        columnas_numericas = datos.select_dtypes(include=['float64', 'int64']).columns
        y_col = columnas_numericas[0] if len(columnas_numericas) > 0 else datos.columns[1]
        
        # Crear gráfico
        fig = px.line(
            datos, 
            x=x_col, 
            y=y_col,
            title=f"Evolución de {metrica} - Generación Biomasa",
            labels={x_col: 'Fecha', y_col: 'Valor Biomasa'},
            color_discrete_sequence=['#228B22']  # Color verde para biomasa
        )
        
        fig.update_layout(
            template='plotly_white',
            height=400,
            font=dict(family="Inter, sans-serif"),
            title_font_size=16,
            xaxis_title_font_size=14,
            yaxis_title_font_size=14
        )
        
        return fig
        
    except Exception as e:
        print(f"Error al crear gráfico biomasa: {e}")
        return px.line(title="Error al crear el gráfico")

def crear_tabla_biomasa(datos):
    """Crear tabla interactiva para datos biomasa"""
    try:
        if datos.empty:
            return html.P("No hay datos para mostrar en la tabla.")
        
        # Preparar datos para la tabla
        datos_tabla = datos.copy()
        
        # Formatear columnas numéricas
        for col in datos_tabla.select_dtypes(include=['float64', 'int64']).columns:
            datos_tabla[col] = datos_tabla[col].apply(format_number)
        
        # Formatear fechas
        for col in datos_tabla.select_dtypes(include=['datetime64']).columns:
            datos_tabla[col] = datos_tabla[col].apply(format_date)
        
        # Limitar a primeras 100 filas para rendimiento
        if len(datos_tabla) > 100:
            datos_tabla = datos_tabla.head(100)
            mensaje = html.P(f"Mostrando las primeras 100 filas de {len(datos)} registros totales.", 
                           className="text-muted mb-2")
        else:
            mensaje = html.P(f"Mostrando todos los {len(datos_tabla)} registros.", 
                           className="text-muted mb-2")
        
        return html.Div([
            mensaje,
            dash_table.DataTable(
                data=datos_tabla.to_dict('records'),
                columns=[{"name": col, "id": col} for col in datos_tabla.columns],
                style_table={'overflowX': 'auto'},
                style_cell={
                    'textAlign': 'left',
                    'padding': '10px',
                    'fontFamily': 'Inter, sans-serif'
                },
                style_header={
                    'backgroundColor': '#228B22',
                    'color': 'white',
                    'fontWeight': 'bold'
                },
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': '#F0FFF0'
                    }
                ],
                page_size=20,
                sort_action="native",
                filter_action="native"
            )
        ])
        
    except Exception as e:
        print(f"Error al crear tabla biomasa: {e}")
        return html.P(f"Error al crear la tabla: {str(e)}")
