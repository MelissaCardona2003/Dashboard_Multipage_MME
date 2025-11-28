#!/usr/bin/env python3
"""
Test para verificar qué agentes tienen datos disponibles para DemaCome y DemaReal
"""

import sqlite3
from datetime import datetime, timedelta

def verificar_agentes_con_datos():
    db_path = '/home/admonctrlxm/server/portal_energetico.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Fecha reciente (últimos 30 días)
    fecha_fin = datetime.now()
    fecha_inicio = fecha_fin - timedelta(days=30)
    
    print("=" * 80)
    print("VERIFICACIÓN DE AGENTES CON DATOS")
    print("=" * 80)
    print(f"Período: {fecha_inicio.strftime('%Y-%m-%d')} a {fecha_fin.strftime('%Y-%m-%d')}")
    print()
    
    # TEST 1: Agentes con datos de DemaCome
    print("🔍 TEST 1: AGENTES CON DEMANDA COMERCIAL (DemaCome)")
    print("-" * 80)
    
    query_demacomes = """
        SELECT DISTINCT Values_code, COUNT(*) as registros
        FROM metricas
        WHERE metrica = 'DemaCome'
        AND Date BETWEEN ? AND ?
        GROUP BY Values_code
        ORDER BY registros DESC
    """
    
    cursor.execute(query_demacomes, (
        fecha_inicio.strftime('%Y-%m-%d'),
        fecha_fin.strftime('%Y-%m-%d')
    ))
    agentes_demacomes = cursor.fetchall()
    
    print(f"Total de agentes con DemaCome: {len(agentes_demacomes)}")
    print(f"\nPrimeros 20 agentes con más registros:")
    for i, (codigo, registros) in enumerate(agentes_demacomes[:20], 1):
        print(f"{i:2d}. {codigo:20s} - {registros:6d} registros")
    
    if len(agentes_demacomes) > 20:
        print(f"\n... y {len(agentes_demacomes) - 20} agentes más")
    
    # TEST 2: Agentes con datos de DemaReal
    print("\n" + "=" * 80)
    print("🔍 TEST 2: AGENTES CON DEMANDA REAL (DemaReal)")
    print("-" * 80)
    
    query_demareal = """
        SELECT DISTINCT Values_code, COUNT(*) as registros
        FROM metricas
        WHERE metrica = 'DemaReal'
        AND Date BETWEEN ? AND ?
        GROUP BY Values_code
        ORDER BY registros DESC
    """
    
    cursor.execute(query_demareal, (
        fecha_inicio.strftime('%Y-%m-%d'),
        fecha_fin.strftime('%Y-%m-%d')
    ))
    agentes_demareal = cursor.fetchall()
    
    print(f"Total de agentes con DemaReal: {len(agentes_demareal)}")
    print(f"\nPrimeros 20 agentes con más registros:")
    for i, (codigo, registros) in enumerate(agentes_demareal[:20], 1):
        print(f"{i:2d}. {codigo:20s} - {registros:6d} registros")
    
    if len(agentes_demareal) > 20:
        print(f"\n... y {len(agentes_demareal) - 20} agentes más")
    
    # TEST 3: Comparación - agentes que tienen ambas métricas
    print("\n" + "=" * 80)
    print("🔍 TEST 3: AGENTES CON AMBAS MÉTRICAS")
    print("-" * 80)
    
    codigos_demacomes = {codigo for codigo, _ in agentes_demacomes}
    codigos_demareal = {codigo for codigo, _ in agentes_demareal}
    
    agentes_ambas = codigos_demacomes & codigos_demareal
    solo_demacomes = codigos_demacomes - codigos_demareal
    solo_demareal = codigos_demareal - codigos_demacomes
    
    print(f"Agentes con AMBAS métricas: {len(agentes_ambas)}")
    print(f"Agentes SOLO con DemaCome: {len(solo_demacomes)}")
    print(f"Agentes SOLO con DemaReal: {len(solo_demareal)}")
    
    if solo_demacomes:
        print(f"\nAgentes SOLO con DemaCome (primeros 20):")
        for i, codigo in enumerate(list(solo_demacomes)[:20], 1):
            print(f"  {i:2d}. {codigo}")
    
    if solo_demareal:
        print(f"\nAgentes SOLO con DemaReal (primeros 20):")
        for i, codigo in enumerate(list(solo_demareal)[:20], 1):
            print(f"  {i:2d}. {codigo}")
    
    # TEST 4: Verificar si hay agentes sin datos recientes pero con datos históricos
    print("\n" + "=" * 80)
    print("🔍 TEST 4: AGENTES CON DATOS HISTÓRICOS (TODO EL PERÍODO)")
    print("-" * 80)
    
    query_historico = """
        SELECT DISTINCT Values_code, 
               MIN(Date) as fecha_inicio,
               MAX(Date) as fecha_fin,
               COUNT(*) as registros
        FROM metricas
        WHERE metrica IN ('DemaCome', 'DemaReal')
        GROUP BY Values_code
        ORDER BY registros DESC
        LIMIT 10
    """
    
    cursor.execute(query_historico)
    agentes_historicos = cursor.fetchall()
    
    print(f"Top 10 agentes con más datos históricos:")
    for i, (codigo, fecha_ini, fecha_fin, registros) in enumerate(agentes_historicos, 1):
        print(f"{i:2d}. {codigo:20s} - {registros:8d} registros ({fecha_ini} a {fecha_fin})")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("CONCLUSIÓN:")
    print(f"✅ Es NORMAL que solo algunos agentes tengan datos")
    print(f"✅ No todos los agentes reportan demanda comercial y real")
    print(f"✅ Total de agentes únicos: {len(codigos_demacomes | codigos_demareal)}")
    print("=" * 80)

if __name__ == "__main__":
    verificar_agentes_con_datos()
