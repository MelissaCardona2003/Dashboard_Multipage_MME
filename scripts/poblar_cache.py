"""
Script para poblar el cache con datos simulados
Útil cuando la API de XM no está disponible
"""
import sys
import os
sys.path.insert(0, '/home/admonctrlxm/server')

from datetime import date, timedelta
import pandas as pd
from utils.cache_manager import save_to_cache, get_cache_key

def crear_datos_reservas_simulados():
    """Crear datos simulados de reservas hídricas"""
    fecha_fin = date.today() - timedelta(days=1)
    fechas = [fecha_fin - timedelta(days=i) for i in range(14)]
    
    data = {
        'Date': fechas,
        'Values_gwh': [14000 + (i * 50) for i in range(len(fechas))],
        'Values_%': [83.29 + (i * 0.1) for i in range(len(fechas))]
    }
    
    return pd.DataFrame(data)

def crear_datos_aportes_simulados():
    """Crear datos simulados de aportes hídricos"""
    fecha_fin = date.today() - timedelta(days=1)
    fechas = [fecha_fin - timedelta(days=i) for i in range(14)]
    
    data = {
        'Date': fechas,
        'Values_gwh': [220.62 + (i * 2) for i in range(len(fechas))],
        'Values_%': [89.51 + (i * 0.05) for i in range(len(fechas))]
    }
    
    return pd.DataFrame(data)

def crear_datos_generacion_simulados():
    """Crear datos simulados de generación total"""
    fecha_fin = date.today() - timedelta(days=1)
    fechas = [fecha_fin - timedelta(days=i) for i in range(14)]
    
    data = {
        'Date': fechas,
        'Values_gwh': [198.45 + (i * 3) for i in range(len(fechas))]
    }
    
    return pd.DataFrame(data)

def crear_datos_generacion_recurso_simulados():
    """Crear datos simulados de generación por recurso"""
    fecha_fin = date.today() - timedelta(days=1)
    fechas = [fecha_fin - timedelta(days=i) for i in range(7)]
    
    # Crear datos para diferentes tipos de recursos
    tipos = ['HIDRAULICA', 'TERMICA GAS', 'TERMICA CARBON', 'EOLICA', 'SOLAR']
    tipos_renovable = ['HIDRAULICA', 'EOLICA', 'SOLAR']
    
    data = []
    for fecha in fechas:
        for tipo in tipos:
            is_renovable = tipo in tipos_renovable
            base = 5000 if tipo == 'HIDRAULICA' else (2000 if 'TERMICA' in tipo else 1000)
            
            data.append({
                'Date': fecha,
                'Values_Type': tipo,
                'Values_gwh': base + (hash(str(fecha) + tipo) % 500),
                'Es_Renovable': is_renovable
            })
    
    return pd.DataFrame(data)

def poblar_cache_inicial():
    """Poblar el cache con datos simulados"""
    print("🚀 Poblando cache con datos simulados...")
    
    # Preparar fechas
    fecha_fin = date.today() - timedelta(days=1)
    fecha_inicio = fecha_fin - timedelta(days=14)
    
    # 1. Datos de reservas
    df_reservas = crear_datos_reservas_simulados()
    cache_key = get_cache_key('fetch_metric_data', 'VolEmbalDiar', 'Sistema', fecha_inicio, fecha_fin)
    save_to_cache(cache_key, df_reservas, 'metricas_hidricas')
    print(f"✅ Guardadas {len(df_reservas)} filas de reservas")
    
    # 2. Datos de aportes
    df_aportes = crear_datos_aportes_simulados()
    cache_key = get_cache_key('fetch_metric_data', 'AporEner', 'Sistema', fecha_inicio, fecha_fin)
    save_to_cache(cache_key, df_aportes, 'metricas_hidricas')
    print(f"✅ Guardados {len(df_aportes)} filas de aportes")
    
    # 3. Datos de generación total
    df_generacion = crear_datos_generacion_simulados()
    cache_key = get_cache_key('fetch_metric_data', 'Gene', 'Sistema', fecha_inicio, fecha_fin)
    save_to_cache(cache_key, df_generacion, 'metricas_hidricas')
    print(f"✅ Guardadas {len(df_generacion)} filas de generación total")
    
    # 4. Datos de generación por recurso (para fichas XM)
    fecha_inicio_corto = fecha_fin - timedelta(days=7)
    df_gene_recurso = crear_datos_generacion_recurso_simulados()
    cache_key = get_cache_key('fetch_metric_data', 'Gene', 'Recurso', fecha_inicio_corto, fecha_fin)
    save_to_cache(cache_key, df_gene_recurso, 'generacion_xm')
    print(f"✅ Guardadas {len(df_gene_recurso)} filas de generación por recurso")
    
    print("\n✨ Cache poblado exitosamente con datos simulados")
    print("📊 Los tableros ahora mostrarán estos datos en lugar de fallback")
    print("⏱️  Estos datos expirarán según la configuración de cache (1-2 horas)")

if __name__ == '__main__':
    poblar_cache_inicial()
