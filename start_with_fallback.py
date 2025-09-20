#!/usr/bin/env python3
"""
Script para iniciar el dashboard con manejo de errores de conectividad.
"""

import os
import sys
import subprocess
import time
from datetime import datetime

def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def check_connectivity():
    """Verifica conectividad básica de internet"""
    try:
        import urllib.request
        urllib.request.urlopen('https://www.google.com', timeout=5)
        return True
    except:
        return False

def start_dashboard():
    """Inicia el dashboard con reintentos"""
    max_retries = 3
    retry_delay = 10
    
    for attempt in range(max_retries):
        log_message(f"Intento {attempt + 1}/{max_retries} - Iniciando dashboard...")
        
        try:
            # Activar entorno virtual e iniciar
            env = os.environ.copy()
            env['VIRTUAL_ENV'] = '/home/ubuntu/Dashboard_Multipage_MME/dashboard_env'
            env['PATH'] = f"/home/ubuntu/Dashboard_Multipage_MME/dashboard_env/bin:{env['PATH']}"
            
            # Cambiar al directorio correcto
            os.chdir('/home/ubuntu/Dashboard_Multipage_MME')
            
            # Verificar conectividad
            if not check_connectivity():
                log_message("⚠️ Sin conectividad a internet - intentando iniciar con datos locales...")
            
            # Iniciar aplicación
            log_message("🚀 Iniciando aplicación Dash...")
            process = subprocess.run([
                '/home/ubuntu/Dashboard_Multipage_MME/dashboard_env/bin/python', 
                'app.py'
            ], env=env, cwd='/home/ubuntu/Dashboard_Multipage_MME')
            
            if process.returncode == 0:
                log_message("✅ Dashboard iniciado exitosamente")
                return True
                
        except Exception as e:
            log_message(f"❌ Error en intento {attempt + 1}: {e}")
            
        if attempt < max_retries - 1:
            log_message(f"⏳ Esperando {retry_delay} segundos antes del siguiente intento...")
            time.sleep(retry_delay)
    
    log_message("❌ No se pudo iniciar el dashboard después de todos los intentos")
    return False

if __name__ == "__main__":
    log_message("🔄 Iniciando script de arranque del dashboard...")
    success = start_dashboard()
    sys.exit(0 if success else 1)