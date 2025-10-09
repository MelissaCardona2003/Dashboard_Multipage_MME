from dash import dcc, html, callback, register_page
import dash_bootstrap_components as dbc
from .components import crear_header, crear_navbar, crear_sidebar_universal, crear_boton_regresar
from .config import COLORS

register_page(
    __name__,
    path="/generacion/solar",
    name="Generación Solar",
    title="Generación Solar - Ministerio de Minas y Energía de Colombia",
    order=8
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
        titulo_pagina="Generación Solar",
        descripcion_pagina="Análisis y seguimiento de la generación de energía solar en Colombia",
        icono_pagina="fas fa-sun",
        color_tema=COLORS['energia_solar']
    ),
    
    # Container principal
    dbc.Container([
        # Botón de regreso
        crear_boton_regresar(),
        
        # Título principal
        html.Div([
            html.H2([
                html.I(className="fas fa-sun me-3", 
                      style={"color": COLORS['energia_solar']}),
                "Generación Solar"
            ], className="mb-3", style={"color": COLORS['text_primary']}),
            html.P("Selecciona una opción para explorar los datos de generación solar", 
                  className="lead", style={"color": COLORS['text_secondary']})
        ], className="text-center mb-5"),
        
        # Opciones de navegación
        dbc.Row([
            dbc.Col([
                create_technology_card(
                    title="Fuente Solar",
                    description="Tablero completo con gráficas temporales de generación y tabla de participación por plantas solares",
                    icon="fas fa-sun",
                    href="/generacion/solar/fuente",
                    color=COLORS['energia_solar']
                )
            ], md=6),
            
            dbc.Col([
                create_technology_card(
                    title="Análisis Meteorológico",
                    description="Próximamente: Análisis de radiación solar, eficiencia por región y predicción meteorológica",
                    icon="fas fa-cloud-sun",
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
                    "Información sobre Generación Solar"
                ], className="mb-0")
            ]),
            dbc.CardBody([
                html.P([
                    "La generación solar en Colombia ha experimentado un crecimiento significativo en los últimos años, ",
                    "contribuyendo a la diversificación de la matriz energética y al aprovechamiento del recurso solar del país."
                ]),
                html.Ul([
                    html.Li("Plantas solares fotovoltaicas: Conversión directa de luz solar en electricidad"),
                    html.Li("Generación distribuida: Pequeñas instalaciones en techos y superficies"),
                    html.Li("Parques solares: Grandes instalaciones a nivel comercial e industrial")
                ])
            ])
        ])
        
    ], fluid=True, className="py-4")
    
], style={'backgroundColor': COLORS['bg_main'], 'minHeight': '100vh'})
