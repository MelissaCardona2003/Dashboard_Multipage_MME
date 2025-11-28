#!/usr/bin/env python3
"""
Test completo del flujo de datos del dashboard de distribución
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, timedelta
import pandas as pd
from utils._xm import obtener_datos_inteligente

def test_flujo_completo():
    print("="*100)
    print("TEST COMPLETO: FLUJO DE DATOS DEL DASHBOARD DE DISTRIBUCIÓN")
    print("="*100)
    
    # Simular período del dashboard
    fecha_fin = date.today() - timedelta(days=1)
    fecha_inicio = fecha_fin - timedelta(days=30)
    
    print(f"\n📅 Período: {fecha_inicio} a {fecha_fin}")
    print()
    
    # PASO 1: Obtener datos de SQLite
    print("="*100)
    print("PASO 1: OBTENER DATOS DE SQLITE")
    print("="*100)
    
    df_come, warning_come = obtener_datos_inteligente('DemaCome', 'Agente', fecha_inicio, fecha_fin)
    df_real, warning_real = obtener_datos_inteligente('DemaReal', 'Agente', fecha_inicio, fecha_fin)
    
    if df_come is None or df_come.empty:
        print("❌ DemaCome: Sin datos")
        return False
    else:
        print(f"✅ DemaCome: {len(df_come)} registros")
        print(f"   Columnas: {df_come.columns.tolist()}")
        print(f"   Fechas: {df_come['Date'].min()} a {df_come['Date'].max()}")
    
    if df_real is None or df_real.empty:
        print("❌ DemaReal: Sin datos")
        return False
    else:
        print(f"✅ DemaReal: {len(df_real)} registros")
        print(f"   Columnas: {df_real.columns.tolist()}")
    
    # PASO 2: Verificar estructura de datos
    print("\n" + "="*100)
    print("PASO 2: VERIFICAR ESTRUCTURA")
    print("="*100)
    
    # Verificar que tienen las columnas necesarias
    columnas_necesarias_sqlite = ['Date', 'Value', 'recurso']
    columnas_necesarias_api = ['Date', 'Values_code', 'Values_Hour01']
    
    tiene_value = 'Value' in df_come.columns
    tiene_horas = 'Values_Hour01' in df_come.columns
    tiene_codigo = 'Values_code' in df_come.columns or 'recurso' in df_come.columns
    
    print(f"✓ Tiene columna 'Value' (SQLite): {tiene_value}")
    print(f"✓ Tiene columnas horarias (API): {tiene_horas}")
    print(f"✓ Tiene código de agente: {tiene_codigo}")
    
    if not (tiene_value or tiene_horas):
        print("❌ ERROR: No tiene ni Value ni columnas horarias")
        return False
    
    if not tiene_codigo:
        print("❌ ERROR: No tiene columna de código de agente")
        return False
    
    # PASO 3: Simular procesar_datos_horarios
    print("\n" + "="*100)
    print("PASO 3: PROCESAR DATOS (SIMULAR procesar_datos_horarios)")
    print("="*100)
    
    # Identificar columnas
    cols_horas = [col for col in df_come.columns if 'Hour' in col]
    
    if cols_horas:
        print(f"📊 Caso: Datos con columnas horarias ({len(cols_horas)} columnas)")
        df_come_copy = df_come.copy()
        df_come_copy[cols_horas] = df_come_copy[cols_horas].fillna(0)
        df_come_copy['Demanda_GWh'] = df_come_copy[cols_horas].sum(axis=1) / 1_000_000
    elif 'Value' in df_come.columns:
        print(f"📊 Caso: Datos con Value ya agregado (SQLite)")
        df_come_copy = df_come.copy()
        df_come_copy['Demanda_GWh'] = df_come_copy['Value']
    else:
        print("❌ ERROR: No se puede procesar")
        return False
    
    # Verificar resultados
    print(f"\n✅ Procesamiento exitoso:")
    print(f"   Registros: {len(df_come_copy)}")
    print(f"   Demanda promedio: {df_come_copy['Demanda_GWh'].mean():.4f} GWh")
    print(f"   Demanda mínima: {df_come_copy['Demanda_GWh'].min():.4f} GWh")
    print(f"   Demanda máxima: {df_come_copy['Demanda_GWh'].max():.4f} GWh")
    
    # PASO 4: Verificar códigos de agentes
    print("\n" + "="*100)
    print("PASO 4: VERIFICAR CÓDIGOS DE AGENTES")
    print("="*100)
    
    codigo_col = 'Values_code' if 'Values_code' in df_come.columns else 'recurso'
    agentes_unicos = df_come[codigo_col].nunique()
    
    print(f"👥 Agentes únicos: {agentes_unicos}")
    print(f"👥 Primeros 20 agentes:")
    for i, ag in enumerate(sorted(df_come[codigo_col].unique()[:20]), 1):
        print(f"   {i:2d}. {ag}")
    
    # PASO 5: Test de filtrado por agente
    print("\n" + "="*100)
    print("PASO 5: TEST FILTRADO POR AGENTE (AAGG)")
    print("="*100)
    
    df_filtrado = df_come[df_come[codigo_col] == 'AAGG'].copy()
    
    if df_filtrado.empty:
        print("❌ No hay datos para AAGG")
        return False
    else:
        print(f"✅ Datos filtrados: {len(df_filtrado)} registros")
        if 'Value' in df_filtrado.columns:
            print(f"   Demanda promedio: {df_filtrado['Value'].mean():.6f} GWh")
        print(f"\n   Muestra de datos:")
        print(df_filtrado[['Date', codigo_col, 'Value' if 'Value' in df_filtrado.columns else 'Demanda_GWh']].head().to_string(index=False))
    
    print("\n" + "="*100)
    print("✅ TODOS LOS TESTS PASARON")
    print("="*100)
    print("\n🎉 El dashboard debería funcionar correctamente ahora")
    
    return True

if __name__ == "__main__":
    exito = test_flujo_completo()
    sys.exit(0 if exito else 1)
