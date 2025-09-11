# Configuración de Gunicorn para Dashboard MME
bind = "127.0.0.1:8056"
workers = 2
timeout = 120
keepalive = 5
max_requests = 1000
preload_app = False
