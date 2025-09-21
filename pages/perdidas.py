from dash import html, dcc, register_page
import dash_bootstrap_components as dbc

# Imports locales para componentes uniformes
from .components import crear_header, crear_sidebar_universal, crear_boton_regresar
from .config import COLORS

register_page(
    __name__,
    path="/perdidas",
    name="Pérdidas",
    title="Pérdidas del Sistema - Ministerio de Minas y Energía",
    order=6
)

# Definir las áreas de pérdidas
PERDIDAS_AREAS = [
    {"name": "Pérdidas Técnicas", "path": "/perdidas-tecnicas", "icon": "fas fa-cog", "color": "#9C27B0", "description": "Pérdidas inherentes al sistema eléctrico"},
    {"name": "Pérdidas No Técnicas", "path": "/perdidas-comerciales", "icon": "fas fa-exclamation", "color": "#E91E63", "description": "Pérdidas comerciales y fraudes"},
    {"name": "Indicadores", "path": "/perdidas-indicadores", "icon": "fas fa-percentage", "color": "#673AB7", "description": "Indicadores y metas regulatorias"}
]

def create_area_card(area):
    """Crear tarjeta para cada área de pérdidas"""
    return dbc.Col([
        html.A([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(
                            className=area["icon"],
                            style={
                                "fontSize": "5rem",
                                "color": area["color"],
                                "marginBottom": "1.5rem"
                            }
                        ),
                        html.H4(area["name"], 
                               className="mb-2",
                               style={"color": COLORS['text_primary'], "fontWeight": "600"}),
                        html.P(area["description"],
                              className="text-muted small mb-0",
                              style={"fontSize": "0.9rem"})
                    ], className="text-center"),
                ], className="py-4")
            ], 
            className="h-100 shadow-sm area-card",
            style={
                "cursor": "pointer",
                "transition": "all 0.3s ease",
                "border": f"2px solid {area['color']}30"
            }
            )
        ], href=area["path"], style={"textDecoration": "none"})
    ], lg=4, md=6, sm=12, className="mb-4")

layout = html.Div([
    # Sidebar desplegable
    crear_sidebar_universal(),
    
    # Header específico para pérdidas
    crear_header(
        titulo_pagina="Pérdidas Eléctricas",
        descripcion_pagina="Análisis de pérdidas técnicas y comerciales del sistema eléctrico",
        icono_pagina="fas fa-bolt-slash",
        color_tema=COLORS['perdidas']
    ),
    
    # Container principal
    dbc.Container([
        # Botón de regreso
        crear_boton_regresar(),
        
        # Título de la sección
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.I(className="fas fa-exclamation-triangle", 
                          style={"fontSize": "4rem", "color": "#9C27B0", "marginRight": "1rem"}),
                    html.H1("PÉRDIDAS", 
                           style={"color": COLORS['text_primary'], "fontWeight": "700", "display": "inline-block"})
                ], className="text-center mb-2")
            ])
        ]),
        
        dbc.Row([
            dbc.Col([
                html.P("Análisis integral de pérdidas de energía en el sistema eléctrico nacional",
                      className="text-center text-muted mb-5", 
                      style={"fontSize": "1.2rem"})
            ])
        ]),
        
        # Tarjetas de áreas
        dbc.Row([
            create_area_card(area) for area in PERDIDAS_AREAS
        ], justify="center"),
        
        # Información adicional
        dbc.Row([
            dbc.Col([
                dbc.Alert([
                    html.H5([
                        html.I(className="fas fa-info-circle me-2"),
                        "Pérdidas de Energía en el Sistema Eléctrico"
                    ], className="alert-heading"),
                    html.P("Las pérdidas de energía se clasifican en técnicas (inherentes al sistema) y no técnicas (comerciales). Su adecuada gestión es fundamental para la eficiencia del sector eléctrico.", className="mb-3"),
                    html.Hr(),
                    html.P("El marco regulatorio establece metas de pérdidas que los operadores deben cumplir para garantizar la sostenibilidad del sistema.", className="mb-0")
                ], color="warning", className="mt-5")
            ])
        ])
        
    ], fluid=True, className="py-4")
])