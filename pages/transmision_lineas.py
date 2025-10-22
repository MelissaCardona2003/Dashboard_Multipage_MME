
def get_plotly_modules():
    """Importar plotly solo cuando se necesite"""
    import plotly.express as px
    import plotly.graph_objects as go
    return px, go

from dash import dcc, html, Input, Output, State, callback, register_page
import dash_bootstrap_components as dbc
import pandas as pd
from datetime import date, timedelta, datetime
import warnings
import sys
import os
import time

# Imports locales para componentes uniformes
from .components import crear_header, crear_navbar, crear_sidebar_universal
from .config import COLORS

warnings.filterwarnings("ignore")

register_page(
    __name__,
    path="/transmision-lineas",
    name="Líneas de Transmisión",
    title="Líneas de Transmisión - Ministerio de Minas y Energía de Colombia",
    order=20
)

LAST_UPDATE = time.strftime('%Y-%m-%d %H:%M:%S')

def layout():
    """Layout de la página de Líneas de Transmisión"""
    return html.Div([
        # Header y navegación
        crear_header(),
        crear_navbar(),
        
        # Contenido principal
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H1("Líneas de Transmisión", 
                           className="text-center mb-4",
                           style={"color": COLORS['primary']}),
                    html.P("Monitoreo y análisis de las líneas de transmisión del Sistema Interconectado Nacional.",
                          className="text-center text-muted mb-4"),
                    
                    # Placeholder para contenido
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Red de Transmisión", className="mb-3"),
                            html.P("Esta sección contendrá el análisis de las líneas de transmisión.",
                                  className="text-muted"),
                            html.Hr(),
                            html.P(f"Última actualización: {LAST_UPDATE}", 
                                  className="small text-muted"),
                        ])
                    ], className="shadow-sm")
                    
                ], width=12)
            ])
        ], fluid=True, className="py-4"),
        
        # Sidebar universal
        crear_sidebar_universal()
    ])