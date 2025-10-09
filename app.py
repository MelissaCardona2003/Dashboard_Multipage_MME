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
    from pages import index, metricas, demanda
    from pages import generacion_solar, generacion_eolica, generacion_biomasa, generacion_hidraulica
    from pages import generacion_hidraulica_hidrologia, generacion, generacion_termica
    from pages import transmision, transmision_lineas, transmision_subestaciones, transmision_congestion
    from pages import distribucion, distribucion_calidad, distribucion_red, distribucion_transformadores
    from pages import perdidas, perdidas_tecnicas, perdidas_comerciales, perdidas_indicadores
    from pages import restricciones, restricciones_operativas, restricciones_ambientales, restricciones_regulatorias
    from pages import demanda_historica, demanda_patrones, demanda_pronosticos
    print("✅ Todas las páginas importadas correctamente")
except Exception as e:
    print(f"❌ Error importando páginas: {e}")
    import traceback
    traceback.print_exc()

# Layout principal de la aplicación usando page_container
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    page_container
])

if __name__ == "__main__":
    import os
    port = int(os.environ.get('PORT', 8050))
    print(f"🚀 Iniciando servidor Dash en puerto {port}...")
    print("📍 La aplicación estará disponible en: https://vps-0c525a03.vps.ovh.ca/")
    app.run(debug=False, host='0.0.0.0', port=port)

# Exponer el servidor WSGI para Gunicorn
server = app.server