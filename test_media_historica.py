#!/usr/bin/env python3
"""
Script de prueba para diagnosticar el problema de la línea de media histórica
"""
import sys
sys.path.insert(0, '/home/admonctrlxm/server')

from datetime import datetime, timedelta
import pandas as pd
from utils._xm import obtener_datos_inteligente

print("="*80)
print("🧪 TEST: Simulando create_total_timeline_chart")
print("="*80)

# Paso 1: Obtener datos reales (simulando AporEner)
fecha_inicio = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
fecha_fin = datetime.now().strftime('%Y-%m-%d')

print(f"\n1️⃣ Obteniendo datos reales de AporEner...")
data_real, _ = obtener_datos_inteligente('AporEner', 'Rio', fecha_inicio, fecha_fin)

if data_real is None or data_real.empty:
    print("❌ No hay datos reales")
    sys.exit(1)

print(f"✅ Datos reales: {len(data_real)} registros")

# Agrupar por fecha
daily_totals = data_real.groupby('Date')['Value'].sum().reset_index()
daily_totals = daily_totals.sort_values('Date')
print(f"✅ Totales diarios: {len(daily_totals)} días")

# Paso 2: Obtener media histórica
print(f"\n2️⃣ Obteniendo AporEnerMediHist...")
fecha_inicio_hist = daily_totals['Date'].min().strftime('%Y-%m-%d')
fecha_fin_hist = daily_totals['Date'].max().strftime('%Y-%m-%d')

print(f"📅 Rango: {fecha_inicio_hist} a {fecha_fin_hist}")

media_hist_data, warning = obtener_datos_inteligente('AporEnerMediHist', 'Rio', fecha_inicio_hist, fecha_fin_hist)

if media_hist_data is None or media_hist_data.empty:
    print("❌ No se recibieron datos de AporEnerMediHist")
    sys.exit(1)

print(f"✅ Datos de media histórica: {len(media_hist_data)} registros")
print(f"📋 Columnas: {list(media_hist_data.columns)}")

# Paso 3: Filtrar Name NULL
if 'Name' in media_hist_data.columns:
    nulls_antes = media_hist_data['Name'].isna().sum()
    print(f"\n3️⃣ Filtrando Name=NULL...")
    print(f"   Antes: {len(media_hist_data)} registros ({nulls_antes} con NULL)")
    
    media_hist_data = media_hist_data[media_hist_data['Name'].notna()]
    print(f"   Después: {len(media_hist_data)} registros")

# Paso 4: Agrupar por fecha
print(f"\n4️⃣ Agrupando por fecha...")
if not media_hist_data.empty:
    try:
        media_hist_totals = media_hist_data.groupby('Date')['Value'].sum().reset_index()
        media_hist_totals = media_hist_totals.sort_values('Date')
        print(f"✅ Media histórica agregada: {len(media_hist_totals)} días")
        print(f"✅ tiene_media = True")
        
        # Paso 5: Combinar datos
        print(f"\n5️⃣ Combinando datos reales e históricos...")
        merged_data = daily_totals.merge(
            media_hist_totals,
            on='Date',
            how='inner',
            suffixes=('_real', '_hist')
        )
        print(f"✅ Datos combinados: {len(merged_data)} fechas coincidentes")
        
        if len(merged_data) > 0:
            print(f"\n✅✅✅ TODO CORRECTO - LA LÍNEA DEBERÍA APARECER ✅✅✅")
            print(f"\nPrimeros 5 registros combinados:")
            print(merged_data[['Date', 'Value_real', 'Value_hist']].head().to_string(index=False))
        else:
            print(f"\n❌ NO HAY FECHAS COINCIDENTES entre datos reales e históricos")
            print(f"   Rango real: {daily_totals['Date'].min()} a {daily_totals['Date'].max()}")
            print(f"   Rango hist: {media_hist_totals['Date'].min()} a {media_hist_totals['Date'].max()}")
            
    except Exception as e:
        print(f"\n❌ ERROR en agrupación/combinación: {e}")
        import traceback
        traceback.print_exc()
else:
    print(f"❌ media_hist_data está vacío después de filtrar")

print("\n" + "="*80)
