#!/usr/bin/env python3
"""
Test del fix para VoluUtilDiarEner/Embalse y CapaUtilDiarEner/Embalse
"""

import sys
import logging
from datetime import datetime, timedelta

sys.path.insert(0, '/home/admonctrlxm/server')

from etl import etl_xm_to_sqlite
from pydataxm import pydataxm
from utils import db_manager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

def test_embalse_metric(metric_name):
    """
    Prueba cargar una semana de datos para una métrica de Embalse
    """
    print(f"\n{'='*80}")
    print(f"🧪 PROBANDO: {metric_name}/Embalse")
    print(f"{'='*80}\n")
    
    # Probar con una semana de datos históricos
    fecha_fin = datetime(2020, 1, 7)
    fecha_inicio = datetime(2020, 1, 1)
    
    obj_api = pydataxm.ReadDB()
    
    config = {
        'metric': metric_name,
        'entity': 'Embalse',
        'conversion': 'kWh_a_GWh',
        'dias_history': 7,
        'batch_size': 7
    }
    
    try:
        registros = etl_xm_to_sqlite.poblar_metrica(
            obj_api,
            config,
            usar_timeout=False,
            fecha_inicio_custom=fecha_inicio.strftime('%Y-%m-%d'),
            fecha_fin_custom=fecha_fin.strftime('%Y-%m-%d')
        )
        
        print(f"\n✅ ETL completado: {registros} registros insertados")
        
        # Verificar en SQLite
        print(f"\n🔍 Verificando SQLite...")
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*), COUNT(DISTINCT fecha), COUNT(DISTINCT recurso)
                FROM metrics
                WHERE metrica = ? AND entidad = ?
                AND fecha BETWEEN ? AND ?
            """, (metric_name, 'Embalse', 
                  fecha_inicio.strftime('%Y-%m-%d'),
                  fecha_fin.strftime('%Y-%m-%d')))
            
            total, dias, embalses = cursor.fetchone()
            print(f"  📊 Total registros: {total}")
            print(f"  📅 Días distintos: {dias}")
            print(f"  🏭 Embalses distintos: {embalses}")
            
            # Mostrar algunos ejemplos
            cursor.execute("""
                SELECT fecha, recurso, valor, unidad
                FROM metrics
                WHERE metrica = ? AND entidad = ?
                ORDER BY fecha, recurso
                LIMIT 10
            """, (metric_name, 'Embalse'))
            
            print(f"\n  📄 Primeros registros:")
            for row in cursor.fetchall():
                print(f"    {row[0]} | {row[1]:20s} | {row[2]:8.2f} {row[3]}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n" + "="*80)
    print("🔧 TEST DEL FIX PARA MÉTRICAS DE EMBALSE")
    print("="*80)
    
    # Probar ambas métricas
    success1 = test_embalse_metric('VoluUtilDiarEner')
    success2 = test_embalse_metric('CapaUtilDiarEner')
    
    print("\n" + "="*80)
    if success1 and success2:
        print("✅ AMBAS MÉTRICAS FUNCIONAN CORRECTAMENTE")
        print("="*80)
        print("\n💡 Siguiente paso: Ejecutar ETL completo para cargar 5 años de datos\n")
    else:
        print("❌ ERRORES DETECTADOS - REVISAR LOGS")
        print("="*80 + "\n")

if __name__ == "__main__":
    main()
