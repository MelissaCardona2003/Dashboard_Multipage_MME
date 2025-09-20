#!/usr/bin/env python3

from dash import Dash, html, dcc, page_container
import dash_bootstrap_components as dbc

# Crear la aplicación Dash
app = Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Poppins:wght@300;400;500;600;700;800&display=swap",
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"
    ],
    suppress_callback_exceptions=True
)

# Layout simple para prueba
app.layout = html.Div([
    html.H1("Test Server"),
    html.P("Puerto correcto: 9000")
])

if __name__ == "__main__":
    print("🚀 Iniciando servidor de prueba Dash...")
    print("📍 La aplicación estará disponible en: http://0.0.0.0:9000/")
    app.run_server(debug=False, host='0.0.0.0', port=9000)