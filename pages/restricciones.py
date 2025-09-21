from dash import html, dcc, register_page
import dash_bootstrap_components as dbc

# Imports locales para componentes uniformes
from .components import crear_header, crear_sidebar_universal, crear_boton_regresar
from .config import COLORS

register_page(
    __name__,
    path="/restricciones",
    name="Restricciones",
    title="Restricciones Operativas - Ministerio de Minas y Energía",
    order=11
)

# Definir las subsecciones de restricciones
RESTRICCIONES_SUBSECTIONS = [
    {"name": "Restricciones Operativas", "path": "/restricciones-operativas", "icon": "fas fa-stop-circle", "color": "#F44336", "description": "Restricciones activas del sistema"},
    {"name": "Restricciones Ambientales", "path": "/restricciones-ambientales", "icon": "fas fa-leaf", "color": "#E53935", "description": "Limitaciones por factores ambientales"},
    {"name": "Restricciones Regulatorias", "path": "/restricciones-regulatorias", "icon": "fas fa-gavel", "color": "#D32F2F", "description": "Restricciones por normatividad"}
]

def create_subsection_card(subsection):
    """Crear tarjeta para cada subsección de restricciones"""
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
    
    # Header personalizado de la página
    crear_header(
        titulo_pagina="Restricciones del Sistema Eléctrico",
        descripcion_pagina="Análisis de restricciones operativas y limitaciones del sistema eléctrico nacional",
        icono_pagina="fas fa-exclamation-triangle",
        color_tema=COLORS['primary']
    ),
    
    # Botón para regresar al inicio
    crear_boton_regresar(),
    
    # Container principal
    dbc.Container([
        # Tarjetas de subsecciones
        dbc.Row([
            create_subsection_card(subsection) for subsection in RESTRICCIONES_SUBSECTIONS
        ]),
        
    ], fluid=True, className="py-4")
])