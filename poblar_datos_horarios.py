#!/usr/bin/env python3
"""
Script para poblar la tabla metrics_hourly con datos de DemaCome y DemaReal
Procesa datos existentes en API XM para el rango de fechas configurado.
"""

import sys
import logging
from datetime import datetime, timedelta
from etl.etl_xm_to_sqlite import poblar_metrica
from utils import db_manager
from pydataxm.pydataxm import ReadDB

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def poblar_horarios_demanda():
    """Pobla datos horarios de DemaCome y DemaReal para últimos 7 días."""
    
    print("=" * 80)
    print("🚀 POBLACIÓN DE DATOS HORARIOS - DemaCome y DemaReal")
    print("=" * 80)
    
    # Crear objeto API XM
    print("\n📡 Conectando con API XM...")
    obj_api = ReadDB()
    
    # Configuraciones para las métricas
    configs = [
        {
            'metric': 'DemaCome',
            'entity': 'Agente',
            'conversion': 'horas_a_diario',
            'dias_history': 7,
            'batch_size': 7
        },
        {
            'metric': 'DemaReal',
            'entity': 'Agente',
            'conversion': 'horas_a_diario',
            'dias_history': 7,
            'batch_size': 7
        }
    ]
    
    # Procesar cada métrica
    for config in configs:
        metric = config['metric']
        entity = config['entity']
        
        print("\n" + "=" * 80)
        print(f"📊 Poblando {metric} ({entity})")
        print("=" * 80)
        
        try:
            registros = poblar_metrica(obj_api, config, usar_timeout=True, timeout_seconds=120)
            print(f"✅ {metric} completado: {registros} registros agregados")
        except Exception as e:
            print(f"❌ Error en {metric}: {e}")
            import traceback
            traceback.print_exc()
    
    # Verificar resultados
    print("\n" + "=" * 80)
    print("🔍 VERIFICACIÓN DE DATOS POBLADOS")
    print("=" * 80)
    
    import sqlite3
    import pandas as pd
    
    conn = sqlite3.connect('portal_energetico.db')
    
    # Contar registros por métrica
    query = """
    SELECT metrica, COUNT(*) as registros, COUNT(DISTINCT fecha) as dias_unicos
    FROM metrics_hourly
    GROUP BY metrica
    """
    df = pd.read_sql_query(query, conn)
    
    print("\n📊 Registros poblados:")
    print(df.to_string(index=False))
    
    # Mostrar ejemplo de una fecha reciente
    query_ejemplo = """
    SELECT metrica, fecha, hora, valor_mwh
    FROM metrics_hourly
    WHERE fecha = (SELECT MAX(fecha) FROM metrics_hourly)
    AND hora IN (1, 12, 24)
    ORDER BY metrica, hora
    LIMIT 10
    """
    df_ejemplo = pd.read_sql_query(query_ejemplo, conn)
    
    if not df_ejemplo.empty:
        print("\n🔍 Ejemplo de últimos datos (horas 1, 12, 24):")
        print(df_ejemplo.to_string(index=False))
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ POBLACIÓN COMPLETADA")
    print("=" * 80)

if __name__ == '__main__':
    try:
        poblar_horarios_demanda()
    except KeyboardInterrupt:
        print("\n⚠️  Proceso interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
