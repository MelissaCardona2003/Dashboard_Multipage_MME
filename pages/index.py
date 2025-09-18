import dash
from dash import html, dcc, register_page
import dash_bootstrap_components as dbc
from datetime import datetime

# Imports locales para componentes uniformes
from .components import crear_header, crear_navbar, crear_sidebar_universal
from .config import COLORS

register_page(
    __name__,
    path="/",
    name="Inicio",
    title="Dashboard Energético - Ministerio de Minas y Energía",
    order=0
)

layout = html.Div([
    # Sidebar desplegable
    crear_sidebar_universal(),
    
    # Header uniforme
    # Header principal de inicio (mantiene el diseño original)
    crear_header(),
    # Barra de navegación eliminada
    
    # Container principal
    dbc.Container([
        # Contenido principal (ahora ocupa todo el ancho)
        dbc.Row([
            dbc.Col([
                # Bienvenida principal
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.H2([
                                html.I(className="fas fa-tachometer-alt me-3", style={"color": COLORS['primary']}),
                                "Dashboard Energético Nacional"
                            ], className="text-center mb-4", style={"color": COLORS['text_primary']}),
                            
                            html.P([
                                "Bienvenido al sistema integral de análisis energético del ",
                                html.Strong("Ministerio de Minas y Energía de Colombia", style={"color": COLORS['primary']}),
                                ". Esta plataforma proporciona herramientas avanzadas para el análisis de proximidad entre granjas solares, comunidades energéticas, métricas del sistema eléctrico nacional y datos hidrológicos."
                            ], className="text-center lead mb-4", style={"color": COLORS['text_secondary']}),
                            
                            # Estadísticas principales
                            dbc.Row([
                                dbc.Col([
                                    dbc.Card([
                                        dbc.CardBody([
                                            html.H3("8", className="text-center mb-0", style={"color": COLORS['primary'], "fontSize": "3rem"}),
                                            html.P("Módulos Activos", className="text-center mb-0", style={"color": COLORS['text_secondary']})
                                        ])
                                    ], color="primary", outline=True)
                                ], md=3),
                                dbc.Col([
                                    dbc.Card([
                                        dbc.CardBody([
                                            html.H3("190+", className="text-center mb-0", style={"color": COLORS['secondary'], "fontSize": "3rem"}),
                                            html.P("Métricas XM", className="text-center mb-0", style={"color": COLORS['text_secondary']})
                                        ])
                                    ], color="secondary", outline=True)
                                ], md=3),
                                dbc.Col([
                                    dbc.Card([
                                        dbc.CardBody([
                                            html.H3("1000+", className="text-center mb-0", style={"color": COLORS['info'], "fontSize": "3rem"}),
                                            html.P("Granjas Monitoreadas", className="text-center mb-0", style={"color": COLORS['text_secondary']})
                                        ])
                                    ], color="info", outline=True)
                                ], md=3),
                                dbc.Col([
                                    dbc.Card([
                                        dbc.CardBody([
                                            html.H3("24/7", className="text-center mb-0", style={"color": COLORS['success'], "fontSize": "3rem"}),
                                            html.P("Sistema Activo", className="text-center mb-0", style={"color": COLORS['text_secondary']})
                                        ])
                                    ], color="success", outline=True)
                                ], md=3)
                            ], className="mb-5"),
                            
                            html.Hr(),
                            
                            # Módulos disponibles
                            html.H4([
                                html.I(className="fas fa-th-large me-2", style={"color": COLORS['primary']}),
                                "Módulos del Sistema"
                            ], className="mb-4", style={"color": COLORS['text_primary']}),
                            
                            # Sección 1: Análisis y Métricas
                            html.H5([
                                html.I(className="fas fa-chart-bar me-2", style={"color": COLORS['primary']}),
                                "Herramienta para explorar las métricas de XM"
                            ], className="mb-3", style={"color": COLORS['primary']}),
                            
                            dbc.Row([
                                dbc.Col([
                                    dbc.Card([
                                        dbc.CardBody([
                                            html.H5([
                                                html.I(className="fas fa-chart-line me-2", style={"color": COLORS['info']}),
                                                "Métricas del Sistema XM"
                                            ], style={"color": COLORS['info']}),
                                            html.P("Acceso completo a las 190+ métricas oficiales del sistema eléctrico nacional a través de la API de XM. Consulta datos en tiempo real de generación, demanda, precios y transacciones comerciales con filtros avanzados y visualizaciones interactivas.",
                                                   className="mb-3", style={"color": COLORS['text_secondary']}),
                                            html.Ul([
                                                html.Li("⚡ 190+ métricas oficiales de XM"),
                                                html.Li("📈 Datos en tiempo real y históricos"),
                                                html.Li("🔍 Filtros por métrica, entidad y fechas"),
                                                html.Li("📋 Visualizaciones dinámicas Plotly"),
                                                html.Li("� Exportación de datos y gráficos")
                                            ], style={"color": COLORS['text_secondary'], "fontSize": "0.9rem"}),
                                            dbc.Button([
                                                html.I(className="fas fa-arrow-right me-2"),
                                                "Consultar Métricas"
                                            ], href="/metricas", color="info", className="w-100")
                                        ])
                                    ], className="h-100", style={'border': '2px solid #17a2b8'})
                                ], md=12, className="mb-4")
                            ]),
                            
                            html.Hr(className="my-4"),
                            
                            # Sección 2: Dashboards Especializados
                            html.H5([
                                html.I(className="fas fa-dashboard me-2", style={"color": COLORS['primary']}),
                                "Dashboards Especializados"
                            ], className="mb-3 mt-4", style={"color": COLORS['primary']}),
                            
                            dbc.Row([
                                # Hidrología
                                dbc.Col([
                                    dbc.Card([
                                        dbc.CardBody([
                                            html.H5([
                                                html.I(className="fas fa-tint me-2", style={"color": "#007bff"}),
                                                "Análisis Hidrológico Integral"
                                            ], style={"color": "#007bff"}),
                                            html.P("Sistema completo de monitoreo hidrológico con datos de XM. Incluye seguimiento de caudales de ríos, análisis de aportes hídricos, gestión de embalses con niveles en tiempo real, y análisis de disponibilidad hídrica para generación hidroeléctrica. Filtros por región y río específico.",
                                                   className="mb-3", style={"color": COLORS['text_secondary']}),
                                            html.Ul([
                                                html.Li("💧 Caudales de ríos en tiempo real"),
                                                html.Li("🏔️ Niveles y capacidad de embalses"),
                                                html.Li("📊 Análisis de aportes hídricos"),
                                                html.Li("🔍 Filtros por región y río"),
                                                html.Li("� Visualizaciones especializadas"),
                                                html.Li("⚡ Indicadores de carga durante consultas")
                                            ], style={"color": COLORS['text_secondary'], "fontSize": "0.9rem"}),
                                            dbc.Button([
                                                html.I(className="fas fa-arrow-right me-2"),
                                                "Ver Dashboard"
                                            ], href="/hidrologia", color="primary", className="w-100")
                                        ])
                                    ], className="h-100", style={'border': '2px solid #007bff'})
                                ], md=6, className="mb-4"),
                                
                                # Demanda
                                dbc.Col([
                                    dbc.Card([
                                        dbc.CardBody([
                                            html.H5([
                                                html.I(className="fas fa-chart-area me-2", style={"color": "#9932CC"}),
                                                "Análisis de Demanda Energética"
                                            ], style={"color": "#9932CC"}),
                                            html.P("Dashboard especializado en el análisis integral de la demanda energética nacional. Incluye monitoreo de patrones de consumo temporal y geográfico, análisis de picos y valles de demanda, proyecciones futuras y segmentación por sectores industriales y residenciales.",
                                                   className="mb-3", style={"color": COLORS['text_secondary']}),
                                            html.Ul([
                                                html.Li("📊 Patrones de consumo nacional"),
                                                html.Li("📈 Análisis de picos y valles"),
                                                html.Li("🏭 Segmentación por sectores"),
                                                html.Li("📍 Análisis regional detallado"),
                                                html.Li("⏰ Variaciones horarias y estacionales"),
                                                html.Li("🔮 Proyecciones de demanda")
                                            ], style={"color": COLORS['text_secondary'], "fontSize": "0.9rem"}),
                                            dbc.Button([
                                                html.I(className="fas fa-arrow-right me-2"),
                                                "Ver Dashboard"
                                            ], href="/demanda", color="secondary", className="w-100", style={"backgroundColor": "#9932CC", "borderColor": "#9932CC"})
                                        ])
                                    ], className="h-100", style={'border': '2px solid #9932CC'})
                                ], md=6, className="mb-4")
                            ]),
                            
                            html.Hr(className="my-4"),
                            
                            # Sección 3: Generación por Fuente
                            html.H5([
                                html.I(className="fas fa-bolt me-2", style={"color": COLORS['primary']}),
                                "Dashboards de Generación por Fuente"
                            ], className="mb-3 mt-4", style={"color": COLORS['primary']}),
                            
                            dbc.Row([
                                # Solar
                                dbc.Col([
                                    dbc.Card([
                                        dbc.CardBody([
                                            html.H5([
                                                html.I(className="fas fa-sun me-2", style={"color": "#FF8C00"}),
                                                "Generación Solar Fotovoltaica"
                                            ], style={"color": "#FF8C00"}),
                                            html.P("Dashboard especializado en energía solar fotovoltaica con datos oficiales de XM. Monitoreo de radiación solar por regiones, análisis de eficiencia de plantas solares, seguimiento de producción nacional y evaluación del potencial solar por departamentos.",
                                                   className="mb-3", style={"color": COLORS['text_secondary']}),
                                            html.Ul([
                                                html.Li("☀️ Radiación solar por regiones"),
                                                html.Li("🔋 Eficiencia de plantas fotovoltaicas"),
                                                html.Li("📍 Producción por departamentos"),
                                                html.Li("📊 Análisis de potencial solar"),
                                                html.Li("📈 Tendencias de generación"),
                                                html.Li("🌤️ Variables meteorológicas")
                                            ], style={"color": COLORS['text_secondary'], "fontSize": "0.9rem"}),
                                            dbc.Button([
                                                html.I(className="fas fa-arrow-right me-2"),
                                                "Ver Dashboard"
                                            ], href="/generacion-solar", className="w-100", style={"backgroundColor": "#FF8C00", "borderColor": "#FF8C00", "color": "white"})
                                        ])
                                    ], className="h-100", style={'border': '2px solid #FF8C00'})
                                ], md=6, className="mb-4"),
                                
                                # Eólica
                                dbc.Col([
                                    dbc.Card([
                                        dbc.CardBody([
                                            html.H5([
                                                html.I(className="fas fa-wind me-2", style={"color": "#20B2AA"}),
                                                "Generación Eólica"
                                            ], style={"color": "#20B2AA"}),
                                            html.P("Análisis integral de energía eólica con datos de XM. Monitoreo de velocidades de viento, rendimiento de aerogeneradores, análisis de patrones estacionales, evaluación del recurso eólico y seguimiento de la producción en parques eólicos nacionales.",
                                                   className="mb-3", style={"color": COLORS['text_secondary']}),
                                            html.Ul([
                                                html.Li("💨 Velocidades de viento por zonas"),
                                                html.Li("🌪️ Rendimiento de aerogeneradores"),
                                                html.Li("📅 Patrones estacionales"),
                                                html.Li("🗺️ Mapas de recurso eólico"),
                                                html.Li("⚡ Producción de parques eólicos"),
                                                html.Li("📊 Factores de planta")
                                            ], style={"color": COLORS['text_secondary'], "fontSize": "0.9rem"}),
                                            dbc.Button([
                                                html.I(className="fas fa-arrow-right me-2"),
                                                "Ver Dashboard"
                                            ], href="/generacion-eolica", className="w-100", style={"backgroundColor": "#20B2AA", "borderColor": "#20B2AA", "color": "white"})
                                        ])
                                    ], className="h-100", style={'border': '2px solid #20B2AA'})
                                ], md=6, className="mb-4")
                            ]),
                            
                            dbc.Row([
                                # Biomasa
                                dbc.Col([
                                    dbc.Card([
                                        dbc.CardBody([
                                            html.H5([
                                                html.I(className="fas fa-leaf me-2", style={"color": "#228B22"}),
                                                "Generación por Biomasa"
                                            ], style={"color": "#228B22"}),
                                            html.P("Dashboard de energía renovable por biomasa con datos oficiales de XM. Seguimiento de disponibilidad de biomasa agrícola y forestal, eficiencia de plantas de cogeneración, análisis de gestión sostenible de residuos y evaluación del potencial energético por regiones.",
                                                   className="mb-3", style={"color": COLORS['text_secondary']}),
                                            html.Ul([
                                                html.Li("🌾 Disponibilidad de biomasa por región"),
                                                html.Li("🏭 Eficiencia de plantas de cogeneración"),
                                                html.Li("♻️ Gestión sostenible de residuos"),
                                                html.Li("🌱 Potencial energético renovable"),
                                                html.Li("📊 Análisis de producción"),
                                                html.Li("🌍 Impacto ambiental positivo")
                                            ], style={"color": COLORS['text_secondary'], "fontSize": "0.9rem"}),
                                            dbc.Button([
                                                html.I(className="fas fa-arrow-right me-2"),
                                                "Ver Dashboard"
                                            ], href="/generacion-biomasa", className="w-100", style={"backgroundColor": "#228B22", "borderColor": "#228B22", "color": "white"})
                                        ])
                                    ], className="h-100", style={'border': '2px solid #228B22'})
                                ], md=6, className="mb-4"),
                                
                                # Hidráulica
                                dbc.Col([
                                    dbc.Card([
                                        dbc.CardBody([
                                            html.H5([
                                                html.I(className="fas fa-water me-2", style={"color": "#4682B4"}),
                                                "Generación Hidráulica"
                                            ], style={"color": "#4682B4"}),
                                            html.P("Sistema especializado en generación hidroeléctrica con datos de XM. Monitoreo detallado de embalses nacionales, análisis de eficiencia de turbinado, gestión optimizada de recursos hídricos y seguimiento operativo de centrales hidroeléctricas.",
                                                   className="mb-3", style={"color": COLORS['text_secondary']}),
                                            html.Ul([
                                                html.Li("🏔️ Monitoreo de embalses nacionales"),
                                                html.Li("⚡ Análisis de eficiencia de turbinado"),
                                                html.Li("🏗️ Operación de centrales hidroeléctricas"),
                                                html.Li("🌊 Gestión optimizada de recursos"),
                                                html.Li("📊 Capacidad de almacenamiento"),
                                                html.Li("💧 Coordinación hídrica nacional")
                                            ], style={"color": COLORS['text_secondary'], "fontSize": "0.9rem"}),
                                            dbc.Button([
                                                html.I(className="fas fa-arrow-right me-2"),
                                                "Ver Dashboard"
                                            ], href="/generacion-hidraulica", className="w-100", style={"backgroundColor": "#4682B4", "borderColor": "#4682B4", "color": "white"})
                                        ])
                                    ], className="h-100", style={'border': '2px solid #4682B4'})
                                ], md=6, className="mb-4")
                            ]),
                            
                            html.Hr(className="my-4"),
                            
                            # Información adicional
                            dbc.Row([
                                dbc.Col([
                                    dbc.Alert([
                                        html.H6([
                                            html.I(className="fas fa-lightbulb me-2"),
                                            "Funcionalidades Implementadas"
                                        ], className="alert-heading"),
                                        html.P([
                                            "• ", html.Strong("Integración XM Completa:"), " Acceso directo a 190+ métricas oficiales del operador del mercado",
                                            html.Br(),
                                            "• ", html.Strong("Análisis Geoespacial:"), " Más de 1000 ubicaciones de granjas solares y comunidades energéticas",
                                            html.Br(),
                                            "• ", html.Strong("Visualizaciones Dinámicas:"), " Gráficos interactivos Plotly con exportación y filtros avanzados",
                                            html.Br(),
                                            "• ", html.Strong("Datos Hidrológicos:"), " Monitoreo en tiempo real de caudales, embalses y aportes hídricos"
                                        ], className="mb-0")
                                    ], color="info", className="mb-3"),
                                ], md=6),
                                
                                dbc.Col([
                                    dbc.Alert([
                                        html.H6([
                                            html.I(className="fas fa-cog me-2"),
                                            "Tecnologías y Herramientas"
                                        ], className="alert-heading"),
                                        html.P([
                                            "• ", html.Strong("Backend:"), " Python 3.10+, Dash 2.x, pydataxm",
                                            html.Br(),
                                            "• ", html.Strong("Visualización:"), " Plotly, Dash Bootstrap Components, Font Awesome",
                                            html.Br(),
                                            "• ", html.Strong("Datos:"), " APIs REST de XM, Pandas, NumPy, Geopy",
                                            html.Br(),
                                            "• ", html.Strong("UX:"), " Indicadores de carga, filtros inteligentes, exports automáticos"
                                        ], className="mb-0")
                                    ], color="secondary", className="mb-3"),
                                ], md=6)
                            ]),
                            
                            # Footer de información
                            html.Div([
                                html.P([
                                    html.I(className="fas fa-info-circle me-2"),
                                    "Sistema desarrollado para el análisis integral del sector energético colombiano - ",
                                    html.Strong("Ministerio de Minas y Energía")
                                ], className="text-center mb-2", style={"color": COLORS['text_secondary'], "fontSize": "0.9rem"}),
                                html.P([
                                    html.I(className="fas fa-calendar me-2"),
                                    f"Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')} | ",
                                    html.I(className="fas fa-database me-2"),
                                    "Datos sincronizados con XM - Operador del Mercado"
                                ], className="text-center mb-0", style={"color": COLORS['text_secondary'], "fontSize": "0.8rem"})
                            ], className="mt-4")
                            
                        ])
                    ])
                ], className="shadow-sm", style={'borderRadius': '15px'})
            ], width=12)  # Ahora ocupa todo el ancho
        ])
    ], fluid=True, className="mt-4")
], style={'backgroundColor': COLORS['bg_main'], 'minHeight': '100vh'})
