# file: your_project/pages/coordenadas.py
import dash
from dash import dcc, html, Input, Output, State, callback, register_page
import dash_bootstrap_components as dbc
import pandas as pd
from io import BytesIO
import base64

# Imports locales
from .data_loader import cargar_datos, crear_tabla_principal, preparar_datos_comunidades, filtrar_coordenadas_validas
from .components import (
    crear_header, crear_navbar, crear_sidebar_universal, crear_mapa_plotly,
    crear_grafico_distancias, crear_tabla_dash, crear_cards_top_granjas,
    crear_cards_metricas_principales
)
from .config import COLORS

register_page(
    __name__,
    path="/coordenadas",
    name="Coordenadas",
    title="Dashboard - Granjas Solares y Comunidades Energéticas",
    order=1
)
granjas_actualizadas, _, comunidades, estadisticas, resumen_detallado = cargar_datos()
granjas_validas = filtrar_coordenadas_validas(granjas_actualizadas)
comunidades_muestra = preparar_datos_comunidades(comunidades, sample_size=100)
layout = html.Div([
    # Sidebar desplegable
    crear_sidebar_universal(),
    
    # Header
    # Header dinámico específico para coordenadas
    crear_header(
        titulo_pagina="Análisis de Proximidad Geográfica",
        descripcion_pagina="Sistema de análisis espacial entre granjas solares y comunidades energéticas",
        icono_pagina="fas fa-map-marked-alt",
        informacion_adicional="Herramientas avanzadas de geolocalización para identificar proyectos viables y calcular distancias euclidianas entre infraestructuras energéticas",
        color_tema="#28a745"
    ),
    # Barra de navegación eliminada
    
    # Container principal
    dbc.Container([
        dbc.Row([
            # Contenido principal (ahora ocupa todo el ancho)
            dbc.Col([
                # Tabs de navegación
                dbc.Tabs([
                    dbc.Tab(label="🔍 Explorar por Granja", tab_id="tab-explorar"),
                    dbc.Tab(label="🗺️ Mapas", tab_id="tab-mapas"),
                    dbc.Tab(label="📈 Estadísticas", tab_id="tab-estadisticas"),
                    dbc.Tab(label="📋 Datos", tab_id="tab-datos"),
                ], id="tabs", active_tab="tab-explorar", className="mb-4"),
                
                # Contenido dinámico
                html.Div(id="coordenadas-tab-content")
            ], width=12)  # Ahora ocupa todo el ancho
        ])
    ], fluid=True)
], style={'backgroundColor': COLORS['bg_main'], 'minHeight': '100vh'})

# Callback para manejar el contenido de las tabs
@callback(
    Output("coordenadas-tab-content", "children"),
    Input("tabs", "active_tab")
)
def render_tab_content(active_tab):
    if active_tab == "tab-explorar":
        return crear_contenido_explorar()
    elif active_tab == "tab-mapas":
        return crear_contenido_mapas()
    elif active_tab == "tab-estadisticas":
        return crear_contenido_estadisticas()
    elif active_tab == "tab-datos":
        return crear_contenido_datos()
    
    return html.Div("Selecciona una pestaña")

def crear_contenido_explorar():
    """Crear contenido de la pestaña Explorar"""
    return html.Div([
        html.H2("🔍 Explorador de Proximidad por Granja", 
                className="mb-4", 
                style={'color': COLORS['text_primary'], 'fontWeight': '600'}),
        
        # Explicación principal con diseño profesional
        dbc.Card([
            dbc.CardBody([
                html.H5([
                    html.I(className="fas fa-search", style={'color': COLORS['primary'], 'marginRight': '10px'}),
                    "Funcionalidad de la Herramienta"
                ], className="mb-3", style={'color': COLORS['text_primary'], 'fontWeight': '600'}),
                
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.I(className="fas fa-bullseye", style={'color': COLORS['success'], 'marginRight': '8px'}),
                            html.Strong("Objetivo", style={'color': COLORS['text_primary']}),
                            html.P("Explorar en detalle las comunidades energéticas más cercanas a cada granja solar específica", 
                                  className="mb-0 mt-1", 
                                  style={'color': COLORS['text_secondary'], 'fontSize': '0.9em', 'lineHeight': '1.5'})
                        ])
                    ], width=6),
                    dbc.Col([
                        html.Div([
                            html.I(className="fas fa-cogs", style={'color': COLORS['info'], 'marginRight': '8px'}),
                            html.Strong("Metodología", style={'color': COLORS['text_primary']}),
                            html.P("Ranking de las 10 comunidades más cercanas ordenadas por distancia euclidiana", 
                                  className="mb-0 mt-1", 
                                  style={'color': COLORS['text_secondary'], 'fontSize': '0.9em', 'lineHeight': '1.5'})
                        ])
                    ], width=6)
                ], className="mb-3"),
                
                html.Hr(style={'borderColor': COLORS['border'], 'margin': '1rem 0'}),
                
                html.Div([
                    html.I(className="fas fa-lightbulb", style={'color': COLORS['warning'], 'marginRight': '8px'}),
                    html.Strong("Aplicaciones Estratégicas", style={'color': COLORS['text_primary']}),
                    html.P("Identificación de oportunidades de colaboración, planificación de rutas de transmisión y evaluación de viabilidad de proyectos conjuntos", 
                          className="mb-0 mt-1", 
                          style={'color': COLORS['text_secondary'], 'fontSize': '0.9em', 'lineHeight': '1.5'})
                ])
            ])
        ], className="mb-4", style={'border': f'1px solid {COLORS["border"]}', 'boxShadow': f'0 2px 4px {COLORS["shadow"]}'}),
        
        # Métricas principales
        dbc.Row([
            dbc.Col(card, width=3) for card in crear_cards_metricas_principales(granjas_actualizadas, estadisticas)
        ], className="mb-4"),
        
        html.Hr(style={'borderColor': COLORS['border_dark'], 'margin': '2rem 0'}),
        
        # Selector de granja con diseño mejorado
        html.H4([
            html.I(className="fas fa-solar-panel", style={'color': COLORS['primary'], 'marginRight': '10px'}),
            "Selección de Granja para Análisis Detallado"
        ], className="mb-4", style={'color': COLORS['text_primary'], 'fontWeight': '600'}),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Label("Selecciona una granja para visualizar sus comunidades más cercanas:", 
                                  className="mb-3",
                                  style={'color': COLORS['text_primary'], 'fontWeight': '500', 'fontSize': '1.1em'}),
                        dcc.Dropdown(
                            id="dropdown-granja",
                            options=[{
                                'label': f"Granja {row['Item']} - {row['Municipio']}, {row['Departamento']}", 
                                'value': row['Item']
                            } for _, row in granjas_actualizadas.iterrows()],
                            value=granjas_actualizadas['Item'].iloc[0],
                            style={'color': '#000000', 'fontSize': '0.95em'}
                        )
                    ])
                ], style={'border': f'1px solid {COLORS["border"]}', 'boxShadow': f'0 1px 3px {COLORS["shadow"]}'})
            ], width=8),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-info-circle", style={'color': COLORS['info'], 'marginRight': '8px'}),
                            html.Strong("Información Técnica", style={'color': COLORS['text_primary'], 'fontSize': '0.9em'}),
                            html.P("Cada granja muestra sus 10 comunidades más cercanas con distancias calculadas mediante geolocalización de precisión", 
                                  className="mb-0 mt-2", 
                                  style={'color': COLORS['text_secondary'], 'fontSize': '0.8em', 'lineHeight': '1.4'})
                        ])
                    ])
                ], style={'backgroundColor': '#F8FAFC', 'border': f'1px solid {COLORS["border"]}'})
            ], width=4)
        ], className="mb-4"),
        
        # Información de la granja seleccionada
        html.Div(id="granja-info"),
        
        # Tabla de comunidades cercanas
        html.Div(id="comunidades-cercanas")
    ])

def crear_contenido_mapas():
    """Crear contenido de la pestaña Mapas"""
    return html.Div([
        html.H2("🗺️ Visualización Geográfica Interactiva", 
                className="mb-4", 
                style={'color': COLORS['text_primary'], 'fontWeight': '600'}),
        
        # Descripción general con diseño profesional
        dbc.Card([
            dbc.CardBody([
                html.H5([
                    html.I(className="fas fa-map-marked-alt", style={'color': COLORS['primary'], 'marginRight': '10px'}),
                    "Mapa Integrado de Infraestructura Energética"
                ], className="mb-3", style={'color': COLORS['text_primary'], 'fontWeight': '600'}),
                
                html.P("Visualización geográfica interactiva que muestra la distribución espacial de granjas solares FENOGE y comunidades energéticas identificadas en el territorio colombiano", 
                       className="mb-3", 
                       style={'color': COLORS['text_secondary'], 'fontStyle': 'italic', 'fontSize': '1.05em', 'lineHeight': '1.6'}),
                
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.I(className="fas fa-search-location", style={'color': COLORS['info'], 'marginRight': '8px'}),
                            html.Strong("Análisis Geoespacial", style={'color': COLORS['text_primary']}),
                            html.P("Identificación de patrones de concentración, oportunidades de proximidad y clusters energéticos territoriales", 
                                  className="mb-0 mt-1", 
                                  style={'color': COLORS['text_secondary'], 'fontSize': '0.9em', 'lineHeight': '1.5'})
                        ])
                    ], width=6),
                    dbc.Col([
                        html.Div([
                            html.I(className="fas fa-route", style={'color': COLORS['success'], 'marginRight': '8px'}),
                            html.Strong("Planificación Estratégica", style={'color': COLORS['text_primary']}),
                            html.P("Evaluación de rutas de interconexión, análisis de viabilidad geográfica y optimización de proyectos", 
                                  className="mb-0 mt-1", 
                                  style={'color': COLORS['text_secondary'], 'fontSize': '0.9em', 'lineHeight': '1.5'})
                        ])
                    ], width=6)
                ])
            ])
        ], className="mb-4", style={'border': f'1px solid {COLORS["border"]}', 'boxShadow': f'0 2px 4px {COLORS["shadow"]}'}),
        
        # Leyenda mejorada con diseño profesional
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H6([
                            html.I(className="fas fa-info-circle", style={'color': COLORS['primary'], 'marginRight': '8px'}),
                            "Leyenda del Mapa"
                        ], className="mb-0", style={'color': COLORS['text_primary'], 'fontWeight': '600'})
                    ], style={'backgroundColor': '#F0F9FF', 'border': 'none'}),
                    dbc.CardBody([
                        html.Div([
                            html.P([
                                html.Span("🔴 ", style={'color': COLORS['danger'], 'fontSize': '1.3em', 'marginRight': '8px'}),
                                html.Strong("Granjas Solares FENOGE", style={'color': COLORS['text_primary']})
                            ], className="mb-1"),
                            html.Small("15 instalaciones fotovoltaicas de 1MW cada una", 
                                     style={'color': COLORS['text_secondary'], 'marginLeft': '24px', 'display': 'block'})
                        ], className="mb-3"),
                        html.Div([
                            html.P([
                                html.Span("🔵 ", style={'color': COLORS['primary'], 'fontSize': '1.3em', 'marginRight': '8px'}),
                                html.Strong("Comunidades Energéticas", style={'color': COLORS['text_primary']})
                            ], className="mb-1"),
                            html.Small("Muestra de 100 comunidades (optimización de rendimiento)", 
                                     style={'color': COLORS['text_secondary'], 'marginLeft': '24px', 'display': 'block'})
                        ])
                    ])
                ], style={'border': f'1px solid {COLORS["border"]}', 'boxShadow': f'0 1px 3px {COLORS["shadow"]}'})
            ], width=5),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H6([
                            html.I(className="fas fa-mouse-pointer", style={'color': COLORS['success'], 'marginRight': '8px'}),
                            "Guía de Interacción"
                        ], className="mb-0", style={'color': COLORS['text_primary'], 'fontWeight': '600'})
                    ], style={'backgroundColor': '#F0FDF4', 'border': 'none'}),
                    dbc.CardBody([
                        html.Ul([
                            html.Li("Haga clic en cualquier punto para información detallada", style={'color': COLORS['text_primary'], 'marginBottom': '6px'}),
                            html.Li("Use controles de zoom para explorar regiones específicas", style={'color': COLORS['text_primary'], 'marginBottom': '6px'}),
                            html.Li("Observe patrones de concentración geográfica", style={'color': COLORS['text_primary'], 'marginBottom': '6px'}),
                            html.Li("Identifique oportunidades de interconexión cercana", style={'color': COLORS['text_primary']})
                        ], style={'fontSize': '0.9em', 'lineHeight': '1.4', 'marginBottom': '0'})
                    ])
                ], style={'border': f'1px solid {COLORS["border"]}', 'boxShadow': f'0 1px 3px {COLORS["shadow"]}'})
            ], width=7)
        ], className="mb-4"),
        
        # Mapa principal con mejor altura
        dbc.Card([
            dbc.CardBody([
                dcc.Graph(
                    id="mapa-principal",
                    figure=crear_mapa_plotly(granjas_validas, comunidades_muestra),
                    style={'height': '650px'}
                )
            ], style={'padding': '10px'})
        ], style={'border': f'1px solid {COLORS["border"]}', 'boxShadow': f'0 2px 4px {COLORS["shadow"]}'})
    ])

def crear_contenido_estadisticas():
    """Crear contenido de la pestaña Estadísticas"""
    card_top, card_bottom = crear_cards_top_granjas(estadisticas)
    
    return html.Div([
        html.H2("📈 Análisis Estadístico de Proximidad Geográfica", 
                className="mb-4", 
                style={'color': COLORS['text_primary'], 'fontWeight': '600'}),
        
        # Explicación general con diseño profesional
        dbc.Card([
            dbc.CardBody([
                html.H5("🎯 Descripción del Análisis", 
                       className="mb-3", 
                       style={'color': COLORS['primary'], 'fontWeight': '600'}),
                html.P([
                    "Este análisis evalúa la ", html.Strong("proximidad geográfica", style={'color': COLORS['primary']}), 
                    " entre las granjas solares y las comunidades energéticas para identificar oportunidades de interconexión y colaboración energética."
                ], className="mb-3", style={'color': COLORS['text_primary'], 'lineHeight': '1.6'}),
                
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.I(className="fas fa-ruler", style={'color': COLORS['info'], 'marginRight': '8px'}),
                            html.Strong("Distancia Media", style={'color': COLORS['text_primary']}),
                            html.P("Promedio de distancias a las 10 comunidades más cercanas", 
                                  className="mb-0 mt-1", 
                                  style={'color': COLORS['text_secondary'], 'fontSize': '0.9em'})
                        ])
                    ], width=6),
                    dbc.Col([
                        html.Div([
                            html.I(className="fas fa-dollar-sign", style={'color': COLORS['success'], 'marginRight': '8px'}),
                            html.Strong("Importancia Económica", style={'color': COLORS['text_primary']}),
                            html.P("Menores distancias = menores costos de transmisión", 
                                  className="mb-0 mt-1", 
                                  style={'color': COLORS['text_secondary'], 'fontSize': '0.9em'})
                        ])
                    ], width=6)
                ])
            ])
        ], className="mb-4", style={'border': f'1px solid {COLORS["border"]}', 'boxShadow': f'0 2px 4px {COLORS["shadow"]}'}),
        
        # Rankings con diseño mejorado
        html.H4("📊 Rankings de Ubicación Estratégica", 
                className="mb-4", 
                style={'color': COLORS['text_primary'], 'fontWeight': '600'}),
        
        dbc.Row([
            dbc.Col([
                # Explicación Top 5 Mejores con diseño profesional
                dbc.Card([
                    dbc.CardHeader([
                        html.H6([
                            html.I(className="fas fa-trophy", style={'color': COLORS['success'], 'marginRight': '8px'}),
                            "Mejores Ubicaciones Estratégicas"
                        ], className="mb-0", style={'color': COLORS['text_primary'], 'fontWeight': '600'})
                    ], style={'backgroundColor': '#F0FDF4', 'border': 'none'}),
                    dbc.CardBody([
                        html.P("Granjas con menor distancia promedio a comunidades energéticas", 
                              className="mb-3", 
                              style={'color': COLORS['text_secondary'], 'fontStyle': 'italic'}),
                        
                        html.Div([
                            html.Strong("Ventajas Competitivas:", 
                                      style={'color': COLORS['success'], 'fontSize': '0.95em'}),
                            html.Ul([
                                html.Li("Menores costos de interconexión", style={'color': COLORS['text_primary']}),
                                html.Li("Mayor viabilidad económica", style={'color': COLORS['text_primary']}),
                                html.Li("Implementación más rápida", style={'color': COLORS['text_primary']}),
                                html.Li("Ideales para proyectos piloto", style={'color': COLORS['text_primary']})
                            ], className="mb-0", style={'fontSize': '0.85em', 'lineHeight': '1.5'})
                        ])
                    ])
                ], className="mb-3", style={'border': f'1px solid #D1FAE5'}),
                card_top
            ], width=6),
            
            dbc.Col([
                # Explicación Top 5 Desafíos con diseño profesional
                dbc.Card([
                    dbc.CardHeader([
                        html.H6([
                            html.I(className="fas fa-exclamation-triangle", style={'color': COLORS['warning'], 'marginRight': '8px'}),
                            "Mayores Desafíos de Conectividad"
                        ], className="mb-0", style={'color': COLORS['text_primary'], 'fontWeight': '600'})
                    ], style={'backgroundColor': '#FFFBEB', 'border': 'none'}),
                    dbc.CardBody([
                        html.P("Granjas con mayor distancia promedio a comunidades energéticas", 
                              className="mb-3", 
                              style={'color': COLORS['text_secondary'], 'fontStyle': 'italic'}),
                        
                        html.Div([
                            html.Strong("Consideraciones Estratégicas:", 
                                      style={'color': COLORS['warning'], 'fontSize': '0.95em'}),
                            html.Ul([
                                html.Li("Requieren mayor inversión inicial", style={'color': COLORS['text_primary']}),
                                html.Li("Costos de transmisión elevados", style={'color': COLORS['text_primary']}),
                                html.Li("Alto potencial de impacto social", style={'color': COLORS['text_primary']}),
                                html.Li("Necesitan estrategias especializadas", style={'color': COLORS['text_primary']})
                            ], className="mb-0", style={'fontSize': '0.85em', 'lineHeight': '1.5'})
                        ])
                    ])
                ], className="mb-3", style={'border': f'1px solid #FED7AA'}),
                card_bottom
            ], width=6)
        ], className="mb-5"),
        
        # Gráfico con explicación mejorada
        html.H4("📈 Distribución de Distancias por Granja", 
                className="mb-3", 
                style={'color': COLORS['text_primary'], 'fontWeight': '600'}),
        
        dbc.Card([
            dbc.CardBody([
                html.P([
                    html.I(className="fas fa-chart-line", style={'color': COLORS['info'], 'marginRight': '8px'}),
                    "Este gráfico presenta el ", html.Strong("rango completo de distancias", style={'color': COLORS['primary']}), 
                    " (mínima, promedio y máxima) para cada granja, permitiendo identificar patrones de dispersión y concentración de comunidades en el territorio nacional."
                ], className="mb-0", style={'color': COLORS['text_primary'], 'lineHeight': '1.6'})
            ])
        ], className="mb-3", style={'backgroundColor': '#F8FAFC', 'border': f'1px solid {COLORS["border"]}'}),
        
        dcc.Graph(
            id="grafico-distancias",
            figure=crear_grafico_distancias(estadisticas)
        )
    ])

def crear_contenido_datos():
    """Crear contenido de la pestaña Datos"""
    tabla_principal = crear_tabla_principal(granjas_actualizadas, estadisticas)
    
    return html.Div([
        html.H2("📋 Base de Datos del Análisis de Proximidad", 
                className="mb-4", 
                style={'color': COLORS['text_primary'], 'fontWeight': '600'}),
        
        # Descripción general con diseño profesional
        dbc.Card([
            dbc.CardBody([
                html.H5([
                    html.I(className="fas fa-database", style={'color': COLORS['primary'], 'marginRight': '10px'}),
                    "Información sobre las Bases de Datos"
                ], className="mb-3", style={'color': COLORS['text_primary'], 'fontWeight': '600'}),
                
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.I(className="fas fa-table", style={'color': COLORS['success'], 'marginRight': '8px'}),
                            html.Strong("Contenido", style={'color': COLORS['text_primary']}),
                            html.P("Datos completos utilizados en el análisis de proximidad geográfica entre granjas solares y comunidades energéticas", 
                                  className="mb-0 mt-1", 
                                  style={'color': COLORS['text_secondary'], 'fontSize': '0.9em', 'lineHeight': '1.5'})
                        ])
                    ], width=6),
                    dbc.Col([
                        html.Div([
                            html.I(className="fas fa-download", style={'color': COLORS['info'], 'marginRight': '8px'}),
                            html.Strong("Formatos Disponibles", style={'color': COLORS['text_primary']}),
                            html.P("CSV (texto plano) y Excel (.xlsx) para análisis externos y procesamiento", 
                                  className="mb-0 mt-1", 
                                  style={'color': COLORS['text_secondary'], 'fontSize': '0.9em', 'lineHeight': '1.5'})
                        ])
                    ], width=6)
                ])
            ])
        ], className="mb-4", style={'border': f'1px solid {COLORS["border"]}', 'boxShadow': f'0 2px 4px {COLORS["shadow"]}'}),
        
        dbc.Tabs([
            dbc.Tab([
                html.H4("🎯 Tabla Principal del Análisis", 
                        className="mt-4 mb-3", 
                        style={'color': COLORS['text_primary'], 'fontWeight': '600'}),
                
                # Explicación mejorada de la tabla principal
                dbc.Card([
                    dbc.CardHeader([
                        html.H6([
                            html.I(className="fas fa-chart-area", style={'color': COLORS['primary'], 'marginRight': '8px'}),
                            "Tabla Consolidada de Análisis"
                        ], className="mb-0", style={'color': COLORS['text_primary'], 'fontWeight': '600'})
                    ], style={'backgroundColor': '#F0F9FF', 'border': 'none'}),
                    dbc.CardBody([
                        html.P("Combina información técnica de granjas solares con estadísticas de proximidad calculadas", 
                              className="mb-3", 
                              style={'color': COLORS['text_secondary'], 'fontStyle': 'italic', 'fontSize': '1.05em'}),
                        
                        dbc.Row([
                            dbc.Col([
                                html.Strong("📊 Datos Incluidos:", style={'color': COLORS['primary'], 'fontSize': '0.95em'}),
                                html.Ul([
                                    html.Li("Información técnica (ubicación, potencia, beneficiarios)", style={'color': COLORS['text_primary']}),
                                    html.Li("Distancia mínima a comunidades", style={'color': COLORS['text_primary']}),
                                    html.Li("Distancia promedio (indicador clave)", style={'color': COLORS['text_primary']}),
                                    html.Li("Distancia máxima del rango analizado", style={'color': COLORS['text_primary']})
                                ], className="mb-0", style={'fontSize': '0.85em', 'lineHeight': '1.5'})
                            ], width=6),
                            dbc.Col([
                                html.Strong("💼 Aplicación Recomendada:", style={'color': COLORS['success'], 'fontSize': '0.95em'}),
                                html.P("Análisis comparativo entre granjas, priorización de proyectos de interconexión y evaluación de viabilidad económica", 
                                      className="mb-0 mt-1", 
                                      style={'color': COLORS['text_primary'], 'fontSize': '0.85em', 'lineHeight': '1.5'})
                            ], width=6)
                        ])
                    ])
                ], className="mb-4", style={'border': f'1px solid #DBEAFE'}),
                
                crear_tabla_dash(tabla_principal, "tabla-principal"),
                
                dbc.Row([
                    dbc.Col([
                        dbc.Button("📥 Descargar CSV", id="btn-csv-principal", color="primary", className="me-2"),
                        dbc.Button("📥 Descargar Excel", id="btn-excel-principal", color="success")
                    ], width=12)
                ], className="mt-3"),
                
                dcc.Download(id="download-csv-principal"),
                dcc.Download(id="download-excel-principal")
            ], label="🎯 Tabla Principal"),
            
            dbc.Tab([
                html.H4("🏗️ Base de Datos de Granjas Solares", 
                        className="mt-4 mb-3", 
                        style={'color': COLORS['text_primary'], 'fontWeight': '600'}),
                
                # Explicación mejorada de granjas
                dbc.Card([
                    dbc.CardHeader([
                        html.H6([
                            html.I(className="fas fa-solar-panel", style={'color': COLORS['success'], 'marginRight': '8px'}),
                            "Registro Técnico de Instalaciones FENOGE"
                        ], className="mb-0", style={'color': COLORS['text_primary'], 'fontWeight': '600'})
                    ], style={'backgroundColor': '#F0FDF4', 'border': 'none'}),
                    dbc.CardBody([
                        html.P("Base de datos completa de las granjas solares incluidas en el programa de Fuentes No Convencionales de Energía", 
                              className="mb-3", 
                              style={'color': COLORS['text_secondary'], 'fontStyle': 'italic', 'fontSize': '1.05em'}),
                        
                        dbc.Row([
                            dbc.Col([
                                html.Strong("🔍 Información Técnica:", style={'color': COLORS['success'], 'fontSize': '0.95em'}),
                                html.Ul([
                                    html.Li("Identificación única por granja", style={'color': COLORS['text_primary']}),
                                    html.Li("Geolocalización precisa (coordenadas)", style={'color': COLORS['text_primary']}),
                                    html.Li("Especificaciones técnicas (potencia kW)", style={'color': COLORS['text_primary']}),
                                    html.Li("Información social (beneficiarios)", style={'color': COLORS['text_primary']})
                                ], className="mb-0", style={'fontSize': '0.85em', 'lineHeight': '1.5'})
                            ], width=6),
                            dbc.Col([
                                html.Strong("💼 Uso Estratégico:", style={'color': COLORS['info'], 'fontSize': '0.95em'}),
                                html.P("Consulta de datos técnicos, planificación de proyectos específicos y análisis de distribución territorial", 
                                      className="mb-0 mt-1", 
                                      style={'color': COLORS['text_primary'], 'fontSize': '0.85em', 'lineHeight': '1.5'})
                            ], width=6)
                        ])
                    ])
                ], className="mb-4", style={'border': f'1px solid #D1FAE5'}),
                
                crear_tabla_dash(granjas_actualizadas, "tabla-granjas"),
                
                dbc.Row([
                    dbc.Col([
                        dbc.Button("📥 Descargar CSV", id="btn-csv-granjas", color="primary", className="me-2"),
                        dbc.Button("📥 Descargar Excel", id="btn-excel-granjas", color="success")
                    ], width=12)
                ], className="mt-3"),
                
                dcc.Download(id="download-csv-granjas"),
                dcc.Download(id="download-excel-granjas")
            ], label="🏗️ Granjas"),
            
            dbc.Tab([
                html.H4("⚡ Comunidades Energéticas", 
                        className="mt-4 mb-3", 
                        style={'color': COLORS['text_primary'], 'fontWeight': '600'}),
                
                # Explicación mejorada de comunidades
                dbc.Card([
                    dbc.CardHeader([
                        html.H6([
                            html.I(className="fas fa-users", style={'color': COLORS['warning'], 'marginRight': '8px'}),
                            "Registro de Comunidades Energéticas"
                        ], className="mb-0", style={'color': COLORS['text_primary'], 'fontWeight': '600'})
                    ], style={'backgroundColor': '#FFFBEB', 'border': 'none'}),
                    dbc.CardBody([
                        html.P("Catálogo de comunidades energéticas identificadas como potenciales beneficiarias de proyectos de interconexión", 
                              className="mb-3", 
                              style={'color': COLORS['text_secondary'], 'fontStyle': 'italic', 'fontSize': '1.05em'}),
                        
                        dbc.Row([
                            dbc.Col([
                                html.Strong("🔍 Datos Registrados:", style={'color': COLORS['warning'], 'fontSize': '0.95em'}),
                                html.Ul([
                                    html.Li("Identificación y denominación oficial", style={'color': COLORS['text_primary']}),
                                    html.Li("Ubicación geográfica detallada", style={'color': COLORS['text_primary']}),
                                    html.Li("Potencia estimada requerida (kWp)", style={'color': COLORS['text_primary']}),
                                    html.Li("Inversión estimada para desarrollo", style={'color': COLORS['text_primary']})
                                ], className="mb-0", style={'fontSize': '0.85em', 'lineHeight': '1.5'})
                            ], width=6),
                            dbc.Col([
                                html.Strong("💼 Aplicación Práctica:", style={'color': COLORS['info'], 'fontSize': '0.95em'}),
                                html.P("Identificación de socios estratégicos, estimación de costos de proyectos y análisis de potencial energético territorial", 
                                      className="mb-0 mt-1", 
                                      style={'color': COLORS['text_primary'], 'fontSize': '0.85em', 'lineHeight': '1.5'})
                            ], width=6)
                        ])
                    ])
                ], className="mb-4", style={'border': f'1px solid #FED7AA'}),
                
                dbc.Alert([
                    html.I(className="fas fa-info-circle", style={'color': COLORS['info'], 'marginRight': '8px'}),
                    html.Strong(f"Muestra Optimizada: ", style={'color': COLORS['text_primary']}),
                    f"Visualizando 50 de {len(comunidades)} comunidades para garantizar rendimiento óptimo. Descargue la tabla completa para acceso total a los datos."
                ], color="light", className="mb-3", style={'border': f'1px solid {COLORS["border"]}'}),
                         
                crear_tabla_dash(comunidades.head(50), "tabla-comunidades"),
                
                dbc.Row([
                    dbc.Col([
                        dbc.Button("📥 Descargar CSV", id="btn-csv-comunidades", color="primary", className="me-2"),
                        dbc.Button("📥 Descargar Excel", id="btn-excel-comunidades", color="success")
                    ], width=12)
                ], className="mt-3"),
                
                dcc.Download(id="download-csv-comunidades"),
                dcc.Download(id="download-excel-comunidades")
            ], label="⚡ Comunidades")
        ])
    ])

# Callback para actualizar información de granja seleccionada
@callback(
    [Output("granja-info", "children"),
     Output("comunidades-cercanas", "children")],
    Input("dropdown-granja", "value")
)
def actualizar_granja_info(granja_seleccionada):
    if not granja_seleccionada:
        return "", ""
    
    # Información de la granja
    granja_info = granjas_actualizadas[granjas_actualizadas['Item'] == granja_seleccionada].iloc[0]
    stats_granja = estadisticas[estadisticas['Item'] == granja_seleccionada].iloc[0]
    
    info_card = dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.H6([
                        html.I(className="fas fa-solar-panel", style={'color': COLORS['success'], 'marginRight': '8px'}),
                        f"Granja Solar {granja_seleccionada}"
                    ], className="mb-0", style={'color': COLORS['text_primary'], 'fontWeight': '600'})
                ], style={'backgroundColor': '#F0FDF4', 'border': 'none'}),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.P([
                                html.I(className="fas fa-map-marker-alt", style={'color': COLORS['primary'], 'marginRight': '6px'}),
                                html.Strong("Ubicación:", style={'color': COLORS['text_primary']}), html.Br(),
                                html.Span(f"{granja_info['Municipio']}, {granja_info['Departamento']}", 
                                         style={'color': COLORS['text_secondary'], 'fontSize': '0.9em'})
                            ], className="mb-2")
                        ], width=12),
                        dbc.Col([
                            html.P([
                                html.I(className="fas fa-bolt", style={'color': COLORS['warning'], 'marginRight': '6px'}),
                                html.Strong("Potencia Instalada:", style={'color': COLORS['text_primary']}), html.Br(),
                                html.Span(f"{granja_info['Potencia  KW']} kW", 
                                         style={'color': COLORS['text_secondary'], 'fontSize': '0.9em', 'fontWeight': 'bold'})
                            ], className="mb-2")
                        ], width=6),
                        dbc.Col([
                            html.P([
                                html.I(className="fas fa-users", style={'color': COLORS['info'], 'marginRight': '6px'}),
                                html.Strong("Beneficiarios:", style={'color': COLORS['text_primary']}), html.Br(),
                                html.Span(f"{granja_info['Beneficiarios']} personas", 
                                         style={'color': COLORS['text_secondary'], 'fontSize': '0.9em', 'fontWeight': 'bold'})
                            ], className="mb-0")
                        ], width=6)
                    ])
                ])
            ], style={'border': f'1px solid #D1FAE5', 'boxShadow': f'0 2px 4px {COLORS["shadow"]}'})
        ], width=6),
        
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.H6([
                        html.I(className="fas fa-chart-line", style={'color': COLORS['primary'], 'marginRight': '8px'}),
                        "Estadísticas de Proximidad"
                    ], className="mb-0", style={'color': COLORS['text_primary'], 'fontWeight': '600'})
                ], style={'backgroundColor': '#F0F9FF', 'border': 'none'}),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.P([
                                html.I(className="fas fa-map-pin", style={'color': COLORS['success'], 'marginRight': '6px'}),
                                html.Strong("Distancia Mínima:", style={'color': COLORS['text_primary']}), html.Br(),
                                html.Span(f"{stats_granja['Distancia_Min']:.2f} km", 
                                         style={'color': COLORS['success'], 'fontSize': '0.9em', 'fontWeight': 'bold'})
                            ], className="mb-2")
                        ], width=12),
                        dbc.Col([
                            html.P([
                                html.I(className="fas fa-balance-scale", style={'color': COLORS['info'], 'marginRight': '6px'}),
                                html.Strong("Distancia Promedio:", style={'color': COLORS['text_primary']}), html.Br(),
                                html.Span(f"{stats_granja['Distancia_Media']:.2f} km", 
                                         style={'color': COLORS['info'], 'fontSize': '0.9em', 'fontWeight': 'bold'})
                            ], className="mb-2")
                        ], width=6),
                        dbc.Col([
                            html.P([
                                html.I(className="fas fa-arrows-alt-h", style={'color': COLORS['warning'], 'marginRight': '6px'}),
                                html.Strong("Distancia Máxima:", style={'color': COLORS['text_primary']}), html.Br(),
                                html.Span(f"{stats_granja['Distancia_Max']:.2f} km", 
                                         style={'color': COLORS['warning'], 'fontSize': '0.9em', 'fontWeight': 'bold'})
                            ], className="mb-0")
                        ], width=6)
                    ])
                ])
            ], style={'border': f'1px solid #DBEAFE', 'boxShadow': f'0 2px 4px {COLORS["shadow"]}'})
        ], width=6)
    ], className="mb-4")
    
    # Tabla de comunidades cercanas
    comunidades_detalle = resumen_detallado[
        resumen_detallado['Granja_Item'] == granja_seleccionada
    ].sort_values('Ranking')[['Ranking', 'Comunidad_ID', 'Comunidad_Nombre', 
                             'Comunidad_Municipio', 'Distancia_km']]
    
    tabla_comunidades = html.Div([
        html.H4([
            html.I(className="fas fa-project-diagram", style={'color': COLORS['primary'], 'marginRight': '10px'}),
            f"Análisis de Proximidad - Granja {granja_seleccionada}"
        ], className="mb-3", style={'color': COLORS['text_primary'], 'fontWeight': '600'}),
        
        # Explicación mejorada de la tabla de comunidades cercanas
        dbc.Card([
            dbc.CardHeader([
                html.H6([
                    html.I(className="fas fa-table", style={'color': COLORS['info'], 'marginRight': '8px'}),
                    "Comunidades Energéticas Más Próximas"
                ], className="mb-0", style={'color': COLORS['text_primary'], 'fontWeight': '600'})
            ], style={'backgroundColor': '#F0F9FF', 'border': 'none'}),
            dbc.CardBody([
                html.P("Ranking de las 10 comunidades energéticas con menor distancia euclidiana a esta granja solar, priorizadas para análisis de viabilidad de interconexión", 
                      className="mb-3", 
                      style={'color': COLORS['text_secondary'], 'fontStyle': 'italic', 'fontSize': '1.05em'}),
                
                dbc.Row([
                    dbc.Col([
                        html.Strong("📊 Criterios de Ranking:", style={'color': COLORS['info'], 'fontSize': '0.95em'}),
                        html.Ul([
                            html.Li("Posición 1: Comunidad más cercana (prioridad máxima)", style={'color': COLORS['text_primary']}),
                            html.Li("Distancia en kilómetros (línea recta)", style={'color': COLORS['text_primary']}),
                            html.Li("Identificación única y ubicación municipal", style={'color': COLORS['text_primary']})
                        ], className="mb-0", style={'fontSize': '0.85em', 'lineHeight': '1.5'})
                    ], width=6),
                    dbc.Col([
                        html.Strong("💼 Interpretación Estratégica:", style={'color': COLORS['success'], 'fontSize': '0.95em'}),
                        html.P("Menores distancias indican mayor viabilidad técnica y económica para proyectos de interconexión, reduciendo costos de transmisión y tiempos de implementación", 
                              className="mb-0 mt-1", 
                              style={'color': COLORS['text_primary'], 'fontSize': '0.85em', 'lineHeight': '1.5'})
                    ], width=6)
                ])
            ])
        ], className="mb-3", style={'border': f'1px solid #DBEAFE'}),
        
        crear_tabla_dash(comunidades_detalle, f"tabla-comunidades-{granja_seleccionada}"),
        
        dbc.Row([
            dbc.Col([
                dbc.Button("📥 Descargar CSV", id="btn-csv-comunidades-cercanas", color="primary", className="me-2"),
                dbc.Button("📥 Descargar Excel", id="btn-excel-comunidades-cercanas", color="success")
            ], width=12)
        ], className="mt-3"),
        
        dcc.Download(id="download-csv-comunidades-cercanas"),
        dcc.Download(id="download-excel-comunidades-cercanas")
    ])
    
    return info_card, tabla_comunidades

# Funciones auxiliares para descargas
def to_csv(df):
    return df.to_csv(index=False)

def to_excel_download(df):
    import base64
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Datos')
    excel_data = output.getvalue()
    return base64.b64encode(excel_data).decode()

# Callbacks para descargas
def crear_callbacks_descarga():
    """Crear callbacks para todas las descargas"""
    
    # Callback para tabla principal
    @callback(
        Output("download-csv-principal", "data"),
        Input("btn-csv-principal", "n_clicks"),
        prevent_initial_call=True
    )
    def descargar_csv_principal(n_clicks):
        if n_clicks:
            tabla_principal = crear_tabla_principal(granjas_actualizadas, estadisticas)
            return dict(content=to_csv(tabla_principal), filename="tabla_principal.csv")
    
    @callback(
        Output("download-excel-principal", "data"),
        Input("btn-excel-principal", "n_clicks"),
        prevent_initial_call=True
    )
    def descargar_excel_principal(n_clicks):
        if n_clicks:
            tabla_principal = crear_tabla_principal(granjas_actualizadas, estadisticas)
            return dict(content=to_excel_download(tabla_principal), filename="tabla_principal.xlsx", base64=True)
    
    # Callbacks para granjas
    @callback(
        Output("download-csv-granjas", "data"),
        Input("btn-csv-granjas", "n_clicks"),
        prevent_initial_call=True
    )
    def descargar_csv_granjas(n_clicks):
        if n_clicks:
            return dict(content=to_csv(granjas_actualizadas), filename="base_granjas.csv")
    
    @callback(
        Output("download-excel-granjas", "data"),
        Input("btn-excel-granjas", "n_clicks"),
        prevent_initial_call=True
    )
    def descargar_excel_granjas(n_clicks):
        if n_clicks:
            return dict(content=to_excel_download(granjas_actualizadas), filename="base_granjas.xlsx", base64=True)
    
    # Callbacks para comunidades
    @callback(
        Output("download-csv-comunidades", "data"),
        Input("btn-csv-comunidades", "n_clicks"),
        prevent_initial_call=True
    )
    def descargar_csv_comunidades(n_clicks):
        if n_clicks:
            return dict(content=to_csv(comunidades.head(50)), filename="comunidades_muestra.csv")
    
    @callback(
        Output("download-excel-comunidades", "data"),
        Input("btn-excel-comunidades", "n_clicks"),
        prevent_initial_call=True
    )
    def descargar_excel_comunidades(n_clicks):
        if n_clicks:
            return dict(content=to_excel_download(comunidades.head(50)), filename="comunidades_muestra.xlsx", base64=True)

# Callbacks para comunidades cercanas (dinámicas)
@callback(
    Output("download-csv-comunidades-cercanas", "data"),
    [Input("btn-csv-comunidades-cercanas", "n_clicks")],
    [State("dropdown-granja", "value")],
    prevent_initial_call=True
)
def descargar_csv_comunidades_cercanas(n_clicks, granja_seleccionada):
    if n_clicks and granja_seleccionada:
        comunidades_detalle = resumen_detallado[
            resumen_detallado['Granja_Item'] == granja_seleccionada
        ].sort_values('Ranking')[['Ranking', 'Comunidad_ID', 'Comunidad_Nombre', 
                                 'Comunidad_Municipio', 'Distancia_km']]
        return dict(content=to_csv(comunidades_detalle), filename=f"comunidades_cercanas_granja_{granja_seleccionada}.csv")

@callback(
    Output("download-excel-comunidades-cercanas", "data"),
    [Input("btn-excel-comunidades-cercanas", "n_clicks")],
    [State("dropdown-granja", "value")],
    prevent_initial_call=True
)
def descargar_excel_comunidades_cercanas(n_clicks, granja_seleccionada):
    if n_clicks and granja_seleccionada:
        comunidades_detalle = resumen_detallado[
            resumen_detallado['Granja_Item'] == granja_seleccionada
        ].sort_values('Ranking')[['Ranking', 'Comunidad_ID', 'Comunidad_Nombre', 
                                 'Comunidad_Municipio', 'Distancia_km']]
        return dict(content=to_excel_download(comunidades_detalle), filename=f"comunidades_cercanas_granja_{granja_seleccionada}.xlsx", base64=True)

# Crear todos los callbacks de descarga
crear_callbacks_descarga()