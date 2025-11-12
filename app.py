# -*- coding: utf-8 -*-
import sys
import io

# Configurar salida estándar con UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from dash import Dash, html, dcc
import dash_bootstrap_components as dbc
import logging
import os
from datetime import date, timedelta

# Configurar logging ANTES de cualquier otra cosa
from utils.logger import setup_logger, configure_root_logger

# Configurar logger raíz
configure_root_logger()

# Logger para este módulo
logger = setup_logger(__name__)

# Reducir verbosidad de otros loggers
logging.getLogger('werkzeug').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('dash').setLevel(logging.INFO)

# Banner de inicio
logger.info("=" * 70)
logger.info("🚀 INICIANDO PORTAL ENERGÉTICO MME")
logger.info(f"Ambiente: {os.getenv('DASH_ENV', 'development')}")
logger.info("=" * 70)

# Limpiar cache corrupto al inicio (ANTES de crear la app)
logger.info("🧹 Verificando integridad del cache...")
try:
    from utils.cache_manager import cleanup_corrupted_cache
    cleanup_corrupted_cache()
    logger.info("✅ Cache verificado correctamente")
except Exception as e:
    logger.warning(f"Error al limpiar cache: {e}")

# ⚡ OPTIMIZACIÓN: Pre-cargar datos comunes para acelerar primera carga
logger.info("⚡ Pre-cargando datos comunes...")
try:
    from utils._xm import get_objetoAPI
    
    objetoAPI = get_objetoAPI()
    if objetoAPI:
        logger.info("📊 API XM disponible - sistema de cache listo")
    else:
        logger.warning("⚠️ API XM no disponible - usando solo cache histórico")
except Exception as e:
    logger.warning(f"Error en pre-carga: {e}")

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
    from dash import page_registry
    
    port = int(os.environ.get('PORT', 8050))
    
    # Inicializar ReadDB ANTES de arrancar el servidor
    logger.info("🔧 Inicializando conexión a API XM...")
    from utils._xm import get_objetoAPI
    api_xm = get_objetoAPI()
    if api_xm:
        logger.info("✅ API XM inicializada correctamente")
    else:
        logger.warning("⚠️ API XM no disponible - se usarán datos en caché")
    
    # Información de páginas registradas
    logger.info(f"📄 Páginas registradas: {len(page_registry)}")
    for path, page_info in page_registry.items():
        logger.debug(f"  - {path}: {page_info.get('name', 'Sin nombre')}")
    
    logger.info("=" * 70)
    logger.info(f"🚀 Iniciando servidor Dash en puerto {port}")
    logger.info("📍 La aplicación estará disponible en:")
    logger.info(f"   - http://localhost:{port}")
    logger.info(f"   - http://127.0.0.1:{port}")
    logger.info(f"   - http://192.168.1.34:{port}")
    logger.info("=" * 70)
    
    try:
        app.run(debug=False, host='0.0.0.0', port=port)
    except Exception as e:
        logger.critical(f"❌ Error al iniciar servidor: {e}", exc_info=True)

# Exponer el servidor WSGI para Gunicorn
server = app.server