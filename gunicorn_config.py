# Configuración OPTIMIZADA de Gunicorn para Dashboard MME
bind = "0.0.0.0:8050"

# OPTIMIZADO: 4 workers para mejor rendimiento en servidor multi-core
workers = 4

# OPTIMIZADO: gthread permite manejar múltiples requests concurrentes por worker
worker_class = "gthread"
threads = 2  # 2 threads por worker = 8 threads totales (4 workers × 2)

# OPTIMIZADO: Timeout extendido para queries largas a API XM (5 minutos)
timeout = 300

# OPTIMIZADO: Keepalive para conexiones persistentes
keepalive = 5

# OPTIMIZADO: Límites de requests con jitter para reciclar workers (prevenir memory leaks)
max_requests = 1000
max_requests_jitter = 50

# OPTIMIZADO: preload_app activado para carga única de la app
# Esto evita que cada worker ejecute callbacks múltiples veces al inicio
# Los callbacks Dash funcionan perfectamente con preload_app=True
preload_app = True

# Logging mejorado
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = "info"
