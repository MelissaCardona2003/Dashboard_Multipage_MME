#!/usr/bin/env python
"""
Script optimizado para ejecutar el dashboard como servicio del sistema
"""
import sys
import os
sys.path.insert(0, '/home/ubuntu/Dashboard_Multipage_MME')

# Cambiar al directorio de la aplicación
os.chdir('/home/ubuntu/Dashboard_Multipage_MME')

# Importar y ejecutar la aplicación
import app

if __name__ == '__main__':
    print("🚀 Iniciando Dashboard MME como servicio...")
    app.app.run_server(
        host='0.0.0.0',
        port=8000,
        debug=False,
        dev_tools_hot_reload=False,
        dev_tools_ui=False,
        dev_tools_props_check=False
    )
