from dash import html, dcc, register_page
import dash_bootstrap_components as dbc

# Imports locales para componentes uniformes
from .components import crear_header, crear_sidebar_universal, crear_boton_regresar
from .config import COLORS

register_page(
    __name__,
    path="/generacion/hidraulica",
    name="Hidráulica",
    title="Hidráulica - Ministerio de Minas y Energía de Colombia",
    order=2
)

# Definir las tecnologías de generación según la imagen con colores institucionales
GENERACION_HIDRAULICA = [
     {"name": "Hidrología", "path": "/generacion/hidraulica/hidrologia", "icon": "fas fa-tint", "color": COLORS['energia_hidraulica'], "description": "Análisis hidrológico y caudales"},
     {"name": "Fuente Hidráulica", "path": "/generacion/hidraulica/fuente", "icon": "fas fa-water", "color": COLORS['energia_hidraulica'], "description": "Tablero de plantas hidráulicas con generación y participación"},
]

def create_technology_card(tech):
    """Crear tarjeta para cada tecnología de generación hidráulica"""
    return dbc.Col([
        html.A([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(
                            className=tech["icon"],
                            style={
                                "fontSize": "5rem",
                                "color": tech["color"],
                                "marginBottom": "1.5rem"
                            }
                        ),
                        html.H4(tech["name"], 
                               className="mb-2",
                               style={"color": COLORS['text_primary'], "fontWeight": "600"}),
                        html.P(tech["description"],
                              className="text-muted small mb-0",
                              style={"fontSize": "0.9rem"})
                    ], className="text-center"),
                ], className="py-4")
            ], 
            className="h-100 shadow-sm tech-card",
            style={
                "cursor": "pointer",
                "transition": "all 0.3s ease",
                "border": f"2px solid {tech['color']}30"
            }
            )
        ], href=tech["path"], style={"textDecoration": "none"})
    ], lg=4, md=6, sm=12, className="mb-4")

layout = html.Div([
    # Sidebar desplegable
    crear_sidebar_universal(),
    
    # Header específico para generación
    crear_header(
        titulo_pagina="Generación hidráulica",
        descripcion_pagina="Análisis por tecnologías de generación hidráulica en Colombia",
        icono_pagina="fas fa-bolt",
        color_tema=COLORS['primary']
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
                          style={"fontSize": "4rem", "color": "#4285F4", "marginRight": "1rem"}),
                    html.H1("GENERACIÓN HIDRÁULICA", 
                           style={"color": COLORS['text_primary'], "fontWeight": "700", "display": "inline-block"})
                ], className="text-center mb-2")
            ])
        ]),
        
        dbc.Row([
            dbc.Col([
                html.P("Análisis integral de las diferentes tecnologías de generación hidráulica en Colombia",
                      className="text-center text-muted mb-5", 
                      style={"fontSize": "1.2rem"})
            ])
        ]),
        
        # Tarjetas de tecnologías
        dbc.Row([
            create_technology_card(tech) for tech in GENERACION_HIDRAULICA
        ]),
        
    ], fluid=True, className="py-4")
])