from dash import html, dcc, register_page
import dash_bootstrap_components as dbc

# Imports locales para componentes uniformes
from .components import crear_header, crear_sidebar_universal, crear_boton_regresar
from .config import COLORS

register_page(
    __name__,
    path="/generacion/eolica",
    name="Generacion Eolica", 
    title="Dashboard Generación Eólica - Ministerio de Minas y Energía de Colombia",
    order=5
)

# Configuración de tecnologías eólicas
GENERACION_EOLICA = {
    'color': COLORS['energia_eolica'],
    'icono': 'fas fa-wind',
    'titulo': 'Generación Eólica'
}

def create_technology_card(title, icon, color, href, description):
    """Crear tarjeta de tecnología para navegación"""
    return dbc.Col([
        dbc.Card([
            dbc.CardBody([
                html.Div([
                    html.I(className=f"{icon} fa-3x mb-3", style={'color': color}),
                    html.H4(title, className="card-title"),
                    html.P(description, className="card-text text-muted"),
                    dbc.Button([
                        html.I(className="fas fa-arrow-right me-2"), 
                        "Ver Tablero"
                    ],
                    href=href,
                    color="primary",
                    size="lg",
                    className="w-100")
                ], className="text-center")
            ])
        ], className="h-100 shadow-sm hover-card", 
           style={'transition': 'all 0.3s ease', 'cursor': 'pointer'})
    ], md=6, lg=4, className="mb-4")

# --- LAYOUT PRINCIPAL ---
layout = html.Div([
    # Sidebar universal
    crear_sidebar_universal(),
    
    # Header
    crear_header(
        titulo_pagina="Generación Eólica",
        descripcion_pagina="Análisis de fuentes de energía eólica del Sistema Interconectado Nacional",
        icono_pagina=GENERACION_EOLICA['icono'],
        color_tema=GENERACION_EOLICA['color']
    ),
    
    # Container principal
    dbc.Container([
        # Botón de regreso
        crear_boton_regresar(),
        
        # Título de la página
        html.Div([
            html.H2([
                html.I(className=f"{GENERACION_EOLICA['icono']} me-3", 
                      style={"color": GENERACION_EOLICA['color']}),
                GENERACION_EOLICA['titulo']
            ], className="mb-3", style={"color": COLORS['text_primary']}),
            html.P("Seleccione una opción para analizar la generación eólica del sistema eléctrico colombiano", 
                  className="lead", style={"color": COLORS['text_secondary']})
        ], className="text-center mb-5"),
        
        # Tarjetas de navegación
        dbc.Row([
            # Fuente Eólica
            create_technology_card(
                title="Fuente Eólica",
                icon="fas fa-wind", 
                color=COLORS['energia_eolica'],
                href="/generacion/eolica/fuente",
                description="Análisis detallado de generación por plantas eólicas con gráficas temporales y participación"
            )
        ], justify="center"),
        
        # Información adicional
        html.Hr(className="my-5"),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5([
                            html.I(className="fas fa-info-circle me-2", 
                                  style={"color": COLORS['energia_eolica']}),
                            "Información sobre Energía Eólica"
                        ]),
                        html.P([
                            "La energía eólica en Colombia ha tenido un desarrollo importante en los últimos años. ",
                            "Este tablero proporciona análisis detallados de:"
                        ], className="mb-3"),
                        html.Ul([
                            html.Li("Generación en tiempo real por plantas eólicas"),
                            html.Li("Participación de cada planta en el sistema"),
                            html.Li("Evolución temporal de la generación"),
                            html.Li("Factores de planta eólicos"),
                            html.Li("Análisis de velocidad del viento y eficiencia")
                        ], className="mb-3"),
                        html.P([
                            "Los datos se obtienen en tiempo real desde el Sistema de Información de XM, ",
                            "siguiendo la metodología oficial para el análisis de generación eólica."
                        ], className="text-muted")
                    ])
                ])
            ], md=12)
        ]),
        
        # Footer
        html.Hr(),
        html.Div([
            html.P([
                "🌪️ Tablero Generación Eólica - ",
                html.Strong("Ministerio de Minas y Energía de Colombia"),
                " | Datos en tiempo real desde XM"
            ], className="text-center text-muted mb-0")
        ])
        
    ], fluid=True, className="py-4")
    
], style={'backgroundColor': COLORS['bg_main'], 'minHeight': '100vh'})
