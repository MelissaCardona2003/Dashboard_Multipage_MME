#!/usr/bin/env python3
"""
Script para poblar el cache con datos históricos de métricas usadas en tableros.
Este script simula datos para las métricas que los tableros necesitan cuando la API está caída.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime
from utils.cache_manager import save_to_cache, get_cache_key

print("=" * 60)
print("📊 POBLACIÓN DE CACHE PARA TABLEROS")
print("=" * 60)

# Métricas adicionales usadas en tableros
METRICAS_TABLEROS = {
    'VoluUtilDiarEner': {
        'entity': 'Embalse',
        'descripcion': 'Volumen Útil Diario por Embalse',
        'embalses': ['GUAVIO', 'PENOL', 'GUATAPE', 'PLAYAS', 'SAN CARLOS', 'PORCE II', 'PORCE III', 
                     'MIEL I', 'SALVAJINA', 'CALIMA', 'BETANIA', 'TOPOCORO', 'JAGUAS'],
        'rango_valores': (50, 150),  # GWh
    },
    'CapaUtilDiarEner': {
        'entity': 'Embalse',
        'descripcion': 'Capacidad Útil Diaria por Embalse',
        'embalses': ['GUAVIO', 'PENOL', 'GUATAPE', 'PLAYAS', 'SAN CARLOS', 'PORCE II', 'PORCE III',
                     'MIEL I', 'SALVAJINA', 'CALIMA', 'BETANIA', 'TOPOCORO', 'JAGUAS'],
        'rango_valores': (100, 250),  # GWh
    },
    'AporCaudal': {
        'entity': 'Rio',
        'descripcion': 'Aportes de Caudal por Río',
        'rios': ['MAGDALENA', 'CAUCA', 'NECHI', 'GUAVIO', 'BOGOTA', 'META', 'SINU', 'ANCHICAYA'],
        'rango_valores': (50, 500),  # m3/s
    },
    'PorcApor': {
        'entity': 'Rio',
        'descripcion': 'Porcentaje de Aportes por Río',
        'rios': ['MAGDALENA', 'CAUCA', 'NECHI', 'GUAVIO', 'BOGOTA', 'META', 'SINU', 'ANCHICAYA'],
        'rango_valores': (0.05, 0.25),  # 5-25% (se multiplicará por 100)
    },
    'ListadoRios': {
        'entity': 'Sistema',
        'descripcion': 'Listado de Ríos con Región',
        'tipo': 'metadata',
    },
    'ListadoEmbalses': {
        'entity': 'Sistema',
        'descripcion': 'Listado de Embalses con Región',
        'tipo': 'metadata',
    },
    'ListadoRecursos': {
        'entity': 'Sistema',
        'descripcion': 'Listado de Recursos de Generación',
        'tipo': 'metadata',
    },
}

def generar_datos_embalses(metric, config, fecha_inicio, fecha_fin):
    """Generar datos simulados para métricas de embalses"""
    print(f"  📦 Generando {config['descripcion']}...")
    
    embalses = config.get('embalses', [])
    min_val, max_val = config.get('rango_valores', (50, 150))
    
    # Generar serie temporal para cada embalse
    fechas = pd.date_range(start=fecha_inicio, end=fecha_fin, freq='D')
    datos = []
    
    for embalse in embalses:
        # Valor base para este embalse (varía por embalse)
        valor_base = np.random.uniform(min_val, max_val)
        
        for fecha in fechas:
            # Variación diaria pequeña (+/- 10%)
            variacion = np.random.uniform(-0.1, 0.1)
            valor = valor_base * (1 + variacion)
            
            datos.append({
                'Date': fecha.date(),
                'Name': embalse,
                'Value': round(valor, 2)
            })
    
    df = pd.DataFrame(datos)
    print(f"    ✅ {len(df)} registros generados para {len(embalses)} embalses")
    return df

def generar_datos_rios(metric, config, fecha_inicio, fecha_fin):
    """Generar datos simulados para métricas de ríos"""
    print(f"  🌊 Generando {config['descripcion']}...")
    
    rios = config.get('rios', [])
    min_val, max_val = config.get('rango_valores', (50, 500))
    
    # Generar serie temporal para cada río
    fechas = pd.date_range(start=fecha_inicio, end=fecha_fin, freq='D')
    datos = []
    
    for rio in rios:
        # Valor base para este río
        valor_base = np.random.uniform(min_val, max_val)
        
        for fecha in fechas:
            # Variación diaria moderada (+/- 20%)
            variacion = np.random.uniform(-0.2, 0.2)
            valor = valor_base * (1 + variacion)
            
            datos.append({
                'Date': fecha.date(),
                'Name': rio,
                'Value': round(valor, 2)
            })
    
    df = pd.DataFrame(datos)
    print(f"    ✅ {len(df)} registros generados para {len(rios)} ríos")
    return df

def generar_metadata_rios():
    """Generar listado de ríos con sus regiones"""
    print(f"  📋 Generando Listado de Ríos con Regiones...")
    
    rios_regiones = {
        'MAGDALENA': 'Magdalena',
        'CAUCA': 'Cauca',
        'NECHI': 'Magdalena',
        'GUAVIO': 'Magdalena',
        'BOGOTA': 'Magdalena',
        'META': 'Orinoco',
        'SINU': 'Caribe',
        'ANCHICAYA': 'Pacífico',
        'SAN JUAN': 'Pacífico',
        'ATRATO': 'Pacífico',
    }
    
    datos = []
    for rio, region in rios_regiones.items():
        datos.append({
            'Date': date.today(),
            'Values_Name': rio,
            'Values_HydroRegion': region
        })
    
    df = pd.DataFrame(datos)
    print(f"    ✅ {len(df)} ríos con región generados")
    return df

def generar_metadata_embalses():
    """Generar listado de embalses con sus regiones"""
    print(f"  📋 Generando Listado de Embalses con Regiones...")
    
    embalses_regiones = {
        'GUAVIO': 'Magdalena',
        'PENOL': 'Cauca',
        'GUATAPE': 'Cauca',
        'PLAYAS': 'Cauca',
        'SAN CARLOS': 'Cauca',
        'PORCE II': 'Cauca',
        'PORCE III': 'Cauca',
        'MIEL I': 'Magdalena',
        'SALVAJINA': 'Cauca',
        'CALIMA': 'Pacífico',
        'BETANIA': 'Magdalena',
        'TOPOCORO': 'Magdalena',
        'JAGUAS': 'Caribe',
    }
    
    datos = []
    for embalse, region in embalses_regiones.items():
        datos.append({
            'Date': date.today(),
            'Values_Name': embalse,
            'Values_HydroRegion': region
        })
    
    df = pd.DataFrame(datos)
    print(f"    ✅ {len(df)} embalses con región generados")
    return df

def generar_metadata_recursos():
    """Generar listado de recursos de generación"""
    print(f"  📋 Generando Listado de Recursos...")
    
    recursos = [
        {'Values_Name': 'HIDRAULICA', 'Values_Type': 'HIDRAULICA', 'Values_SIC': 'HID'},
        {'Values_Name': 'TERMICA', 'Values_Type': 'TERMICA', 'Values_SIC': 'TER'},
        {'Values_Name': 'EOLICA', 'Values_Type': 'EOLICA', 'Values_SIC': 'EOL'},
        {'Values_Name': 'SOLAR', 'Values_Type': 'SOLAR', 'Values_SIC': 'SOL'},
        {'Values_Name': 'BIOMASA', 'Values_Type': 'BIOMASA', 'Values_SIC': 'BIO'},
    ]
    
    df = pd.DataFrame(recursos)
    df['Date'] = date.today()
    print(f"    ✅ {len(df)} recursos generados")
    return df

def main():
    # Rango de fechas para los datos
    fecha_fin = date.today()
    fecha_inicio = fecha_fin - timedelta(days=30)  # Último mes
    
    print(f"\n📅 Rango de fechas: {fecha_inicio} a {fecha_fin}")
    print(f"📁 Directorio de cache: /tmp/portal_energetico_cache/\n")
    
    total_metricas = len(METRICAS_TABLEROS)
    metricas_ok = 0
    metricas_error = 0
    
    for i, (metric, config) in enumerate(METRICAS_TABLEROS.items(), 1):
        print(f"[{i}/{total_metricas}] Procesando métrica: {metric}")
        
        try:
            # Generar datos según tipo de métrica
            if config.get('tipo') == 'metadata':
                # Metadata (sin rango de fechas)
                if metric == 'ListadoRios':
                    df = generar_metadata_rios()
                    fecha_inicio_str = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
                    fecha_fin_str = date.today().strftime('%Y-%m-%d')
                elif metric == 'ListadoEmbalses':
                    df = generar_metadata_embalses()
                    fecha_inicio_str = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
                    fecha_fin_str = date.today().strftime('%Y-%m-%d')
                elif metric == 'ListadoRecursos':
                    df = generar_metadata_recursos()
                    fecha_inicio_str = (date.today() - timedelta(days=14)).strftime('%Y-%m-%d')
                    fecha_fin_str = (date.today() - timedelta(days=7)).strftime('%Y-%m-%d')
            elif config['entity'] == 'Embalse':
                df = generar_datos_embalses(metric, config, fecha_inicio, fecha_fin)
                fecha_inicio_str = fecha_inicio.strftime('%Y-%m-%d')
                fecha_fin_str = fecha_fin.strftime('%Y-%m-%d')
            elif config['entity'] == 'Rio':
                df = generar_datos_rios(metric, config, fecha_inicio, fecha_fin)
                fecha_inicio_str = fecha_inicio.strftime('%Y-%m-%d')
                fecha_fin_str = fecha_fin.strftime('%Y-%m-%d')
            else:
                print(f"  ⚠️  Tipo de métrica no reconocido: {config.get('entity')}")
                metricas_error += 1
                continue
            
            # Guardar en cache usando el mismo formato que fetch_metric_data
            cache_key = get_cache_key('fetch_metric_data', 
                                     metric=metric,
                                     entity=config['entity'],
                                     start_date=fecha_inicio_str,
                                     end_date=fecha_fin_str)
            
            save_to_cache(cache_key, df, cache_type='default')
            print(f"  💾 Guardado en cache: {cache_key[:50]}...")
            metricas_ok += 1
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            metricas_error += 1
        
        print()
    
    # Resumen
    print("=" * 60)
    print("📊 RESUMEN")
    print("=" * 60)
    print(f"✅ Métricas pobladas exitosamente: {metricas_ok}/{total_metricas}")
    if metricas_error > 0:
        print(f"❌ Métricas con errores: {metricas_error}/{total_metricas}")
    print("\n🎉 ¡Proceso completado!")
    print("\nLos tableros ahora tendrán datos históricos disponibles cuando la API esté caída.")
    
    return 0 if metricas_error == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
