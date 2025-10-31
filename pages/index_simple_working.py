import dash
from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc

# Metadata para Dash Pages (auto-discovery)
dash.register_page(
    __name__,
    path="/",
    name="Inicio",
    title="Portal Energético",
    order=0
)

# Ajustes: Restricciones mucho más a la izquierda y más grande, Pérdidas más a la izquierda y más pequeño
MODULES = [
    {
        "id": "generacion", 
        "path": "/generacion", 
        "image": "Recurso 1.png", 
        "left": "13%", 
        "top": "60%", 
        "width": "23%", 
        "title": "G — Generación", 
        "description": "Costo de producir/comprar la energía (contratos + bolsa). Es el componente más variable del CU.",
        "modal_description": "G refleja el precio promedio de la energía adquirida a generadores vía contratos bilaterales y bolsa del MEM (XM). Su dinámica depende de hidrología, combustibles y oferta/demanda; la CREG y XM reportan explícitamente la relación entre precios de bolsa/contratos y el componente G del CU.",
        "formula": "G = Σ(Eᵢ · Pᵢ) / Σ(Eᵢ)",
        "formula_description": "Precio promedio ponderado de la energía comprada; XM/CREG lo analizan como promedio entre contratos y bolsa."
    },
    {
        "id": "transmision", 
        "path": "/transmision", 
        "image": "Recurso 2.png", 
        "left": "11.5%", 
        "top": "30%", 
        "width": "19%", 
        "title": "T — Transmisión", 
        "description": "Peaje del STN (líneas de alta tensión). Cargo regulado y relativamente estable en $/kWh.",
        "modal_description": "T remunera los activos del Sistema de Transmisión Nacional (STN) y su operación. La SSPD y la CREG describen que es un cargo por uso regulado que XM incorpora al CU.",
        "formula": "T = C_uso_STN / E_entregada",
        "formula_description": "Costo total de transmisión por unidad de energía entregada; se publica como cargo unitario."
    },
    {
        "id": "distribucion", 
        "path": "/distribucion", 
        "image": "Recurso 3.png", 
        "left": "29.5%", 
        "top": "2%", 
        "width": "30%", 
        "title": "D — Distribución", 
        "description": "Peaje del SDL (redes locales: media/baja tensión). Cargo regulado por zona/nivel de tensión.",
        "modal_description": "D remunera redes locales (postes, transformadores, operación y expansión). La CREG define los cargos por uso del SDL y XM publica los cargos de distribución que alimentan el CU.",
        "formula": "D = C_SDL / E_entregada",
        "formula_description": "Cargo unitario de distribución aplicado al mercado/nivel de tensión."
    },
    {
        "id": "metricas", 
        "path": "/metricas", 
        "image": "Recurso 4.png", 
        "left": "61.5%", 
        "top": "9%", 
        "width": "24%", 
        "title": "Cv — Comercialización", 
        "description": "Costo variable por kWh de gestión comercial (medición, facturación, atención). Definido en la fórmula tarifaria.",
        "modal_description": "El costo de comercialización tiene parte fija (Cf) y variable (Cv). Para el CU, XM utiliza el término variable regulado por CREG (fórmula tarifaria vigente), aplicado en $/kWh sobre la energía del usuario.",
        "formula": "C_comercialización = Cf + Cv · Eu",
        "formula_description": "En CU se incorpora (Cv) como cargo unitario."
    },
    {
        "id": "restricciones", 
        "path": "/restricciones", 
        "image": "Recurso 6.png", 
        "left": "43.5%", 
        "top": "55.5%", 
        "width": "23%", 
        "title": "R — Restricciones", 
        "description": "Costo por congestiones/limitaciones de red que obligan al CND (XM) a redespachar generación más cara localmente.",
        "modal_description": "Cuando la red se congestiona o hay condiciones operativas, el CND (XM) realiza redespacho y se incurre en costos de restricciones. XM publica que el costo unitario de restricciones es la razón entre el costo total de restricciones y la generación real del sistema en el periodo.",
        "formula": "R = C_restricciones(periodo) / E_generación_real(periodo)",
        "formula_description": "Definición 'costo unitario de restricciones' publicada por XM."
    },
    {
        "id": "perdidas", 
        "path": "/perdidas", 
        "image": "Recurso 5.png", 
        "left": "63%", 
        "top": "43.5%", 
        "width": "16%", 
        "title": "PR — Pérdidas", 
        "description": "Energía adicional que se compra para cubrir pérdidas técnicas/no técnicas reconocidas por CREG. La metodología la aplica ASIC/XM.",
        "modal_description": "En redes hay pérdidas; la regulación reconoce un porcentaje (por mercado/nivel) que el ASIC (en XM) aplica para la liquidación. Esto se traduce en un cargo unitario en el CU asociado a comprar kWh extra para que al medidor llegue lo que el usuario consume.",
        "formula": "PR ≈ G · (1/(1-Lp) - 1)",
        "formula_description": "Si Lp es el porcentaje de pérdidas reconocidas, entonces la energía a comprar es Eu/(1-Lp). La aplicación y series oficiales de pérdidas son calculadas por el ASIC conforme a la CREG 015 de 2018."
    },
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
        
        # Viñetas centrales completas con toda la información detallada
        *[
            html.Div([
                html.Div([
                    html.H3(m['title'], style={
                        "color": "#ffc107", 
                        "marginBottom": "15px", 
                        "fontSize": "1.5rem", 
                        "fontWeight": "700",
                        "textAlign": "center",
                        "textShadow": "2px 2px 4px rgba(0,0,0,0.8)",
                        "borderBottom": "2px solid #ffc107",
                        "paddingBottom": "10px"
                    }),
                    
                    # Descripción corta
                    html.P(m['description'], style={
                        "color": "#ffffff", 
                        "margin": "0 0 15px 0", 
                        "fontSize": "0.95rem", 
                        "lineHeight": "1.6",
                        "textAlign": "justify",
                        "textShadow": "1px 1px 3px rgba(0,0,0,0.8)",
                        "fontWeight": "500"
                    }),
                    
                    html.Hr(style={"margin": "15px 0", "border": "none", "borderTop": "1px solid rgba(255,193,7,0.3)"}),
                    
                    # Descripción técnica ampliada
                    html.Div([
                        html.P([html.Strong("Descripción técnica:", style={"color": "#ffc107"})], 
                               style={"marginBottom": "8px", "fontSize": "0.85rem"}),
                        html.P(m.get('modal_description', ''), style={
                            "color": "#e0e0e0", 
                            "margin": "0 0 12px 0", 
                            "fontSize": "0.8rem", 
                            "lineHeight": "1.5",
                            "textAlign": "justify",
                            "textShadow": "1px 1px 2px rgba(0,0,0,0.7)"
                        })
                    ]),
                    
                    html.Hr(style={"margin": "15px 0", "border": "none", "borderTop": "1px solid rgba(255,193,7,0.3)"}),
                    
                    # Fórmula
                    html.Div([
                        html.P([html.Strong("Fórmula:", style={"color": "#ffc107"})], 
                               style={"marginBottom": "8px", "fontSize": "0.85rem"}),
                        html.Code(m.get('formula', 'No disponible'), style={
                            "display": "block",
                            "padding": "10px",
                            "backgroundColor": "rgba(255,255,255,0.15)",
                            "borderLeft": "3px solid #ffc107",
                            "marginBottom": "8px",
                            "fontSize": "0.85rem",
                            "borderRadius": "5px",
                            "fontFamily": "monospace",
                            "color": "#ffd54f",
                            "textShadow": "1px 1px 2px rgba(0,0,0,0.8)"
                        }),
                        html.P(m.get('formula_description', ''), style={
                            "color": "#d0d0d0", 
                            "fontSize": "0.75rem", 
                            "fontStyle": "italic", 
                            "margin": "0",
                            "lineHeight": "1.4",
                            "textShadow": "1px 1px 2px rgba(0,0,0,0.7)"
                        })
                    ]),
                    
                    html.Hr(style={"margin": "15px 0", "border": "none", "borderTop": "1px solid rgba(255,193,7,0.3)"}),
                    
                    html.P("✨ Haz clic para explorar el sector completo", style={
                        "color": "#ffc107",
                        "fontSize": "0.85rem",
                        "fontWeight": "600",
                        "fontStyle": "italic",
                        "margin": "0",
                        "textAlign": "center",
                        "opacity": "0.95",
                        "textShadow": "1px 1px 2px rgba(0,0,0,0.8)"
                    })
                ])
            ], 
            id=f"tooltip-{m['id']}",
            style={
                "position": "fixed",
                "top": "50%",
                "left": "50%",
                "transform": "translate(-50%, -50%) scale(0.9)",
                "background": "linear-gradient(135deg, rgba(0,0,0,0.95), rgba(20,30,50,0.95))",
                "padding": "25px 28px",
                "borderRadius": "18px",
                "minWidth": "380px",
                "maxWidth": "480px",
                "maxHeight": "85vh",
                "overflowY": "auto",
                "opacity": "0",
                "visibility": "hidden",
                "zIndex": "200",
                "boxShadow": "0 20px 60px rgba(0,0,0,0.8), 0 0 0 1px rgba(255,193,7,0.5)",
                "border": "2px solid rgba(255,193,7,0.7)",
                "backdropFilter": "blur(20px)",
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
                    "position": "fixed",
                    "top": "42%",  # Un poco más arriba
                    "left": "54%",  # Más a la derecha para tapar el título
                    "transform": "translate(-50%, -50%)",  # Centrado exacto
                    "width": "60px",
                    "height": "60px",
                    "borderRadius": "50%",
                    "backgroundColor": "#F2C330",
                    "color": "#2C3E50",
                    "fontSize": "32px",
                    "fontWeight": "bold",
                    "border": "4px solid #2C3E50",
                    "cursor": "pointer",
                    "zIndex": "10",  # Más bajo que tooltips (100) y modales (1000)
                    "boxShadow": "0 8px 20px rgba(0,0,0,0.5), 0 0 0 3px rgba(242,195,48,0.4)",
                    "transition": "all 0.3s ease",
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center",
                    "animation": "pulse 2s ease-in-out infinite"
                },
                title="Clic para ver información sobre el Costo Unitario (CU)"
            )
        ]),
        
        # Modal de información sobre ecuación de costo unitario
        html.Div([
            html.Div([
                html.Div([
                    html.H3("¿Qué es el Costo Unitario (CU)?", style={
                        "color": "#F2C330",
                        "marginBottom": "15px",
                        "textAlign": "center",
                        "fontWeight": "600",
                        "fontSize": "20px"
                    }),
                    html.Div([
                        html.H4("CU = G + T + D + Cv + PR + R", style={
                            "color": "#1E3A8A",
                            "textAlign": "center",
                            "fontSize": "22px",
                            "fontWeight": "bold",
                            "marginBottom": "15px",
                            "padding": "12px",
                            "backgroundColor": "#F8F9FA",
                            "borderRadius": "8px",
                            "border": "2px solid #F2C330"
                        })
                    ]),
                    html.P([
                        "Es el ", html.Strong("valor por kWh"), " que paga el usuario regulado por la energía entregada, calculado con la ",
                        html.Strong("metodología de la CREG"), " e implementado/publicado por XM."
                    ], style={"marginBottom": "15px", "fontSize": "14px", "lineHeight": "1.6", "color": "#333"}),
                    
                    html.Hr(style={"margin": "20px 0", "border": "none", "borderTop": "1px solid #ddd"}),
                    
                    html.H5("Descripción ampliada:", style={"color": "#1E3A8A", "marginBottom": "10px", "fontSize": "16px"}),
                    html.P([
                        "El ", html.Strong("Costo Unitario de prestación del servicio (CU)"), " agrega, en $/kWh, los costos de ",
                        html.Strong("Generación (G)"), ", ", html.Strong("Transmisión (T)"), ", ", html.Strong("Distribución (D)"), ", ",
                        html.Strong("Comercialización variable (Cv)"), ", ", html.Strong("Pérdidas reconocidas (PR)"), " y ",
                        html.Strong("Restricciones (R)"), ". XM publica series de CU por periodo, mercado y nivel de tensión bajo la metodología ",
                        html.Strong("CREG 119 de 2007"), " (con desarrollos posteriores y opción tarifaria cuando aplica)."
                    ], style={"marginBottom": "15px", "fontSize": "13px", "lineHeight": "1.6", "color": "#555"}),
                    
                    html.Hr(style={"margin": "20px 0", "border": "none", "borderTop": "1px solid #ddd"}),
                    
                    html.H5("Relación básica:", style={"color": "#1E3A8A", "marginBottom": "10px", "fontSize": "16px"}),
                    html.Div([
                        html.Code("CU = G + T + D + Cv + PR + R", style={
                            "display": "block",
                            "padding": "8px",
                            "backgroundColor": "#f5f5f5",
                            "borderLeft": "3px solid #F2C330",
                            "marginBottom": "8px",
                            "fontSize": "13px"
                        }),
                        html.Code("Factura (energía) = CU × kWh del usuario", style={
                            "display": "block",
                            "padding": "8px",
                            "backgroundColor": "#f5f5f5",
                            "borderLeft": "3px solid #F2C330",
                            "fontSize": "13px"
                        })
                    ], style={"marginBottom": "15px"}),
                    
                    html.Hr(style={"margin": "20px 0", "border": "none", "borderTop": "1px solid #ddd"}),
                    
                    html.Div([
                        html.P([html.Strong("G:"), " Generación - Costo de producir/comprar la energía"], style={"marginBottom": "6px", "fontSize": "13px"}),
                        html.P([html.Strong("T:"), " Transmisión - Peaje del STN (líneas de alta tensión)"], style={"marginBottom": "6px", "fontSize": "13px"}),
                        html.P([html.Strong("D:"), " Distribución - Peaje del SDL (redes locales)"], style={"marginBottom": "6px", "fontSize": "13px"}),
                        html.P([html.Strong("Cv:"), " Comercialización - Costo variable por kWh"], style={"marginBottom": "6px", "fontSize": "13px"}),
                        html.P([html.Strong("PR:"), " Pérdidas Reconocidas - Energía adicional para cubrir pérdidas"], style={"marginBottom": "6px", "fontSize": "13px"}),
                        html.P([html.Strong("R:"), " Restricciones - Costo por redespacho operativo"], style={"marginBottom": "6px", "fontSize": "13px"})
                    ], style={
                        "color": "#333333",
                        "lineHeight": "1.5",
                        "marginBottom": "15px"
                    }),
                    
                    html.P([
                        html.Em("Nota: "),
                        "El CU calculado/aplicado y su evolución se documentan en informes CREG/SSPD. ",
                        "Haz clic en cada sector del mapa para ver detalles específicos y fórmulas de cada componente."
                    ], style={"fontSize": "12px", "color": "#666", "fontStyle": "italic", "marginBottom": "15px"}),
                    
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
                            "marginTop": "10px",
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
