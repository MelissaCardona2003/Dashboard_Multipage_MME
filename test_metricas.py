#!/usr/bin/env python3
"""
Script para verificar métricas de generación disponibles en XM
"""
import sys
from datetime import date, timedelta
sys.path.append('/home/admonctrlxm/server')

def test_metricas_generacion():
    from utils._xm import get_objetoAPI
    
    objetoAPI = get_objetoAPI()
    if not objetoAPI:
        print("❌ No se pudo conectar a la API XM")
        return
    
    print("🔍 Verificando métricas de generación disponibles...")
    
    # Obtener lista de métricas
    try:
        metricas = objetoAPI.listar_metricas()
        print(f"📊 Total métricas disponibles: {len(metricas)}")
        
        # Filtrar métricas relacionadas con generación
        metricas_gene = [m for m in metricas if 'Gene' in str(m) or 'Gener' in str(m)]
        print(f"📊 Métricas de generación encontradas: {len(metricas_gene)}")
        
        for metrica in metricas_gene[:10]:  # Mostrar solo las primeras 10
            print(f"  - {metrica}")
            
        # Probar diferentes combinaciones
        fecha_fin = date.today() - timedelta(days=1)
        fecha_inicio = fecha_fin
        
        print(f"\n🔍 Probando métricas para fecha: {fecha_inicio}")
        
        # Probar Gene/Recurso
        try:
            df1 = objetoAPI.request_data('Gene', 'Recurso', fecha_inicio, fecha_fin)
            print(f"✅ Gene/Recurso: {len(df1) if df1 is not None else 0} registros")
        except Exception as e:
            print(f"❌ Gene/Recurso: {e}")
        
        # Probar Gene/Planta  
        try:
            df2 = objetoAPI.request_data('Gene', 'Planta', fecha_inicio, fecha_fin)
            print(f"✅ Gene/Planta: {len(df2) if df2 is not None else 0} registros")
        except Exception as e:
            print(f"❌ Gene/Planta: {e}")
            
        # Probar Gene/Sistema
        try:
            df3 = objetoAPI.request_data('Gene', 'Sistema', fecha_inicio, fecha_fin)
            print(f"✅ Gene/Sistema: {len(df3) if df3 is not None else 0} registros")
        except Exception as e:
            print(f"❌ Gene/Sistema: {e}")
            
        # Probar otras variantes
        variantes = [
            ('Genera', 'Recurso'),
            ('Generacion', 'Planta'),
            ('Generation', 'Resource'),
            ('Gene', 'Type')
        ]
        
        for metrica, entidad in variantes:
            try:
                df = objetoAPI.request_data(metrica, entidad, fecha_inicio, fecha_fin)
                print(f"✅ {metrica}/{entidad}: {len(df) if df is not None else 0} registros")
            except Exception as e:
                print(f"❌ {metrica}/{entidad}: Error")
        
    except Exception as e:
        print(f"❌ Error general: {e}")

if __name__ == "__main__":
    test_metricas_generacion()