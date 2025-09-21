from dash import dcc, html, Input, Output, State, dash_table, ALL, callback, register_page
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import datetime as dt
from datetime import date, timedelta, datetime
import warnings
import sys
import os
import time
import traceback

# Imports locales para componentes uniformes
from .components import crear_header, crear_navbar, crear_sidebar_universal
from .config import COLORS

warnings.filterwarnings("ignore")

register_page(
    __name__,
    path="/transmision-congestion",
    name="Congestión",
    title="Congestión de Transmisión - Ministerio de Minas y Energía de Colombia",
    order=22
)

LAST_UPDATE = time.strftime('%Y-%m-%d %H:%M:%S')

def layout():
    """Layout de la página de Congestión"""
    return html.Div([
        # Header y navegación
        crear_header(),
        crear_navbar(),
        
        # Contenido principal
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H1("Congestión de Transmisión", 
                           className="text-center mb-4",
                           style={"color": COLORS['primary']}),
                    html.P("Análisis de congestión y restricciones en la red de transmisión.",
                          className="text-center text-muted mb-4"),
                    
                    # Placeholder para contenido
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Análisis de Congestión", className="mb-3"),
                            html.P("Esta sección contendrá el análisis de congestión en las líneas de transmisión.",
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