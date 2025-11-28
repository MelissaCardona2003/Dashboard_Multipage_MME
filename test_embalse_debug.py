#!/usr/bin/env python3
"""
Test script para investigar el error "string indices must be integers"
en las métricas VoluUtilDiarEner/Embalse y CapaUtilDiarEner/Embalse
"""

import sys
from datetime import datetime, timedelta
import traceback

# Agregar el directorio raíz al path
sys.path.insert(0, '/home/admonctrlxm/server')

from pydataxm import pydataxm

def test_metric_api(metric_name, entity_name, test_dates):
    """
    Prueba la API XM para una métrica específica y muestra la estructura de datos
    """
    print(f"\n{'='*80}")
    print(f"🔍 PROBANDO: {metric_name}/{entity_name}")
    print(f"{'='*80}\n")
    
    objective_function = pydataxm.ReadDB()
    
    for start_date, end_date in test_dates:
        print(f"\n📅 Rango: {start_date} → {end_date}")
        print(f"-" * 80)
        
        try:
            # Intentar obtener datos
            df = objective_function.request_data(
                metric_name,
                entity_name,
                start_date,
                end_date
            )
            
            if df is None:
                print(f"⚠️  API devolvió None")
                continue
                
            if df.empty:
                print(f"⚠️  DataFrame vacío")
                continue
            
            # Mostrar información detallada
            print(f"✅ Datos recibidos: {len(df)} filas")
            print(f"\n📊 Columnas: {list(df.columns)}")
            print(f"📊 Tipos de datos:\n{df.dtypes}")
            
            # Mostrar primeras filas
            print(f"\n📄 Primeras 3 filas:")
            print(df.head(3).to_string())
            
            # Verificar estructura de cada fila
            print(f"\n🔬 Análisis de primera fila:")
            primera_fila = df.iloc[0]
            for col in df.columns:
                valor = primera_fila[col]
                print(f"  - {col}: tipo={type(valor).__name__}, valor={valor}")
            
            # Si hay columna 'Values_code' o similar, mostrar valores únicos
            for col in df.columns:
                if 'code' in col.lower() or 'recurso' in col.lower() or 'embalse' in col.lower():
                    unicos = df[col].unique()
                    print(f"\n🏷️  Valores únicos en '{col}': {len(unicos)}")
                    print(f"   Primeros 5: {list(unicos[:5])}")
            
        except Exception as e:
            print(f"❌ ERROR: {type(e).__name__}: {str(e)}")
            print(f"\n📋 Traceback completo:")
            traceback.print_exc()

def main():
    print("\n" + "="*80)
    print("🔍 DIAGNÓSTICO DE MÉTRICAS DE EMBALSE")
    print("="*80)
    
    # Definir rangos de prueba
    # 1. Últimos días (donde SÍ hay datos según SQLite)
    fecha_fin = datetime(2025, 11, 24)
    fecha_inicio_reciente = fecha_fin - timedelta(days=7)
    
    # 2. Rango histórico (donde NO hay datos según SQLite)
    fecha_inicio_historico = datetime(2020, 1, 1)
    fecha_fin_historico = datetime(2020, 1, 7)
    
    test_dates = [
        (fecha_inicio_reciente.strftime('%Y-%m-%d'), fecha_fin.strftime('%Y-%m-%d')),
        (fecha_inicio_historico.strftime('%Y-%m-%d'), fecha_fin_historico.strftime('%Y-%m-%d'))
    ]
    
    # Probar VoluUtilDiarEner/Embalse
    test_metric_api('VoluUtilDiarEner', 'Embalse', test_dates)
    
    # Probar CapaUtilDiarEner/Embalse
    test_metric_api('CapaUtilDiarEner', 'Embalse', test_dates)
    
    print("\n" + "="*80)
    print("✅ DIAGNÓSTICO COMPLETADO")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
