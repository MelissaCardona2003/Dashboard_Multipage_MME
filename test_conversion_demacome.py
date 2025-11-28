#!/usr/bin/env python3
"""
Test específico para conversión horas_a_diario de DemaCome/Agente
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pydataxm.pydataxm import ReadDB
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

# Importar la función de conversión del ETL
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'etl'))
from etl_xm_to_sqlite import convertir_unidades

def test_conversion():
    print("="*70)
    print("🧪 TEST: Conversión horas_a_diario para DemaCome/Agente")
    print("="*70)
    
    obj_api = ReadDB()
    
    # Probar con un rango que sabemos que funciona
    print("\n📡 Consultando API: DemaCome/Agente (2020-01-08 a 2020-01-10)")
    df = obj_api.request_data(
        'DemaCome',
        'Agente',
        start_date='2020-01-08',
        end_date='2020-01-10'
    )
    
    print(f"\n📊 ANTES de conversión:")
    print(f"   - Shape: {df.shape}")
    print(f"   - Columnas: {list(df.columns)}")
    print(f"   - Tiene 'Value': {'Value' in df.columns}")
    
    # Verificar columnas horarias
    hour_cols = [col for col in df.columns if 'Hour' in col and col.startswith('Values_Hour')]
    print(f"   - Columnas horarias: {len(hour_cols)}")
    
    if len(hour_cols) > 0:
        print(f"\n📋 Primera fila (valores horarios):")
        primera_fila = df.iloc[0]
        suma_manual = 0
        for col in hour_cols:
            val = primera_fila[col]
            if pd.notna(val):
                suma_manual += float(val)
        print(f"   - Agente: {primera_fila['Values_code']}")
        print(f"   - Fecha: {primera_fila['Date']}")
        print(f"   - Suma manual 24 horas: {suma_manual:.2f} kWh = {suma_manual/1e6:.4f} GWh")
    
    # APLICAR CONVERSIÓN
    print(f"\n🔄 Aplicando conversión 'horas_a_diario'...")
    df_convertido = convertir_unidades(df.copy(), 'DemaCome', 'horas_a_diario')
    
    print(f"\n📊 DESPUÉS de conversión:")
    print(f"   - Shape: {df_convertido.shape}")
    print(f"   - Columnas: {list(df_convertido.columns)}")
    print(f"   - Tiene 'Value': {'Value' in df_convertido.columns}")
    
    if 'Value' in df_convertido.columns:
        print(f"   - Valores 'Value' creados: {df_convertido['Value'].notna().sum()}/{len(df_convertido)}")
        print(f"   - Rango valores: {df_convertido['Value'].min():.4f} - {df_convertido['Value'].max():.4f} GWh")
        print(f"   - Promedio: {df_convertido['Value'].mean():.4f} GWh")
        
        print(f"\n📋 Primeras 5 filas con Value:")
        print(df_convertido[['Date', 'Values_code', 'Value']].head(5))
        
        # Verificar si hay valores cero o muy bajos
        valores_bajos = (df_convertido['Value'] < 0.001).sum()
        if valores_bajos > 0:
            print(f"\n⚠️  Atención: {valores_bajos} filas con valores < 0.001 GWh (serán filtradas en ETL)")
            print(f"   Ejemplos:")
            print(df_convertido[df_convertido['Value'] < 0.001][['Date', 'Values_code', 'Value']].head(10))
    else:
        print(f"\n❌ ERROR: No se creó la columna 'Value'")
        print(f"   Esto causará que el ETL falle")
    
    print(f"\n{'='*70}")
    if 'Value' in df_convertido.columns and df_convertido['Value'].notna().sum() > 0:
        print("✅ CONVERSIÓN EXITOSA")
    else:
        print("❌ CONVERSIÓN FALLÓ")
    print(f"{'='*70}")

if __name__ == "__main__":
    test_conversion()
