#!/usr/bin/env python3
"""
Monitor de progreso de ETL DemaCome/Agente
Muestra progreso en tiempo real
"""

import sys
import time
from datetime import datetime

sys.path.insert(0, '/home/admonctrlxm/server')
from utils import db_manager

def mostrar_progreso():
    """Muestra el progreso actual de DemaCome/Agente"""
    
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        
        # Obtener estadísticas
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT fecha) as dias,
                MIN(fecha) as primera,
                MAX(fecha) as ultima
            FROM metrics
            WHERE metrica = 'DemaCome' AND entidad = 'Agente'
        """)
        
        result = cursor.fetchone()
        dias = result[0] if result[0] else 0
        primera = result[1]
        ultima = result[2]
        
        # Calcular progreso
        dias_esperados = 2155
        completitud = (dias / dias_esperados * 100) if dias_esperados > 0 else 0
        dias_faltantes = dias_esperados - dias
        
        # Progreso por año
        cursor.execute("""
            SELECT 
                strftime('%Y', fecha) as año,
                COUNT(DISTINCT fecha) as dias
            FROM metrics
            WHERE metrica = 'DemaCome' AND entidad = 'Agente'
            GROUP BY año
            ORDER BY año
        """)
        
        años = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Mostrar resumen
        print(f"\n{'='*80}")
        print(f"📊 ETL DemaCome/Agente - Progreso Actual")
        print(f"{'='*80}")
        print(f"📅 Actualizado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\n📈 Progreso Global:")
        print(f"   Días cargados: {dias:,}/{dias_esperados:,} ({completitud:.1f}%)")
        print(f"   Días faltantes: {dias_faltantes:,}")
        print(f"   Rango actual: {primera} → {ultima}")
        
        print(f"\n📅 Progreso por Año:")
        for año in ['2020', '2021', '2022', '2023', '2024', '2025']:
            dias_año = años.get(año, 0)
            if año == '2020' or año == '2024':
                dias_totales = 366  # Años bisiestos
            elif año == '2025':
                dias_totales = 329  # Hasta nov 24
            else:
                dias_totales = 365
            
            progreso_año = (dias_año / dias_totales * 100) if dias_totales > 0 else 0
            barra_llena = int(progreso_año / 5)
            barra_vacia = 20 - barra_llena
            barra = '█' * barra_llena + '░' * barra_vacia
            
            estado = "✅" if progreso_año >= 95 else "🔄" if progreso_año > 0 else "⏳"
            print(f"   {año}: {barra} {progreso_año:5.1f}% ({dias_año:3d}/{dias_totales}) {estado}")
        
        # Barra de progreso global
        barra_llena = int(completitud / 5)
        barra_vacia = 20 - barra_llena
        barra_global = '█' * barra_llena + '░' * barra_vacia
        
        print(f"\n🎯 Progreso Total:")
        print(f"   [{barra_global}] {completitud:.1f}%")
        
        # Estimación de tiempo restante (si hay progreso reciente)
        print(f"\n💡 Tip: Usa Ctrl+C para salir del monitor")
        print(f"{'='*80}\n")

if __name__ == "__main__":
    print("\n🔄 Monitor de ETL DemaCome/Agente")
    print("Actualizándose cada 60 segundos...\n")
    
    try:
        while True:
            mostrar_progreso()
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n\n👋 Monitor detenido por el usuario\n")
