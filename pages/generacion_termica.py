from dash import dcc, html, Input, Output, State, dash_table, ALL, callback, register_page
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import time

# Imports locales
from .components import crear_header, crear_sidebar_universal, crear_boton_regresar
from .config import COLORS

# Inicializar data
print("✅ Iniciando módulo generacion_termica.py...")

try:
    from pydataxm import ReadDB
    objetoAPI = ReadDB()
    print("✅ API XM inicializada correctamente en generacion_termica.py")
    print(f"🔍 objetoAPI = {objetoAPI}")
    
except Exception as e:
    print(f"⚠️ Error inicializando API en generacion_termica.py: {e}")
    objetoAPI = None

register_page(
    __name__,
    path="/generacion/termica",
    name="Generación Térmica",
    title="Generación Térmica - Ministerio de Minas y Energía",
    order=7
)

def layout(**kwargs):
    """Layout principal de la página de generación térmica"""
    return html.Div([
        # Header
        crear_header(
            titulo_pagina="Generación Térmica",
            descripcion_pagina="Análisis de plantas térmicas, gas natural, carbón y combustóleo",
            icono_pagina="fas fa-fire",
            color_tema=COLORS['energia_termica']
        ),

        # Contenido principal
        dbc.Container([
            # Botón de regreso
            crear_boton_regresar(),
            
            # Selector de métricas
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-chart-line me-2", style={"color": COLORS['energia_termica']}),
                    html.H5("Panel de Control - Generación Térmica", className="mb-0")
                ]),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Seleccionar Métrica:", className="fw-bold"),
                            dcc.Dropdown(
                                id="dropdown-metrica-termica",
                                options=[
                                    {"label": "Generación Térmica Total", "value": "generacion_termica"},
                                    {"label": "Generación Gas Natural", "value": "generacion_gas"},
                                    {"label": "Generación Carbón", "value": "generacion_carbon"},
                                    {"label": "Disponibilidad Térmica", "value": "disponibilidad_termica"}
                                ],
                                value="generacion_termica",
                                placeholder="Seleccione una métrica de generación térmica...",
                                style={"marginBottom": "15px"}
                            )
                        ], width=6),
                        dbc.Col([
                            html.Label("Entidad:", className="fw-bold"),
                            dcc.Dropdown(
                                id="dropdown-entidad-termica",
                                options=[
                                    {"label": "Sistema Nacional", "value": "Sistema"},
                                    {"label": "Termozipa", "value": "TERMOZIPA"},
                                    {"label": "Termoflores", "value": "TERMOFLORES"},
                                    {"label": "Thermal Power", "value": "THERMAL"}
                                ],
                                value="Sistema",
                                placeholder="Seleccione entidad...",
                                style={"marginBottom": "15px"}
                            )
                        ], width=6)
                    ]),
                    
                    dbc.Row([
                        dbc.Col([
                            html.Label("Fecha Inicio:", className="fw-bold"),
                            dcc.DatePickerSingle(
                                id="date-picker-inicio-termica",
                                date="2024-01-01",
                                display_format="DD/MM/YYYY",
                                style={"width": "100%"}
                            )
                        ], width=6),
                        dbc.Col([
                            html.Label("Fecha Fin:", className="fw-bold"),
                            dcc.DatePickerSingle(
                                id="date-picker-fin-termica",
                                date=datetime.now().strftime("%Y-%m-%d"),
                                display_format="DD/MM/YYYY",
                                style={"width": "100%"}
                            )
                        ], width=6)
                    ]),
                    
                    html.Hr(),
                    dbc.Row([
                        dbc.Col([
                            dbc.Button(
                                [html.I(className="fas fa-search me-2"), "Consultar Datos"],
                                id="btn-consultar-termica",
                                color="primary",
                                size="lg",
                                className="w-100"
                            )
                        ], width=12)
                    ])
                ])
            ], className="mb-4"),

            # Área de resultados
            html.Div(id="resultados-termica"),

            # Información adicional
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-info-circle me-2", style={"color": COLORS['energia_termica']}),
                    html.H6("Información Técnica - Generación Térmica", className="mb-0")
                ]),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.H6("🔥 Tecnologías Térmicas", className="text-primary"),
                            html.Ul([
                                html.Li("Centrales de Gas Natural"),
                                html.Li("Plantas de Carbón"),
                                html.Li("Ciclo Combinado"),
                                html.Li("Combustóleo/Diesel")
                            ])
                        ], width=3),
                        dbc.Col([
                            html.H6("📊 Métricas Clave", className="text-success"),
                            html.Ul([
                                html.Li("Generación por Combustible"),
                                html.Li("Eficiencia Térmica"),
                                html.Li("Factor de Planta"),
                                html.Li("Emisiones CO₂")
                            ])
                        ], width=3),
                        dbc.Col([
                            html.H6("🌍 Impacto Ambiental", className="text-warning"),
                            html.Ul([
                                html.Li("Monitoreo de Emisiones"),
                                html.Li("Uso de Combustibles"),
                                html.Li("Eficiencia Energética"),
                                html.Li("Transición Energética")
                            ])
                        ], width=3),
                        dbc.Col([
                            html.H6("📈 Análisis Operativo", className="text-info"),
                            html.Ul([
                                html.Li("Despacho Económico"),
                                html.Li("Costos Variables"),
                                html.Li("Mantenimientos"),
                                html.Li("Disponibilidad")
                            ])
                        ], width=3)
                    ])
                ])
            ], className="mt-4")

        ], fluid=True, className="py-4"),

        # Sidebar universal
        crear_sidebar_universal()
    ])

# Callback para consultar datos
@callback(
    Output("resultados-termica", "children"),
    [Input("btn-consultar-termica", "n_clicks")],
    [State("dropdown-metrica-termica", "value"),
     State("dropdown-entidad-termica", "value"),
     State("date-picker-inicio-termica", "date"),
     State("date-picker-fin-termica", "date")],
    prevent_initial_call=True
)
def actualizar_datos_termica(n_clicks, metrica, entidad, fecha_inicio, fecha_fin):
    """Callback para actualizar los datos de generación térmica"""
    if not n_clicks or not metrica:
        return html.Div()

    try:
        # Generar datos de ejemplo para demostración
        fechas = pd.date_range(start=fecha_inicio, end=fecha_fin, freq='D')
        valores = np.random.normal(1000, 200, len(fechas))  # Datos simulados
        data = pd.DataFrame({"Valor": valores}, index=fechas)
        
        if data is None or data.empty:
            return dbc.Alert("No se encontraron datos para la consulta realizada.", color="warning")

        # Crear gráfico
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data["Valor"],
            mode='lines+markers',
            name=metrica,
            line=dict(color=COLORS['energia_termica'], width=3),
            marker=dict(size=6, color=COLORS['energia_termica'])
        ))

        fig.update_layout(
            title=f"Análisis de {metrica}",
            xaxis_title="Fecha",
            yaxis_title="Valor (MW)",
            template="plotly_white",
            height=500,
            showlegend=True,
            hovermode='x unified'
        )

        # Crear tabla de datos
        tabla = dash_table.DataTable(
            data=data.reset_index().tail(10).to_dict('records'),
            columns=[{"name": col, "id": col} for col in data.reset_index().columns],
            style_cell={'textAlign': 'center'},
            style_header={'backgroundColor': COLORS['energia_termica'], 'color': 'white', 'fontWeight': 'bold'},
            page_size=10
        )

        return html.Div([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-chart-area me-2"),
                    html.H5(f"Gráfico: {metrica}", className="mb-0")
                ]),
                dbc.CardBody([
                    dcc.Graph(figure=fig)
                ])
            ], className="mb-4"),
            
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-table me-2"),
                    html.H5("Datos Recientes", className="mb-0")
                ]),
                dbc.CardBody([
                    tabla
                ])
            ])
        ])

    except Exception as e:
        return dbc.Alert(f"Error al procesar los datos: {str(e)}", color="danger")