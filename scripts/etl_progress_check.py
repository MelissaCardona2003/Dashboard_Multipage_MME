import sqlite3
from datetime import datetime, timedelta
import os

# Detectar ruta de la base de datos
db_candidates = [
    os.path.join(os.path.dirname(__file__), '../portal_energetico.db'),
    os.path.join(os.path.dirname(__file__), 'portal_energetico.db'),
    os.path.join(os.getcwd(), 'portal_energetico.db'),
]
db_path = None
for path in db_candidates:
    if os.path.exists(os.path.abspath(path)):
        db_path = os.path.abspath(path)
        break
if not db_path:
    raise FileNotFoundError('No se encontró portal_energetico.db en rutas conocidas.')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Rango esperado
fecha_inicio = datetime(2020, 1, 1).date()
fecha_fin = datetime(2025, 11, 24).date()
total_dias = (fecha_fin - fecha_inicio).days + 1

metricas_objetivo = [
    ('VoluUtilDiarEner', 'Embalses - Volumen Útil Diario'),
    ('CapaUtilDiarEner', 'Embalses - Capacidad Útil Diario'),
    ('AporEner', 'Aportes de Ríos'),
    ('AporEnerMediHist', 'Aportes Medios Históricos'),
    ('PorcApor', 'Porcentaje de Aportes'),
    ('Gene', 'Generación'),
    ('AporCaudal', 'Aportes de Caudal'),
    ('DemaCome', 'Demanda Comercial'),
    ('DemaReal', 'Demanda Real'),
    ('DemaNoAtenProg', 'Demanda No Atendida Programada'),
]

print(f"{'Métrica':30} | {'Días con datos':>14} | {'Desde':>10} | {'Hasta':>10} | {'Estado':>10}")
print('-'*90)
for metrica, descripcion in metricas_objetivo:
    cursor.execute('SELECT COUNT(DISTINCT fecha), MIN(fecha), MAX(fecha) FROM metrics WHERE metrica=?', (metrica,))
    d, f1, f2 = cursor.fetchone()
    estado = '✅ Completa' if d == total_dias else ('⚠️ Incompleta' if d > 0 else '❌ Vacía')
    print(f"{descripcion:30} | {d:14} | {f1 or '-':10} | {f2 or '-':10} | {estado:>10}")
    if d > 0 and d < total_dias:
        # Mostrar algunos días faltantes
        cursor.execute('SELECT DISTINCT fecha FROM metrics WHERE metrica=?', (metrica,))
        dias_metric = set(r[0] for r in cursor.fetchall())
        all_days = set((fecha_inicio + timedelta(days=i)).isoformat() for i in range(total_dias))
        faltantes = sorted(list(all_days - dias_metric))
        print(f"   Ejemplo días faltantes: {faltantes[:3]} ... total: {len(faltantes)}")
    elif d == 0:
        print(f"   Sin datos para esta métrica.")

conn.close()
