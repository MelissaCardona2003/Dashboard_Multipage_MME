#!/usr/bin/env python3
"""
Script de prueba para el dashboard de Comercialización
Verifica que las funciones principales funcionan correctamente
"""

import sys
import pandas as pd
from datetime import date, timedelta

# Agregar path del proyecto
sys.path.insert(0, '/home/admonctrlxm/server')

from utils._xm import fetch_metric_data

def obtener_precio_bolsa(fecha_inicio, fecha_fin):
    """Obtener datos de Precio Bolsa Nacional (copia de la función del dashboard)"""
    try:
        df = fetch_metric_data('PrecBolsNaci', 'Sistema', fecha_inicio, fecha_fin)
        
        if df is None or df.empty:
            return pd.DataFrame()
        
        hour_cols = [c for c in df.columns if 'Hour' in c]
        df['Promedio_Diario'] = df[hour_cols].mean(axis=1)
        df['Metrica'] = 'Precio Bolsa Nacional'
        
        df_result = pd.DataFrame({
            'Date': pd.to_datetime(df['Date']),
            'Value': df['Promedio_Diario'],
            'Metrica': df['Metrica']
        })
        
        df_result['Datos_Horarios'] = df[['Date'] + hour_cols].to_dict('records')
        
        return df_result
    except Exception as e:
        print(f"Error: {e}")
        return pd.DataFrame()

def obtener_precio_escasez(fecha_inicio, fecha_fin):
    """Obtener datos de Precio Escasez (copia de la función del dashboard)"""
    try:
        df = fetch_metric_data('PrecEsca', 'Sistema', fecha_inicio, fecha_fin)
        
        if df is None or df.empty:
            return pd.DataFrame()
        
        df['Date'] = pd.to_datetime(df['Date'])
        df['Metrica'] = 'Precio Escasez'
        
        return df[['Date', 'Value', 'Metrica']]
    except Exception as e:
        print(f"Error: {e}")
        return pd.DataFrame()

def test_fetch_direct():
    """Test 1: Verificar fetch directo de API"""
    print("=" * 60)
    print("TEST 1: Fetch directo de API XM")
    print("=" * 60)
    
    fecha_fin = date.today() - timedelta(days=1)
    fecha_inicio = fecha_fin - timedelta(days=7)
    
    print(f"\n📅 Rango: {fecha_inicio} a {fecha_fin}")
    
    # Test PrecBolsNaci
    print("\n1️⃣ Obteniendo PrecBolsNaci...")
    df_bolsa = fetch_metric_data('PrecBolsNaci', 'Sistema', fecha_inicio, fecha_fin)
    
    if df_bolsa is not None and not df_bolsa.empty:
        print(f"   ✅ Datos obtenidos: {len(df_bolsa)} días")
        print(f"   📊 Columnas: {list(df_bolsa.columns)[:5]}... (total: {len(df_bolsa.columns)})")
        
        # Verificar columnas horarias
        hour_cols = [c for c in df_bolsa.columns if 'Hour' in c]
        print(f"   ⏰ Columnas horarias encontradas: {len(hour_cols)}")
        
        if len(hour_cols) == 24:
            print("   ✅ Formato correcto: 24 columnas horarias")
        else:
            print(f"   ⚠️ Advertencia: Se esperaban 24 columnas, encontradas {len(hour_cols)}")
    else:
        print("   ❌ No se obtuvieron datos")
        return False
    
    # Test PrecEsca
    print("\n2️⃣ Obteniendo PrecEsca...")
    df_escasez = fetch_metric_data('PrecEsca', 'Sistema', fecha_inicio, fecha_fin)
    
    if df_escasez is not None and not df_escasez.empty:
        print(f"   ✅ Datos obtenidos: {len(df_escasez)} días")
        print(f"   📊 Columnas: {list(df_escasez.columns)}")
    else:
        print("   ❌ No se obtuvieron datos")
        return False
    
    print("\n✅ TEST 1 PASSED")
    return True

def test_functions():
    """Test 2: Verificar funciones del dashboard"""
    print("\n" + "=" * 60)
    print("TEST 2: Funciones del dashboard")
    print("=" * 60)
    
    fecha_fin = date.today() - timedelta(days=1)
    fecha_inicio = fecha_fin - timedelta(days=7)
    
    print(f"\n📅 Rango: {fecha_inicio} a {fecha_fin}")
    
    # Test obtener_precio_bolsa
    print("\n1️⃣ Testing obtener_precio_bolsa()...")
    df_bolsa = obtener_precio_bolsa(fecha_inicio, fecha_fin)
    
    if not df_bolsa.empty:
        print(f"   ✅ Datos obtenidos: {len(df_bolsa)} días")
        print(f"   📊 Columnas: {list(df_bolsa.columns)}")
        
        # Verificar columnas requeridas
        required = ['Date', 'Value', 'Metrica', 'Datos_Horarios']
        missing = [col for col in required if col not in df_bolsa.columns]
        
        if not missing:
            print("   ✅ Todas las columnas requeridas presentes")
            
            # Verificar promedio
            primer_dia = df_bolsa.iloc[0]
            print(f"\n   📈 Ejemplo primer día:")
            print(f"      Fecha: {primer_dia['Date']}")
            print(f"      Promedio diario: ${primer_dia['Value']:.2f}")
            print(f"      Métrica: {primer_dia['Metrica']}")
            
            # Verificar datos horarios
            datos_hora = primer_dia['Datos_Horarios']
            if isinstance(datos_hora, dict):
                hour_keys = [k for k in datos_hora.keys() if 'Hour' in k]
                print(f"      Datos horarios: {len(hour_keys)} horas disponibles")
                
                if len(hour_keys) == 24:
                    print("   ✅ 24 horas completas en Datos_Horarios")
                else:
                    print(f"   ⚠️ Solo {len(hour_keys)} horas disponibles")
            else:
                print("   ❌ Datos_Horarios no es un diccionario")
                return False
        else:
            print(f"   ❌ Columnas faltantes: {missing}")
            return False
    else:
        print("   ❌ DataFrame vacío")
        return False
    
    # Test obtener_precio_escasez
    print("\n2️⃣ Testing obtener_precio_escasez()...")
    df_escasez = obtener_precio_escasez(fecha_inicio, fecha_fin)
    
    if not df_escasez.empty:
        print(f"   ✅ Datos obtenidos: {len(df_escasez)} días")
        print(f"   📊 Columnas: {list(df_escasez.columns)}")
        
        # Verificar columnas requeridas
        required = ['Date', 'Value', 'Metrica']
        missing = [col for col in required if col not in df_escasez.columns]
        
        if not missing:
            print("   ✅ Todas las columnas requeridas presentes")
            
            primer_dia = df_escasez.iloc[0]
            print(f"\n   📈 Ejemplo primer día:")
            print(f"      Fecha: {primer_dia['Date']}")
            print(f"      Precio: ${primer_dia['Value']:.2f}")
            print(f"      Métrica: {primer_dia['Metrica']}")
        else:
            print(f"   ❌ Columnas faltantes: {missing}")
            return False
    else:
        print("   ❌ DataFrame vacío")
        return False
    
    print("\n✅ TEST 2 PASSED")
    return True

def test_statistics():
    """Test 3: Cálculo de estadísticas para fichas KPI"""
    print("\n" + "=" * 60)
    print("TEST 3: Estadísticas para fichas KPI")
    print("=" * 60)
    
    fecha_fin = date.today() - timedelta(days=1)
    fecha_inicio = fecha_fin - timedelta(days=30)
    
    print(f"\n📅 Rango: {fecha_inicio} a {fecha_fin} (30 días)")
    
    df_bolsa = obtener_precio_bolsa(fecha_inicio, fecha_fin)
    df_escasez = obtener_precio_escasez(fecha_inicio, fecha_fin)
    
    if df_bolsa.empty or df_escasez.empty:
        print("❌ No hay datos disponibles")
        return False
    
    # Calcular estadísticas
    precio_promedio_bolsa = df_bolsa['Value'].mean()
    precio_max_bolsa = df_bolsa['Value'].max()
    precio_min_bolsa = df_bolsa['Value'].min()
    precio_escasez_actual = df_escasez['Value'].iloc[-1]
    
    print("\n💰 ESTADÍSTICAS PRECIO BOLSA NACIONAL:")
    print(f"   Promedio: ${precio_promedio_bolsa:.2f} $/kWh")
    print(f"   Máximo:   ${precio_max_bolsa:.2f} $/kWh")
    print(f"   Mínimo:   ${precio_min_bolsa:.2f} $/kWh")
    print(f"   Días con datos: {len(df_bolsa)}")
    
    print("\n⚠️  PRECIO ESCASEZ:")
    print(f"   Actual: ${precio_escasez_actual:.2f} $/kWh")
    print(f"   Días con datos: {len(df_escasez)}")
    
    # Validaciones
    if precio_promedio_bolsa > 0 and precio_max_bolsa >= precio_promedio_bolsa:
        print("\n✅ Estadísticas consistentes")
    else:
        print("\n❌ Estadísticas inconsistentes")
        return False
    
    print("\n✅ TEST 3 PASSED")
    return True

def main():
    """Ejecutar todos los tests"""
    print("\n" + "🧪" * 30)
    print("INICIANDO TESTS DEL DASHBOARD DE COMERCIALIZACIÓN")
    print("🧪" * 30)
    
    results = []
    
    try:
        results.append(("Fetch directo API", test_fetch_direct()))
        results.append(("Funciones dashboard", test_functions()))
        results.append(("Estadísticas KPI", test_statistics()))
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN DE TESTS")
    print("=" * 60)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(result for _, result in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 TODOS LOS TESTS PASARON EXITOSAMENTE")
        print("=" * 60)
        print("\n✅ El dashboard de Comercialización está listo para usar")
        print("📍 Acceder en: http://localhost:8050/comercializacion")
        return 0
    else:
        print("❌ ALGUNOS TESTS FALLARON")
        print("=" * 60)
        return 1

if __name__ == '__main__':
    sys.exit(main())
