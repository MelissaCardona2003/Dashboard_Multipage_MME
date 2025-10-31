#!/usr/bin/env python3
"""
Script para debuggear la estructura de datos de XM
"""
import sys
import os
from datetime import date, timedelta
import pandas as pd

# Agregar el directorio actual al path para importar utils
sys.path.append('/home/admonctrlxm/server')

from utils._xm import fetch_metric_data

def main():
    print("🔍 Debuggeando estructura de datos XM...")
    
    fecha_fin = date.today() - timedelta(days=1)
    fecha_inicio = fecha_fin
    
    print(f"📅 Fecha: {fecha_inicio}")
    
    # Obtener datos de generación por recurso
    print("\n1️⃣ Obteniendo Gene/Recurso...")
    df_gene = fetch_metric_data('Gene', 'Recurso', fecha_inicio, fecha_fin)
    
    if df_gene is not None and not df_gene.empty:
        print(f"✅ Datos obtenidos: {len(df_gene)} registros")
        print(f"📊 Columnas: {list(df_gene.columns)}")
        print(f"📊 Tipos de datos:")
        for col in df_gene.columns:
            print(f"  {col}: {df_gene[col].dtype}")
        
        print(f"\n📋 Primeras 5 filas:")
        print(df_gene.head())
        
        # Verificar columnas de valores únicos
        for col in df_gene.columns:
            if df_gene[col].dtype == 'object':
                valores_unicos = df_gene[col].unique()[:10]  # Primeros 10
                print(f"\n🔍 {col} - Valores únicos (muestra): {valores_unicos}")
    else:
        print("❌ No se obtuvieron datos")
    
    # También probar otros tipos de métricas
    print("\n2️⃣ Probando Gene/Planta...")
    df_planta = fetch_metric_data('Gene', 'Planta', fecha_inicio, fecha_fin)
    
    if df_planta is not None and not df_planta.empty:
        print(f"✅ Gene/Planta: {len(df_planta)} registros")
        print(f"📊 Columnas Planta: {list(df_planta.columns)}")
    else:
        print("❌ No hay datos Gene/Planta")

if __name__ == "__main__":
    main()