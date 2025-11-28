#!/usr/bin/env python3
"""
Test para reproducir el error cuando se selecciona una región específica
"""
import sys
sys.path.insert(0, '/home/admonctrlxm/server')

from datetime import datetime, timedelta
import pandas as pd
from utils._xm import obtener_datos_inteligente
import traceback

print("="*80)
print("🧪 TEST: Simulando selección de región 'Antioquia'")
print("="*80)

try:
    # Paso 1: Obtener datos reales para la región
    fecha_inicio = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    fecha_fin = datetime.now().strftime('%Y-%m-%d')
    region = "Antioquia"
    
    print(f"\n1️⃣ Obteniendo datos de AporEner para región {region}...")
    data_real, _ = obtener_datos_inteligente('AporEner', 'Rio', fecha_inicio, fecha_fin)
    
    if data_real is None or data_real.empty:
        print("❌ No hay datos reales")
        sys.exit(1)
    
    # Filtrar por región (simulando el callback)
    from pages.generacion_hidraulica_hidrologia import get_rio_region_dict
    rio_region = get_rio_region_dict()
    
    print(f"✅ Diccionario río-región cargado: {len(rio_region)} entradas")
    
    # Aplicar mapeo
    data_real['Name_Upper'] = data_real['Name'].str.strip().str.upper()
    data_real['Region'] = data_real['Name_Upper'].map(rio_region)
    
    # Filtrar por región
    region_normalized = region.strip().title()
    data_filtered = data_real[data_real['Region'] == region_normalized]
    
    print(f"✅ Datos filtrados para {region_normalized}: {len(data_filtered)} registros")
    
    if data_filtered.empty:
        print(f"❌ No hay datos para la región {region_normalized}")
        sys.exit(1)
    
    # Paso 2: Agrupar por fecha (como hace create_total_timeline_chart)
    daily_totals = data_filtered.groupby('Date')['Value'].sum().reset_index()
    daily_totals = daily_totals.sort_values('Date')
    
    print(f"✅ Totales diarios: {len(daily_totals)} días")
    print(f"   Tipo de columna Date: {type(daily_totals['Date'].iloc[0])}")
    
    # Paso 3: Obtener fechas min/max con conversión segura
    fecha_min = daily_totals['Date'].min()
    fecha_max = daily_totals['Date'].max()
    
    print(f"\n2️⃣ Convirtiendo fechas...")
    print(f"   fecha_min tipo: {type(fecha_min)}, valor: {fecha_min}")
    print(f"   fecha_max tipo: {type(fecha_max)}, valor: {fecha_max}")
    
    if hasattr(fecha_min, 'strftime'):
        fecha_inicio_hist = fecha_min.strftime('%Y-%m-%d')
    else:
        fecha_inicio_hist = str(fecha_min)
        
    if hasattr(fecha_max, 'strftime'):
        fecha_fin_hist = fecha_max.strftime('%Y-%m-%d')
    else:
        fecha_fin_hist = str(fecha_max)
    
    print(f"✅ Fechas convertidas: {fecha_inicio_hist} a {fecha_fin_hist}")
    
    # Paso 4: Obtener media histórica
    print(f"\n3️⃣ Obteniendo AporEnerMediHist...")
    media_hist_data, _ = obtener_datos_inteligente('AporEnerMediHist', 'Rio', fecha_inicio_hist, fecha_fin_hist)
    
    if media_hist_data is None or media_hist_data.empty:
        print("❌ No hay datos de media histórica")
        sys.exit(1)
    
    print(f"✅ Datos de media histórica: {len(media_hist_data)} registros")
    
    # Paso 5: Filtrar Name NULL
    media_hist_data = media_hist_data[media_hist_data['Name'].notna()]
    print(f"✅ Después de filtrar NULL: {len(media_hist_data)} registros")
    
    # Paso 6: Aplicar filtro de región
    media_hist_data['Name_Upper'] = media_hist_data['Name'].str.strip().str.upper()
    media_hist_data['Region'] = media_hist_data['Name_Upper'].map(rio_region)
    
    print(f"\n4️⃣ Filtrando media histórica por región {region_normalized}...")
    print(f"   Antes: {len(media_hist_data)} registros")
    
    media_hist_filtered = media_hist_data[media_hist_data['Region'] == region_normalized]
    print(f"   Después: {len(media_hist_filtered)} registros")
    
    if media_hist_filtered.empty:
        print(f"❌ No hay datos históricos para {region_normalized}")
        sys.exit(1)
    
    # Paso 7: Agrupar por fecha
    print(f"\n5️⃣ Agrupando media histórica por fecha...")
    media_hist_totals = media_hist_filtered.groupby('Date')['Value'].sum().reset_index()
    media_hist_totals = media_hist_totals.sort_values('Date')
    
    print(f"✅ Media histórica agregada: {len(media_hist_totals)} días")
    print(f"   Tipo de Value: {media_hist_totals['Value'].dtype}")
    
    # Paso 8: Combinar datos (el punto crítico)
    print(f"\n6️⃣ Combinando datos reales e históricos...")
    merged_data = daily_totals.merge(
        media_hist_totals,
        on='Date',
        how='inner',
        suffixes=('_real', '_hist')
    )
    
    print(f"✅ Datos combinados: {len(merged_data)} fechas")
    print(f"   Columnas: {list(merged_data.columns)}")
    print(f"   Tipos de datos:")
    print(f"     Value_real: {merged_data['Value_real'].dtype}")
    print(f"     Value_hist: {merged_data['Value_hist'].dtype}")
    
    # Paso 9: Calcular porcentaje (aquí puede estar el problema)
    print(f"\n7️⃣ Calculando porcentajes...")
    merged_data['porcentaje'] = (merged_data['Value_real'] / merged_data['Value_hist']) * 100
    print(f"   Tipo de porcentaje: {merged_data['porcentaje'].dtype}")
    
    # Paso 10: Probar el loop que causa el error
    print(f"\n8️⃣ Probando loop de formateo (donde ocurre el error)...")
    
    for i in range(min(3, len(merged_data) - 1)):  # Solo primeros 3 para prueba
        print(f"\n   Iteración {i}:")
        
        # Obtener valores
        porcentaje_raw = merged_data.iloc[i]['porcentaje']
        valor_real_raw = merged_data.iloc[i]['Value_real']
        valor_hist_raw = merged_data.iloc[i]['Value_hist']
        
        print(f"     Valores raw: porcentaje={porcentaje_raw} (tipo={type(porcentaje_raw)})")
        print(f"                  valor_real={valor_real_raw} (tipo={type(valor_real_raw)})")
        print(f"                  valor_hist={valor_hist_raw} (tipo={type(valor_hist_raw)})")
        
        # Convertir a float
        porcentaje = float(porcentaje_raw)
        valor_real = float(valor_real_raw)
        valor_hist = float(valor_hist_raw)
        variacion = float(porcentaje - 100)
        signo = '+' if variacion >= 0 else ''
        
        print(f"     Después de float(): porcentaje={porcentaje}, variacion={variacion}")
        
        # Intentar formatear (aquí debería fallar si hay problema)
        try:
            texto = f"Variación: {signo}{variacion:.1f}%"
            print(f"     ✅ Formato exitoso: {texto}")
        except Exception as e:
            print(f"     ❌ ERROR en formato: {e}")
            raise
    
    print(f"\n" + "="*80)
    print(f"✅✅✅ TODO FUNCIONÓ CORRECTAMENTE ✅✅✅")
    print(f"="*80)
    print(f"\nSi el test pasó pero el dashboard falla, puede ser:")
    print(f"  1. Caché del navegador (Ctrl+Shift+Delete)")
    print(f"  2. El servidor no se recargó (verificar PID)")
    print(f"  3. Hay otro lugar en el código con el mismo error")
    
except Exception as e:
    print(f"\n❌❌❌ ERROR ENCONTRADO ❌❌❌")
    print(f"="*80)
    print(f"Error: {e}")
    print(f"Tipo: {type(e).__name__}")
    print(f"\nTraceback completo:")
    traceback.print_exc()
    print(f"="*80)

print("\n")
