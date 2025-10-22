import dash
from dash import dcc, html, Input, Output, State, callback, register_page
import dash_bootstrap_components as dbc

register_page(__name__, path="/", name="Inicio", title="Portal Energético", order=0)

# Ajustes: Restricciones mucho más a la izquierda y más grande, Pérdidas más a la izquierda y más pequeño
MODULES = [
    {"id": "generacion", "path": "/generacion", "image": "Recurso 1.png", "left": "13%", "top": "60%", "width": "23%", "title": "Generación Eléctrica", "description": "Explore el análisis completo de la generación de energía eléctrica en Colombia. Incluye datos en tiempo real de plantas hidroeléctricas, térmicas, eólicas, solares y de biomasa. Monitoree la capacidad instalada, producción diaria y eficiencia energética por tecnología."},
    {"id": "transmision", "path": "/transmision", "image": "Recurso 2.png", "left": "11.5%", "top": "30%", "width": "19%", "title": "Transmisión Nacional", "description": "Supervise la red de transmisión eléctrica de alta tensión que conecta todo el territorio nacional. Incluye el estado operativo de líneas de transmisión, subestaciones, transformadores y análisis de congestión del sistema interconectado."},
    {"id": "distribucion", "path": "/distribucion", "image": "Recurso 3.png", "left": "29.5%", "top": "2%", "width": "30%", "title": "Distribución Local", "description": "Monitoree la red de distribución eléctrica a nivel local y regional. Incluye la calidad del servicio eléctrico, gestión de transformadores de distribución, indicadores de continuidad y confiabilidad del suministro en todo el país."},
    {"id": "metricas", "path": "/metricas", "image": "Recurso 4.png", "left": "61.5%", "top": "9%", "width": "24%", "title": "Comercialización", "description": "Acceda al análisis completo del mercado eléctrico colombiano. Incluye precios de bolsa en tiempo real, contratos bilaterales, métricas comerciales, liquidaciones y análisis financiero del sector energético nacional."},
    {"id": "restricciones", "path": "/restricciones", "image": "Recurso 6.png", "left": "43.5%", "top": "55.5%", "width": "23%", "title": "Restricciones", "description": "Gestione las restricciones que afectan la operación del sistema eléctrico. Incluye restricciones operativas por mantenimiento, limitaciones ambientales, regulatorias y de seguridad que impactan la generación y transmisión."},
    {"id": "perdidas", "path": "/perdidas", "image": "Recurso 5.png", "left": "63%", "top": "43.5%", "width": "16%", "title": "Pérdidas Energéticas", "description": "Controle y analice las pérdidas técnicas y comerciales del sistema eléctrico nacional. Incluye indicadores de eficiencia energética, pérdidas en transmisión y distribución, y estrategias de reducción implementadas."},
]

def layout():
    return html.Div([
        # SVG de fondo
        html.Img(
            src="/assets/portada.svg",
            id="background-svg",
            style={
                "position": "fixed",
                "top": "0",
                "left": "0", 
                "width": "100%",
                "height": "100vh",
                "objectFit": "contain",
                "zIndex": "1",
                "pointerEvents": "none",
                "transition": "filter 0.6s ease"
            }
        ),
        
        # Módulos con flotación y sombras amarillas restauradas
        *[
            html.A([
                html.Img(
                    src=f"/assets/{m['image']}",
                    className="floating-module-safe",  # Nueva clase sin conflictos
                    style={
                        "width": "100%", 
                        "height": "auto", 
                        "transition": "all 0.6s cubic-bezier(0.4, 0, 0.2, 1)",
                        "border": "none !important",
                        "outline": "none !important",
                        "background": "transparent !important",
                        "backgroundColor": "transparent !important",
                        "boxShadow": "none !important",
                        # Sombra amarilla sutil restaurada
                        "filter": "drop-shadow(0 8px 20px rgba(255, 193, 7, 0.35)) drop-shadow(0 4px 10px rgba(255, 165, 0, 0.25))"
                    }
                )
            ],
            href=m["path"],
            id=f"module-{m['id']}",
            className="custom-module floating-container",
            style={
                "position": "absolute",
                "left": m["left"],
                "top": m["top"], 
                "width": m["width"],
                "cursor": "pointer",
                "textDecoration": "none",
                "transition": "all 0.6s cubic-bezier(0.4, 0, 0.2, 1)",
                "zIndex": "10",
                "border": "none !important",
                "outline": "none !important",
                "background": "transparent !important",
                "backgroundColor": "transparent !important",
                "boxShadow": "none !important",
                # Animación de flotación suave
                "animation": "gentle-float 4s ease-in-out infinite"
            }
        ) for m in MODULES
        ],
        
        # Viñetas centrales más pequeñas y elegantes
        *[
            html.Div([
                html.H3(m['title'], style={
                    "color": "#ffc107", 
                    "marginBottom": "12px", 
                    "fontSize": "1.4rem", 
                    "fontWeight": "600",
                    "textAlign": "center",
                    "textShadow": "1px 1px 3px rgba(0,0,0,0.8)"
                }),
                html.P(m['description'][:180] + "..." if len(m['description']) > 180 else m['description'], style={
                    "color": "#ffffff", 
                    "margin": "0 0 12px 0", 
                    "fontSize": "0.9rem", 
                    "lineHeight": "1.5",
                    "textAlign": "justify",
                    "textShadow": "1px 1px 2px rgba(0,0,0,0.7)"
                }),
                html.P("✨ Haz clic para explorar", style={
                    "color": "#ffc107",
                    "fontSize": "0.8rem",
                    "fontStyle": "italic",
                    "margin": "0",
                    "textAlign": "center",
                    "opacity": "0.9"
                })
            ], 
            id=f"tooltip-{m['id']}",
            style={
                "position": "fixed",
                "top": "50%",
                "left": "50%",
                "transform": "translate(-50%, -50%) scale(0.9)",
                "background": "linear-gradient(135deg, rgba(0,0,0,0.92), rgba(20,30,50,0.92))",
                "padding": "18px 22px",
                "borderRadius": "15px",
                "minWidth": "280px",
                "maxWidth": "320px",
                "opacity": "0",
                "visibility": "hidden",
                "zIndex": "200",
                "boxShadow": "0 15px 40px rgba(0,0,0,0.6)",
                "border": "1px solid rgba(255,193,7,0.6)",
                "backdropFilter": "blur(15px)",
                "pointerEvents": "none",
                "transition": "all 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55)"
            }) for m in MODULES
        ],
        
        # Botón de información para ecuación de costo unitario
        html.Div([
            html.Button(
                "ℹ",  # Símbolo de información
                id="info-button",
                style={
                    "position": "absolute",
                    "top": "42%",  # Cerca del título "SECTOR Energético"
                    "left": "65%",  # Al lado derecho del título
                    "width": "35px",
                    "height": "35px",
                    "borderRadius": "50%",
                    "backgroundColor": "#F2C330",
                    "color": "#FFFFFF",
                    "fontSize": "18px",
                    "fontWeight": "bold",
                    "border": "2px solid #FFFFFF",
                    "cursor": "pointer",
                    "zIndex": "300",
                    "boxShadow": "0 4px 12px rgba(0,0,0,0.3)",
                    "transition": "all 0.3s ease",
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center"
                }
            )
        ]),
        
        # Modal de información sobre ecuación de costo unitario
        html.Div([
            html.Div([
                html.Div([
                    html.H3("Ecuación de Costo Unitario de Energía", style={
                        "color": "#F2C330",
                        "marginBottom": "20px",
                        "textAlign": "center",
                        "fontWeight": "600"
                    }),
                    html.Div([
                        html.H4("Cu = G + T + D + Cv + PR + R", style={
                            "color": "#1E3A8A",
                            "textAlign": "center",
                            "fontSize": "24px",
                            "fontWeight": "bold",
                            "marginBottom": "25px",
                            "padding": "15px",
                            "backgroundColor": "#F8F9FA",
                            "borderRadius": "8px",
                            "border": "2px solid #F2C330"
                        })
                    ]),
                    html.Div([
                        html.P([html.Strong("Cu:"), " Costo Unitario de Energía"], style={"marginBottom": "8px"}),
                        html.P([html.Strong("G:"), " Costo de Generación"], style={"marginBottom": "8px"}),
                        html.P([html.Strong("T:"), " Costo de Transmisión"], style={"marginBottom": "8px"}),
                        html.P([html.Strong("D:"), " Costo de Distribución"], style={"marginBottom": "8px"}),
                        html.P([html.Strong("Cv:"), " Costo de Comercialización"], style={"marginBottom": "8px"}),
                        html.P([html.Strong("PR:"), " Pérdidas Reconocidas"], style={"marginBottom": "8px"}),
                        html.P([html.Strong("R:"), " Restricciones y Servicios Complementarios"], style={"marginBottom": "8px"})
                    ], style={
                        "color": "#333333",
                        "fontSize": "14px",
                        "lineHeight": "1.5"
                    }),
                    html.Button(
                        "Cerrar",
                        id="close-info-button",
                        style={
                            "backgroundColor": "#F2C330",
                            "color": "#FFFFFF",
                            "border": "none",
                            "padding": "10px 20px",
                            "borderRadius": "5px",
                            "cursor": "pointer",
                            "fontSize": "14px",
                            "fontWeight": "bold",
                            "marginTop": "20px",
                            "width": "100%"
                        }
                    )
                ], style={
                    "backgroundColor": "#FFFFFF",
                    "padding": "30px",
                    "borderRadius": "15px",
                    "boxShadow": "0 20px 60px rgba(0,0,0,0.3)",
                    "maxWidth": "500px",
                    "width": "90%",
                    "maxHeight": "80vh",
                    "overflowY": "auto"
                })
            ], style={
                "position": "fixed",
                "top": "0",
                "left": "0",
                "width": "100%",
                "height": "100%",
                "backgroundColor": "rgba(0,0,0,0.7)",
                "display": "none",  # Inicialmente oculto
                "alignItems": "center",
                "justifyContent": "center",
                "zIndex": "1000",
                "backdropFilter": "blur(5px)"
            })
        ], id="info-modal"),
        
        # SOLUCIÓN SIMPLE: Crear las animaciones con estilos inline
        html.Div(id="custom-styles", style={"display": "none"}),
        
        # SOLUCIÓN SIMPLE: JavaScript básico sin conflictos
        html.Div(id="hover-handler", style={"display": "none"})
    ], id="page-background", style={
        "width": "100%",
        "height": "100vh", 
        "overflow": "hidden",
        "background": "#FCF3D6",  # Color EXACTO del fondo del SVG extraído del archivo
        "transition": "background 0.6s ease"  # Transición para sincronizar con SVG
    })
