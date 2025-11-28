#!/usr/bin/env python3
"""
Verificar que el dashboard puede consultar datos de DemaCome y DemaReal por agente desde SQLite
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta, date
from utils._xm import obtener_datos_inteligente

print("="*100)
print("TEST: CONSULTA DE DATOS POR AGENTE DESDE EL DASHBOARD")
print("="*100)

# Período de prueba
fecha_fin = date.today() - timedelta(days=1)
fecha_inicio = fecha_fin - timedelta(days=7)

print(f"\nPeríodo: {fecha_inicio} a {fecha_fin}")
print()

# TEST 1: DemaCome por Agente (todos los agentes)
print("="*100)
print("TEST 1: DemaCome por Agente (TODOS)")
print("="*100)

df_demacomes, warning = obtener_datos_inteligente(
    'DemaCome',
    'Agente',
    fecha_inicio,
    fecha_fin
)

if df_demacomes is not None and not df_demacomes.empty:
    print(f"✅ Datos obtenidos: {len(df_demacomes)} registros")
    print(f"📋 Columnas: {df_demacomes.columns.tolist()}")
    
    # Buscar columna de código
    code_col = 'Values_code' if 'Values_code' in df_demacomes.columns else ('recurso' if 'recurso' in df_demacomes.columns else 'Name')
    if code_col in df_demacomes.columns:
        agentes_unicos = df_demacomes[code_col].nunique()
        print(f"👥 Agentes únicos: {agentes_unicos}")
        print(f"👥 Primeros 20 agentes:")
        agentes = sorted(df_demacomes[code_col].unique()[:20].tolist())
        for i, ag in enumerate(agentes, 1):
            print(f"  {i:2d}. {ag}")
    
    # Verificar valores
    if 'Value' in df_demacomes.columns:
        print(f"\n📊 Estadísticas de valores:")
        print(f"  Promedio: {df_demacomes['Value'].mean():.4f} GWh")
        print(f"  Mínimo: {df_demacomes['Value'].min():.4f} GWh")
        print(f"  Máximo: {df_demacomes['Value'].max():.4f} GWh")
else:
    print("❌ No se obtuvieron datos")
    if warning:
        print(f"⚠️ Advertencia: {warning}")

print()

# TEST 2: DemaCome filtrado por un agente específico (AAGG)
print("="*100)
print("TEST 2: DemaCome por Agente (FILTRADO: AAGG)")
print("="*100)

# Simular el filtrado que hace el dashboard
if df_demacomes is not None and not df_demacomes.empty:
    code_col = 'Values_code' if 'Values_code' in df_demacomes.columns else 'recurso'
    
    if code_col in df_demacomes.columns:
        df_filtrado = df_demacomes[df_demacomes[code_col] == 'AAGG'].copy()
        
        if not df_filtrado.empty:
            print(f"✅ Datos filtrados: {len(df_filtrado)} registros")
            print(f"📊 Valores del agente AAGG:")
            print(df_filtrado[['Date', code_col, 'Value']].head(10).to_string(index=False))
        else:
            print("❌ No se encontraron datos para AAGG")
            print(f"   Códigos disponibles: {sorted(df_demacomes[code_col].unique()[:10].tolist())}")
    else:
        print(f"❌ Columna de código no encontrada. Columnas: {df_demacomes.columns.tolist()}")

print()

# TEST 3: DemaReal por Agente
print("="*100)
print("TEST 3: DemaReal por Agente")
print("="*100)

df_demareal, warning = obtener_datos_inteligente(
    'DemaReal',
    'Agente',
    fecha_inicio,
    fecha_fin
)

if df_demareal is not None and not df_demareal.empty:
    print(f"✅ Datos obtenidos: {len(df_demareal)} registros")
    
    code_col = 'Values_code' if 'Values_code' in df_demareal.columns else 'recurso'
    if code_col in df_demareal.columns:
        agentes_unicos = df_demareal[code_col].nunique()
        print(f"👥 Agentes únicos: {agentes_unicos}")
        
        # Mostrar muestra
        print(f"\n📊 Muestra de datos (primeros 10 registros):")
        print(df_demareal[['Date', code_col, 'Value']].head(10).to_string(index=False))
else:
    print("❌ No se obtuvieron datos")
    if warning:
        print(f"⚠️ Advertencia: {warning}")

print()
print("="*100)
print("CONCLUSIÓN:")
if df_demacomes is not None and not df_demacomes.empty and df_demareal is not None and not df_demareal.empty:
    print("✅ SQLite tiene datos desagregados por agente")
    print("✅ El dashboard debería poder mostrar gráficas por agente individual")
else:
    print("❌ Hay problemas con los datos")
print("="*100)
