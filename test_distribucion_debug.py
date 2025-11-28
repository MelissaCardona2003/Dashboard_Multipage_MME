#!/usr/bin/env python3
"""
Test de diagnóstico para el tablero de distribución
Problemas reportados:
1. Demanda No Atendida sale en ceros
2. Al filtrar por agente específico no salen datos
"""

import sys
import pandas as pd
from datetime import date, timedelta
sys.path.insert(0, '/home/admonctrlxm/server')

from utils._xm import obtener_datos_inteligente

print("=" * 80)
print("DIAGNÓSTICO: Tablero de Distribución")
print("=" * 80)

# Fechas de prueba
fecha_fin = date.today() - timedelta(days=1)
fecha_inicio = fecha_fin - timedelta(days=7)

print(f"\n📅 Rango de fechas: {fecha_inicio} a {fecha_fin}")

# ========================================
# TEST 1: DemaCome (Demanda Comercial)
# ========================================
print("\n" + "=" * 80)
print("TEST 1: DemaCome - Demanda Comercial por Agente")
print("=" * 80)

df_come, warning = obtener_datos_inteligente('DemaCome', 'Agente', 
                                              fecha_inicio.strftime('%Y-%m-%d'),
                                              fecha_fin.strftime('%Y-%m-%d'))

if df_come is not None and not df_come.empty:
    print(f"✅ Datos obtenidos: {len(df_come)} registros")
    print(f"\n📊 Columnas disponibles:")
    print(df_come.columns.tolist())
    print(f"\n📊 Primeros registros:")
    print(df_come.head())
    
    # Identificar columna de código
    code_col = None
    if 'Values_code' in df_come.columns:
        code_col = 'Values_code'
    elif 'Values_Code' in df_come.columns:
        code_col = 'Values_Code'
    
    if code_col:
        print(f"\n🔍 Agentes únicos encontrados: {df_come[code_col].nunique()}")
        print(f"Ejemplos: {df_come[code_col].unique()[:5]}")
    
    # Verificar columnas de horas
    cols_horas = [col for col in df_come.columns if 'Hour' in col]
    print(f"\n⏰ Columnas de horas encontradas: {len(cols_horas)}")
    if cols_horas:
        print(f"Ejemplos: {cols_horas[:5]}")
else:
    print("❌ No se obtuvieron datos de DemaCome")

# ========================================
# TEST 2: DemaReal (Demanda Real)
# ========================================
print("\n" + "=" * 80)
print("TEST 2: DemaReal - Demanda Real por Agente")
print("=" * 80)

df_real, warning = obtener_datos_inteligente('DemaReal', 'Agente',
                                              fecha_inicio.strftime('%Y-%m-%d'),
                                              fecha_fin.strftime('%Y-%m-%d'))

if df_real is not None and not df_real.empty:
    print(f"✅ Datos obtenidos: {len(df_real)} registros")
    print(f"\n📊 Columnas disponibles:")
    print(df_real.columns.tolist())
else:
    print("❌ No se obtuvieron datos de DemaReal")

# ========================================
# TEST 3: Demanda No Atendida
# ========================================
print("\n" + "=" * 80)
print("TEST 3: DenoEner - Demanda No Atendida Programada")
print("=" * 80)

df_dna, warning = obtener_datos_inteligente('DenoEner', 'Area',
                                             fecha_inicio.strftime('%Y-%m-%d'),
                                             fecha_fin.strftime('%Y-%m-%d'))

if df_dna is not None and not df_dna.empty:
    print(f"✅ Datos obtenidos: {len(df_dna)} registros")
    print(f"\n📊 Columnas disponibles:")
    print(df_dna.columns.tolist())
    print(f"\n📊 Primeros registros:")
    print(df_dna.head())
    
    # Verificar valores
    if 'Value' in df_dna.columns:
        print(f"\n📈 Estadísticas de valores:")
        print(f"  Min: {df_dna['Value'].min()}")
        print(f"  Max: {df_dna['Value'].max()}")
        print(f"  Mean: {df_dna['Value'].mean()}")
        print(f"  Sum: {df_dna['Value'].sum()}")
else:
    print("❌ No se obtuvieron datos de DenoEner")
    
# ========================================
# TEST 4: Filtrado por agente específico
# ========================================
print("\n" + "=" * 80)
print("TEST 4: Filtrado por Agente Específico")
print("=" * 80)

if df_come is not None and not df_come.empty and code_col:
    # Tomar el primer agente como ejemplo
    agente_ejemplo = df_come[code_col].iloc[0]
    print(f"🔍 Filtrando por agente: {agente_ejemplo}")
    
    df_filtrado = df_come[df_come[code_col] == agente_ejemplo].copy()
    print(f"✅ Registros después del filtro: {len(df_filtrado)}")
    
    if len(df_filtrado) > 0:
        print(f"\n📊 Datos filtrados:")
        print(df_filtrado.head())
    else:
        print("❌ El filtro no devolvió datos")
else:
    print("⚠️ No hay datos para probar filtrado")

print("\n" + "=" * 80)
print("RESUMEN DE DIAGNÓSTICO")
print("=" * 80)
print("""
PROBLEMAS DETECTADOS Y SOLUCIONES:

1. Demanda No Atendida en ceros:
   - Verificar si la métrica es 'DenoEner' o 'DemandaNoAtendida'
   - Revisar si hay datos en el rango de fechas seleccionado
   
2. Filtro por agente no funciona:
   - Verificar el nombre correcto de la columna de código
   - Asegurar que el código del agente coincide exactamente
""")
