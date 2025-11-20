#!/usr/bin/env python3
"""
Script de diagnóstico completo para identificar problemas en el dashboard
"""
import sys
sys.path.insert(0, '/home/admonctrlxm/server')

from datetime import date, timedelta
from utils._xm import obtener_datos_desde_sqlite
import sqlite3

print("=" * 80)
print("DIAGNÓSTICO COMPLETO DEL DASHBOARD")
print("=" * 80)

# 1. VERIFICAR DATOS DE FICHAS
print("\n📊 1. DATOS DE LAS FICHAS EN GENERACION.PY")
print("-" * 80)

fecha_fin = date.today() - timedelta(days=1)

# Reservas Hídricas
df_vol, fecha_vol = obtener_datos_desde_sqlite('VoluUtilDiarEner', 'Embalse', fecha_fin)
df_cap, fecha_cap = obtener_datos_desde_sqlite('CapaUtilDiarEner', 'Embalse', fecha_fin)

if df_vol is not None and df_cap is not None:
    col = 'Value' if 'Value' in df_vol.columns else 'Values_code'
    vol_gwh = df_vol[col].sum()
    cap_gwh = df_cap[col].sum()
    reserva_pct = (vol_gwh / cap_gwh * 100) if cap_gwh > 0 else 0
    print(f"✅ Reservas Hídricas: {reserva_pct:.2f}% ({vol_gwh:.2f} GWh / {cap_gwh:.2f} GWh)")
    print(f"   Fecha: {fecha_vol}")
else:
    print("❌ Reservas Hídricas: Sin datos")

# Generación SIN
df_gen, fecha_gen = obtener_datos_desde_sqlite('Gene', 'Sistema', fecha_fin)
if df_gen is not None and 'Value' in df_gen.columns:
    gen_gwh = df_gen['Value'].sum()
    print(f"✅ Generación SIN: {gen_gwh:.2f} GWh")
    print(f"   Fecha: {fecha_gen}")
else:
    print("❌ Generación SIN: Sin datos")

# 2. VERIFICAR DATOS EN SQLITE
print("\n📦 2. ESTADO DE LA BASE DE DATOS SQLite")
print("-" * 80)

conn = sqlite3.connect('/home/admonctrlxm/server/portal_energetico.db')
cursor = conn.cursor()

# Total de registros
cursor.execute("SELECT COUNT(*) FROM metrics")
total = cursor.fetchone()[0]
print(f"Total registros: {total}")

# Registros por métrica
cursor.execute("""
    SELECT metrica, entidad, COUNT(*) as cnt, 
           MIN(fecha) as fecha_min, MAX(fecha) as fecha_max
    FROM metrics 
    GROUP BY metrica, entidad
    ORDER BY metrica, entidad
""")
metricas = cursor.fetchall()

print("\nMétricas disponibles:")
for metrica, entidad, cnt, fecha_min, fecha_max in metricas:
    print(f"  • {metrica}/{entidad}: {cnt} registros ({fecha_min} → {fecha_max})")

# Verificar datos de distribución
print("\n📍 3. DATOS DE DISTRIBUCIÓN (DemaCome, DemaReal)")
print("-" * 80)

cursor.execute("""
    SELECT metrica, fecha, COUNT(*) as cnt, SUM(valor_gwh) as total_gwh
    FROM metrics 
    WHERE metrica IN ('DemaCome', 'DemaReal')
    AND fecha >= date('now', '-7 days')
    GROUP BY metrica, fecha
    ORDER BY fecha DESC, metrica
""")
distribucion = cursor.fetchall()

if distribucion:
    print("Últimos 7 días:")
    for metrica, fecha, cnt, total_gwh in distribucion:
        print(f"  {fecha}: {metrica} = {total_gwh:.2f} GWh ({cnt} agentes)")
else:
    print("❌ No hay datos recientes de DemaCome/DemaReal")

conn.close()

# 4. VERIFICAR SERVICIO
print("\n🔧 4. ESTADO DEL SERVICIO")
print("-" * 80)

import subprocess
try:
    result = subprocess.run(
        ['systemctl', 'is-active', 'dashboard-mme'],
        capture_output=True,
        text=True
    )
    if result.stdout.strip() == 'active':
        print("✅ Servicio dashboard-mme: ACTIVO")
    else:
        print(f"⚠️ Servicio dashboard-mme: {result.stdout.strip()}")
except Exception as e:
    print(f"❌ Error verificando servicio: {e}")

# 5. VERIFICAR ARCHIVOS PYTHON
print("\n📝 5. VERIFICACIÓN DE ARCHIVOS CLAVE")
print("-" * 80)

import os
archivos = [
    'pages/generacion.py',
    'pages/generacion_hidraulica_hidrologia.py',
    'pages/generacion_fuentes_unificado.py',
    'pages/distribucion_demanda_unificado.py',
    'utils/_xm.py',
    'etl/etl_xm_to_sqlite.py'
]

for archivo in archivos:
    ruta = f'/home/admonctrlxm/server/{archivo}'
    if os.path.exists(ruta):
        stat = os.stat(ruta)
        from datetime import datetime
        mtime = datetime.fromtimestamp(stat.st_mtime)
        print(f"✅ {archivo}")
        print(f"   Última modificación: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print(f"❌ {archivo}: NO EXISTE")

# 6. RECOMENDACIONES
print("\n💡 6. RECOMENDACIONES")
print("-" * 80)
print("1. Limpia el caché del navegador:")
print("   Chrome/Firefox: Ctrl+Shift+R (Windows/Linux) o Cmd+Shift+R (Mac)")
print()
print("2. Verifica que estás viendo la URL correcta:")
print("   http://localhost:8050 (o la URL configurada)")
print()
print("3. Revisa los logs del servicio:")
print("   sudo journalctl -u dashboard-mme.service -f")
print()
print("4. Compara con datos de XM:")
print("   https://www.xm.com.co/consumo/demanda-de-energia-sin")
print()
print("=" * 80)
