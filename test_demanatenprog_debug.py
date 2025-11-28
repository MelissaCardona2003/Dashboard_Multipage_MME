#!/usr/bin/env python3
"""
Test script para investigar DemaNoAtenProg/Area
Verifica disponibilidad de datos en API XM
"""

import sys
from datetime import datetime, timedelta
import traceback

sys.path.insert(0, '/home/admonctrlxm/server')

from pydataxm import pydataxm

def test_demaNoAtenProg_api():
    """
    Prueba la API XM para DemaNoAtenProg/Area en diferentes rangos
    """
    print(f"\n{'='*80}")
    print("🔍 DIAGNÓSTICO: DemaNoAtenProg/Area")
    print(f"{'='*80}\n")
    
    objective_function = pydataxm.ReadDB()
    
    # Definir rangos de prueba
    rangos_prueba = [
        ("2025-11-01", "2025-11-24", "Últimos días (donde SÍ hay datos)"),
        ("2020-01-01", "2020-01-07", "Inicio histórico (2020)"),
        ("2022-01-01", "2022-01-07", "Mitad del rango (2022)"),
        ("2024-01-01", "2024-01-07", "Reciente (2024)")
    ]
    
    for start_date, end_date, descripcion in rangos_prueba:
        print(f"\n📅 Rango: {start_date} → {end_date} ({descripcion})")
        print(f"-" * 80)
        
        try:
            df = objective_function.request_data(
                'DemaNoAtenProg',
                'Area',
                start_date,
                end_date
            )
            
            if df is None:
                print(f"⚠️  API devolvió None")
                continue
                
            if df.empty:
                print(f"⚠️  DataFrame vacío - NO HAY DATOS EN API XM")
                continue
            
            # Mostrar información
            print(f"✅ Datos recibidos: {len(df)} filas")
            print(f"📊 Columnas: {list(df.columns)}")
            
            # Contar fechas únicas
            if 'Date' in df.columns:
                fechas_unicas = df['Date'].nunique()
                print(f"📅 Fechas distintas: {fechas_unicas}")
            
            # Contar áreas únicas
            if 'Name' in df.columns:
                areas = df['Name'].nunique()
                print(f"🏷️  Áreas distintas: {areas}")
                print(f"   Áreas: {df['Name'].unique()[:5].tolist()}")
            
            # Mostrar primeras filas
            print(f"\n📄 Primeras 3 filas:")
            print(df.head(3).to_string())
            
        except Exception as e:
            print(f"❌ ERROR: {type(e).__name__}: {str(e)}")
            if "404" in str(e) or "Not Found" in str(e):
                print(f"   → API XM no tiene datos para este rango")
            else:
                print(f"\n📋 Traceback:")
                traceback.print_exc()

def analizar_gaps_sqlite():
    """
    Analiza los gaps en SQLite para DemaNoAtenProg/Area
    """
    print(f"\n{'='*80}")
    print("🔍 ANÁLISIS DE GAPS EN SQLITE")
    print(f"{'='*80}\n")
    
    from utils import db_manager
    
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        
        # Obtener estadísticas
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT fecha) as dias,
                COUNT(DISTINCT recurso) as areas,
                MIN(fecha) as primera,
                MAX(fecha) as ultima
            FROM metrics
            WHERE metrica = 'DemaNoAtenProg' AND entidad = 'Area'
        """)
        
        result = cursor.fetchone()
        print(f"📊 Estado actual en SQLite:")
        print(f"   Total registros: {result[0]:,}")
        print(f"   Días con datos: {result[1]}")
        print(f"   Áreas: {result[2]}")
        print(f"   Rango: {result[3]} → {result[4]}")
        
        # Analizar distribución por año
        cursor.execute("""
            SELECT 
                strftime('%Y', fecha) as año,
                COUNT(DISTINCT fecha) as dias,
                COUNT(*) as registros
            FROM metrics
            WHERE metrica = 'DemaNoAtenProg' AND entidad = 'Area'
            GROUP BY año
            ORDER BY año
        """)
        
        print(f"\n📅 Distribución por año:")
        for row in cursor.fetchall():
            print(f"   {row[0]}: {row[1]} días ({row[2]:,} registros)")

def main():
    print("\n" + "="*80)
    print("🔍 DIAGNÓSTICO DE DEMANATENPROG/AREA")
    print("="*80)
    
    # Analizar SQLite primero
    analizar_gaps_sqlite()
    
    # Probar API
    test_demaNoAtenProg_api()
    
    print("\n" + "="*80)
    print("✅ DIAGNÓSTICO COMPLETADO")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
