"""
Módulo de utilidades para manejo de API XM con fallback
"""

import pandas as pd
from datetime import datetime, timedelta
import json
import os

def create_fallback_data():
    """
    Crea datos de ejemplo cuando la API XM no está disponible
    """
    # Fechas de ejemplo (últimos 30 días)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Datos de ejemplo para hidrología
    rios_ejemplo = [
        'MAGDALENA', 'CAUCA', 'ATRATO', 'SINÚ', 'AMAZONAS',
        'ORINOCO', 'BAUDÓ', 'PATÍA', 'SAN JORGE', 'CESAR'
    ]
    
    regiones_ejemplo = [
        'ANTIOQUIA', 'CUNDINAMARCA', 'VALLE DEL CAUCA', 
        'SANTANDER', 'BOYACÁ', 'TOLIMA', 'HUILA', 'CALDAS'
    ]
    
    # Generar datos de ejemplo
    data = []
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    for date in date_range:
        for rio in rios_ejemplo:
            for region in regiones_ejemplo:
                # Valores aleatorios pero realistas
                import random
                caudal = random.uniform(50, 500)  # m³/s
                energia = random.uniform(10, 100)  # GWh
                volumen_pct = random.uniform(30, 95)  # %
                
                data.append({
                    'Fecha': date.strftime('%Y-%m-%d'),
                    'Rio': rio,
                    'Region': region,
                    'AporCaudal_m3s': caudal,
                    'CapaUtilDiarEner_GWh': energia,
                    'Volumen_Porcentaje': volumen_pct
                })
    
    return pd.DataFrame(data)

def create_api_status_message():
    """
    Crea un mensaje de estado para mostrar cuando la API no está disponible
    """
    return {
        'status': 'offline',
        'message': 'API XM temporalmente no disponible',
        'details': 'El servidor de XM (servapibi.xm.com.co) no está respondiendo. Mostrando datos de ejemplo.',
        'suggestion': 'Intente recargar la página en unos minutos.',
        'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

def save_api_status(status_info):
    """
    Guarda el estado de la API en un archivo temporal
    """
    try:
        status_file = '/tmp/xm_api_status.json'
        with open(status_file, 'w') as f:
            json.dump(status_info, f, indent=2)
    except Exception as e:
        print(f"Error guardando estado API: {e}")

def load_api_status():
    """
    Carga el estado guardado de la API
    """
    try:
        status_file = '/tmp/xm_api_status.json'
        if os.path.exists(status_file):
            with open(status_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error cargando estado API: {e}")
    return None