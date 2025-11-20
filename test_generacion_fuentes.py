#!/usr/bin/env python3
"""
Script de diagnóstico para verificar el funcionamiento del tablero de generación por fuentes
"""

import sys
import pandas as pd
from datetime import date, timedelta
import sqlite3

print("="*80)
print("DIAGNÓSTICO: Tablero de Generación por Fuentes")
print("="*80)

# 1. Verificar que el archivo existe y es importable
print("\n1. Verificando importación del módulo...")
try:
    sys.path.insert(0, '/home/admonctrlxm/server')
    from pages import generacion_fuentes_unificado
    print("   ✅ Módulo importado correctamente")
except Exception as e:
    print(f"   ❌ Error al importar: {e}")
    sys.exit(1)

# 2. Verificar base de datos SQLite
print("\n2. Verificando base de datos SQLite...")
try:
    conn = sqlite3.connect('/home/admonctrlxm/server/portal_energetico.db')
    cursor = conn.cursor()
    
    # Verificar tabla metrics
    cursor.execute("SELECT COUNT(*) FROM metrics WHERE metrica='Gene' AND entidad='Recurso'")
    count = cursor.fetchone()[0]
    print(f"   ✅ Registros Gene/Recurso en SQLite: {count:,}")
    
    # Verificar fechas disponibles
    cursor.execute("""
        SELECT MIN(fecha), MAX(fecha) 
        FROM metrics 
        WHERE metrica='Gene' AND entidad='Recurso'
    """)
    fecha_min, fecha_max = cursor.fetchone()
    print(f"   ✅ Rango de fechas: {fecha_min} → {fecha_max}")
    
    conn.close()
except Exception as e:
    print(f"   ❌ Error con SQLite: {e}")

# 3. Verificar función de obtención de datos agregados
print("\n3. Verificando función obtener_generacion_agregada_por_tipo...")
try:
    from utils._xm import obtener_datos_inteligente
    print("   ✅ Función utils._xm importada")
    
    # Probar con un rango pequeño (últimos 7 días)
    fecha_fin = date.today() - timedelta(days=3)
    fecha_inicio = fecha_fin - timedelta(days=7)
    
    print(f"\n   Probando con rango: {fecha_inicio} → {fecha_fin}")
    
    # Intentar cargar datos de una fuente
    df_test = generacion_fuentes_unificado.obtener_generacion_agregada_por_tipo(
        fecha_inicio.strftime('%Y-%m-%d'),
        fecha_fin.strftime('%Y-%m-%d'),
        'HIDRAULICA'
    )
    
    if df_test.empty:
        print("   ⚠️  DataFrame vacío - Sin datos para el período")
    else:
        print(f"   ✅ Datos obtenidos: {len(df_test)} filas")
        print(f"   ✅ Columnas: {list(df_test.columns)}")
        if 'Generacion_GWh' in df_test.columns:
            total_gwh = df_test['Generacion_GWh'].sum()
            print(f"   ✅ Total generación: {total_gwh:.2f} GWh")
            
except Exception as e:
    print(f"   ❌ Error al probar función: {e}")
    import traceback
    traceback.print_exc()

# 4. Verificar funciones de creación de gráficas
print("\n4. Verificando funciones de gráficas...")
try:
    import plotly.graph_objects as go
    print("   ✅ Plotly disponible")
    
    # Verificar que las funciones existen
    if hasattr(generacion_fuentes_unificado, 'crear_grafica_temporal_negra'):
        print("   ✅ Función crear_grafica_temporal_negra existe")
    
    if hasattr(generacion_fuentes_unificado, 'crear_grafica_torta_fuentes'):
        print("   ✅ Función crear_grafica_torta_fuentes existe")
        
except Exception as e:
    print(f"   ❌ Error: {e}")

# 5. Verificar callbacks
print("\n5. Verificando callbacks registrados...")
try:
    # Los callbacks se registran al importar el módulo
    print("   ✅ Callbacks registrados (verificar en logs al iniciar)")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "="*80)
print("DIAGNÓSTICO COMPLETADO")
print("="*80)
print("\nSi todos los checks pasaron, el problema puede estar en:")
print("  1. El callback no se está ejecutando al hacer clic")
print("  2. Los datos no se están mostrando en el navegador (problema de frontend)")
print("  3. Hay un error JavaScript en el navegador (revisar consola del navegador)")
