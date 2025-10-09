import dash
from dash import html, dcc, register_page
import dash_bootstrap_components as dbc
from datetime import datetime

# Imports locales para componentes uniformes
from .components import crear_header, crear_navbar, crear_sidebar_universal
from .config import COLORS

register_page(
    __name__,
    path="/",
    name="Inicio",
    title="Portal energetico nacional - Ministerio de Minas y Energía",
    order=0
)

# Definir los datos de las secciones principales del sector energético
SECTOR_SECTIONS = {
    "generacion": {
        "title": "Generación",
        "icon": "fas fa-bolt",
        "color": COLORS['accent'],
        "description": "Análisis de generación eléctrica por tecnología",
        "path": "/generacion"
    },
    "transmision": {
        "title": "Transmisión",
        "icon": "fas fa-broadcast-tower",
        "color": COLORS['transmision'],
        "description": "Infraestructura de transmisión eléctrica",
        "path": "/transmision"
    },
    "distribucion": {
        "title": "Distribución",
        "icon": "fas fa-project-diagram",
        "color": COLORS['distribucion'],
        "description": "Redes de distribución y consumo final",
        "path": "/distribucion"
    },
    "demanda": {
        "title": "Demanda",
        "icon": "fas fa-chart-bar",
        "color": COLORS['demanda'],
        "description": "Análisis de demanda energética nacional",
        "path": "/demanda"
    },
    "perdidas": {
        "title": "Pérdidas",
        "icon": "fas fa-exclamation-triangle",
        "color": COLORS['perdidas'],
        "description": "Análisis de pérdidas en el sistema eléctrico",
        "path": "/perdidas"
    },
    "restricciones": {
        "title": "Restricciones",
        "icon": "fas fa-ban",
        "color": COLORS['restricciones'],
        "description": "Restricciones operativas del sistema",
        "path": "/restricciones"
    }
}

# Enlaces externos (como métricas)
EXTERNAL_LINKS = [
    {
        "title": "Métricas",
        "icon": "fas fa-tachometer-alt",
        "color": "#FF5722",
        "description": "Portal de métricas de XM",
        "url": "/metricas"
    }
]

def create_sector_icon_card(section_key, section_data):
    """Crear tarjeta de ícono para cada sector principal con diseño mejorado"""
    return dbc.Col([
        html.A([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        # Contenedor del ícono con efecto circular
                        html.Div([
                            html.I(
                                className=section_data["icon"],
                                style={
                                    "fontSize": "3.5rem",
                                    "color": section_data["color"]
                                }
                            )
                        ], 
                        style={
                            "width": "100px",
                            "height": "100px",
                            "borderRadius": "50%",
                            "background": f"linear-gradient(135deg, {section_data['color']}15, {section_data['color']}25)",
                            "border": f"3px solid {section_data['color']}40",
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                            "margin": "0 auto 1.5rem auto",
                            "transition": "all 0.3s ease"
                        },
                        className="icon-container"),
                        
                        # Título del sector
                        html.H4(section_data["title"],
                               className="mb-3",
                               style={
                                   "color": COLORS['text_primary'], 
                                   "fontWeight": "700",
                                   "fontSize": "1.4rem",
                                   "letterSpacing": "0.02em"
                               }),
                        
                        # Descripción
                        html.P(section_data["description"],
                              className="text-muted mb-0",
                              style={
                                  "fontSize": "0.95rem",
                                  "lineHeight": "1.5",
                                  "color": COLORS['text_secondary']
                              })
                    ], className="text-center"),
                ], className="py-4 px-3")
            ],
            className="h-100 border-0 sector-card",
            style={
                "borderRadius": "16px",
                "transition": "all 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
                "cursor": "pointer",
                "background": COLORS['bg_card'],
                "boxShadow": f"0 4px 20px {COLORS['shadow_sm']}, 0 1px 3px {COLORS['shadow_md']}",
                "border": f"1px solid {COLORS['border_light']}"
            })
        ],
        href=section_data["path"],
        style={"textDecoration": "none"},
        className="sector-card-link")
    ], width=12, md=6, xl=4, className="mb-4")

def create_external_link_card(link):
    """Crear tarjeta para enlaces externos con diseño mejorado"""
    return dbc.Col([
        html.A([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        # Contenedor del ícono con efecto circular
                        html.Div([
                            html.I(
                                className=link["icon"],
                                style={
                                    "fontSize": "3rem",
                                    "color": link["color"]
                                }
                            )
                        ], 
                        style={
                            "width": "80px",
                            "height": "80px",
                            "borderRadius": "50%",
                            "background": f"linear-gradient(135deg, {link['color']}15, {link['color']}25)",
                            "border": f"3px solid {link['color']}40",
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                            "margin": "0 auto 1.5rem auto",
                            "transition": "all 0.3s ease"
                        },
                        className="icon-container"),
                        
                        # Título del enlace
                        html.H5(link["title"],
                               className="mb-2",
                               style={
                                   "color": COLORS['text_primary'], 
                                   "fontWeight": "600",
                                   "fontSize": "1.2rem"
                               }),
                        
                        # Descripción
                        html.P(link["description"],
                              className="text-muted small mb-0",
                              style={
                                  "fontSize": "0.9rem",
                                  "color": COLORS['text_secondary']
                              })
                    ], className="text-center"),
                ], className="py-4 px-3")
            ],
            className="h-100 border-0 external-card",
            style={
                "borderRadius": "12px",
                "transition": "all 0.3s ease",
                "cursor": "pointer",
                "background": COLORS['bg_card'],
                "boxShadow": f"0 2px 8px {COLORS['shadow_sm']}",
                "border": f"1px solid {COLORS['border_light']}"
            })
        ],
        href=link["url"],
        style={"textDecoration": "none"},
        className="sector-card-link")
    ], width=12, md=6, lg=4, className="mb-4")

def layout(**kwargs):
    """Layout principal de la página de inicio"""
    return html.Div([
        # Navbar
        crear_navbar(),

        # Hero Section - Encabezado principal mejorado
        html.Div([
            dbc.Container([
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            # Icono del Ministerio
                            html.Div([
                                html.I(
                                    className="fas fa-bolt",
                                    style={
                                        "fontSize": "4rem",
                                        "color": "#14B8A6",
                                        "marginBottom": "1rem"
                                    }
                                )
                            ]),
                            
                            # Título principal (actualizado)
                            html.H1([
                                "Portal energetico nacional"
                            ],
                            style={
                                "fontSize": "3.5rem",
                                "fontWeight": "800",
                                "marginBottom": "1rem",
                                "color": "#FFFFFF",
                                "textShadow": "0 2px 4px rgba(0,0,0,0.3)",
                                "letterSpacing": "-0.02em"
                            }),
                            
                            # Subtítulo
                            html.P([
                                "Sistema integral de monitoreo y análisis del sector energético colombiano"
                            ],
                            style={
                                "fontSize": "1.3rem",
                                "opacity": "0.9",
                                "maxWidth": "700px",
                                "margin": "0 auto 2rem auto",
                                "lineHeight": "1.6",
                                "color": "#F1F5F9"
                            }),
                            
                            # Fecha y hora de actualización
                            html.Div([
                                html.I(className="fas fa-clock me-2"),
                                f"Última actualización: {datetime.now().strftime('%d/%m/%Y - %H:%M')} COT"
                            ],
                            style={
                                "fontSize": "1rem",
                                "opacity": "0.8",
                                "color": "#CBD5E1",
                                "fontWeight": "500"
                            })
                        ], className="text-center")
                    ], width=12)
                ])
            ], fluid=True, className="py-5")
        ], 
        className="hero-section",
        style={
            "background": "linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #0D9488 100%)",
            "minHeight": "60vh",
            "display": "flex",
            "alignItems": "center"
        }),
        
        # Sección principal con subtítulo
        html.Div([
            dbc.Container([
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.H2("Sectores del Sistema Energético",
                                   style={
                                       "color": COLORS['text_primary'],
                                       "fontWeight": "700",
                                       "fontSize": "2.5rem",
                                       "marginBottom": "0.5rem",
                                       "textAlign": "center"
                                   }),
                            html.P("Explore cada componente del sistema energético nacional",
                                  style={
                                      "color": COLORS['text_secondary'],
                                      "fontSize": "1.1rem",
                                      "textAlign": "center",
                                      "marginBottom": "3rem"
                                  })
                        ])
                    ], width=12)
                ])
            ], fluid=True)
        ], className="py-5"),
        
        # Grid de sectores principales
        html.Div([
            dbc.Container([
                dbc.Row([
                    create_sector_icon_card(key, data)
                    for key, data in SECTOR_SECTIONS.items()
                ], className="g-4")
            ], fluid=True)
        ], className="pb-5"),
        
        # Sección de enlaces externos
        html.Div([
            dbc.Container([
                dbc.Row([
                    dbc.Col([
                        html.H3("Herramientas Adicionales",
                               style={
                                   "color": COLORS['text_primary'],
                                   "fontWeight": "600",
                                   "fontSize": "2rem",
                                   "marginBottom": "2rem",
                                   "textAlign": "center"
                               })
                    ], width=12)
                ]),
                
                dbc.Row([
                    create_external_link_card(link)
                    for link in EXTERNAL_LINKS
                ], className="g-4", justify="center")
                
            ], fluid=True)
        ], className="py-5", style={"background": COLORS['bg_section']}),
        
        # Footer informativo
        html.Div([
            dbc.Container([
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.Div([
                                    html.I(className="fas fa-info-circle me-3",
                                          style={"color": COLORS['info'], "fontSize": "1.5rem"}),
                                    html.Div([
                                        html.Strong("Información del Sistema", 
                                                   style={"color": COLORS['text_primary'], "fontSize": "1.1rem"}),
                                        html.Br(),
                                        html.Small([
                                            "Datos en tiempo real desde la API de XM (Operador del Sistema) • ",
                                            "Información actualizada cada 5 minutos • ",
                                            "Cobertura nacional del Sistema Interconectado"
                                        ], 
                                        className="text-muted",
                                        style={"lineHeight": "1.6"})
                                    ], style={"flex": "1"})
                                ], style={"display": "flex", "alignItems": "center"})
                            ])
                        ], 
                        className="border-0",
                        style={"background": "rgba(255,255,255,0.8)", "backdropFilter": "blur(10px)"})
                    ], width=12)
                ])
            ], fluid=True)
        ], className="py-4"),

        # Sidebar universal
        crear_sidebar_universal()
    ])