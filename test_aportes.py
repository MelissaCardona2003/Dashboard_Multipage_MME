#!/usr/bin/env python3
"""
Script para probar el cálculo de aportes hídricos
"""
import sys
sys.path.insert(0, '/home/admonctrlxm/server')

from utils._xm import fetch_metric_data
import pandas as pd
from datetime import datetime

def test_aportes_hidricos(fecha):
    """
    Prueba el cálculo de aportes hídricos
    """
    print(f"\n{'='*60}")
    print(f"Probando Aportes Hídricos para fecha: {fecha}")
    print(f"{'='*60}\n")
    
    # Calcular el rango desde el primer día del mes hasta la fecha final
    fecha_final = pd.to_datetime(fecha)
    fecha_inicio = fecha_final.replace(day=1)
    fecha_inicio_str = fecha_inicio.strftime('%Y-%m-%d')
    fecha_final_str = fecha_final.strftime('%Y-%m-%d')
    
    print(f"Período: {fecha_inicio_str} a {fecha_final_str}\n")
    
    # 1. Probar métrica principal de Aportes Energía
    print("1. Probando AporEner (métrica principal)...")
    aportes = fetch_metric_data('AporEner', 'Sistema', fecha_inicio_str, fecha_final_str)
    if aportes is not None and not aportes.empty:
        print(f"   ✓ Datos encontrados: {len(aportes)} registros")
        print(f"   Promedio: {aportes['Value'].mean():.2f}")
        print(f"   Primeros valores:\n{aportes.head()}")
    else:
        print("   ✗ Sin datos")
    
    # 2. Probar métrica alternativa AportesDiariosEnergia
    print("\n2. Probando AportesDiariosEnergia (alternativa 1)...")
    aportes_alt1 = fetch_metric_data('AportesDiariosEnergia', 'Sistema', fecha_inicio_str, fecha_final_str)
    if aportes_alt1 is not None and not aportes_alt1.empty:
        print(f"   ✓ Datos encontrados: {len(aportes_alt1)} registros")
        print(f"   Promedio: {aportes_alt1['Value'].mean():.2f}")
    else:
        print("   ✗ Sin datos")
    
    # 3. Probar métrica alternativa AportesEnergia
    print("\n3. Probando AportesEnergia (alternativa 2)...")
    aportes_alt2 = fetch_metric_data('AportesEnergia', 'Sistema', fecha_inicio_str, fecha_final_str)
    if aportes_alt2 is not None and not aportes_alt2.empty:
        print(f"   ✓ Datos encontrados: {len(aportes_alt2)} registros")
        print(f"   Promedio: {aportes_alt2['Value'].mean():.2f}")
    else:
        print("   ✗ Sin datos")
    
    # 4. Probar Media Histórica
    print("\n4. Probando AporEnerMediHist (media histórica)...")
    media_hist = fetch_metric_data('AporEnerMediHist', 'Sistema', fecha_inicio_str, fecha_final_str)
    if media_hist is not None and not media_hist.empty:
        print(f"   ✓ Datos encontrados: {len(media_hist)} registros")
        print(f"   Promedio: {media_hist['Value'].mean():.2f}")
        print(f"   Primeros valores:\n{media_hist.head()}")
    else:
        print("   ✗ Sin datos")
    
    # 5. Calcular el porcentaje si tenemos ambos datos
    print("\n" + "="*60)
    print("RESULTADO FINAL:")
    print("="*60)
    
    if aportes is not None and not aportes.empty and media_hist is not None and not media_hist.empty:
        aportes_valor = aportes['Value'].mean()
        media_valor = media_hist['Value'].mean()
        if media_valor > 0:
            porcentaje = round((aportes_valor / media_valor) * 100, 2)
            print(f"✓ Aportes: {aportes_valor:.2f} GWh")
            print(f"✓ Media Histórica: {media_valor:.2f} GWh")
            print(f"✓ Porcentaje: {porcentaje}%")
            return porcentaje, aportes_valor
        else:
            print("✗ Media histórica es cero, no se puede calcular porcentaje")
    else:
        print("✗ Faltan datos (aportes o media histórica)")
        print(f"   - Aportes disponibles: {'Sí' if aportes is not None and not aportes.empty else 'No'}")
        print(f"   - Media histórica disponible: {'Sí' if media_hist is not None and not media_hist.empty else 'No'}")
    
    return None, None

if __name__ == "__main__":
    # Probar con varias fechas
    fechas = [
        "2025-10-31",
        "2025-10-01", 
        "2025-09-30",
    ]
    
    for fecha in fechas:
        test_aportes_hidricos(fecha)
        print("\n")
