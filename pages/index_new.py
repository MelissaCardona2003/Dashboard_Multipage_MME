import dash
from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc

# Metadata para Dash Pages (auto-discovery)
dash.register_page(
    __name__,
    path="/home",
    name="Inicio Mejorado",
    title="Portal Energético",
    order=0
)

# Configuración de módulos con posiciones ajustadas para el diagrama
MODULES = [
    {
        "id": "generacion", 
        "path": "/generacion", 
        "icon": "⚙️",  # Engranaje para generación
        "label": "GENERACIÓN",
        "left": "13%", 
        "top": "60%", 
        "width": "200px", 
        "color": "#4CAF50",  # Verde
        "description": "Producción de energía eléctrica"
    },
    {
        "id": "transmision", 
        "path": "/transmision", 
        "icon": "📡",  # Ondas para transmisión
        "label": "TRANSMISIÓN",
        "left": "11.5%", 
        "top": "30%", 
        "width": "200px", 
        "color": "#2196F3",  # Azul
        "description": "Transporte de energía de alta tensión"
    },
    {
        "id": "distribucion", 
        "path": "/distribucion", 
        "icon": "⚡",  # Rayo para distribución
        "label": "DISTRIBUCIÓN",
        "left": "29.5%", 
        "top": "2%", 
        "width": "240px", 
        "color": "#FF9800",  # Naranja
        "description": "Redes locales y entrega final"
    },
    {
        "id": "comercializacion", 
        "path": "/metricas", 
        "icon": "💰",  # Dinero para comercialización
        "label": "COMERCIALIZACIÓN",
        "left": "61.5%", 
        "top": "9%", 
        "width": "220px", 
        "color": "#9C27B0",  # Púrpura
        "description": "Gestión comercial y facturación"
    },
    {
        "id": "restricciones", 
        "path": "/restricciones", 
        "icon": "🚫",  # Prohibido para restricciones
        "label": "RESTRICCIONES",
        "left": "43.5%", 
        "top": "55.5%", 
        "width": "210px", 
        "color": "#F44336",  # Rojo
        "description": "Limitaciones operativas del sistema"
    },
    {
        "id": "perdidas", 
        "path": "/perdidas", 
        "icon": "📉",  # Gráfico bajando para pérdidas
        "label": "PÉRDIDAS",
        "left": "63%", 
        "top": "43.5%", 
        "width": "180px", 
        "color": "#795548",  # Café
        "description": "Pérdidas técnicas y no técnicas"
    },
]

def layout():
    return html.Div([
        # SVG de fondo (fijo, sin cambios)
        html.Img(
            src="/assets/portada.svg",
            id="background-svg-new",
            style={
                "position": "fixed",
                "top": "0",
                "left": "0", 
                "width": "100%",
                "height": "100vh",
                "objectFit": "contain",
                "zIndex": "1",
                "pointerEvents": "none"
            }
        ),
        
        # Módulos con estilo limpio y moderno (SIN animación de flotación)
        *[
            html.A([
                html.Div([
                    # Icono grande
                    html.Div(m['icon'], style={
                        "fontSize": "48px",
                        "marginBottom": "8px",
                        "filter": "drop-shadow(0 4px 8px rgba(0,0,0,0.3))"
                    }),
                    # Label
                    html.Div(m['label'], style={
                        "fontSize": "16px",
                        "fontWeight": "700",
                        "letterSpacing": "1px",
                        "color": "#FFFFFF",
                        "textShadow": "2px 2px 4px rgba(0,0,0,0.8)",
                        "marginBottom": "4px"
                    }),
                    # Línea decorativa
                    html.Div(style={
                        "width": "60px",
                        "height": "3px",
                        "backgroundColor": m['color'],
                        "margin": "0 auto 8px auto",
                        "borderRadius": "2px",
                        "boxShadow": f"0 2px 8px {m['color']}"
                    }),
                    # Descripción corta
                    html.Div(m['description'], style={
                        "fontSize": "12px",
                        "color": "#E0E0E0",
                        "textAlign": "center",
                        "lineHeight": "1.4",
                        "opacity": "0.9"
                    })
                ], style={
                    "display": "flex",
                    "flexDirection": "column",
                    "alignItems": "center",
                    "justifyContent": "center",
                    "height": "100%",
                    "padding": "20px"
                })
            ],
            href=m["path"],
            id=f"module-new-{m['id']}",
            className="module-card-stable",  # Nueva clase sin animaciones
            style={
                "position": "absolute",
                "left": m["left"],
                "top": m["top"], 
                "width": m["width"],
                "height": "180px",
                "cursor": "pointer",
                "textDecoration": "none",
                "zIndex": "10",
                # Fondo con gradiente y glassmorphism
                "background": "linear-gradient(135deg, rgba(0,0,0,0.7), rgba(30,30,30,0.8))",
                "backdropFilter": "blur(10px)",
                "borderRadius": "16px",
                "border": f"2px solid {m['color']}",
                "boxShadow": f"0 8px 24px rgba(0,0,0,0.4), 0 0 20px {m['color']}40",
                # Transiciones suaves SOLO en hover
                "transition": "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
                # SIN animación continua
                "transform": "translateY(0) scale(1)"
            }
        ) for m in MODULES
        ],
        
        # Botón de información central
        html.Div([
            html.Button(
                "ℹ",
                id="info-button-new",
                style={
                    "position": "fixed",
                    "top": "42%",
                    "left": "54%",
                    "transform": "translate(-50%, -50%)",
                    "width": "70px",
                    "height": "70px",
                    "borderRadius": "50%",
                    "backgroundColor": "#F2C330",
                    "color": "#2C3E50",
                    "fontSize": "36px",
                    "fontWeight": "bold",
                    "border": "4px solid #2C3E50",
                    "cursor": "pointer",
                    "zIndex": "50",
                    "boxShadow": "0 8px 24px rgba(0,0,0,0.5), 0 0 0 4px rgba(242,195,48,0.3)",
                    "transition": "all 0.3s ease",
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center"
                },
                title="Información del Sistema Energético"
            )
        ]),
        
        # Modal de información (mismo contenido que antes)
        html.Div([
            html.Div([
                html.Div([
                    html.Button(
                        "✕",
                        id="close-info-new",
                        style={
                            "position": "absolute",
                            "top": "15px",
                            "right": "15px",
                            "background": "transparent",
                            "border": "none",
                            "fontSize": "24px",
                            "cursor": "pointer",
                            "color": "#999",
                            "transition": "color 0.2s"
                        }
                    ),
                    html.H3("Sistema Energético Nacional", style={
                        "color": "#F2C330",
                        "marginBottom": "20px",
                        "textAlign": "center",
                        "fontWeight": "600",
                        "fontSize": "24px"
                    }),
                    html.Div([
                        html.H4("CU = G + T + D + Cv + PR + R", style={
                            "color": "#1E3A8A",
                            "textAlign": "center",
                            "fontSize": "20px",
                            "fontWeight": "bold",
                            "marginBottom": "20px",
                            "padding": "15px",
                            "backgroundColor": "#F8F9FA",
                            "borderRadius": "8px",
                            "border": "2px solid #F2C330"
                        })
                    ]),
                    html.P([
                        "El ", html.Strong("Costo Unitario (CU)"), " es el valor por kWh que paga el usuario regulado. ",
                        "Integra todos los costos del sistema eléctrico colombiano."
                    ], style={"marginBottom": "20px", "fontSize": "15px", "lineHeight": "1.6", "color": "#333"}),
                    
                    html.Hr(style={"margin": "20px 0", "border": "none", "borderTop": "1px solid #ddd"}),
                    
                    html.H5("Componentes:", style={"color": "#1E3A8A", "marginBottom": "15px", "fontSize": "18px"}),
                    html.Div([
                        html.Div([
                            html.Span("⚙️", style={"fontSize": "20px", "marginRight": "10px"}),
                            html.Strong("G - Generación:"),
                            " Costo de producir/comprar energía"
                        ], style={"marginBottom": "10px", "fontSize": "14px"}),
                        html.Div([
                            html.Span("📡", style={"fontSize": "20px", "marginRight": "10px"}),
                            html.Strong("T - Transmisión:"),
                            " Peaje del sistema de alta tensión"
                        ], style={"marginBottom": "10px", "fontSize": "14px"}),
                        html.Div([
                            html.Span("⚡", style={"fontSize": "20px", "marginRight": "10px"}),
                            html.Strong("D - Distribución:"),
                            " Peaje de redes locales"
                        ], style={"marginBottom": "10px", "fontSize": "14px"}),
                        html.Div([
                            html.Span("💰", style={"fontSize": "20px", "marginRight": "10px"}),
                            html.Strong("Cv - Comercialización:"),
                            " Gestión comercial variable"
                        ], style={"marginBottom": "10px", "fontSize": "14px"}),
                        html.Div([
                            html.Span("📉", style={"fontSize": "20px", "marginRight": "10px"}),
                            html.Strong("PR - Pérdidas:"),
                            " Energía para cubrir pérdidas"
                        ], style={"marginBottom": "10px", "fontSize": "14px"}),
                        html.Div([
                            html.Span("🚫", style={"fontSize": "20px", "marginRight": "10px"}),
                            html.Strong("R - Restricciones:"),
                            " Costo operativo de redespacho"
                        ], style={"marginBottom": "10px", "fontSize": "14px"})
                    ], style={"marginBottom": "20px"}),
                    
                    html.P([
                        "💡 ",
                        html.Em("Haz clic en cada componente del diagrama para explorar información detallada y métricas en tiempo real.")
                    ], style={"fontSize": "13px", "color": "#666", "fontStyle": "italic", "textAlign": "center"})
                ], style={
                    "backgroundColor": "#FFFFFF",
                    "padding": "35px",
                    "borderRadius": "16px",
                    "boxShadow": "0 20px 60px rgba(0,0,0,0.3)",
                    "maxWidth": "550px",
                    "width": "90%",
                    "maxHeight": "85vh",
                    "overflowY": "auto",
                    "position": "relative"
                })
            ], style={
                "position": "fixed",
                "top": "0",
                "left": "0",
                "width": "100%",
                "height": "100%",
                "backgroundColor": "rgba(0,0,0,0.75)",
                "display": "none",
                "alignItems": "center",
                "justifyContent": "center",
                "zIndex": "1000",
                "backdropFilter": "blur(8px)"
            })
        ], id="info-modal-new"),
        
        # Estilos CSS adicionales
        html.Style("""
            /* Hover en módulos - SOLO transformación suave */
            .module-card-stable:hover {
                transform: translateY(-8px) scale(1.05) !important;
                box-shadow: 0 16px 40px rgba(0,0,0,0.6), 0 0 30px currentColor !important;
                filter: brightness(1.1);
            }
            
            /* Hover en botón info */
            #info-button-new:hover {
                transform: translate(-50%, -50%) scale(1.1) !important;
                box-shadow: 0 12px 32px rgba(0,0,0,0.6), 0 0 0 6px rgba(242,195,48,0.4) !important;
            }
            
            /* Hover en botón cerrar */
            #close-info-new:hover {
                color: #F2C330 !important;
                transform: rotate(90deg) !important;
            }
            
            /* Animación suave para el modal */
            #info-modal-new[style*="display: flex"] {
                animation: fadeIn 0.3s ease;
            }
            
            @keyframes fadeIn {
                from {
                    opacity: 0;
                    transform: scale(0.95);
                }
                to {
                    opacity: 1;
                    transform: scale(1);
                }
            }
            
            /* Scrollbar personalizado para el modal */
            #info-modal-new ::-webkit-scrollbar {
                width: 8px;
            }
            
            #info-modal-new ::-webkit-scrollbar-track {
                background: #f1f1f1;
                border-radius: 10px;
            }
            
            #info-modal-new ::-webkit-scrollbar-thumb {
                background: #F2C330;
                border-radius: 10px;
            }
            
            #info-modal-new ::-webkit-scrollbar-thumb:hover {
                background: #d4a820;
            }
        """)
    ], style={
        "width": "100%",
        "height": "100vh", 
        "overflow": "hidden",
        "background": "#FCF3D6",
        "position": "relative"
    })

# Callbacks para interactividad
@callback(
    Output("info-modal-new", "style"),
    [Input("info-button-new", "n_clicks"),
     Input("close-info-new", "n_clicks")],
    [State("info-modal-new", "style")],
    prevent_initial_call=True
)
def toggle_modal(info_clicks, close_clicks, current_style):
    """Toggle del modal de información"""
    if current_style is None:
        current_style = {"display": "none"}
    
    # Si está oculto, mostrarlo
    if current_style.get("display") == "none":
        return {
            "position": "fixed",
            "top": "0",
            "left": "0",
            "width": "100%",
            "height": "100%",
            "backgroundColor": "rgba(0,0,0,0.75)",
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "center",
            "zIndex": "1000",
            "backdropFilter": "blur(8px)"
        }
    # Si está visible, ocultarlo
    else:
        return {**current_style, "display": "none"}
