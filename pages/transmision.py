from dash import html, dcc, register_page
import dash_bootstrap_components as dbc

# Imports locales para componentes uniformes
from .components import crear_header, crear_sidebar_universal, crear_boton_regresar
from .config import COLORS

register_page(
    __name__,
    path="/transmision",
    name="Transmisión",
    title="Transmisión Eléctrica - Ministerio de Minas y Energía",
    order=9
)

# Definir las subsecciones de transmisión
TRANSMISION_SUBSECTIONS = [
    {"name": "Líneas de Transmisión", "path": "/transmision-lineas", "icon": "fas fa-plug", "color": "#00BCD4", "description": "Red de líneas de alta tensión"},
    {"name": "Subestaciones", "path": "/transmision-subestaciones", "icon": "fas fa-building", "color": "#0097A7", "description": "Infraestructura de subestaciones"},
    {"name": "Congestión", "path": "/transmision-congestion", "icon": "fas fa-traffic-light", "color": "#00ACC1", "description": "Análisis de congestión del sistema"}
]

def create_subsection_card(subsection):
    """Crear tarjeta para cada subsección de transmisión"""
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
    
    # Header específico para transmisión
    crear_header(
        titulo_pagina="Transmisión Eléctrica",
        descripcion_pagina="Infraestructura de transmisión y subestaciones del sistema eléctrico",
        icono_pagina="fas fa-broadcast-tower",
        color_tema=COLORS['transmision']
    ),
    
    # Container principal
    dbc.Container([
        # Botón de regreso
        crear_boton_regresar(),
        
        # Título de la sección
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.I(className="fas fa-broadcast-tower", 
                          style={"fontSize": "4rem", "color": "#00BCD4", "marginRight": "1rem"}),
                    html.H1("TRANSMISIÓN ELÉCTRICA", 
                           style={"color": COLORS['text_primary'], "fontWeight": "700", "display": "inline-block"})
                ], className="text-center mb-2")
            ])
        ]),
        
        dbc.Row([
            dbc.Col([
                html.P("Infraestructura de transmisión y transporte de energía eléctrica",
                      className="text-center text-muted mb-5", 
                      style={"fontSize": "1.2rem"})
            ])
        ]),
        
        # Tarjetas de subsecciones
        dbc.Row([
            create_subsection_card(subsection) for subsection in TRANSMISION_SUBSECTIONS
        ]),
        
    ], fluid=True, className="py-4")
])