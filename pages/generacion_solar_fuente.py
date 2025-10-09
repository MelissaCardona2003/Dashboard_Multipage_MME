from dash import dcc, html, Input, Output, State, dash_table, ALL, callback, register_page
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import datetime as dt
from datetime import date, timedelta
import warnings
import sys
import os
import time
import traceback
from flask import Flask, jsonify
import dash
import traceback

# Use the installed pydataxm package instead of local module
try:
    from pydataxm.pydataxm import ReadDB
    PYDATAXM_AVAILABLE = True
except ImportError:
    PYDATAXM_AVAILABLE = False
    print("⚠️ pydataxm no está disponible. Algunos datos pueden no cargarse correctamente.")

# Imports locales para componentes uniformes
from .components import crear_header, crear_navbar, crear_sidebar_universal, crear_boton_regresar
from .config import COLORS
from .utils_xm import fetch_gene_recurso_chunked

warnings.filterwarnings("ignore")

register_page(
    __name__,
    path="/generacion/solar/fuente",
    name="Fuente Solar",
    title="Tablero Fuente Solar - Ministerio de Minas y Energía de Colombia",
    order=9
)

# Inicializar API XM
objetoAPI = None
if PYDATAXM_AVAILABLE:
    try:
        objetoAPI = ReadDB()
        print("✅ API XM inicializada correctamente en fuente solar")
    except Exception as e:
        print(f"❌ Error al inicializar API XM en fuente solar: {e}")
        objetoAPI = None

def obtener_listado_recursos():
    """Obtener el listado de recursos para identificar plantas solares"""
    try:
        if objetoAPI is None:
            print("API no disponible - retornando DataFrame vacío")
            return pd.DataFrame()
        # Usar fechas históricas para mayor probabilidad de datos
        fecha_fin = date.today() - timedelta(days=14)
        fecha_inicio = fecha_fin - timedelta(days=7)
        recursos = objetoAPI.request_data("ListadoRecursos", "Sistema", fecha_inicio, fecha_fin)
        if recursos is not None and not recursos.empty:
            # Filtrar solo plantas solares (Values_Type)
            if 'Values_Type' in recursos.columns:
                plantas_solares = recursos[
                    recursos['Values_Type'].str.contains('SOLAR|FOTOVOLTAICA', na=False, case=False)
                ].copy()
                return plantas_solares
            else:
                print("No se encontró la columna 'Values_Type' en recursos")
        print("No se obtuvieron recursos solares")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error obteniendo listado de recursos solares: {e}")
    return pd.DataFrame()

def _detectar_columna_sic(recursos_df: pd.DataFrame, f_ini: date, f_fin: date):
    if recursos_df is None or recursos_df.empty or objetoAPI is None:
        return None
    candidatos = ['Values_SIC','Values_Sic','Values_ResourceSIC','Values_ResourceCode','Values_Code']
    cols_str = [c for c in recursos_df.columns if recursos_df[c].dtype == 'object']
    orden = [c for c in candidatos if c in recursos_df.columns] + [c for c in cols_str if c not in candidatos]
    def muestra(serie: pd.Series):
        vals = (serie.dropna().astype(str).str.strip().loc[lambda s: s.str.match(r'^[A-Z0-9]{3,6}$', na=False)].unique().tolist())
        return vals[:3]
    for col in orden:
        cods = muestra(recursos_df[col])
        if len(cods) < 2:
            continue
        try:
            prueba = objetoAPI.request_data("Gene", "Recurso", f_ini, f_fin, cods)
            if prueba is not None and not prueba.empty:
                if 'Values_code' in prueba.columns and prueba['Values_code'].astype(str).isin(cods).any():
                    print(f"Columna SIC detectada: {col}")
                    return col
                print(f"Columna SIC detectada (sin Values_code): {col}")
                return col
        except Exception as e:
            print(f"Candidata {col} falló: {e}")
            continue
    print("No fue posible detectar columna SIC")
    return None

def obtener_generacion_plantas(fecha_inicio, fecha_fin, plantas_df=None):
    """Obtener datos de generación por plantas solares (Gene por Recurso con SIC y lotes)"""
    try:
        if objetoAPI is None or plantas_df is None or plantas_df.empty:
            return pd.DataFrame(), pd.DataFrame()
        col_sic = _detectar_columna_sic(plantas_df, fecha_inicio, fecha_fin)
        if not col_sic:
            return pd.DataFrame(), pd.DataFrame()
        codigos = (plantas_df[col_sic].dropna().astype(str).str.strip().loc[lambda s: s.str.match(r'^[A-Z0-9]{3,6}$', na=False)].unique().tolist())
        if not codigos:
            return pd.DataFrame(), pd.DataFrame()
        df_generacion = fetch_gene_recurso_chunked(objetoAPI, fecha_inicio, fecha_fin, codigos, batch_size=50, chunk_days=30)
        if df_generacion is None or df_generacion.empty:
            return pd.DataFrame(), pd.DataFrame()
        plantas_min = plantas_df[[col_sic,'Values_Name']].drop_duplicates().rename(columns={col_sic:'Codigo','Values_Name':'Planta'})
        df_generacion = df_generacion.merge(plantas_min, on='Codigo', how='left')
        participacion_total = df_generacion.groupby('Planta', as_index=False)['Generacion_GWh'].sum()
        total = participacion_total['Generacion_GWh'].sum()
        participacion_total['Participacion_%'] = (participacion_total['Generacion_GWh']/total*100).round(2) if total>0 else 0.0
        participacion_total['Estado'] = participacion_total['Participacion_%'].apply(lambda x: 'Alto' if x>=25 else ('Medio' if x>=10 else 'Bajo'))
        return df_generacion, participacion_total
    except Exception as e:
        print(f"Error en obtener_generacion_plantas solares: {e}")
        traceback.print_exc()
        return pd.DataFrame(), pd.DataFrame()

def crear_grafica_temporal_negra(df_generacion, planta_seleccionada=None):
    """Gráfica con línea negra: serie nacional y opcionalmente una planta seleccionada (punteada)."""
    if df_generacion.empty:
        return go.Figure().add_annotation(text="No hay datos disponibles",
                                          xref="paper", yref="paper", x=0.5, y=0.5)

    nacional = (df_generacion.groupby('Fecha', as_index=False)['Generacion_GWh']
                .sum().sort_values('Fecha'))
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=nacional['Fecha'], y=nacional['Generacion_GWh'],
        mode='lines+markers', name='Nacional',
        line=dict(color='black', width=2), marker=dict(color='black', size=5),
        hovertemplate='Fecha: %{x}<br>Generación: %{y:.2f} GWh<extra></extra>'
    ))
    if planta_seleccionada:
        df_p = df_generacion[df_generacion['Planta'] == planta_seleccionada]
        df_p = df_p.groupby('Fecha', as_index=False)['Generacion_GWh'].sum().sort_values('Fecha')
        if not df_p.empty:
            fig.add_trace(go.Scatter(
                x=df_p['Fecha'], y=df_p['Generacion_GWh'],
                mode='lines+markers', name=planta_seleccionada,
                line=dict(color='black', width=2, dash='dot'), marker=dict(color='black', size=5),
                hovertemplate='Fecha: %{x}<br>Generación: %{y:.2f} GWh<extra></extra>'
            ))
    fig.update_layout(
        title='Evolución Temporal de Generación Solar',
        xaxis_title='Fecha', yaxis_title='Generación (GWh)',
        hovermode='x unified', showlegend=True, height=500, template='plotly_white'
    )
    return fig

def crear_tabla_participacion(df_participacion):
    """Crear tabla de participación con semáforo"""
    if df_participacion.empty:
        return html.Div("No hay datos de participación disponibles")
    
    # Umbrales adaptativos
    dfp = df_participacion.copy()
    if len(dfp) >= 3 and dfp['Participacion_%'].sum() > 0:
        p50 = float(dfp['Participacion_%'].quantile(0.50))
        p75 = float(dfp['Participacion_%'].quantile(0.75))
    else:
        p50, p75 = 5.0, 25.0
    def clas(v):
        return 'Alto' if v >= p75 else ('Medio' if v >= p50 else 'Bajo')
    dfp['Estado'] = dfp['Participacion_%'].apply(clas)
    dfp = dfp.sort_values('Participacion_%', ascending=False)

    # Agregar fila TOTAL
    total_gwh = dfp['Generacion_GWh'].sum()
    total_row = pd.DataFrame([
        {
            'Planta': 'TOTAL',
            'Generacion_GWh': total_gwh,
            'Participacion_%': 100.0,
            'Estado': 'Total'
        }
    ])
    df_tabla = pd.concat([dfp, total_row], ignore_index=True)

    # Preparar datos para la tabla
    tabla_data = []
    for _, row in df_tabla.iterrows():
        tabla_data.append({
            'Planta': row['Planta'],
            'Generacion_GWh': f"{row['Generacion_GWh']:.2f}",
            'Participacion_%': f"{row['Participacion_%']:.2f}%",
            'Estado': row['Estado']
        })
    
    leyenda = html.Div([
        html.Div(html.Strong("¿Cómo leer esta tabla?"), className="mb-1", style={"color": COLORS['text_secondary']}),
        html.Ul([
            html.Li("Participación (%): porcentaje de la generación total del período que aporta cada planta. Se calcula como (GWh de la planta / GWh total) × 100."),
            html.Li(
                f"Semáforo adaptativo: los umbrales se calculan con percentiles de las participaciones del período. Alto ≥ p75={p75:.2f}%, Medio ≥ p50={p50:.2f}% y < p75, Bajo < p50."
            ),
            html.Li("Interpretación cualitativa: Alto = principales aportantes del período (cuartil superior); Medio = aportantes típicos (entre la mediana y p75); Bajo = aporte relativo menor (por debajo de la mediana)."),
            html.Li("Fila TOTAL: resume el 100% del período y no se usa para calcular ni colorear el semáforo."),
            html.Li("Nota: Los percentiles se recalculan al cambiar fechas o filtros. Los colores no implican calidad técnica ni disponibilidad; reflejan posición relativa en el período seleccionado.")
        ], style={"marginBottom": 0, "color": COLORS['text_secondary'], "fontSize": "0.9rem"})
    ], className="mb-2")

    tabla = dash_table.DataTable(
        data=tabla_data,
        columns=[
            {"name": "Planta", "id": "Planta"},
            {"name": "Generación (GWh)", "id": "Generacion_GWh"},
            {"name": "Participación (%)", "id": "Participacion_%"},
            {"name": "Estado", "id": "Estado"}
        ],
        style_cell={
            'textAlign': 'left',
            'padding': '10px',
            'fontFamily': 'Arial',
            'fontSize': '14px'
        },
        style_header={
            'backgroundColor': COLORS['energia_solar'],
            'color': 'white',
            'fontWeight': 'bold'
        },
        style_data_conditional=[
            {
                'if': {'filter_query': '{Planta} = TOTAL'},
                'fontWeight': '700',
                'backgroundColor': '#f1f3f5'
            },
            {
                'if': {'filter_query': '{Estado} = Alto'},
                'backgroundColor': '#d4edda',
                'color': '#155724'
            },
            {
                'if': {'filter_query': '{Estado} = Medio'},
                'backgroundColor': '#fff3cd',
                'color': '#856404'
            },
            {
                'if': {'filter_query': '{Estado} = Bajo'},
                'backgroundColor': '#f8d7da',
                'color': '#721c24'
            }
        ],
        sort_action="native",
        page_action="native",
        page_current=0,
        page_size=15
    )
    return html.Div([leyenda, tabla])

# Layout principal
layout = html.Div([
    # Sidebar universal
    crear_sidebar_universal(),
    
    # Header
    crear_header(
        titulo_pagina="Fuente Solar",
        descripcion_pagina="Tablero de plantas solares con generación y participación del Sistema Interconectado Nacional",
        icono_pagina="fas fa-sun",
        color_tema=COLORS['energia_solar']
    ),
    
    # Container principal
    dbc.Container([
        # Botón de regreso
        crear_boton_regresar(),
        
        # Título de la página
        html.Div([
            html.H2([
                html.I(className="fas fa-sun me-3", 
                      style={"color": COLORS['energia_solar']}),
                "Tablero Fuente Solar"
            ], className="mb-3", style={"color": COLORS['text_primary']}),
            html.P("Análisis detallado de generación por plantas solares del sistema eléctrico colombiano", 
                  className="lead", style={"color": COLORS['text_secondary']})
        ], className="text-center mb-5"),
        
        # Controles de filtro
        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Rango de Fechas:", className="fw-bold"),
                        dcc.DatePickerRange(
                            id='date-range-solar',
                            start_date=date.today() - timedelta(days=7),
                            end_date=date.today(),
                            display_format='DD/MM/YYYY',
                            style={'width': '100%'}
                        )
                    ], md=4),
                    dbc.Col([
                        html.Label("Planta (opcional - una a la vez):", className="fw-bold"),
                        dcc.Dropdown(
                            id='planta-dropdown-solar',
                            placeholder="Selecciona una planta (opcional)",
                            multi=False
                        )
                    ], md=6),
                    dbc.Col([
                        html.Br(),
                        dbc.Button(
                            "Actualizar Datos",
                            id="btn-actualizar-solar",
                            color="primary",
                            className="w-100"
                        )
                    ], md=2)
                ])
            ])
        ], className="mb-4"),
        
        # Contenedor de resultados con loading
        dcc.Loading(
            id="loading-solar",
            type="circle",
            children=html.Div(id="contenido-solar")
        ),
        
    ], fluid=True, className="py-4")
    
], style={'backgroundColor': COLORS['bg_main'], 'minHeight': '100vh'})

# Callbacks
@callback(
    [Output('planta-dropdown-solar', 'options'),
     Output('contenido-solar', 'children')],
    [Input('btn-actualizar-solar', 'n_clicks'),
     Input('date-range-solar', 'start_date'),
     Input('date-range-solar', 'end_date')],
    [State('planta-dropdown-solar', 'value')]
)
def actualizar_tablero_solar(n_clicks, fecha_inicio, fecha_fin, plantas_seleccionadas):
    if not fecha_inicio or not fecha_fin:
        return [], dbc.Alert("Selecciona un rango de fechas válido", color="info")
    
    try:
        # Convertir fechas
        fecha_inicio_dt = dt.datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        fecha_fin_dt = dt.datetime.strptime(fecha_fin, "%Y-%m-%d").date()
        
        # Obtener listado de plantas solares
        plantas_df = obtener_listado_recursos()
        
        if plantas_df.empty:
            return [], dbc.Alert("No se pudieron obtener los datos de plantas solares", color="warning")
        
        # Opciones para el dropdown
        # Detectar columna SIC para usarla en el selector
        col_sic = _detectar_columna_sic(plantas_df, fecha_inicio_dt, fecha_fin_dt)
        opciones_plantas = []
        if col_sic:
            opciones_plantas = [
                {'label': f"{row['Values_Name']}", 'value': row[col_sic]}
                for _, row in plantas_df.iterrows() if pd.notna(row.get(col_sic))
            ]
        
        # Obtener datos de generación
        df_generacion, df_participacion = obtener_generacion_plantas(fecha_inicio_dt, fecha_fin_dt, plantas_df)
        
        if df_generacion.empty:
            return opciones_plantas, dbc.Alert("No se encontraron datos de generación para el período seleccionado", color="info")
        
        # Identificar planta seleccionada (una sola)
        planta_seleccionada = None
        if plantas_seleccionadas:
            cod_sel = plantas_seleccionadas
            if isinstance(cod_sel, list):
                cod_sel = cod_sel[0] if cod_sel else None
            if cod_sel is not None:
                nombre = df_generacion.loc[df_generacion['Codigo'] == cod_sel, 'Planta']
                planta_seleccionada = nombre.iloc[0] if not nombre.empty else None
        
        # Crear contenido
        contenido = [
            # Gráfica temporal
            dbc.Card([
                dbc.CardHeader([
                    html.H5([
                        html.I(className="fas fa-chart-line me-2"),
                        "Evolución Temporal de Generación Solar"
                    ], className="mb-0")
                ]),
                dbc.CardBody([
                    dcc.Graph(
                        figure=crear_grafica_temporal_negra(df_generacion, planta_seleccionada),
                        config={'displayModeBar': True}
                    )
                ])
            ], className="mb-4"),
            
            # Tabla de participación
            dbc.Card([
                dbc.CardHeader([
                    html.H5([
                        html.I(className="fas fa-table me-2"),
                        "Participación por Planta Solar"
                    ], className="mb-0")
                ]),
                dbc.CardBody([
                    crear_tabla_participacion(df_participacion)
                ])
            ])
        ]
        
        return opciones_plantas, contenido
        
    except Exception as e:
        print(f"Error en callback solar: {e}")
        traceback.print_exc()
        return [], dbc.Alert(f"Error al procesar los datos: {str(e)}", color="danger")