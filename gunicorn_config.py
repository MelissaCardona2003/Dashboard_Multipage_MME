# Configuración de Gunicorn para Dashboard MME
bind = "0.0.0.0:8050"
workers = 2
timeout = 120
keepalive = 5
max_requests = 1000
preload_app = False
