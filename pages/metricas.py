import dash
from dash import dcc, html, Input, Output, callback, dash_table, register_page
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import datetime as dt
from datetime import date, timedelta
import sys
import os
from io import BytesIO
import base64
import warnings
import zipfile

try:
    from pydataxm.pydataxm import ReadDB
    PYDATAXM_AVAILABLE = True
except ImportError:
    PYDATAXM_AVAILABLE = False
    print("⚠️ pydataxm no está disponible. Algunos datos pueden no cargarse correctamente.")

# Imports locales para componentes uniformes
from .components import crear_header, crear_navbar, crear_sidebar_universal, crear_boton_regresar
from .config import COLORS

warnings.filterwarnings("ignore")

# =============================================================================
# SISTEMA AUTOMÁTICO DE GENERACIÓN DE INFORMACIÓN DE MÉTRICAS
# =============================================================================

def generar_info_automatica_metrica(metric_id, metric_name, metric_description, metric_units):
    """
    Genera automáticamente información detallada de una métrica basada en:
    - MetricId: Código de la métrica
    - MetricName: Nombre descriptivo 
    - MetricDescription: Descripción técnica de XM
    - MetricUnits: Unidades de medida
    """
    
    # Mapas de patrones para categorización automática
    PATRONES_CATEGORIA = {
        'demanda': {
            'keywords': ['dema', 'demand', 'consumo', 'cons'],
            'descripcion_base': 'consumo eléctrico del sistema',
            'uso_mme': 'planificación energética, proyección de crecimiento de demanda, dimensionamiento de infraestructura, políticas de eficiencia energética',
            'valores_criticos': 'Monitorear picos >11,000 MW y crecimiento >4% anual'
        },
        'generacion': {
            'keywords': ['gene', 'gener', 'generation'],
            'descripcion_base': 'producción de energía eléctrica',
            'uso_mme': 'evaluación de confiabilidad del parque generador, planificación de nueva capacidad, monitoreo operativo, cálculo de márgenes de reserva',
            'valores_criticos': 'Mantener margen >200 MW sobre demanda máxima'
        },
        'precio': {
            'keywords': ['prec', 'price', 'costo', 'cost'],
            'descripcion_base': 'formación de precios del mercado eléctrico',
            'uso_mme': 'diseño de políticas tarifarias, evaluación de subsidios FSSRI, análisis de competitividad del mercado, señales de inversión',
            'valores_criticos': 'Precio escasez 446.26 $/kWh - Monitorear >300 $/kWh'
        },
        'reserva': {
            'keywords': ['rese', 'reser', 'almac', 'embal'],
            'descripcion_base': 'disponibilidad energética del sistema',
            'uso_mme': 'gestión de alertas energéticas, coordinación intersectorial agua-energía, planificación ante fenómenos climáticos, declaración de emergencias',
            'valores_criticos': '<30% activa alerta amarilla, <20% emergencia energética'
        },
        'transacciones': {
            'keywords': ['trans', 'expo', 'impo', 'intercam'],
            'descripcion_base': 'intercambios energéticos',
            'uso_mme': 'política de integración energética regional, aprovechamiento de complementariedad, generación de divisas, evaluación de nuevas interconexiones',
            'valores_criticos': 'Capacidad máxima 500 MW con Ecuador'
        },
        'transmision': {
            'keywords': ['transm', 'restric', 'restrict', 'congestion'],
            'descripcion_base': 'operación del sistema de transmisión',
            'uso_mme': 'planificación de expansión de transmisión, identificación de cuellos de botella, evaluación de proyectos de infraestructura, análisis de confiabilidad',
            'valores_criticos': 'Restricciones frecuentes indican necesidad de refuerzo'
        },
        'combustible': {
            'keywords': ['combu', 'fuel', 'gas', 'carbon'],
            'descripcion_base': 'consumo de combustibles para generación térmica',
            'uso_mme': 'política de combustibles, evaluación de seguridad energética, análisis de dependencia de importaciones, cálculo de emisiones GEI',
            'valores_criticos': 'Alto consumo indica operación térmica intensiva'
        },
        'perdidas': {
            'keywords': ['perd', 'loss', 'reconcil'],
            'descripcion_base': 'eficiencia del sistema eléctrico',
            'uso_mme': 'evaluación de eficiencia operativa, políticas anti-hurto, priorización de inversiones en reducción de pérdidas, benchmarking de operadores',
            'valores_criticos': 'Meta nacional <8% pérdidas totales'
        },
        'capacidad': {
            'keywords': ['capa', 'capacity', 'disp', 'available'],
            'descripcion_base': 'disponibilidad de capacidad de generación',
            'uso_mme': 'cálculo de margen de reserva, evaluación de confiabilidad, planificación de mantenimientos, licitaciones de cargo por confiabilidad',
            'valores_criticos': 'Margen mínimo 12% según regulación CREG'
        }
    }
    
    # Determinar categoría basada en palabras clave
    categoria_detectada = 'general'
    info_categoria = {
        'descripcion_base': 'variable del sistema eléctrico colombiano',
        'uso_mme': 'análisis del sector energético, toma de decisiones técnicas, supervisión del mercado eléctrico, planificación energética nacional',
        'valores_criticos': 'Evaluar según contexto operativo y histórico'
    }
    
    metric_lower = (metric_id + ' ' + metric_name + ' ' + metric_description).lower()
    
    for categoria, datos in PATRONES_CATEGORIA.items():
        if any(keyword in metric_lower for keyword in datos['keywords']):
            categoria_detectada = categoria
            info_categoria = datos
            break
    
    # Generar descripción práctica inteligente
    descripcion_completa = f"{metric_description} Esta métrica representa {info_categoria['descripcion_base']} y es fundamental para el monitoreo y operación del Sistema Interconectado Nacional (SIN)."
    
    # Generar nombre amigable si no existe
    nombre_amigable = metric_name if metric_name and metric_name.strip() else f"Métrica {metric_id}"
    
    # Unidades con fallback
    unidad_final = metric_units if metric_units and metric_units != 'N/A' else 'Ver especificación XM'
    
    return {
        'nombre': nombre_amigable,
        'descripcion_practica': descripcion_completa,
        'unidad': unidad_final,
        'uso_directo': f"El MME utiliza esta métrica para: {info_categoria['uso_mme']}",
        'valor_critico': info_categoria['valores_criticos'],
        'categoria': categoria_detectada,
        'descripcion_tecnica_xm': metric_description
    }

# Función expandida para obtener información detallada
def obtener_info_metrica_completa(metric_id):
    """Obtener información específica y práctica de una métrica"""
    
    # Primero buscar en el diccionario manual para métricas importantes
    METRICAS_IMPORTANTES = {
        'DemaEner': {
            'nombre': 'Demanda de Energía',
            'descripcion_practica': 'Consumo total de energía eléctrica del Sistema Interconectado Nacional (SIN) medido en MWh. Representa la energía que requieren todos los usuarios del país: residenciales, comerciales, industriales y oficiales. Es el indicador principal para evaluar el crecimiento del sector energético.',
            'unidad': 'MWh',
            'uso_directo': 'El MME utiliza esta métrica para: 1) Proyectar el crecimiento energético del país y planificar nueva capacidad de generación, 2) Dimensionar las redes de transmisión necesarias, 3) Establecer políticas de eficiencia energética, 4) Calcular subsidios y contribuciones del FSSRI',
            'valor_critico': 'Demanda máxima histórica Colombia: ~11,800 MWh/h. Picos >12,000 MWh/h requieren activación de reservas de emergencia.',
            'categoria': 'demanda'
        },
        'GeneReal': {
            'nombre': 'Generación Real',
            'descripcion_practica': 'Energía efectivamente producida por todas las plantas generadoras del SIN en tiempo real. Incluye plantas hidráulicas, térmicas, eólicas, solares y menores. Muestra la capacidad real del sistema vs. la capacidad instalada, considerando mantenimientos, fallas y restricciones operativas.',
            'unidad': 'MWh',
            'uso_directo': 'El MME la usa para: 1) Monitorear la confiabilidad del parque generador nacional, 2) Evaluar la necesidad de nuevas licitaciones de generación, 3) Detectar problemas operativos en tiempo real, 4) Coordinar con el ONS medidas de emergencia',
            'valor_critico': 'Margen mínimo 200-300 MW sobre demanda. Déficit vs demanda activa Plan de Emergencia del ONS.',
            'categoria': 'generacion'
        },
        'PrecBols': {
            'nombre': 'Precio de Bolsa Nacional',
            'descripcion_practica': 'Costo marginal del sistema eléctrico colombiano expresado en pesos por kWh. Se determina por el costo de la planta más costosa que debe operar para atender la demanda. Refleja la escasez o abundancia energética del país y es clave para las señales económicas del mercado.',
            'unidad': 'COP$/kWh',
            'uso_directo': 'El MME lo utiliza para: 1) Diseñar esquemas tarifarios y políticas de subsidios, 2) Evaluar la necesidad de declarar emergencias energéticas, 3) Establecer señales para nuevas inversiones en generación, 4) Monitorear la competitividad del mercado',
            'valor_critico': 'Precio de escasez: 446.26 $/kWh (2025). Valores >300 $/kWh indican tensión del sistema.',
            'categoria': 'precio'
        }
    }
    
    # Si es una métrica importante, usar información manual
    if metric_id in METRICAS_IMPORTANTES:
        return METRICAS_IMPORTANTES[metric_id]
    
    # Para otras métricas, generar automáticamente
    try:
        if not todas_las_metricas.empty:
            metric_info = todas_las_metricas[todas_las_metricas['MetricId'] == metric_id]
            if not metric_info.empty:
                first_record = metric_info.iloc[0]
                return generar_info_automatica_metrica(
                    metric_id=metric_id,
                    metric_name=first_record.get('MetricName', ''),
                    metric_description=first_record.get('MetricDescription', ''),
                    metric_units=first_record.get('MetricUnits', 'N/A')
                )
    except Exception:
        pass
    
    # Fallback para casos excepcionales
    return {
        'nombre': f'Métrica {metric_id}',
        'descripcion_practica': f'Variable del sistema eléctrico colombiano monitoreada por XM. Forma parte del conjunto de {len(todas_las_metricas)} métricas disponibles para análisis del sector energético.',
        'unidad': 'Ver especificación técnica XM',
        'uso_directo': 'Análisis técnico especializado del comportamiento del sistema eléctrico nacional para toma de decisiones del MME',
        'valor_critico': 'Los umbrales críticos deben definirse según análisis histórico y contexto operativo específico',
        'categoria': 'general'
    }

register_page(
    __name__,
    path="/metricas",
    name="Metricas",
    title="Dashboard Energético XM - Colombia",
    order=2
)
# Inicializar API XM
objetoAPI = None
todas_las_metricas = pd.DataFrame()

try:
    if PYDATAXM_AVAILABLE:
        objetoAPI = ReadDB()
        todas_las_metricas = objetoAPI.get_collections()
        print("API XM inicializada correctamente")
        print(f"Métricas disponibles: {len(todas_las_metricas)}")
    else:
        print("⚠️ pydataxm no está disponible - usando datos mock")
except Exception as e:
    print(f"Error al inicializar API XM: {e}")
    objetoAPI = None
    todas_las_metricas = pd.DataFrame()

# Función para obtener opciones únicas de MetricId y Entity
def get_metric_options():
    print(f"🔍 [DEBUG] get_metric_options() llamada - todas_las_metricas está vacío: {todas_las_metricas.empty}")
    print(f"🔍 [DEBUG] Forma de todas_las_metricas: {todas_las_metricas.shape}")
    print(f"🔍 [DEBUG] objetoAPI disponible: {objetoAPI is not None}")
    
    if todas_las_metricas.empty or objetoAPI is None:
        print("⚠️ [DEBUG] Retornando opciones vacías porque todas_las_metricas está vacío o objetoAPI es None")
        return [], []
    
    # Crear opciones de métricas y ordenarlas alfabéticamente por MetricName
    metric_options = [
        {"label": f"{row['MetricId']} - {row['MetricName']}", "value": row['MetricId']}
        for _, row in todas_las_metricas.iterrows()
    ]
    
    # Ordenar alfabéticamente por el label (que incluye MetricName)
    metric_options = sorted(metric_options, key=lambda x: x['label'])
    
    entity_options = [
        {"label": entity, "value": entity}
        for entity in todas_las_metricas['Entity'].unique()
        if pd.notna(entity)
    ]
    
    # También ordenar las entidades alfabéticamente
    entity_options = sorted(entity_options, key=lambda x: x['label'])
    
    print(f"📊 Opciones de métricas creadas para el dropdown: {len(metric_options)}")
    print(f"🏢 Opciones de entidades disponibles: {len(entity_options)}")
    
    return metric_options, entity_options

metric_options, entity_options = get_metric_options()
print(f"🔍 [DEBUG] Layout - metric_options: {len(metric_options)} opciones disponibles")
print(f"🔍 [DEBUG] Layout - entity_options: {len(entity_options)} opciones disponibles")

layout = html.Div([
    # Sidebar desplegable
    crear_sidebar_universal(),
    
    # Header uniforme
    # Header dinámico específico para métricas
    crear_header(
        titulo_pagina="Métricas Energéticas",
        descripcion_pagina="Consulta y análisis de variables del mercado eléctrico colombiano",
        icono_pagina="fas fa-chart-line",
        color_tema=COLORS['primary']
    ),
    # Barra de navegación eliminada
    
    # Container principal
    dbc.Container([
        # Botón de regreso
        crear_boton_regresar(),
        
        dbc.Row([
            # Contenido principal (ahora ocupa todo el ancho)
            dbc.Col([
                # Panel de controles en tabs
                dbc.Tabs([
                    dbc.Tab(label="📊 Consulta de Métricas", tab_id="tab-consulta"),
                    dbc.Tab(label="📈 Análisis Energético", tab_id="tab-analisis"),
                    dbc.Tab(label="🔍 Exploración Avanzada", tab_id="tab-exploracion"),
                    dbc.Tab(label="📚 Guía para Ingenieros", tab_id="tab-guia"),
                ], id="metricas-tabs", active_tab="tab-consulta", className="mb-4"),
                
                # Contenido dinámico
                html.Div(id="metricas-tab-content")
            ], width=12)  # Ahora ocupa todo el ancho
        ])
    ], fluid=True)
], style={'backgroundColor': COLORS['bg_main'], 'minHeight': '100vh'})

# Layout del panel de controles energéticos
def crear_panel_controles_metricas():
    # Mostrar alerta si la API XM no está disponible
    if objetoAPI is None or todas_las_metricas.empty:
        return dbc.Card([
            dbc.CardBody([
                html.Div([
                    html.I(className="fas fa-exclamation-triangle me-2", style={"color": "#DC2626"}),
                    html.Strong("Servicio XM No Disponible", style={"fontSize": "1.1rem", "color": "#DC2626"})
                ], className="mb-3 d-flex align-items-center"),
                
                dbc.Alert([
                    html.H6([
                        html.I(className="fas fa-plug me-2"),
                        "Conexión con XM Interrumpida"
                    ], className="alert-heading"),
                    html.P([
                        "No se pudo establecer conexión con los datos de XM. Esto puede deberse a:"
                    ], className="mb-2"),
                    html.Ul([
                        html.Li("Problemas de conectividad a internet"),
                        html.Li("La librería pydataxm no está instalada correctamente"),
                        html.Li("Los servidores de XM están temporalmente no disponibles")
                    ]),
                    html.Hr(),
                    html.P([
                        html.Strong("Solución: "),
                        "Verifica tu conexión a internet y recarga la página. ",
                        "Si el problema persiste, contacta al administrador del sistema."
                    ], className="mb-0")
                ], color="danger")
            ])
        ], className="shadow-sm")
    
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.I(className="fas fa-cogs me-2", style={"color": COLORS['primary']}),
                html.Strong("Panel de Consulta Energética", style={"fontSize": "1.1rem", "color": COLORS['text_primary']})
            ], className="mb-3 d-flex align-items-center"),
            
            dbc.Row([
                dbc.Col([
                    html.Label([
                        html.I(className="fas fa-chart-bar me-2"),
                        "Métrica Energética"
                    ], className="fw-bold mb-2 d-flex align-items-center"),
                    dcc.Dropdown(
                        id="metric-dropdown",
                        options=metric_options,
                        value=metric_options[0]["value"] if metric_options else None,
                        placeholder="Selecciona una métrica energética...",
                        className="form-control-modern mb-0",
                        style={"fontSize": "0.95rem"}
                    )
                ], lg=4, md=6, sm=12),
                
                dbc.Col([
                    html.Label([
                        html.I(className="fas fa-building me-2"),
                        "Entidad del Sistema"
                    ], className="fw-bold mb-2 d-flex align-items-center"),
                    dcc.Dropdown(
                        id="entity-dropdown",
                        options=entity_options,
                        placeholder="Selecciona una entidad...",
                        className="form-control-modern mb-0",
                        style={"fontSize": "0.95rem"}
                    )
                ], lg=4, md=6, sm=12),
                
                dbc.Col([
                    html.Label([
                        html.I(className="fas fa-calendar-range me-2"),
                        "Período de Análisis"
                    ], className="fw-bold mb-2 d-flex align-items-center"),
                    dcc.DatePickerRange(
                        id="date-picker-range",
                        start_date=date.today() - timedelta(days=7),  # Solo 7 días para consulta más rápida
                        end_date=date.today(),
                        display_format="DD/MM/YYYY",
                        className="form-control-modern",
                        style={"width": "100%"}
                    )
                ], lg=4, md=12, sm=12)
            ], className="g-3 align-items-end mb-3"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Button([
                        html.I(className="fas fa-search me-2"),
                        "Consultar Datos Energéticos"
                    ],
                    id="query-button",
                    color="primary",
                    className="w-100 btn-modern",
                    style={"background": f"linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['accent']} 100%)", "border": "none"}
                    )
                ], lg=6, md=12),
                dbc.Col([
                    dbc.DropdownMenu([
                        dbc.DropdownMenuItem([
                            html.I(className="fas fa-file-excel me-2", style={'color': '#107C41'}),
                            "Descargar Excel (.xlsx)"
                        ], id="download-excel-btn"),
                        dbc.DropdownMenuItem([
                            html.I(className="fas fa-file-csv me-2", style={'color': '#FF6B35'}),
                            "Descargar CSV (.csv)"
                        ], id="download-csv-btn"),
                        dbc.DropdownMenuItem([
                            html.I(className="fas fa-file-pdf me-2", style={'color': '#DC3545'}),
                            "Descargar PDF (.pdf)"
                        ], id="download-pdf-btn"),
                        dbc.DropdownMenuItem(divider=True),
                        dbc.DropdownMenuItem([
                            html.I(className="fas fa-download me-2", style={'color': COLORS['primary']}),
                            "Descargar Todo (.zip)"
                        ], id="download-all-btn"),
                    ],
                    label=[
                        html.I(className="fas fa-download me-2"),
                        "Descargar Reporte"
                    ],
                    id="download-dropdown",
                    color="secondary",
                    className="w-100",
                    style={'width': '100%'}
                    ),
                    # Componentes de descarga
                    dcc.Download(id="download-metricas-excel"),
                    dcc.Download(id="download-metricas-csv"),
                    dcc.Download(id="download-metricas-pdf"),
                    dcc.Download(id="download-metricas-zip")
                ], lg=6, md=12)
            ], className="g-3")
        ], className="p-4")
    ], className="shadow-sm")

# Aquí NO se incluye metricas-results-content porque debe estar dentro del tab

# Callback para manejar tabs
@callback(
    Output("metricas-tab-content", "children"),
    Input("metricas-tabs", "active_tab")
)
def render_metricas_tab_content(active_tab):
    if active_tab == "tab-consulta":
        return html.Div([
            crear_panel_controles_metricas(),
            html.Div(id="metricas-results-content", className="mt-4")
        ])
    elif active_tab == "tab-analisis":
        return html.Div([
            dbc.Card([
                dbc.CardBody([
                    html.H4([
                        html.I(className="fas fa-chart-line me-2", style={"color": COLORS['primary']}),
                        "Análisis Energético del Sistema"
                    ], className="mb-4"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("⚡ Generación vs Demanda", className="mb-3"),
                                    html.P("Análisis comparativo entre generación eléctrica y demanda nacional.", className="text-muted")
                                ])
                            ], className="h-100")
                        ], md=6),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("🔋 Mix Energético", className="mb-3"),
                                    html.P("Composición de fuentes de energía en el sistema eléctrico colombiano.", className="text-muted")
                                ])
                            ], className="h-100")
                        ], md=6)
                    ])
                ])
            ], className="shadow-sm"),
            html.Div(id="metricas-results-content-analisis", className="mt-4")
        ])
    elif active_tab == "tab-exploracion":
        return html.Div([
            dbc.Card([
                dbc.CardBody([
                    html.H4([
                        html.I(className="fas fa-search-plus me-2", style={"color": COLORS['primary']}),
                        "Exploración Avanzada de Datos"
                    ], className="mb-4"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("🔍 Análisis Multivariable", className="mb-3"),
                                    html.P("Exploración de correlaciones entre múltiples métricas energéticas.", className="text-muted")
                                ])
                            ], className="h-100")
                        ], md=6),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("📊 Métricas Personalizadas", className="mb-3"),
                                    html.P("Creación de indicadores energéticos específicos para análisis.", className="text-muted")
                                ])
                            ], className="h-100")
                        ], md=6)
                    ])
                ])
            ], className="shadow-sm"),
            html.Div(id="metricas-results-content-exploracion", className="mt-4")
        ])
    elif active_tab == "tab-guia":
        return crear_guia_ingenieros()
    
    return html.Div()

def crear_guia_ingenieros():
    """Crear guía detallada para ingenieros del MME"""
    return html.Div([
        # Header de la guía
        dbc.Card([
            dbc.CardBody([
                html.H3([
                    html.I(className="fas fa-user-tie me-3", style={"color": COLORS['primary']}),
                    "Guía de Métricas para Ingenieros del MME"
                ], className="mb-3", style={'color': COLORS['text_primary'], 'fontWeight': '600'}),
                
                dbc.Alert([
                    html.I(className="fas fa-info-circle me-2", style={'color': COLORS['info']}),
                    html.Strong("Objetivo: "),
                    "Esta guía ayuda a identificar las métricas XM más adecuadas para generar tableros específicos según las necesidades del Ministerio de Minas y Energía."
                ], color="light", className="mb-3", style={'border': f'1px solid {COLORS["border"]}'})
            ])
        ], className="mb-4", style={'border': f'1px solid {COLORS["border"]}', 'boxShadow': f'0 2px 4px {COLORS["shadow_md"]}'}),
        
        # Métricas críticas
        dbc.Card([
            dbc.CardHeader([
                html.H5([
                    html.I(className="fas fa-star me-2", style={'color': '#FFD700'}),
                    "Métricas Críticas para Tableros MME"
                ], className="mb-0", style={'color': COLORS['text_primary'], 'fontWeight': '600'})
            ], style={'backgroundColor': '#FFFDF0', 'border': 'none'}),
            dbc.CardBody([
                dbc.Row([
                    crear_card_metrica_detallada("DemaEner", METRICAS_DETALLADAS["DemaEner"]),
                    crear_card_metrica_detallada("GeneReal", METRICAS_DETALLADAS["GeneReal"]),
                ], className="mb-3"),
                dbc.Row([
                    crear_card_metrica_detallada("PrecBols", METRICAS_DETALLADAS["PrecBols"]),
                    crear_card_metrica_detallada("ReseAmb", METRICAS_DETALLADAS["ReseAmb"]),
                ])
            ])
        ], className="mb-4", style={'border': f'1px solid #FEF3C7'}),
        
        # Categorización de métricas
        dbc.Card([
            dbc.CardHeader([
                html.H5([
                    html.I(className="fas fa-layer-group me-2", style={'color': COLORS['primary']}),
                    "Clasificación por Categorías"
                ], className="mb-0", style={'color': COLORS['text_primary'], 'fontWeight': '600'})
            ], style={'backgroundColor': '#F0F9FF', 'border': 'none'}),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.H6([
                            html.I(className="fas fa-bolt me-2", style={'color': COLORS['warning']}),
                            "Demanda y Consumo"
                        ], style={'color': COLORS['text_primary']}),
                        html.Ul([
                            html.Li("DemaEner - Demanda Nacional"),
                            html.Li("DemaComeSISTEMA - Demanda Comercial"),
                            html.Li("ConsEner - Consumo Total")
                        ], style={'fontSize': '0.9em', 'color': COLORS['text_secondary']})
                    ], md=6),
                    dbc.Col([
                        html.H6([
                            html.I(className="fas fa-industry me-2", style={'color': COLORS['success']}),
                            "Generación"
                        ], style={'color': COLORS['text_primary']}),
                        html.Ul([
                            html.Li("GeneReal - Generación Real"),
                            html.Li("GeneIdea - Generación Ideal"),
                            html.Li("CapaEfec - Capacidad Efectiva")
                        ], style={'fontSize': '0.9em', 'color': COLORS['text_secondary']})
                    ], md=6)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        html.H6([
                            html.I(className="fas fa-dollar-sign me-2", style={'color': COLORS['info']}),
                            "Económicas"
                        ], style={'color': COLORS['text_primary']}),
                        html.Ul([
                            html.Li("PrecBols - Precio Bolsa"),
                            html.Li("CostoMarginal - Costo Marginal"),
                            html.Li("ValorTransacciones - Transacciones")
                        ], style={'fontSize': '0.9em', 'color': COLORS['text_secondary']})
                    ], md=6),
                    dbc.Col([
                        html.H6([
                            html.I(className="fas fa-tint me-2", style={'color': '#0EA5E9'}),
                            "Hidrológicas"
                        ], style={'color': COLORS['text_primary']}),
                        html.Ul([
                            html.Li("ReseAmb - Reserva Ambiental"),
                            html.Li("VolUte - Volumen Útil"),
                            html.Li("AporEner - Aportes Energéticos")
                        ], style={'fontSize': '0.9em', 'color': COLORS['text_secondary']})
                    ], md=6)
                ])
            ])
        ], className="mb-4", style={'border': f'1px solid #DBEAFE'}),
        
        # Recomendaciones para tableros
        dbc.Card([
            dbc.CardHeader([
                html.H5([
                    html.I(className="fas fa-lightbulb me-2", style={'color': '#F59E0B'}),
                    "Recomendaciones para Tableros Específicos"
                ], className="mb-0", style={'color': COLORS['text_primary'], 'fontWeight': '600'})
            ], style={'backgroundColor': '#FFFBEB', 'border': 'none'}),
            dbc.CardBody([
                dbc.Accordion([
                    dbc.AccordionItem([
                        html.P("🎯 Métricas recomendadas: DemaEner, ConsEner, PrecBols", className="mb-2"),
                        html.P("📊 Frecuencia: Datos horarios para análisis detallado", className="mb-2"),
                        html.P("💡 Casos de uso: Proyecciones de demanda, análisis de picos de consumo, correlación precio-demanda", className="mb-0")
                    ], title="📈 Tablero de Demanda Energética Nacional"),
                    
                    dbc.AccordionItem([
                        html.P("🎯 Métricas recomendadas: GeneReal, CapaEfec, ReseAmb", className="mb-2"),
                        html.P("📊 Frecuencia: Datos diarios y horarios", className="mb-2"),
                        html.P("💡 Casos de uso: Monitoreo de disponibilidad, planificación operativa, gestión de embalses", className="mb-0")
                    ], title="⚡ Tablero de Generación y Capacidad"),
                    
                    dbc.AccordionItem([
                        html.P("🎯 Métricas recomendadas: PrecBols, CostoMarginal, ValorTransacciones", className="mb-2"),
                        html.P("📊 Frecuencia: Datos horarios para volatilidad", className="mb-2"),
                        html.P("💡 Casos de uso: Análisis de mercado, seguimiento financiero, alertas de precios", className="mb-0")
                    ], title="💰 Tablero Económico del Sector"),
                    
                    dbc.AccordionItem([
                        html.P("🎯 Métricas recomendadas: ReseAmb, AporEner, VolUte", className="mb-2"),
                        html.P("📊 Frecuencia: Datos diarios y semanales", className="mb-2"),
                        html.P("💡 Casos de uso: Gestión de sequías, planificación hídrica, alertas hidrológicas", className="mb-0")
                    ], title="🌊 Tablero Hidrológico Nacional")
                ])
            ])
        ], className="mb-4", style={'border': f'1px solid #FED7AA'})
    ])

def crear_card_metrica_detallada(metric_id, info):
    """Crear card detallada para una métrica específica"""
    return dbc.Col([
        dbc.Card([
            dbc.CardBody([
                html.H6([
                    html.I(className="fas fa-chart-bar me-2", style={'color': COLORS['primary']}),
                    f"{metric_id} - {info['nombre']}"
                ], className="mb-2", style={'color': COLORS['text_primary'], 'fontWeight': '600'}),
                
                html.P(info['descripcion'], className="mb-2", style={'color': COLORS['text_secondary'], 'fontSize': '0.9em'}),
                
                dbc.Row([
                    dbc.Col([
                        html.Small([
                            html.Strong("Unidad: ", style={'color': COLORS['text_primary']}),
                            info['unidad']
                        ], style={'color': COLORS['text_secondary']})
                    ], width=6),
                    dbc.Col([
                        html.Small([
                            html.Strong("Frecuencia: ", style={'color': COLORS['text_primary']}),
                            info['frecuencia']
                        ], style={'color': COLORS['text_secondary']})
                    ], width=6)
                ], className="mb-2"),
                
                html.Small([
                    html.Strong("Criticidad: "),
                    dbc.Badge(info['criticidad'], 
                             color="danger" if info['criticidad'] == "Alta" else "warning" if info['criticidad'] == "Media" else "secondary",
                             className="me-2")
                ], className="mb-2", style={'display': 'block'}),
                
                html.P([
                    html.Strong("💼 Aplicaciones: ", style={'color': COLORS['primary'], 'fontSize': '0.9em'}),
                    html.Br(),
                    ", ".join(info['aplicaciones'])
                ], className="mb-0", style={'color': COLORS['text_secondary'], 'fontSize': '0.8em'})
            ])
        ], style={'height': '100%', 'border': f'1px solid {COLORS["border"]}', 'boxShadow': f'0 1px 3px {COLORS["shadow_sm"]}'})
    ], md=6, className="mb-3")

# Callbacks originales para funcionalidad (actualizando IDs)

# Callback para actualizar las opciones de entidad según la métrica seleccionada
@callback(
    [Output("entity-dropdown", "options"),
     Output("entity-dropdown", "value")],
    [Input("metric-dropdown", "value")]
)
def update_entity_options(selected_metric):
    if not selected_metric or todas_las_metricas.empty or objetoAPI is None:
        return [], None
    
    # Filtrar las entidades disponibles para la métrica seleccionada
    metric_data = todas_las_metricas[todas_las_metricas['MetricId'] == selected_metric]
    
    if metric_data.empty:
        return [], None
    
    # Obtener las entidades únicas para esta métrica
    available_entities = metric_data['Entity'].dropna().unique()
    
    entity_options = [
        {"label": entity, "value": entity}
        for entity in available_entities
    ]
    
    # Ordenar las entidades alfabéticamente
    entity_options = sorted(entity_options, key=lambda x: x['label'])
    
    # Seleccionar automáticamente la primera entidad disponible (después del ordenamiento)
    default_value = entity_options[0]["value"] if len(entity_options) > 0 else None
    
    return entity_options, default_value

# Callback para mostrar información de la métrica seleccionada (actualizado para nuevo layout)
@callback(
    Output("metricas-results-content", "children"),
    [Input("query-button", "n_clicks")],
    [dash.dependencies.State("metric-dropdown", "value"),
     dash.dependencies.State("entity-dropdown", "value"),
     dash.dependencies.State("date-picker-range", "start_date"),
     dash.dependencies.State("date-picker-range", "end_date")]
)
def display_metric_results(n_clicks, selected_metric, selected_entity, start_date, end_date):
    print(f"🔍 [DEBUG] Callback ejecutado - n_clicks: {n_clicks}, metric: {selected_metric}, entity: {selected_entity}, dates: {start_date} to {end_date}")
    print(f"🔍 [DEBUG] objetoAPI disponible: {objetoAPI is not None}, métricas cargadas: {len(todas_las_metricas)}")
    
    if not n_clicks or not selected_metric:
        print("⚠️ [DEBUG] Callback terminado - falta métrica o no hay clicks")
        return dbc.Alert("👆 Selecciona una métrica y haz clic en 'Consultar Datos Energéticos'", color="info", className="text-center")
    
    if todas_las_metricas.empty or objetoAPI is None:
        return dbc.Alert([
            html.I(className="fas fa-exclamation-triangle me-2"),
            html.Strong("Servicio XM no disponible: "),
            "No se pudieron cargar las métricas de XM. Verifica la conexión a internet y que la librería pydataxm esté correctamente instalada."
        ], color="warning")
    
    metric_data = todas_las_metricas[todas_las_metricas['MetricId'] == selected_metric]
    
    if metric_data.empty:
        return dbc.Alert("Métrica no encontrada.", color="warning")
    
    # Información básica de la métrica
    metric_name = metric_data.iloc[0]['MetricName']
    available_entities = metric_data['Entity'].dropna().unique()
    metric_type = metric_data.iloc[0].get('Type', 'N/A')
    max_days = metric_data.iloc[0].get('MaxDays', 'N/A')
    units = metric_data.iloc[0].get('MetricUnits', 'N/A')
    description = metric_data.iloc[0].get('MetricDescription', 'Sin descripción disponible')
    
    # Obtener información detallada y educativa completa
    info_detallada = obtener_info_metrica_completa(selected_metric)
    
    # Card simplificado con información específica y práctica
    info_card = dbc.Card([
        dbc.CardHeader([
            html.H5([
                html.I(className="fas fa-chart-line me-2", style={'color': COLORS['primary']}),
                f"{selected_metric} - {info_detallada['nombre']}"
            ], className="mb-0", style={'color': COLORS['text_primary'], 'fontWeight': '600'})
        ], style={'backgroundColor': '#F0F9FF', 'border': 'none'}),
        dbc.CardBody([
            # Información práctica esencial
            dbc.Row([
                dbc.Col([
                    html.H6("¿Qué es y para qué sirve?", style={'color': COLORS['text_primary'], 'fontWeight': '600'}),
                    html.P(info_detallada['descripcion_practica'], 
                          style={'color': COLORS['text_secondary'], 'fontSize': '1rem', 'lineHeight': '1.5'})
                ], md=12)
            ], className="mb-3"),
            
            dbc.Row([
                dbc.Col([
                    html.H6("Uso directo en el MME:", style={'color': COLORS['text_primary'], 'fontWeight': '600'}),
                    html.P(info_detallada['uso_directo'], 
                          style={'color': COLORS['text_secondary'], 'fontSize': '0.95rem'})
                ], md=8),
                dbc.Col([
                    html.H6("Unidad:", style={'color': COLORS['text_primary'], 'fontWeight': '600'}),
                    html.P(f"{info_detallada['unidad']} ({units})" if units != 'N/A' and units != info_detallada['unidad'] else info_detallada['unidad'], 
                          style={'color': COLORS['text_secondary'], 'fontSize': '0.95rem', 'fontWeight': '500'})
                ], md=4)
            ], className="mb-3"),
            
            dbc.Alert([
                html.I(className="fas fa-exclamation-triangle me-2", style={'color': '#DC2626'}),
                html.Strong("Valores críticos: "),
                info_detallada['valor_critico']
            ], color="warning", className="mb-3"),
            
            # Información técnica XM y entidades disponibles
            html.Hr(),
            dbc.Row([
                dbc.Col([
                    html.H6("Descripción técnica XM:", style={'color': COLORS['text_primary'], 'fontSize': '0.9rem'}),
                    html.P(
                        info_detallada.get('descripcion_tecnica_xm', description), 
                        style={'color': COLORS['text_secondary'], 'fontSize': '0.85rem', 'fontStyle': 'italic'}
                    )
                ], md=8),
                dbc.Col([
                    html.H6(f"Entidades disponibles: {len(available_entities)}", 
                           style={'color': COLORS['text_primary'], 'fontSize': '0.9rem'}),
                    html.P(", ".join(available_entities[:5]) + ("..." if len(available_entities) > 5 else ""), 
                          style={'color': COLORS['text_secondary'], 'fontSize': '0.8rem'})
                ], md=4)
            ]),
            
            # Información adicional de categorización automática
            html.Hr(),
            dbc.Row([
                dbc.Col([
                    dbc.Badge(
                        f"📂 Categoría: {info_detallada.get('categoria', 'general').title()}", 
                        color="info", 
                        className="me-2"
                    ),
                    dbc.Badge(
                        f"🔧 Tipo: {metric_type}", 
                        color="secondary", 
                        className="me-2"
                    ),
                    dbc.Badge(
                        f"📅 Días máximos: {max_days}", 
                        color="light", 
                        text_color="dark"
                    )
                ], md=12)
            ])
        ])
    ], className="mb-4", style={'border': f'1px solid #DBEAFE', 'boxShadow': f'0 2px 4px {COLORS["shadow_md"]}'})
    
    
    # Si hay entidad y fechas seleccionadas, intentar consultar datos
    if selected_entity and start_date and end_date:
        try:
            # Verificar que la API esté disponible
            if objetoAPI is None:
                api_error_alert = dbc.Alert([
                    html.I(className="fas fa-exclamation-circle me-2"),
                    html.Strong("API XM no disponible: "),
                    "No se pudo inicializar la conexión con los datos de XM. ",
                    "Verifica que la librería pydataxm esté instalada y que haya conectividad a internet."
                ], color="danger", className="mt-3")
                return html.Div([info_card, api_error_alert])
            
            # Convertir fechas
            start_dt = dt.datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = dt.datetime.strptime(end_date, "%Y-%m-%d").date()
            
            # Realizar consulta a la API
            print(f"🔍 [DEBUG] Iniciando consulta API XM")
            print(f"🔍 [DEBUG] Parámetros: metric={selected_metric}, entity={selected_entity}, start={start_dt}, end={end_dt}")
            print(f"🔍 [DEBUG] Objeto API: {type(objetoAPI)}")
            
            data = objetoAPI.request_data(selected_metric, selected_entity, start_dt, end_dt)
            print(f"🔍 [DEBUG] Respuesta API: type={type(data)}, empty={data is None or (hasattr(data, 'empty') and data.empty)}")
            
            if data is not None and not data.empty:
                print(f"✅ Datos obtenidos: {len(data)} registros")
                
                # Crear explicación de las columnas de la tabla
                columnas_info = dbc.Card([
                    dbc.CardHeader([
                        html.H6([
                            html.I(className="fas fa-info-circle me-2"),
                            "Explicación de la Tabla de Datos"
                        ], className="mb-0")
                    ]),
                    dbc.CardBody([
                        html.P([
                            html.Strong("Estructura de la tabla:"), 
                            " Cada fila representa un registro temporal de la métrica seleccionada."
                        ], className="mb-2"),
                        html.Ul([
                            html.Li([
                                html.Strong("Date: "), 
                                "Fecha y hora del registro en formato YYYY-MM-DD HH:MM:SS (UTC-5 Colombia)"
                            ]),
                            html.Li([
                                html.Strong("Values: "), 
                                f"Valor numérico de la métrica en {units if units != 'N/A' else 'unidades correspondientes'}"
                            ]),
                            html.Li([
                                html.Strong("Entity: "), 
                                f"Entidad o agente del mercado al que corresponde el dato ({selected_entity})"
                            ]),
                            html.Li([
                                html.Strong("MetricId: "), 
                                f"Código único de la métrica en el sistema XM ({selected_metric})"
                            ])
                        ], style={'fontSize': '0.9rem'}),
                        html.Hr(),
                        html.P([
                            html.Strong("Interpretación:"), 
                            f" Los valores mostrados representan {info_detallada['descripcion_practica'][:100]}... ",
                            html.Br(),
                            html.Strong("Frecuencia de datos:"), 
                            " La mayoría de métricas se reportan con frecuencia horaria o diaria según la naturaleza del dato."
                        ], style={'fontSize': '0.85rem', 'color': '#6B7280'})
                    ])
                ], className="mb-3")
                
                # Crear tabla de datos
                data_table = dbc.Card([
                    dbc.CardHeader([
                        html.H6([
                            html.I(className="fas fa-table me-2"),
                            f"Datos Consultados ({len(data)} registros)"
                        ], className="mb-0")
                    ]),
                    dbc.CardBody([
                        dash_table.DataTable(
                            data=data.head(100).to_dict('records'),  # Limitar para rendimiento
                            columns=[{"name": i, "id": i} for i in data.columns],
                            style_cell={
                                'textAlign': 'left',
                                'padding': '10px',
                                'fontFamily': 'Inter, Arial',
                                'fontSize': '12px',
                                'border': '1px solid #e5e7eb',
                                'color': '#1f2937'
                            },
                            style_header={
                                'backgroundColor': '#1e40af',
                                'color': 'white',
                                'fontWeight': 'bold',
                                'border': '1px solid #d3d3d3'
                            },
                            style_data={
                                'backgroundColor': 'rgba(248, 248, 248, 0.8)',
                                'color': '#1f2937',
                                'border': '1px solid #e5e7eb'
                            },
                            sort_action="native",
                            filter_action="native",
                            page_action="native",
                            page_current=0,
                            page_size=10,
                            export_format="xlsx",
                            export_headers="display"
                        )
                    ])
                ])
                
                return html.Div([info_card, columnas_info, data_table])
            else:
                print("⚠️ [DEBUG] No se encontraron datos en la consulta")
                print(f"⚠️ [DEBUG] Data returned: {data}")
                if hasattr(data, 'shape'):
                    print(f"⚠️ [DEBUG] Data shape: {data.shape}")
                no_data_alert = dbc.Alert(
                    "No se encontraron datos para los parámetros seleccionados. Intenta con un rango de fechas más amplio o una métrica diferente.",
                    color="warning",
                    className="mt-3"
                )
                return html.Div([info_card, no_data_alert])
                
        except Exception as e:
            print(f"❌ [DEBUG] Error en la consulta: {str(e)}")
            print(f"❌ [DEBUG] Error type: {type(e)}")
            import traceback
            print(f"❌ [DEBUG] Traceback: {traceback.format_exc()}")
            error_alert = dbc.Alert(
                f"Error al consultar los datos: {str(e)}",
                color="danger",
                className="mt-3"
            )
            return html.Div([info_card, error_alert])
    
    return info_card

# =============================================================================
# CALLBACKS PARA DESCARGAS DE REPORTES
# =============================================================================

# Función auxiliar para generar datos de muestra o usar datos reales
def obtener_datos_reporte():
    """Obtener datos para el reporte"""
    try:
        # Intentar obtener datos reales de la API
        objectxm = ReadDB()
        metricas_list = objectxm.request_data_available()
        
        # Crear DataFrame con información de métricas
        df_metricas = pd.DataFrame({
            'Métrica': metricas_list[:50],  # Primeras 50 métricas
            'Tipo': ['Energética'] * min(50, len(metricas_list)),
            'Estado': ['Disponible'] * min(50, len(metricas_list)),
            'Última_Actualización': [dt.datetime.now().strftime('%Y-%m-%d')] * min(50, len(metricas_list))
        })
        
        return df_metricas
    except:
        # Datos de ejemplo si la API no está disponible
        return pd.DataFrame({
            'Métrica': ['DemaEner', 'GeneReal', 'PrecBols', 'ReseAmb', 'CapaEfec'],
            'Descripción': ['Demanda Energía', 'Generación Real', 'Precio Bolsa', 'Reserva Ambiental', 'Capacidad Efectiva'],
            'Tipo': ['Demanda', 'Generación', 'Precio', 'Reserva', 'Capacidad'],
            'Estado': ['Disponible'] * 5,
            'Última_Actualización': [dt.datetime.now().strftime('%Y-%m-%d')] * 5
        })

# Callback para descarga Excel
@callback(
    Output("download-metricas-excel", "data"),
    Input("download-excel-btn", "n_clicks"),
    prevent_initial_call=True
)
def download_excel_report(n_clicks):
    if n_clicks:
        df = obtener_datos_reporte()
        
        # Crear buffer para Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Métricas_Disponibles', index=False)
            
            # Agregar hoja de resumen
            resumen_df = pd.DataFrame({
                'Estadística': ['Total Métricas', 'Métricas Disponibles', 'Fecha Reporte'],
                'Valor': [len(df), len(df[df['Estado'] == 'Disponible']), dt.datetime.now().strftime('%Y-%m-%d %H:%M')]
            })
            resumen_df.to_excel(writer, sheet_name='Resumen', index=False)
        
        excel_data = output.getvalue()
        
        return dcc.send_bytes(
            excel_data,
            filename=f"reporte_metricas_energeticas_{dt.datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        )
    return dash.no_update

# Callback para descarga CSV
@callback(
    Output("download-metricas-csv", "data"),
    Input("download-csv-btn", "n_clicks"),
    prevent_initial_call=True
)
def download_csv_report(n_clicks):
    if n_clicks:
        df = obtener_datos_reporte()
        
        return dcc.send_data_frame(
            df.to_csv,
            filename=f"reporte_metricas_energeticas_{dt.datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            index=False
        )
    return dash.no_update

# Callback para descarga PDF (simulado como texto)
@callback(
    Output("download-metricas-pdf", "data"),
    Input("download-pdf-btn", "n_clicks"),
    prevent_initial_call=True
)
def download_pdf_report(n_clicks):
    if n_clicks:
        df = obtener_datos_reporte()
        
        # Crear contenido del reporte en texto
        reporte_texto = f"""
REPORTE DE MÉTRICAS ENERGÉTICAS XM
==========================================

Fecha de Generación: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Total de Métricas: {len(df)}

MÉTRICAS DISPONIBLES:
"""
        
        for idx, row in df.iterrows():
            reporte_texto += f"\n{idx+1}. {row.get('Métrica', 'N/A')} - {row.get('Tipo', 'N/A')} - {row.get('Estado', 'N/A')}"
        
        reporte_texto += f"""

RESUMEN ESTADÍSTICO:
- Métricas Disponibles: {len(df[df['Estado'] == 'Disponible']) if 'Estado' in df.columns else len(df)}
- Última Actualización: {dt.datetime.now().strftime('%Y-%m-%d')}

---
Generado por Dashboard MME - Sistema de Métricas Energéticas
"""
        
        return dict(
            content=reporte_texto,
            filename=f"reporte_metricas_energeticas_{dt.datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        )
    return dash.no_update

# Callback para descarga completa (ZIP)
@callback(
    Output("download-metricas-zip", "data"),
    Input("download-all-btn", "n_clicks"),
    prevent_initial_call=True
)
def download_complete_report(n_clicks):
    if n_clicks:
        import zipfile
        
        df = obtener_datos_reporte()
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Agregar CSV
            csv_data = df.to_csv(index=False)
            zip_file.writestr("metricas_energeticas.csv", csv_data)
            
            # Agregar Excel
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Métricas', index=False)
            zip_file.writestr("metricas_energeticas.xlsx", excel_buffer.getvalue())
            
            # Agregar reporte de texto
            reporte_texto = f"""
REPORTE COMPLETO DE MÉTRICAS ENERGÉTICAS XM
==========================================

Fecha de Generación: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Total de Métricas Analizadas: {len(df)}

Este paquete contiene:
1. metricas_energeticas.csv - Datos en formato CSV
2. metricas_energeticas.xlsx - Datos en formato Excel
3. reporte_completo.txt - Este reporte descriptivo

ANÁLISIS DETALLADO:
{df.to_string(index=False)}

---
Dashboard MME - Ministerio de Minas y Energía
Sistema de Análisis de Métricas Energéticas
"""
            zip_file.writestr("reporte_completo.txt", reporte_texto)
        
        zip_data = zip_buffer.getvalue()
        
        return dcc.send_bytes(
            zip_data,
            filename=f"reporte_completo_metricas_{dt.datetime.now().strftime('%Y%m%d_%H%M')}.zip"
        )
    return dash.no_update
