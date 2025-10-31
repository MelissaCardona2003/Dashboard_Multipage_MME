#!/usr/bin/env python3
"""
Script para actualizar el cache con datos reales de XM
Ejecutar periódicamente (ej: cada hora con cron) para mantener datos frescos
"""
import sys
sys.path.insert(0, '/home/admonctrlxm/server')

from datetime import date, timedelta
from utils._xm import get_objetoAPI, fetch_metric_data
from utils.cache_manager import get_cache_stats, cleanup_old_cache
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def actualizar_datos_hidrologia():
    """Actualizar datos de hidrología"""
    print("\n📊 Actualizando datos de hidrología...")
    
    fecha_fin = date.today() - timedelta(days=1)
    fecha_inicio = fecha_fin - timedelta(days=14)
    
    # Intentar obtener datos reales
    metricas = [
        ('VolEmbalDiar', 'Sistema', 'Reservas Hídricas'),
        ('AporEner', 'Sistema', 'Aportes Hídricos'),
        ('Gene', 'Sistema', 'Generación Total')
    ]
    
    exito = 0
    for metric, entity, nombre in metricas:
        print(f"\n🔍 Consultando {nombre} ({metric}/{entity})...")
        data = fetch_metric_data(metric, entity, fecha_inicio, fecha_fin)
        
        if data is not None and not data.empty:
            print(f"✅ {nombre}: {len(data)} registros obtenidos")
            exito += 1
        else:
            print(f"⚠️ {nombre}: No hay datos disponibles")
    
    return exito > 0

def actualizar_datos_generacion_xm():
    """Actualizar datos de generación por recurso"""
    print("\n⚡ Actualizando datos de generación por recurso...")
    
    fecha_fin = date.today() - timedelta(days=1)
    fecha_inicio = fecha_fin - timedelta(days=7)
    
    print(f"\n🔍 Consultando Gene/Recurso...")
    data = fetch_metric_data('Gene', 'Recurso', fecha_inicio, fecha_fin)
    
    if data is not None and not data.empty:
        print(f"✅ Generación por recurso: {len(data)} registros obtenidos")
        
        # Mostrar resumen
        if 'Values_Type' in data.columns:
            tipos = data['Values_Type'].unique()
            print(f"📋 Tipos de recursos: {', '.join(tipos[:5])}...")
        
        return True
    else:
        print(f"⚠️ Generación por recurso: No hay datos disponibles")
        return False

def main():
    print("="*60)
    print("🔄 ACTUALIZACIÓN DE DATOS DE XM")
    print("="*60)
    
    # Verificar conexión a API
    print("\n🌐 Verificando conexión a API de XM...")
    api = get_objetoAPI()
    
    if api is None:
        print("❌ API de XM no disponible")
        print("ℹ️  La aplicación usará datos históricos del cache")
        
        # Mostrar stats del cache
        stats = get_cache_stats()
        print(f"\n📊 Cache actual:")
        print(f"   - Items en memoria: {stats['memory_items']}")
        print(f"   - Items en disco: {stats['disk_items']}")
        print(f"   - Tamaño total: {stats['total_size_mb']:.2f} MB")
        
        return 1
    
    print("✅ Conexión exitosa a API de XM")
    
    # Limpiar cache expirado
    print("\n🧹 Limpiando cache expirado...")
    cleaned = cleanup_old_cache()
    
    # Actualizar datos
    hidrologia_ok = actualizar_datos_hidrologia()
    generacion_ok = actualizar_datos_generacion_xm()
    
    # Mostrar estadísticas finales
    stats = get_cache_stats()
    print("\n" + "="*60)
    print("📊 RESUMEN DE ACTUALIZACIÓN")
    print("="*60)
    print(f"✅ Hidrología: {'OK' if hidrologia_ok else 'FALLO'}")
    print(f"✅ Generación: {'OK' if generacion_ok else 'FALLO'}")
    print(f"\n📦 Cache:")
    print(f"   - Items en memoria: {stats['memory_items']}")
    print(f"   - Items en disco: {stats['disk_items']}")
    print(f"   - Tamaño total: {stats['total_size_mb']:.2f} MB")
    print("="*60)
    
    return 0 if (hidrologia_ok or generacion_ok) else 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
