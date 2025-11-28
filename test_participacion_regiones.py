#!/usr/bin/env python3
"""
Test script para verificar el cálculo de participación por regiones
"""
import sys
sys.path.insert(0, '/home/admonctrlxm/server')

from datetime import date
import pandas as pd
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('test')

# Import utils directly
from utils._xm import obtener_datos_inteligente
from utils.config import REGIONES_COLOMBIA

def test_participacion():
    """Probar cálculo de participación"""
    print("="*80)
    print("TEST: Calculando participación por regiones")
    print("="*80)
    
    # Usar fecha actual
    fecha_actual = date.today().strftime('%Y-%m-%d')
    print(f"\n📅 Fecha de consulta: {fecha_actual}")
    
    # Obtener datos de capacidad (CapaUtilDiarEner)
    df_capacidad, warning = obtener_datos_inteligente('CapaUtilDiarEner', 'Embalse', fecha_actual, fecha_actual)
    
    if df_capacidad is None or df_capacidad.empty:
        print("\n❌ ERROR: No se obtuvieron datos de capacidad")
        return
    
    print(f"\n✅ Datos de capacidad obtenidos: {len(df_capacidad)} registros")
    
    # Agrupar por región
    regiones_resumen = []
    
    for region_nombre, embalses_region in REGIONES_COLOMBIA.items():
        df_region = df_capacidad[df_capacidad['Name'].isin(embalses_region)].copy()
        
        if df_region.empty:
            continue
        
        # Convertir Wh a GWh y calcular total
        df_region['Capacidad_GWh'] = df_region['Value'] / 1_000_000
        total_region_gwh = df_region['Capacidad_GWh'].sum()
        
        regiones_resumen.append({
            'Región': region_nombre,
            'Total (GWh)': total_region_gwh
        })
    
    regiones_totales = pd.DataFrame(regiones_resumen)
    
    if regiones_totales.empty:
        print("\n❌ ERROR: No se obtuvieron datos de regiones")
        return
    
    print(f"\n✅ Datos obtenidos: {len(regiones_totales)} regiones")
    print(f"\n📊 Columnas disponibles:")
    for col in regiones_totales.columns:
        print(f"   - {col}")
    
    print(f"\n📈 Datos de regiones:")
    print(regiones_totales.to_string(index=False))
    
    # Verificar si existe la columna 'Participación (%)'
    if 'Participación (%)' in regiones_totales.columns:
        print(f"\n✅ Columna 'Participación (%)' encontrada")
        print(f"\n📊 Valores de participación:")
        for _, row in regiones_totales.iterrows():
            region = row['Región']
            participacion = row['Participación (%)']
            total = row['Total (GWh)']
            print(f"   {region:20s}: {participacion:6.2f}% (Capacidad: {total:.2f} GWh)")
        
        # Calcular suma de participaciones
        suma_participacion = regiones_totales['Participación (%)'].sum()
        print(f"\n📊 Suma de participaciones: {suma_participacion:.2f}%")
        
        if abs(suma_participacion - 100.0) < 0.01:
            print("✅ La suma de participaciones es correcta (100%)")
        else:
            print(f"⚠️ La suma de participaciones NO es 100% (diferencia: {suma_participacion - 100.0:.2f}%)")
    else:
        print(f"\n❌ ERROR: Columna 'Participación (%)' NO encontrada")
        print(f"\nColumnas disponibles: {list(regiones_totales.columns)}")
    
    # Calcular totales
    total_capacidad_nacional = regiones_totales['Total (GWh)'].sum()
    print(f"\n🔢 Total capacidad nacional: {total_capacidad_nacional:.2f} GWh")

if __name__ == '__main__':
    test_participacion()
