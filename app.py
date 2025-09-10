
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

# Importar las páginas DESPUÉS de crear la aplicación
try:
    from pages import index, coordenadas, metricas, hidrologia, demanda
    from pages import generacion_solar, generacion_eolica, generacion_biomasa, generacion_hidraulica
    print("✅ Todas las páginas importadas correctamente")
except Exception as e:
    print(f"❌ Error importando páginas: {e}")

# Layout principal de la aplicación usando page_container
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    page_container
])

if __name__ == "__main__":
    print("🚀 Iniciando servidor Dash...")
    print("📍 La aplicación estará disponible en: http://127.0.0.1:8056/")
    app.run(debug=True, port=8056)
