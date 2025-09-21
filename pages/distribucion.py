from dash import html, dcc, register_page
import dash_bootstrap_components as dbc

# Imports locales para componentes uniformes
from .components import crear_header, crear_sidebar_universal, crear_boton_regresar
from .config import COLORS

register_page(
    __name__,
    path="/distribucion",
    name="Distribución",
    title="Distribución Eléctrica - Ministerio de Minas y Energía",
    order=10
)

# Definir las subsecciones de distribución
DISTRIBUCION_SUBSECTIONS = [
    {"name": "Red de Distribución", "path": "/distribucion-red", "icon": "fas fa-sitemap", "color": "#3F51B5", "description": "Redes locales de distribución"},
    {"name": "Transformadores", "path": "/distribucion-transformadores", "icon": "fas fa-bolt", "color": "#3949AB", "description": "Infraestructura de transformación"},
    {"name": "Calidad del Servicio", "path": "/distribucion-calidad", "icon": "fas fa-chart-line", "color": "#303F9F", "description": "Indicadores de calidad"}
]

def create_subsection_card(subsection):
    """Crear tarjeta para cada subsección de distribución"""
    return dbc.Col([
        html.A([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(
                            className=subsection["icon"],
                            style={
                                "fontSize": "5rem",
                                "color": subsection["color"],
                                "marginBottom": "1.5rem"
                            }
                        ),
                        html.H4(subsection["name"], 
                               className="mb-2",
                               style={"color": COLORS['text_primary'], "fontWeight": "600"}),
                        html.P(subsection["description"],
                              className="text-muted small mb-0",
                              style={"fontSize": "0.9rem"})
                    ], className="text-center"),
                ], className="py-4")
            ], 
            className="h-100 shadow-sm subsection-card",
            style={
                "cursor": "pointer",
                "transition": "all 0.3s ease",
                "border": f"2px solid {subsection['color']}30"
            }
            )
        ], href=subsection["path"], style={"textDecoration": "none"})
    ], lg=4, md=6, sm=12, className="mb-4")

layout = html.Div([
    # Sidebar desplegable
    crear_sidebar_universal(),
    
    # Header específico para distribución
    crear_header(
        titulo_pagina="Distribución Eléctrica",
        descripcion_pagina="Redes de distribución, calidad del servicio y atención a usuarios",
        icono_pagina="fas fa-project-diagram",
        color_tema=COLORS['distribucion']
    ),
    
    # Container principal
    dbc.Container([
        # Botón de regreso
        crear_boton_regresar(),
        
        # Título de la sección
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.I(className="fas fa-project-diagram", 
                          style={"fontSize": "4rem", "color": "#3F51B5", "marginRight": "1rem"}),
                    html.H1("DISTRIBUCIÓN ELÉCTRICA", 
                           style={"color": COLORS['text_primary'], "fontWeight": "700", "display": "inline-block"})
                ], className="text-center mb-2")
            ])
        ]),
        
        dbc.Row([
            dbc.Col([
                html.P("Redes de distribución y consumo final de energía eléctrica",
                      className="text-center text-muted mb-5", 
                      style={"fontSize": "1.2rem"})
            ])
        ]),
        
        # Tarjetas de subsecciones
        dbc.Row([
            create_subsection_card(subsection) for subsection in DISTRIBUCION_SUBSECTIONS
        ]),
        
    ], fluid=True, className="py-4")
])