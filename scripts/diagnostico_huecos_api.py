
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import sqlite3
from datetime import datetime, timedelta
from utils._xm import get_objetoAPI
from utils.db_manager import upsert_metrics_bulk
import pandas as pd

# Configuración de métricas a analizar
METRICAS = [
    ('Gene', 'Sistema'),
    ('DemaCome', 'Sistema'),
    ('DemaReal', 'Sistema'),
    ('AporCaudal', 'Sistema'),
    ('DemaNoAtenProg', 'Sistema'),
]

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'portal_energetico.db')
fecha_inicio = datetime(2020, 1, 1).date()
fecha_fin = datetime(2025, 11, 24).date()
total_dias = (fecha_fin - fecha_inicio).days + 1
all_days = set((fecha_inicio + timedelta(days=i)).isoformat() for i in range(total_dias))

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
api = get_objetoAPI()

for metrica, entidad in METRICAS:
    cursor.execute('SELECT DISTINCT fecha FROM metrics WHERE metrica=?', (metrica,))
    dias_metric = set(r[0] for r in cursor.fetchall())
    faltantes = sorted(list(all_days - dias_metric))
    if not faltantes:
        print(f"✅ {metrica}: Sin huecos.")
        continue
    print(f"🔎 {metrica}: {len(faltantes)} días faltantes. Probando descarga...")
    for dia in faltantes:
        try:
            df = api.request_data(metrica, entidad, dia, dia)
            if df is not None and not df.empty:
                print(f"   [OK] {dia}: API devolvió {len(df)} registros. Insertando...")
                # Insertar en BD
                metrics_data = []
                for _, row in df.iterrows():
                    fecha = row['Date'] if isinstance(row['Date'], str) else row['Date'].strftime('%Y-%m-%d')
                    valor = row.get('Value', 0)
                    recurso_val = row.get('Name') or row.get('Values_code') or '_SISTEMA_'
                    metrics_data.append((fecha, metrica, entidad, recurso_val, valor, 'GWh'))
                upsert_metrics_bulk(metrics_data)
            else:
                print(f"   [NO DATA] {dia}: API no devolvió datos.")
        except Exception as e:
            print(f"   [ERROR] {dia}: {e}")

conn.close()
print("\nDiagnóstico de huecos completado.")
