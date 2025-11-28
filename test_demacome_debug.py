#!/usr/bin/env python3
"""
Script de debugging para DemaCome/Agente
Prueba diferentes rangos de fechas y analiza las respuestas
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pydataxm.pydataxm import ReadDB
import pandas as pd
from datetime import datetime, date, timedelta
import traceback

def test_demacome_agente():
    """Probar DemaCome/Agente con diferentes rangos"""
    
    print("="*70)
    print("🧪 DEBUG: DemaCome/Agente")
    print("="*70)
    
    obj_api = ReadDB()
    
    # Rangos de prueba
    tests = [
        ("2020-01-01", "2020-01-07", "Primer rango que funcionó en ETL"),
        ("2020-01-08", "2020-01-14", "Rango que falló en ETL"),
        ("2020-11-18", "2020-11-24", "Inicio del rango faltante"),
        ("2021-01-01", "2021-01-07", "Rango de 2021"),
        ("2024-01-01", "2024-01-07", "Rango de 2024"),
        ("2025-11-16", "2025-11-21", "Rango reciente que funcionó"),
    ]
    
    for start_date, end_date, descripcion in tests:
        print(f"\n{'='*70}")
        print(f"📅 Probando: {start_date} → {end_date}")
        print(f"   Descripción: {descripcion}")
        print(f"{'='*70}")
        
        try:
            df = obj_api.request_data(
                'DemaCome',
                'Agente',
                start_date=start_date,
                end_date=end_date
            )
            
            if df is None:
                print("❌ API devolvió None")
                continue
                
            if df.empty:
                print("⚠️  API devolvió DataFrame vacío")
                continue
            
            print(f"✅ Datos recibidos: {len(df)} filas")
            print(f"\n📊 Información del DataFrame:")
            print(f"   - Columnas: {list(df.columns)}")
            print(f"   - Shape: {df.shape}")
            
            # Verificar columnas importantes
            if 'Date' in df.columns:
                fechas_unicas = df['Date'].nunique()
                print(f"   - Fechas únicas: {fechas_unicas}")
            
            if 'Values_code' in df.columns:
                agentes_unicos = df['Values_code'].nunique()
                print(f"   - Agentes únicos: {agentes_unicos}")
                print(f"   - Ejemplos de agentes: {list(df['Values_code'].unique()[:5])}")
            
            # Verificar columnas horarias
            hour_cols = [col for col in df.columns if 'Hour' in col and col.startswith('Values_Hour')]
            print(f"   - Columnas horarias encontradas: {len(hour_cols)}")
            
            if len(hour_cols) > 0:
                print(f"   - Primera columna horaria: {hour_cols[0]}")
                print(f"   - Última columna horaria: {hour_cols[-1]}")
            
            # Verificar si hay valores
            if 'Value' in df.columns:
                print(f"   - Columna 'Value' encontrada")
                print(f"   - Valores no nulos: {df['Value'].notna().sum()}")
                if df['Value'].notna().sum() > 0:
                    print(f"   - Rango valores: {df['Value'].min():.2f} - {df['Value'].max():.2f}")
            
            # Mostrar primeras filas
            print(f"\n📋 Primeras 3 filas:")
            print(df.head(3).to_string())
            
            # Verificar si hay problemas de formato
            print(f"\n🔍 Verificaciones:")
            
            # Check 1: ¿Hay valores nulos en columnas críticas?
            if 'Date' in df.columns:
                nulls_date = df['Date'].isna().sum()
                print(f"   - Valores nulos en 'Date': {nulls_date}")
            
            if 'Values_code' in df.columns:
                nulls_code = df['Values_code'].isna().sum()
                print(f"   - Valores nulos en 'Values_code': {nulls_code}")
            
            # Check 2: ¿Formato de fechas correcto?
            if 'Date' in df.columns and len(df) > 0:
                primera_fecha = str(df['Date'].iloc[0])
                print(f"   - Formato primera fecha: '{primera_fecha}' (tipo: {type(df['Date'].iloc[0])})")
            
            # Check 3: ¿Valores horarios tienen datos?
            if len(hour_cols) == 24:
                total_valores_horarios = 0
                for col in hour_cols:
                    total_valores_horarios += df[col].notna().sum()
                print(f"   - Total valores horarios no nulos: {total_valores_horarios}")
                
                # Probar sumar horas
                primera_fila = df.iloc[0]
                suma_horas = 0
                for col in hour_cols:
                    val = primera_fila[col]
                    if pd.notna(val):
                        suma_horas += float(val)
                print(f"   - Suma 24 horas (primera fila): {suma_horas:.2f} kWh = {suma_horas/1e6:.4f} GWh")
            
            print(f"\n✅ Test completado exitosamente")
            
        except Exception as e:
            print(f"\n❌ ERROR:")
            print(f"   Tipo: {type(e).__name__}")
            print(f"   Mensaje: {str(e)}")
            print(f"\n📋 Traceback completo:")
            traceback.print_exc()

if __name__ == "__main__":
    test_demacome_agente()
