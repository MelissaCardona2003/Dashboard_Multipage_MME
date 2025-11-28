#!/usr/bin/env python3
"""
Script de verificación completa de tableros de Generación e Hidrología
"""
import sys
sys.path.insert(0, '/home/admonctrlxm/server')

from datetime import date, timedelta
import pandas as pd

print("="*80)
print("VERIFICACIÓN DE TABLEROS - GENERACIÓN E HIDROLOGÍA")
print("="*80)

# Test 1: Verificar SQLite está funcionando
print("\n" + "="*80)
print("TEST 1: Verificar acceso a base de datos SQLite")
print("="*80)

try:
    from utils.db_manager import get_metric_data
    fecha_test = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    df_test = get_metric_data('VoluUtilDiarEner', 'Embalse', fecha_test, fecha_test)
    
    if df_test is not None and not df_test.empty:
        print(f"✅ SQLite funciona correctamente")
        print(f"   - Registros obtenidos: {len(df_test)}")
        print(f"   - Columnas: {list(df_test.columns)}")
        print(f"   - Suma de valores: {df_test['valor_gwh'].sum():.2f} GWh")
    else:
        print("❌ SQLite no devolvió datos")
except Exception as e:
    print(f"❌ Error al acceder a SQLite: {e}")

# Test 2: Verificar obtener_datos_inteligente
print("\n" + "="*80)
print("TEST 2: Verificar obtener_datos_inteligente (Hidrología)")
print("="*80)

try:
    from utils._xm import obtener_datos_inteligente
    fecha_test = date.today().strftime('%Y-%m-%d')
    
    df_vol, warning = obtener_datos_inteligente('VoluUtilDiarEner', 'Embalse', fecha_test, fecha_test)
    
    if df_vol is not None and not df_vol.empty:
        print(f"✅ obtener_datos_inteligente funciona correctamente")
        print(f"   - Fuente: {'SQLite' if warning is None else 'API XM'}")
        print(f"   - Registros: {len(df_vol)}")
        print(f"   - Suma: {df_vol['Value'].sum():.2f} GWh")
        
        # Verificar que los valores estén en GWh (no en Wh)
        valor_promedio = df_vol['Value'].mean()
        if valor_promedio > 1000:
            print(f"   ✅ Valores en rango GWh correcto (promedio: {valor_promedio:.2f} GWh)")
        elif valor_promedio < 0.001:
            print(f"   ❌ PROBLEMA: Valores muy pequeños (promedio: {valor_promedio:.10f} GWh)")
            print(f"      Posible conversión duplicada Wh→GWh")
        else:
            print(f"   ⚠️ Valores inusuales (promedio: {valor_promedio:.2f} GWh)")
    else:
        print("❌ obtener_datos_inteligente no devolvió datos")
        if warning:
            print(f"   Advertencia: {warning}")
except Exception as e:
    print(f"❌ Error en obtener_datos_inteligente: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Verificar métricas de Generación
print("\n" + "="*80)
print("TEST 3: Verificar métricas del tablero de Generación")
print("="*80)

try:
    from utils.db_manager import get_metric_data
    fecha_fin = date.today() - timedelta(days=1)
    
    # Buscar datos válidos (hasta 5 días atrás)
    reserva_encontrada = False
    for dias_atras in range(6):
        fecha_busqueda = (fecha_fin - timedelta(days=dias_atras)).strftime('%Y-%m-%d')
        
        df_vol = get_metric_data('VoluUtilDiarEner', 'Embalse', fecha_busqueda, fecha_busqueda)
        df_cap = get_metric_data('CapaUtilDiarEner', 'Embalse', fecha_busqueda, fecha_busqueda)
        
        if df_vol is not None and not df_vol.empty and df_cap is not None and not df_cap.empty:
            vol_total_gwh = df_vol['valor_gwh'].sum()
            cap_total_gwh = df_cap['valor_gwh'].sum()
            
            if vol_total_gwh >= 10000:
                reserva_pct = round((vol_total_gwh / cap_total_gwh) * 100, 2)
                print(f"✅ Reservas Hídricas encontradas (fecha: {fecha_busqueda})")
                print(f"   - Volumen: {vol_total_gwh:,.2f} GWh")
                print(f"   - Capacidad: {cap_total_gwh:,.2f} GWh")
                print(f"   - Porcentaje: {reserva_pct:.2f}%")
                reserva_encontrada = True
                break
            else:
                print(f"   ⚠️ Datos incompletos en {fecha_busqueda}: {vol_total_gwh:.2f} GWh")
    
    if not reserva_encontrada:
        print("❌ No se encontraron datos válidos de reservas")
        
except Exception as e:
    print(f"❌ Error al verificar métricas de Generación: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Verificar cálculo de participación (Hidrología)
print("\n" + "="*80)
print("TEST 4: Verificar cálculo de participación por regiones")
print("="*80)

try:
    from utils._xm import obtener_datos_inteligente
    fecha_test = date.today().strftime('%Y-%m-%d')
    
    # Obtener datos de capacidad
    df_cap, _ = obtener_datos_inteligente('CapaUtilDiarEner', 'Embalse', fecha_test, fecha_test)
    
    if df_cap is not None and not df_cap.empty:
        # Obtener información de regiones
        yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
        today = date.today().strftime('%Y-%m-%d')
        embalses_info, _ = obtener_datos_inteligente('ListadoEmbalses','Sistema', yesterday, today)
        
        if embalses_info is not None and not embalses_info.empty:
            embalses_info['Values_Name'] = embalses_info['Values_Name'].str.strip().str.upper()
            embalses_info['Values_HydroRegion'] = embalses_info['Values_HydroRegion'].str.strip().str.title()
            
            # Mapear regiones
            embalse_region_dict = dict(zip(embalses_info['Values_Name'], embalses_info['Values_HydroRegion']))
            df_cap['Region'] = df_cap['Name'].map(embalse_region_dict)
            
            # Calcular por región
            regiones = df_cap.groupby('Region')['Value'].sum()
            total_nacional = regiones.sum()
            
            print("✅ Cálculo de participación por regiones:")
            print(f"\n   Total Nacional: {total_nacional:,.2f} GWh\n")
            
            for region, capacidad in regiones.items():
                if region and str(region).lower() not in ['sin nacional', 'rios estimados', '']:
                    participacion = (capacidad / total_nacional * 100) if total_nacional > 0 else 0
                    print(f"   {region:15s}: {capacidad:8,.2f} GWh ({participacion:5.2f}%)")
            
            suma_participacion = sum([(cap / total_nacional * 100) for cap in regiones.values() if total_nacional > 0])
            print(f"\n   Suma de participaciones: {suma_participacion:.2f}%")
            
            if abs(suma_participacion - 100.0) < 0.1:
                print("   ✅ Suma correcta (100%)")
            else:
                print(f"   ⚠️ Suma incorrecta (debería ser 100%)")
        else:
            print("❌ No se pudo obtener información de embalses")
    else:
        print("❌ No se pudieron obtener datos de capacidad")
        
except Exception as e:
    print(f"❌ Error al verificar participación: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("VERIFICACIÓN COMPLETADA")
print("="*80)
