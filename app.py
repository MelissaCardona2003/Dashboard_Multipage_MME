# -*- coding: utf-8 -*-
import sys
import io

# Configurar salida estándar con UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from dash import Dash, html, dcc
import dash_bootstrap_components as dbc

# Crear la aplicación Dash con soporte multi-página
app = Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Poppins:wght@300;400;500;600;700;800&display=swap",
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"
    ],
    external_scripts=[
        "/assets/hover-effects.js"
    ],
    suppress_callback_exceptions=True
)

# El servidor para Gunicorn
server = app.server

# AHORA importar y registrar las páginas manualmente
import pages.index_simple_working
import pages.generacion_fuentes_unificado

# Importar page_container DESPUÉS de registrar páginas
from dash import page_container

# Layout principal con page_container
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    page_container
])

if __name__ == "__main__":
    import os
    port = int(os.environ.get('PORT', 8050))
    print(f"🚀 Iniciando servidor Dash en puerto {port}...")
    print("📍 La aplicación estará disponible en:")
    print(f"   - http://localhost:{port}")
    print(f"   - http://127.0.0.1:{port}")
    try:
        app.run(debug=False, host='0.0.0.0', port=port)
    except Exception as e:
        print(f"❌ Error al iniciar servidor: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import os
    port = int(os.environ.get('PORT', 8050))
    print(f"🚀 Iniciando servidor Dash en puerto {port}...")
    print("📍 La aplicación estará disponible en:")
    print(f"   - http://localhost:{port}")
    print(f"   - http://127.0.0.1:{port}")
    print(f"   - http://192.168.1.34:{port}")
    try:
        app.run(debug=False, host='0.0.0.0', port=port)
    except Exception as e:
        print(f"❌ Error al iniciar servidor: {e}")
        import traceback
        traceback.print_exc()
        input("Presiona Enter para cerrar...")

# Exponer el servidor WSGI para Gunicorn
server = app.server