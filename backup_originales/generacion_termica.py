from dash import dcc, html, callback, register_page
import dash_bootstrap_components as dbc
from .components import crear_header, crear_navbar, crear_sidebar_universal, crear_boton_regresar
from .config import COLORS

register_page(
    __name__,
    path="/generacion/termica",
    name="Generación Térmica",
    title="Generación Térmica - Ministerio de Minas y Energía de Colombia",
    order=6
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
        titulo_pagina="Generación Térmica",
        descripcion_pagina="Análisis y seguimiento de la generación de energía térmica en Colombia",
        icono_pagina="fas fa-fire",
        color_tema=COLORS['energia_termica']
    ),
    
    # Container principal
    dbc.Container([
        # Botón de regreso
        crear_boton_regresar(),
        
        # Título principal
        html.Div([
            html.H2([
                html.I(className="fas fa-fire me-3", 
                      style={"color": COLORS['energia_termica']}),
                "Generación Térmica"
            ], className="mb-3", style={"color": COLORS['text_primary']}),
            html.P("Selecciona una opción para explorar los datos de generación térmica", 
                  className="lead", style={"color": COLORS['text_secondary']})
        ], className="text-center mb-5"),
        
        # Opciones de navegación
        dbc.Row([
            dbc.Col([
                create_technology_card(
                    title="Fuente Térmica",
                    description="Tablero completo con gráficas temporales de generación y tabla de participación por plantas térmicas",
                    icon="fas fa-fire",
                    href="/generacion/termica/fuente",
                    color=COLORS['energia_termica']
                )
            ], md=6),
            
            dbc.Col([
                create_technology_card(
                    title="Análisis Detallado",
                    description="Próximamente: Análisis avanzado de eficiencia, costos y emisiones de plantas térmicas",
                    icon="fas fa-chart-bar",
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
                    "Información sobre Generación Térmica"
                ], className="mb-0")
            ]),
            dbc.CardBody([
                html.P([
                    "La generación térmica en Colombia incluye plantas que utilizan combustibles fósiles como carbón, gas natural y combustibles líquidos. ",
                    "Estas plantas son fundamentales para la confiabilidad del sistema eléctrico, especialmente durante períodos de sequía."
                ]),
                html.Ul([
                    html.Li("Plantas de carbón: Generación de base con alta capacidad"),
                    html.Li("Plantas de gas natural: Flexibilidad operativa y menores emisiones"),
                    html.Li("Plantas de combustible líquido: Generación de respaldo")
                ])
            ])
        ])
        
    ], fluid=True, className="py-4")
    
], style={'backgroundColor': COLORS['bg_main'], 'minHeight': '100vh'})
