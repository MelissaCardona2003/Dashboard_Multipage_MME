#!/usr/bin/env python3
"""
Sistema de validación automática de caches
Previene caches con unidades incorrectas (kWh en lugar de GWh)
"""
import os
import pickle
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Métricas que DEBEN estar en GWh en cache
METRICS_MUST_BE_GWH = ['AporEner', 'AporEnerMediHist']

# Umbrales para detectar errores de unidad
GWH_MAX_REASONABLE = 1000  # Si promedio > 1000, probablemente está en kWh
GWH_MIN_REASONABLE = 0.001  # Si promedio < 0.001, probablemente sobre-convertido

def validate_cache_units(cache_dir='/tmp/portal_energetico_cache/'):
    """
    Valida que todos los caches tengan unidades correctas
    Retorna: (valid, invalid) - listas de archivos
    """
    valid = []
    invalid = []
    
    if not os.path.exists(cache_dir):
        logger.warning(f"⚠️ Directorio de cache no existe: {cache_dir}")
        return valid, invalid
    
    for filename in os.listdir(cache_dir):
        if not filename.endswith('.pkl'):
            continue
        
        filepath = os.path.join(cache_dir, filename)
        try:
            with open(filepath, 'rb') as f:
                data, exp = pickle.load(f)
            
            # Solo validar si es DataFrame con columnas esperadas
            if not hasattr(data, 'columns') or 'Value' not in data.columns:
                continue
            
            # Solo validar métricas de energía
            if 'Id' not in data.columns or 'Rio' not in data['Id'].values:
                continue
            
            promedio = data['Value'].mean()
            size_kb = os.path.getsize(filepath) / 1024
            
            # Detectar si está en kWh (promedio > 1000 GWh es sospechoso)
            if promedio > GWH_MAX_REASONABLE:
                invalid.append({
                    'file': filename,
                    'path': filepath,
                    'promedio': promedio,
                    'size_kb': size_kb,
                    'error': 'Valores en kWh (debería ser GWh)'
                })
                logger.error(f"❌ CACHE INVÁLIDO: {filename[:40]}... promedio={promedio:.0f} (> {GWH_MAX_REASONABLE})")
            
            # Detectar sobre-conversión
            elif promedio < GWH_MIN_REASONABLE and promedio > 0:
                invalid.append({
                    'file': filename,
                    'path': filepath,
                    'promedio': promedio,
                    'size_kb': size_kb,
                    'error': 'Valores demasiado pequeños (sobre-convertido?)'
                })
                logger.warning(f"⚠️ CACHE SOSPECHOSO: {filename[:40]}... promedio={promedio:.6f} (< {GWH_MIN_REASONABLE})")
            
            else:
                valid.append({
                    'file': filename,
                    'promedio': promedio,
                    'size_kb': size_kb
                })
        
        except Exception as e:
            logger.debug(f"No se pudo validar {filename}: {e}")
    
    return valid, invalid

def clean_invalid_caches(auto_delete=False):
    """
    Limpia caches con unidades incorrectas
    auto_delete: Si True, elimina automáticamente. Si False, solo reporta.
    """
    valid, invalid = validate_cache_units()
    
    if not invalid:
        logger.info("✅ Todos los caches tienen unidades correctas")
        return 0
    
    logger.warning(f"⚠️ Encontrados {len(invalid)} caches con unidades incorrectas:")
    
    deleted_count = 0
    for item in invalid:
        logger.warning(f"   - {item['file'][:50]}... ({item['size_kb']:.1f}KB, {item['error']})")
        
        if auto_delete:
            try:
                os.remove(item['path'])
                deleted_count += 1
                logger.info(f"   🗑️  Eliminado: {item['file']}")
            except Exception as e:
                logger.error(f"   ❌ Error eliminando: {e}")
    
    if auto_delete:
        logger.info(f"✅ Limpieza completada: {deleted_count}/{len(invalid)} caches eliminados")
    else:
        logger.info(f"💡 Ejecuta clean_invalid_caches(auto_delete=True) para eliminarlos")
    
    return len(invalid)

def validate_single_cache_data(data, metric_name):
    """
    Valida que un DataFrame tenga unidades correctas ANTES de guardar
    Retorna: (is_valid, error_message)
    """
    if data is None or not hasattr(data, 'columns'):
        return True, None  # No validar datos no-DataFrame
    
    if 'Value' not in data.columns:
        return True, None  # No tiene Value, no aplicable
    
    if metric_name not in METRICS_MUST_BE_GWH:
        return True, None  # No es métrica de energía crítica
    
    promedio = data['Value'].mean()
    
    if promedio > GWH_MAX_REASONABLE:
        return False, f"Valores parecen estar en kWh (promedio={promedio:.0f}, esperado <{GWH_MAX_REASONABLE} GWh)"
    
    if promedio < GWH_MIN_REASONABLE and promedio > 0:
        return False, f"Valores sospechosamente pequeños (promedio={promedio:.6f}, esperado >{GWH_MIN_REASONABLE} GWh)"
    
    return True, None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    print("="*80)
    print("🔍 VALIDADOR DE CACHES - Sistema de Prevención de Errores de Unidad")
    print("="*80)
    
    valid, invalid = validate_cache_units()
    
    print(f"\n📊 RESUMEN:")
    print(f"   ✅ Caches válidos: {len(valid)}")
    print(f"   ❌ Caches inválidos: {len(invalid)}")
    
    if invalid:
        print(f"\n⚠️  ACCIÓN REQUERIDA:")
        print(f"   Ejecuta: clean_invalid_caches(auto_delete=True)")
        print(f"   O reinicia el servidor para regenerar caches")
    else:
        print(f"\n✅ Sistema de cache saludable")
    
    print("="*80)
