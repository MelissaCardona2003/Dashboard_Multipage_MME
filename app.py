
from dash import Dash
import dash_bootstrap_components as dbc

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

if __name__ == "__main__":
    print("🚀 Iniciando servidor Dash...")
    print("📍 La aplicación estará disponible en: http://127.0.0.1:8055/")
    app.run(debug=True, port=8055)
