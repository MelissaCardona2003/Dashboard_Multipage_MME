from dash import html, dcc, register_page
import dash_bootstrap_components as dbc

# Imports locales para componentes uniformes
from .components import crear_header, crear_sidebar_universal, crear_boton_regresar
from .config import COLORS

register_page(
    __name__,
    path="/generacion",
    name="Generación",
    title="Generación Eléctrica - Ministerio de Minas y Energía",
    order=2
)

# Definir las tecnologías de generación según la imagen con colores institucionales
GENERACION_TECHNOLOGIES = [
    {"name": "Hidráulica", "path": "/generacion/hidraulica", "icon": "fas fa-water", "color": COLORS['energia_hidraulica'], "description": "Generación hidroeléctrica y embalses"},
    {"name": "Hidrología", "path": "/generacion/hidraulica", "icon": "fas fa-tint", "color": COLORS['energia_hidraulica'], "description": "Análisis hidrológico y caudales"},
    {"name": "Combustible fósil", "path": "/generacion/termica", "icon": "fas fa-fire", "color": COLORS['energia_termica'], "description": "Generación térmica con gas, carbón y combustóleo"},
    {"name": "Eólica", "path": "/generacion/eolica", "icon": "fas fa-wind", "color": COLORS['energia_eolica'], "description": "Generación eólica terrestre y marina"},
    {"name": "Biomasa", "path": "/generacion/biomasa", "icon": "fas fa-leaf", "color": COLORS['energia_biomasa'], "description": "Generación con biomasa y residuos"},
    {"name": "Solar", "path": "/generacion/solar", "icon": "fas fa-sun", "color": COLORS['energia_solar'], "description": "Energía solar fotovoltaica y térmica"}
]

def create_technology_card(tech):
    """Crear tarjeta para cada tecnología de generación"""
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
        titulo_pagina="Generación Eléctrica",
        descripcion_pagina="Análisis por tecnologías de generación eléctrica en Colombia",
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
                    html.H1("GENERACIÓN ELÉCTRICA", 
                           style={"color": COLORS['text_primary'], "fontWeight": "700", "display": "inline-block"})
                ], className="text-center mb-2")
            ])
        ]),
        
        dbc.Row([
            dbc.Col([
                html.P("Análisis integral de las diferentes tecnologías de generación eléctrica en Colombia",
                      className="text-center text-muted mb-5", 
                      style={"fontSize": "1.2rem"})
            ])
        ]),
        
        # Tarjetas de tecnologías
        dbc.Row([
            create_technology_card(tech) for tech in GENERACION_TECHNOLOGIES
        ]),
        
    ], fluid=True, className="py-4")
])