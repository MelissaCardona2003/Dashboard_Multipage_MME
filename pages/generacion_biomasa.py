from dash import dcc, html, callback, register_page
import dash_bootstrap_components as dbc
from .components import crear_header, crear_navbar, crear_sidebar_universal, crear_boton_regresar
from .config import COLORS

register_page(
    __name__,
    path="/generacion/biomasa",
    name="Generación Biomasa",
    title="Generación Biomasa - Ministerio de Minas y Energía de Colombia",
    order=10
)

def create_technology_card(title, description, icon, href, color):
    """Crear tarjeta de tecnología"""
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.I(className=f"{icon} fa-3x mb-3", style={"color": color}),
                html.H4(title, className="card-title"),
                html.P(description, className="card-text"),
                dbc.Button("Ver Tablero", href=href, color="primary", 
                          external_link=True, className="mt-3")
            ], className="text-center")
        ])
    ], className="h-100 shadow-sm hover-shadow", 
       style={"transition": "all 0.3s ease"})

# Layout principal
layout = html.Div([
    # Sidebar universal
    crear_sidebar_universal(),
    
    # Header
    crear_header(
        titulo_pagina="Generación Biomasa",
        descripcion_pagina="Análisis y seguimiento de la generación de energía con biomasa en Colombia",
        icono_pagina="fas fa-leaf",
        color_tema=COLORS['energia_biomasa']
    ),
    
    # Container principal
    dbc.Container([
        # Botón de regreso
        crear_boton_regresar(),
        
        # Título principal
        html.Div([
            html.H2([
                html.I(className="fas fa-leaf me-3", 
                      style={"color": COLORS['energia_biomasa']}),
                "Generación Biomasa"
            ], className="mb-3", style={"color": COLORS['text_primary']}),
            html.P("Selecciona una opción para explorar los datos de generación con biomasa", 
                  className="lead", style={"color": COLORS['text_secondary']})
        ], className="text-center mb-5"),
        
        # Opciones de navegación
        dbc.Row([
            dbc.Col([
                create_technology_card(
                    title="Fuente Biomasa",
                    description="Tablero completo con gráficas temporales de generación y tabla de participación por plantas de biomasa",
                    icon="fas fa-leaf",
                    href="/generacion/biomasa/fuente",
                    color=COLORS['energia_biomasa']
                )
            ], md=6),
            
            dbc.Col([
                create_technology_card(
                    title="Análisis Sostenibilidad",
                    description="Próximamente: Análisis de sostenibilidad, impacto ambiental y eficiencia de biomasa",
                    icon="fas fa-recycle",
                    href="#",
                    color=COLORS['text_muted']
                )
            ], md=6)
        ], className="g-4 mb-5"),
        
        # Información adicional
        dbc.Card([
            dbc.CardHeader([
                html.H5([
                    html.I(className="fas fa-info-circle me-2"),
                    "Información sobre Generación con Biomasa"
                ], className="mb-0")
            ]),
            dbc.CardBody([
                html.P([
                    "La generación con biomasa en Colombia aprovecha residuos orgánicos y cultivos energéticos para producir electricidad, ",
                    "contribuyendo a la economía circular y la reducción de residuos."
                ]),
                html.Ul([
                    html.Li("Biomasa vegetal: Residuos forestales y agrícolas"),
                    html.Li("Biogás: Aprovechamiento de residuos orgánicos y rellenos sanitarios"),
                    html.Li("Cultivos energéticos: Plantaciones específicas para generación eléctrica")
                ])
            ])
        ])
        
    ], fluid=True, className="py-4")
    
], style={'backgroundColor': COLORS['bg_main'], 'minHeight': '100vh'})
