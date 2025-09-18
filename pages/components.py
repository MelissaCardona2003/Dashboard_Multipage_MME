"""
Componentes del dashboard Dash
"""
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from .config import COLORS, MAP_CONFIG

def crear_sidebar_universal():
    """Crear un sidebar universal que se puede mostrar/ocultar"""
    return html.Div([
        # Botón toggle para mostrar/ocultar sidebar
        html.Button([
            html.I(className="fas fa-bars")
        ], id="sidebar-toggle", className="btn btn-primary", style={
            'position': 'fixed',
            'top': '20px',
            'left': '20px',
            'zIndex': '1050',
            'borderRadius': '8px',
            'padding': '10px 12px'
        }),
        
        # Overlay
        html.Div(id="sidebar-overlay", className="sidebar-overlay", style={
            'position': 'fixed',
            'top': '0',
            'left': '0',
            'width': '100vw',
            'height': '100vh',
            'background': 'rgba(0,0,0,0.3)',
            'zIndex': '1030',
            'display': 'none'
        }),
        
        # Sidebar principal
        html.Div([
            # Header del sidebar
            html.Div([
                html.Div([
                    html.I(className="fas fa-robot me-2", style={"color": COLORS['primary']}),
                    html.H6("IA Energético", className="mb-0", style={"color": COLORS['primary'], "fontWeight": "bold"})
                ], className="d-flex align-items-center"),
                
                html.Button([
                    html.I(className="fas fa-times")
                ], id="sidebar-close", className="btn btn-link p-1", style={
                    'color': COLORS['text_secondary'],
                    'fontSize': '1rem',
                    'border': 'none',
                    'background': 'transparent',
                    'position': 'absolute',
                    'right': '15px',
                    'top': '15px'
                })
            ], style={'position': 'relative', 'padding': '20px', 'borderBottom': f'1px solid {COLORS["border"]}'}),
            
            # Contenido del sidebar
            html.Div([
                # Enlaces de navegación principales
                html.H6("📊 Dashboards", className="mb-3", style={'color': COLORS['primary'], 'fontWeight': '600'}),
                
                # Inicio
                dbc.NavLink([
                    html.I(className="fas fa-home me-3", style={"color": COLORS['primary']}),
                    "Inicio"
                ], href="/", active="exact", className="nav-link-sidebar mb-2"),
                
                # Métricas
                dbc.NavLink([
                    html.I(className="fas fa-chart-line me-3", style={"color": COLORS['info']}),
                    "Métricas"
                ], href="/metricas", active="exact", className="nav-link-sidebar mb-2"),
                
                # Tableros (acordeón)
                dbc.Accordion([
                    dbc.AccordionItem([
                        # Hidrología
                        dbc.NavLink([
                            html.I(className="fas fa-tint me-3", style={"color": COLORS['accent']}),
                            "Hidrología"
                        ], href="/hidrologia", active="exact", className="nav-link-sidebar ms-3 mb-2"),
                        
                        # Generación (sub-acordeón)
                        dbc.Accordion([
                            dbc.AccordionItem([
                                dbc.NavLink([
                                    html.I(className="fas fa-sun me-3", style={"color": "#FFA500"}),
                                    "Solar"
                                ], href="/generacion/solar", active="exact", className="nav-link-sidebar ms-4"),
                                dbc.NavLink([
                                    html.I(className="fas fa-wind me-3", style={"color": "#00CED1"}),
                                    "Eólica"
                                ], href="/generacion/eolica", active="exact", className="nav-link-sidebar ms-4"),
                                dbc.NavLink([
                                    html.I(className="fas fa-leaf me-3", style={"color": "#228B22"}),
                                    "Biomasa"
                                ], href="/generacion/biomasa", active="exact", className="nav-link-sidebar ms-4"),
                                dbc.NavLink([
                                    html.I(className="fas fa-water me-3", style={"color": "#4682B4"}),
                                    "Hidráulica"
                                ], href="/generacion/hidraulica", active="exact", className="nav-link-sidebar ms-4")
                            ], title="⚡ Generación", item_id="generacion")
                        ], id="accordion-generacion", className="ms-3 mb-2", flush=True, always_open=False),
                        
                        # Demanda
                        dbc.NavLink([
                            html.I(className="fas fa-chart-area me-3", style={"color": "#9932CC"}),
                            "Demanda"
                        ], href="/demanda", active="exact", className="nav-link-sidebar ms-3")
                    ], title="📊 Tableros", item_id="tableros")
                ], id="accordion-tableros", className="mb-4", flush=True, always_open=False),
                
                html.Hr(),
                
                # Información del sistema
                html.H6("ℹ️ Sistema", className="mb-3", style={'color': COLORS['primary'], 'fontWeight': '600'}),
                
                html.Div([
                    html.I(className="fas fa-circle me-2", style={"color": COLORS['success']}),
                    html.Span("Sistema Activo", style={"color": COLORS['success'], "fontSize": "0.9rem"})
                ], className="mb-2"),
                
                html.Div([
                    html.I(className="fas fa-database me-2", style={"color": COLORS['info']}),
                    html.Span("API Conectada", style={"color": COLORS['info'], "fontSize": "0.9rem"})
                ], className="mb-2"),
                
                html.Hr(),
                
                # Enlaces adicionales
                html.H6("🔗 Enlaces", className="mb-3", style={'color': COLORS['primary'], 'fontWeight': '600'}),
                
                html.A([
                    html.I(className="fas fa-external-link-alt me-2"),
                    "Ministerio de Minas"
                ], href="https://www.minenergia.gov.co/", target="_blank", 
                  className="text-decoration-none d-block mb-2", style={"color": COLORS['secondary'], "fontSize": "0.9rem"}),
                
                html.A([
                    html.I(className="fas fa-external-link-alt me-2"),
                    "XM S.A. E.S.P."
                ], href="https://www.xm.com.co/", target="_blank", 
                  className="text-decoration-none d-block", style={"color": COLORS['secondary'], "fontSize": "0.9rem"}),
            ], style={
                'padding': '20px',
                'overflowY': 'auto',
                'height': 'calc(100vh - 80px)'
            })
        ], id="sidebar-content", style={
            'position': 'fixed',
            'top': '0',
            'left': '-300px',
            'width': '300px',
            'height': '100vh',
            'background': COLORS['bg_card'],
            'borderRight': f'1px solid {COLORS["border"]}',
            'boxShadow': '2px 0 10px rgba(0,0,0,0.1)',
            'zIndex': '1040',
            'transition': 'left 0.3s ease-in-out'
        })
    ])

def crear_header(titulo_pagina=None, descripcion_pagina=None, icono_pagina=None, informacion_adicional=None, color_tema=None):
    """Crear el header institucional del dashboard con contenido dinámico por página"""
    
    # Configuración por defecto si no se especifica página
    if not titulo_pagina:
        titulo_pagina = "Agente de IA para el Sector Energético"
        descripcion_pagina = "Asistente Conversacional Inteligente para el Análisis de Métricas Energéticas (XM)"
        icono_pagina = "fas fa-robot"
        informacion_adicional = "Sistema integral de análisis energético del Ministerio de Minas y Energía"
        color_tema = COLORS['primary']
    
    return html.Div([
        html.Div([
            html.H1([
                html.I(className=f"{icono_pagina} me-3", style={"color": color_tema}),
                titulo_pagina
            ], className="hero-title", style={"color": COLORS['text_primary'], "fontWeight": "bold"}),
            html.H4([
                html.I(className="fas fa-info-circle me-2", style={"color": color_tema}),
                descripcion_pagina
            ], className="hero-subtitle mb-3", style={"color": COLORS['text_secondary']}),
            html.P([
                html.I(className="fas fa-building me-2", style={"color": COLORS['primary']}),
                "Ministerio de Minas y Energía - Colombia"
            ], style={
                'fontSize': '1rem',
                'opacity': '0.95',
                'fontWeight': '600',
                'position': 'relative',
                'zIndex': '2',
                'color': COLORS['text_primary']
            }),
            
            # Información adicional específica de la página
            html.P([
                html.I(className="fas fa-lightbulb me-2", style={"color": color_tema}),
                informacion_adicional
            ], style={
                'fontSize': '0.95rem',
                'fontStyle': 'italic',
                'color': COLORS['text_secondary'],
                'marginTop': '1rem'
            }),
            
            # Indicadores flotantes
            html.Div([
                html.Span([
                    html.I(className="fas fa-check-circle me-2"),
                    "Sistema Activo"
                ], className="badge me-3 p-2", style={"background": COLORS['success'], "color": COLORS['text_light']}),
                html.Span([
                    html.I(className="fas fa-chart-line me-2"),
                    "Datos en Tiempo Real"
                ], className="badge me-3 p-2", style={"background": COLORS['info'], "color": COLORS['text_light']}),
                html.Span([
                    html.I(className="fas fa-shield-alt me-2"),
                    "Seguro y Confiable"
                ], className="badge p-2", style={"background": COLORS['accent'], "color": COLORS['text_light']})
            ], style={'marginTop': '2rem', 'position': 'relative', 'zIndex': '2'})
        ], className="hero-header animate-fade-in", style={
            "background": COLORS['bg_header'], 
            "borderRadius": "0", 
            "boxShadow": f"0 2px 8px {COLORS['shadow']}", 
            "padding": "2rem 2rem 1rem 2rem",
            "border": f"1px solid {COLORS['border']}",
            "borderBottom": f"3px solid {color_tema}"
        })
    ], className="mb-4")

def crear_navbar():
    """Barra de navegación eliminada (no se renderiza nada)"""
    return None

def crear_sidebar_metricas(granjas_count, comunidades_count, dist_promedio):
    """Crear sidebar moderno con métricas"""
    return html.Div([
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-chart-pie me-2", style={"color": COLORS['accent']}),
                html.H5("Métricas del Sistema", className="mb-0 d-inline", style={"color": COLORS['primary']})
            ], style={
                'background': f'linear-gradient(135deg, {COLORS["primary"]} 0%, {COLORS["accent"]} 100%)',
                'color': COLORS['text_light'],
                'borderRadius': '20px 20px 0 0',
                'border': 'none'
            }),
            dbc.CardBody([
                crear_metrica_moderna("Granjas Solares", granjas_count, "fas fa-solar-panel", COLORS['primary']),
                html.Hr(style={'margin': '1.5rem 0', 'border': 'none', 'height': '1px', 'background': f'linear-gradient(90deg, transparent, {COLORS["border"]}, transparent)'}),
                crear_metrica_moderna("Comunidades", f"{comunidades_count:,}", "fas fa-users", COLORS['secondary']),
                html.Hr(style={'margin': '1.5rem 0', 'border': 'none', 'height': '1px', 'background': f'linear-gradient(90deg, transparent, {COLORS["border"]}, transparent)'}),
                crear_metrica_moderna("Dist. Promedio", f"{dist_promedio:.1f} km", "fas fa-route", COLORS['accent']),
                # Estado del sistema
                html.Div([
                    html.H6("Estado del Sistema", className="mb-3 mt-4", style={'color': COLORS['primary'], 'fontWeight': '600'}),
                    html.Div([
                        html.Span([
                            html.I(className="fas fa-circle me-2", style={"color": COLORS['success']}),
                            "Online"
                        ], className="d-block mb-2", style={"color": COLORS['success']}),
                        html.Span([
                            html.I(className="fas fa-clock me-2", style={"color": COLORS['info']}),
                            "Actualizado"
                        ], className="d-block mb-2", style={"color": COLORS['info']}),
                        html.Span([
                            html.I(className="fas fa-shield-check me-2", style={"color": COLORS['warning']}),
                            "Seguro"
                        ], className="d-block", style={"color": COLORS['warning']})
                    ])
                ])
            ], style={'padding': '2rem'})
        ], className="sidebar", style={
            'border': f'2px solid {COLORS["accent"]}',
            'borderRadius': '20px',
            'boxShadow': '0 10px 25px -3px rgba(0, 0, 0, 0.1)',
            'background': 'rgba(255, 255, 255, 0.97)',
            'backdropFilter': 'blur(20px)'
        })
    ])

def crear_sidebar_hidrologia(total_rios, total_regiones, caudal_promedio=None):
    """Crear sidebar específico para el contexto hidrológico"""
    return html.Div([
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-water me-2"),
                html.H5("Sistema Hidrológico", className="mb-0 d-inline", style={"color": COLORS['primary']})
            ], style={
                'background': f'linear-gradient(135deg, {COLORS["primary"]} 0%, {COLORS["secondary"]} 100%)',
                'color': COLORS['text_light'],
                'borderRadius': '20px 20px 0 0',
                'border': 'none'
            }),
            dbc.CardBody([
                crear_metrica_moderna("Ríos Monitoreados", f"{total_rios:,}", "fas fa-water", COLORS['primary']),
                html.Hr(style={'margin': '1.5rem 0', 'border': 'none', 'height': '1px', 'background': f'linear-gradient(90deg, transparent, {COLORS["border"]}, transparent)'}),
                crear_metrica_moderna("Regiones Hídricas", f"{total_regiones:,}", "fas fa-map-marked-alt", COLORS['secondary']),
                html.Hr(style={'margin': '1.5rem 0', 'border': 'none', 'height': '1px', 'background': f'linear-gradient(90deg, transparent, {COLORS["border"]}, transparent)'}),
                crear_metrica_moderna("Fuente de Datos", "API XM", "fas fa-database", COLORS['accent']),
                
                # Estado del sistema hidrológico
                html.Div([
                    html.H6("Estado del Sistema", className="mb-3 mt-4", style={'color': COLORS['primary'], 'fontWeight': '600'}),
                    html.Div([
                        html.Span([
                            html.I(className="fas fa-satellite-dish me-2", style={"color": COLORS['success']}),
                            "API Conectada"
                        ], className="d-block mb-2", style={"color": COLORS['success']}),
                        html.Span([
                            html.I(className="fas fa-stream me-2", style={"color": COLORS['info']}),
                            "Datos en Tiempo Real"
                        ], className="d-block mb-2", style={"color": COLORS['info']}),
                        html.Span([
                            html.I(className="fas fa-chart-line me-2", style={"color": COLORS['warning']}),
                            "Monitoreo Activo"
                        ], className="d-block", style={"color": COLORS['warning']})
                    ])
                ])
            ], style={'padding': '2rem'})
        ], className="sidebar", style={
            'border': f'2px solid {COLORS["secondary"]}',
            'borderRadius': '20px',
            'boxShadow': '0 10px 25px -3px rgba(0, 0, 0, 0.1)',
            'background': 'rgba(255, 255, 255, 0.97)',
            'backdropFilter': 'blur(20px)'
        })
    ])

def crear_sidebar_metricas_energeticas(total_metricas, total_entidades, fuente_datos="XM"):
    """Crear sidebar específico para el contexto de métricas energéticas"""
    return html.Div([
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-chart-line me-2"),
                html.H5("Sistema de Métricas", className="mb-0 d-inline", style={"color": COLORS['primary']})
            ], style={
                'background': f'linear-gradient(135deg, {COLORS["primary"]} 0%, {COLORS["accent"]} 100%)',
                'color': COLORS['text_light'],
                'borderRadius': '20px 20px 0 0',
                'border': 'none'
            }),
            dbc.CardBody([
                crear_metrica_moderna("Métricas Disponibles", f"{total_metricas:,}", "fas fa-chart-bar", COLORS['primary']),
                html.Hr(style={'margin': '1.5rem 0', 'border': 'none', 'height': '1px', 'background': f'linear-gradient(90deg, transparent, {COLORS["border"]}, transparent)'}),
                crear_metrica_moderna("Entidades Monitoreadas", f"{total_entidades:,}", "fas fa-building", COLORS['secondary']),
                html.Hr(style={'margin': '1.5rem 0', 'border': 'none', 'height': '1px', 'background': f'linear-gradient(90deg, transparent, {COLORS["border"]}, transparent)'}),
                crear_metrica_moderna("Fuente de Datos", fuente_datos, "fas fa-server", COLORS['accent']),
                
                # Estado del sistema de métricas
                html.Div([
                    html.H6("Estado del Sistema", className="mb-3 mt-4", style={'color': COLORS['primary'], 'fontWeight': '600'}),
                    html.Div([
                        html.Span([
                            html.I(className="fas fa-link me-2", style={"color": COLORS['success']}),
                            "API Activa"
                        ], className="d-block mb-2", style={"color": COLORS['success']}),
                        html.Span([
                            html.I(className="fas fa-sync-alt me-2", style={"color": COLORS['info']}),
                            "Datos Actualizados"
                        ], className="d-block mb-2", style={"color": COLORS['info']}),
                        html.Span([
                            html.I(className="fas fa-shield-alt me-2", style={"color": COLORS['warning']}),
                            "Sistema Estable"
                        ], className="d-block", style={"color": COLORS['warning']})
                    ])
                ])
            ], style={'padding': '2rem'})
        ], className="sidebar", style={
            'border': f'2px solid {COLORS["accent"]}',
            'borderRadius': '20px',
            'boxShadow': '0 10px 25px -3px rgba(0, 0, 0, 0.1)',
            'background': 'rgba(255, 255, 255, 0.97)',
            'backdropFilter': 'blur(20px)'
        })
    ])

def crear_metrica_moderna(titulo, valor, icono, color):
    """Crear una métrica moderna individual"""
    return html.Div([
        html.Div([
            html.I(className=f"{icono} fa-2x mb-3", style={'color': color}),
            html.H3(str(valor), className="metric-value"),
            html.P(titulo, className="metric-label")
        ], className="text-center")
    ], className="metric-card animate-fade-in")

def crear_metrica(titulo, valor, icono):
    """Crear una métrica individual"""
    return html.Div([
        html.P([html.Span(icono), f" {titulo}"], 
               className="mb-1", 
               style={'color': COLORS['text_secondary'], 'fontSize': '0.9rem'}),
        html.H4(str(valor), 
               className="mb-0", 
               style={'color': COLORS['text_primary'], 'fontWeight': 'bold'})
    ])

def crear_mapa_plotly(granjas_df, comunidades_df):
    """Crear mapa moderno con Plotly"""
    fig = go.Figure()
    
    # Granjas con estilo moderno
    if len(granjas_df) > 0:
        fig.add_trace(go.Scattermapbox(
            lat=granjas_df['Latitud'],
            lon=granjas_df['Longitud'],
            mode='markers',
            marker=dict(
                size=16, 
                color=COLORS['primary'], 
                opacity=0.9,
                symbol='circle'
            ),
            text=[f"🏗️ Granja {row['Item']}<br>📍 {row['Municipio']}, {row['Departamento']}<br>⚡ {row['Potencia  KW']} kW<br>👥 {row['Beneficiarios']} beneficiarios" 
                  for _, row in granjas_df.iterrows()],
            name='🏗️ Granjas Solares',
            hovertemplate='%{text}<extra></extra>',
            showlegend=True
        ))
    
    # Comunidades con estilo moderno
    if len(comunidades_df) > 0:
        fig.add_trace(go.Scattermapbox(
            lat=comunidades_df['y'],
            lon=comunidades_df['x'],
            mode='markers',
            marker=dict(
                size=10, 
                color=COLORS['success'], 
                opacity=0.7,
                symbol='circle'
            ),
            text=[f"⚡ CE {row['ID']}<br>📍 {row['Municipio']}<br>🏢 {str(row['Nombre de la comunidad'])[:30]}..." 
                  for _, row in comunidades_df.iterrows()],
            name='⚡ Comunidades Energéticas',
            hovertemplate='%{text}<extra></extra>',
            showlegend=True
        ))
    
    fig.update_layout(
        mapbox=dict(
            style='open-street-map',
            center=dict(lat=MAP_CONFIG['center_lat'], lon=MAP_CONFIG['center_lon']),
            zoom=MAP_CONFIG['zoom']
        ),
        height=600,
        margin=dict(l=0, r=0, t=40, b=0),
        title={
            'text': "🗺️ Ubicación de Granjas y Comunidades Energéticas",
            'x': 0.5,
            'font': {
                'size': 18,
                'family': 'Poppins, sans-serif',
                'color': COLORS['text_primary']
            }
        },
        title_font_color=COLORS['text_primary'],
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_family='Inter, sans-serif',
        legend=dict(
            bgcolor='rgba(255, 255, 255, 0.9)',
            bordercolor=COLORS['border'],
            borderwidth=1,
            font=dict(color=COLORS['text_primary'])
        )
    )
    
    return fig

def crear_grafico_distancias(estadisticas_df):
    """Crear gráfico moderno de barras con distancias"""
    fig = px.bar(
        estadisticas_df.sort_values('Distancia_Media'),
        x='Item', 
        y='Distancia_Media',
        color='Departamento',
        title='📏 Distancia Promedio a las 10 Comunidades Más Cercanas',
        labels={'Item': 'Granja', 'Distancia_Media': 'Distancia Promedio (km)'},
        height=500,
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color=COLORS['text_primary'],
        title_font_color=COLORS['text_primary'],
        title_font_size=18,
        title_font_family='Poppins, sans-serif',
        font_family='Inter, sans-serif',
        showlegend=True,
        legend=dict(
            bgcolor='rgba(255, 255, 255, 0.9)',
            bordercolor=COLORS['border'],
            borderwidth=1
        ),
        xaxis=dict(
            gridcolor='rgba(229, 231, 235, 0.5)',
            zerolinecolor='rgba(229, 231, 235, 0.5)'
        ),
        yaxis=dict(
            gridcolor='rgba(229, 231, 235, 0.5)',
            zerolinecolor='rgba(229, 231, 235, 0.5)'
        )
    )
    
    # Hover personalizado
    fig.update_traces(
        hovertemplate='<b>Granja %{x}</b><br>' +
                      'Distancia: %{y:.2f} km<br>' +
                      '<extra></extra>'
    )
    
    return fig

def crear_tabla_dash(df, table_id):
    """Crear tabla moderna con Dash DataTable"""
    return dash_table.DataTable(
        id=table_id,
        data=df.to_dict('records'),
        columns=[{"name": i, "id": i} for i in df.columns],
        style_table={
            'overflowX': 'auto',
            'borderRadius': '12px',
            'boxShadow': f'0 4px 6px -1px {COLORS["shadow"]}',
            'border': f'2px solid {COLORS["border"]}'
        },
        style_cell={
            'backgroundColor': COLORS['bg_card'],
            'color': COLORS['text_primary'],
            'border': f'1px solid {COLORS["border"]}',
            'textAlign': 'left',
            'padding': '12px 16px',
            'fontFamily': 'Inter, sans-serif',
            'fontSize': '14px'
        },
        style_header={
            'backgroundColor': COLORS['primary'],
            'color': COLORS['text_light'],
            'fontWeight': '600',
            'textTransform': 'uppercase',
            'letterSpacing': '0.5px',
            'fontSize': '12px',
            'border': f'2px solid {COLORS["primary"]}'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': COLORS['bg_main']
            },
            {
                'if': {'state': 'active'},
                'backgroundColor': f'{COLORS["primary"]}20',
                'border': f'1px solid {COLORS["primary"]}',
            }
        ],
        page_size=15,
        sort_action="native",
        filter_action="native",
        style_filter={
            'backgroundColor': COLORS['bg_main'],
            'border': f'1px solid {COLORS["border"]}',
            'borderRadius': '6px'
        }
    )

def crear_cards_top_granjas(estadisticas_df):
    """Crear cards con top granjas"""
    top_5 = estadisticas_df.nsmallest(5, 'Distancia_Media')
    bottom_5 = estadisticas_df.nlargest(5, 'Distancia_Media')
    
    card_top = dbc.Card([
        dbc.CardHeader(html.H5("🏆 Top 5 Mejores Ubicaciones", className="mb-0")),
        dbc.CardBody([
            crear_tabla_dash(top_5[['Item', 'Municipio', 'Distancia_Media']], 'table-top-5')
        ])
    ], style={'backgroundColor': COLORS['bg_card'], 'border': f'1px solid {COLORS["border"]}'})
    
    card_bottom = dbc.Card([
        dbc.CardHeader(html.H5("⚠️ Top 5 Mayores Desafíos", className="mb-0")),
        dbc.CardBody([
            crear_tabla_dash(bottom_5[['Item', 'Municipio', 'Distancia_Media']], 'table-bottom-5')
        ])
    ], style={'backgroundColor': COLORS['bg_card'], 'border': f'1px solid {COLORS["border"]}'})
    
    return card_top, card_bottom

def crear_cards_metricas_principales(granjas_df, estadisticas_df):
    """Crear cards modernos con métricas principales"""
    mejor = estadisticas_df.loc[estadisticas_df['Distancia_Media'].idxmin()]
    peor = estadisticas_df.loc[estadisticas_df['Distancia_Media'].idxmax()]
    
    cards = [
        # Card 1: Granjas Analizadas
        html.Div([
            html.Div([
                html.I(className="fas fa-solar-panel fa-3x mb-3", style={'color': COLORS['primary']}),
                html.H2(len(granjas_df), className="metric-value"),
                html.P("Granjas Analizadas", className="metric-label"),
                html.Small("Instalaciones solares activas", style={'color': COLORS['text_secondary']})
            ], className="text-center p-4")
        ], className="metric-card animate-fade-in"),
        
        # Card 2: Distancia Promedio
        html.Div([
            html.Div([
                html.I(className="fas fa-route fa-3x mb-3", style={'color': COLORS['secondary']}),
                html.H2(f"{estadisticas_df['Distancia_Media'].mean():.1f}", className="metric-value"),
                html.P("Distancia Promedio (km)", className="metric-label"),
                html.Small("A comunidades cercanas", style={'color': COLORS['text_secondary']})
            ], className="text-center p-4")
        ], className="metric-card animate-fade-in"),
        
        # Card 3: Mejor Ubicación
        html.Div([
            html.Div([
                html.I(className="fas fa-trophy fa-3x mb-3", style={'color': COLORS['success']}),
                html.H2(f"#{mejor['Item']}", className="metric-value"),
                html.P("Mejor Ubicación", className="metric-label"),
                html.Small(f"{mejor['Municipio']}", style={'color': COLORS['text_secondary']})
            ], className="text-center p-4")
        ], className="metric-card animate-fade-in"),
        
        # Card 4: Mayor Desafío
        html.Div([
            html.Div([
                html.I(className="fas fa-exclamation-triangle fa-3x mb-3", style={'color': COLORS['warning']}),
                html.H2(f"#{peor['Item']}", className="metric-value"),
                html.P("Mayor Desafío", className="metric-label"),
                html.Small(f"{peor['Municipio']}", style={'color': COLORS['text_secondary']})
            ], className="text-center p-4")
        ], className="metric-card animate-fade-in")
    ]
    
    return cards

# Callbacks para el sidebar
from dash import Input, Output, State, callback, clientside_callback

@callback(
    [Output("sidebar-content", "style"),
     Output("sidebar-overlay", "style")],
    [Input("sidebar-toggle", "n_clicks"),
     Input("sidebar-close", "n_clicks"),
     Input("sidebar-overlay", "n_clicks")],
    [State("sidebar-content", "style"),
     State("sidebar-overlay", "style")],
    prevent_initial_call=True
)
def toggle_sidebar(toggle_clicks, close_clicks, overlay_clicks, sidebar_style, overlay_style):
    """Controlar la apertura y cierre del sidebar"""
    from dash import ctx
    
    if not ctx.triggered:
        return sidebar_style, overlay_style
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Estilos base
    sidebar_hidden = {
        'position': 'fixed',
        'top': '0',
        'left': '-300px',
        'width': '300px',
        'height': '100vh',
        'background': COLORS['bg_card'],
        'borderRight': f'1px solid {COLORS["border"]}',
        'boxShadow': '2px 0 10px rgba(0,0,0,0.1)',
        'zIndex': '1040',
        'transition': 'left 0.3s ease-in-out'
    }
    
    sidebar_visible = sidebar_hidden.copy()
    sidebar_visible['left'] = '0px'
    
    overlay_hidden = {
        'position': 'fixed',
        'top': '0',
        'left': '0',
        'width': '100vw',
        'height': '100vh',
        'background': 'rgba(0,0,0,0.3)',
        'zIndex': '1030',
        'display': 'none'
    }
    
    overlay_visible = overlay_hidden.copy()
    overlay_visible['display'] = 'block'
    
    if button_id == "sidebar-toggle":
        # Abrir sidebar
        return sidebar_visible, overlay_visible
    elif button_id in ["sidebar-close", "sidebar-overlay"]:
        # Cerrar sidebar
        return sidebar_hidden, overlay_hidden
    
    return sidebar_style, overlay_style
