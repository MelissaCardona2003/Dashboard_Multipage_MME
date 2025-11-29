
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
from utils.components import crear_header, crear_navbar, crear_sidebar_universal
from utils.config import COLORS

warnings.filterwarnings("ignore")

register_page(
    __name__,
    path="/perdidas-indicadores",
    name="Indicadores de Pérdidas",
    title="Indicadores de Pérdidas - Ministerio de Minas y Energía de Colombia",
    order=17
)

LAST_UPDATE = time.strftime('%Y-%m-%d %H:%M:%S')

def layout():
    """Layout de la página de Indicadores de Pérdidas"""
    return html.Div([
        # Header y navegación
        crear_header(),
        crear_navbar(),
        
        # Contenido principal
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H1("Indicadores de Pérdidas", 
                           className="text-center mb-4",
                           style={"color": COLORS['primary']}),
                    html.P("Indicadores y métricas de pérdidas del sistema eléctrico.",
                          className="text-center text-muted mb-4"),
                    
                    # Placeholder para contenido
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Indicadores y Métricas", className="mb-3"),
                            html.P("Esta sección contendrá los indicadores de pérdidas del sistema.",
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