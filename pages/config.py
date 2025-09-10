"""
Configuración para el dashboard Dash
"""

# Archivos de datos
DATA_FILES = {
    "granjas_actualizadas": "pages/Base granjas_actualizada.csv",
    "granjas_original": "pages/Base granjas.csv",
    "comunidades": "pages/Base comunidades energéticas.csv",
    "estadisticas": "pages/estadisticas_distancias.csv",
    "resumen_detallado": "pages/resumen_detallado_proximidades.csv"
}

# Configuración de colores y estilos - INSTITUCIONAL MINISTERIO
COLORS = {
    'primary': '#1E3A8A',        # Azul institucional oscuro
    'secondary': '#065F46',      # Verde institucional
    'accent': '#B45309',         # Naranja institucional (energía)
    'success': '#047857',        # Verde éxito
    'warning': '#D97706',        # Naranja advertencia
    'info': '#0369A1',           # Azul información
    'bg_main': '#FAFAFA',        # Fondo principal gris muy claro
    'bg_card': '#FFFFFF',        # Cards blancos puros
    'bg_sidebar': '#F8FAFC',     # Sidebar gris muy claro
    'bg_header': '#F9FAFB',      # Header gris casi blanco
    'bg_gradient_start': '#F8FAFC',  # Inicio gradiente sutil
    'bg_gradient_end': '#F1F5F9',    # Fin gradiente sutil
    'text_primary': '#1F2937',   # Texto principal oscuro
    'text_secondary': '#6B7280', # Texto secundario
    'text_light': '#FFFFFF',     # Texto claro
    'text_muted': '#9CA3AF',     # Texto atenuado
    'border': '#E5E7EB',         # Bordes suaves
    'border_dark': '#D1D5DB',    # Bordes más definidos
    'shadow': 'rgba(0, 0, 0, 0.05)', # Sombras muy suaves
    'overlay': 'rgba(255, 255, 255, 0.98)' # Overlay casi blanco
}

# Configuración del mapa
MAP_CONFIG = {
    'center_lat': 4.5,
    'center_lon': -74.0,
    'zoom': 6,
    'max_zoom': 15,
    'min_zoom': 4
}
