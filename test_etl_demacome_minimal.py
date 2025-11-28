#!/usr/bin/env python3
"""
ETL mínimo para debugging de DemaCome/Agente
Procesa solo un rango pequeño con logging detallado
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pydataxm.pydataxm import ReadDB
from datetime import datetime
import logging
from utils import db_manager
from etl.etl_xm_to_sqlite import poblar_metrica

# Configurar logging detallado
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

def test_etl_demacome():
    print("="*70)
    print("🧪 ETL DEBUG: DemaCome/Agente")
    print("="*70)
    
    # Conectar a API
    obj_api = ReadDB()
    
    # Configuración de DemaCome/Agente
    config = {
        'metric': 'DemaCome',
        'entity': 'Agente',
        'conversion': 'horas_a_diario',
        'dias_history': 1826,
        'batch_size': 7
    }
    
    print(f"\n📋 Configuración:")
    for key, val in config.items():
        print(f"   - {key}: {val}")
    
    # Probar el rango que falla
    print(f"\n🔄 Ejecutando poblar_metrica()...")
    print(f"   Rango: 2020-01-08 a 2020-01-14 (el que falla en ETL)")
    
    try:
        registros = poblar_metrica(
            obj_api,
            config,
            usar_timeout=False,
            fecha_inicio_custom='2020-01-08',
            fecha_fin_custom='2020-01-14'
        )
        
        print(f"\n✅ Resultado: {registros} registros insertados")
        
        # Verificar en base de datos
        import sqlite3
        conn = sqlite3.connect("portal_energetico.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM metrics
            WHERE metrica = 'DemaCome' AND entidad = 'Agente'
            AND fecha BETWEEN '2020-01-08' AND '2020-01-14'
        """)
        
        total_bd = cursor.fetchone()[0]
        print(f"✅ Registros en BD para ese rango: {total_bd}")
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ ERROR:")
        print(f"   Tipo: {type(e).__name__}")
        print(f"   Mensaje: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_etl_demacome()
