#!/usr/bin/env python3
"""
Script para verificar estado del cache sin llamar a la API XM
Útil para diagnóstico y verificación antes de precalentamiento
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pickle
from datetime import datetime, timedelta
from collections import defaultdict

CACHE_DIR = '/var/cache/portal_energetico_cache'

def verificar_cache():
    """Analizar archivos de cache y reportar estado"""
    
    print("=" * 70)
    print("📦 VERIFICACIÓN DE CACHE")
    print("=" * 70)
    print(f"Directorio: {CACHE_DIR}\n")
    
    if not os.path.exists(CACHE_DIR):
        print(f"❌ Directorio de cache no existe: {CACHE_DIR}")
        return
    
    archivos = [f for f in os.listdir(CACHE_DIR) if f.endswith('.pkl')]
    
    if not archivos:
        print("⚠️  Cache vacío - no hay archivos .pkl")
        return
    
    print(f"📊 Total archivos en cache: {len(archivos)}\n")
    
    # Analizar por tipo de métrica
    metricas = defaultdict(list)
    fechas_cache = []
    
    for archivo in archivos:
        filepath = os.path.join(CACHE_DIR, archivo)
        
        try:
            # Obtener timestamp del archivo
            timestamp = os.path.getmtime(filepath)
            fecha_cache = datetime.fromtimestamp(timestamp)
            fechas_cache.append(fecha_cache)
            
            # Extraer tipo de métrica del nombre
            if 'fetch_metric_data' in archivo:
                partes = archivo.split('_')
                if len(partes) >= 4:
                    metrica = partes[3]  # Gene, DemaCome, etc.
                    metricas[metrica].append(fecha_cache)
            elif 'generacion_agregada' in archivo:
                metricas['generacion_agregada'].append(fecha_cache)
            elif 'listado_recursos' in archivo:
                metricas['listado_recursos'].append(fecha_cache)
            else:
                metricas['otros'].append(fecha_cache)
                
        except Exception as e:
            print(f"⚠️  Error leyendo {archivo}: {e}")
            continue
    
    # Reporte por métrica
    print("📋 MÉTRICAS EN CACHE:\n")
    for metrica, fechas in sorted(metricas.items()):
        fecha_mas_reciente = max(fechas)
        dias_antiguedad = (datetime.now() - fecha_mas_reciente).days
        
        emoji = "✅" if dias_antiguedad < 7 else "⚠️" if dias_antiguedad < 30 else "❌"
        
        print(f"{emoji} {metrica:30s} → {len(fechas):3d} archivos | Más reciente: {fecha_mas_reciente.strftime('%Y-%m-%d %H:%M')} ({dias_antiguedad} días)")
    
    # Estadísticas generales
    if fechas_cache:
        fecha_mas_vieja = min(fechas_cache)
        fecha_mas_nueva = max(fechas_cache)
        
        print("\n" + "=" * 70)
        print("📊 ESTADÍSTICAS GENERALES")
        print("=" * 70)
        print(f"Cache más antiguo:  {fecha_mas_vieja.strftime('%Y-%m-%d %H:%M')} ({(datetime.now() - fecha_mas_vieja).days} días)")
        print(f"Cache más reciente: {fecha_mas_nueva.strftime('%Y-%m-%d %H:%M')} ({(datetime.now() - fecha_mas_nueva).days} días)")
        
        # Distribución por antigüedad
        recientes = sum(1 for f in fechas_cache if (datetime.now() - f).days < 7)
        medios = sum(1 for f in fechas_cache if 7 <= (datetime.now() - f).days < 30)
        viejos = sum(1 for f in fechas_cache if (datetime.now() - f).days >= 30)
        
        print(f"\n📈 Distribución:")
        print(f"   Recientes (<7 días):   {recientes:3d} archivos ({recientes/len(fechas_cache)*100:.1f}%)")
        print(f"   Medios (7-30 días):    {medios:3d} archivos ({medios/len(fechas_cache)*100:.1f}%)")
        print(f"   Viejos (>30 días):     {viejos:3d} archivos ({viejos/len(fechas_cache)*100:.1f}%)")
    
    # Recomendaciones
    print("\n" + "=" * 70)
    print("💡 RECOMENDACIONES")
    print("=" * 70)
    
    if not metricas:
        print("⚠️  Cache vacío - ejecutar: python3 scripts/precalentar_cache_v2.py")
    elif fecha_mas_nueva and (datetime.now() - fecha_mas_nueva).days > 7:
        print("⚠️  Cache desactualizado (>7 días)")
        print("   Ejecutar: python3 scripts/precalentar_cache_v2.py")
    else:
        print("✅ Cache en buen estado")
        print("   Ejecución automática en cron: 06:30, 12:30, 20:30")
    
    # Verificar métricas críticas para dashboard
    print("\n" + "=" * 70)
    print("🎯 MÉTRICAS CRÍTICAS PARA DASHBOARD")
    print("=" * 70)
    
    metricas_criticas = {
        'Gene': 'Generación Total (ficha principal)',
        'AporEner': 'Aportes Hídricos (ficha principal)',
        'VoluUtilDiarEner': 'Reservas Hídricas (ficha principal)',
        'generacion_agregada': 'Generación por Fuentes (tab)',
    }
    
    for metrica, descripcion in metricas_criticas.items():
        if metrica in metricas:
            dias = (datetime.now() - max(metricas[metrica])).days
            emoji = "✅" if dias < 7 else "⚠️"
            print(f"{emoji} {metrica:20s} → {descripcion} ({dias} días)")
        else:
            print(f"❌ {metrica:20s} → {descripcion} (NO EXISTE)")
    
    print("\n" + "=" * 70)

if __name__ == '__main__':
    try:
        verificar_cache()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
