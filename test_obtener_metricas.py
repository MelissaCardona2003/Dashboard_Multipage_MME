#!/usr/bin/env python3
"""
Test directo de obtener_metricas_hidricas() para verificar que funciona con el fix
"""

import sys
sys.path.insert(0, '/home/admonctrlxm/server')

from pages.generacion import obtener_metricas_hidricas

print("=" * 80)
print("🧪 TEST: obtener_metricas_hidricas()")
print("=" * 80)

try:
    resultado = obtener_metricas_hidricas()
    
    # Si retornó algo, verificar tipo
    if resultado:
        tipo = type(resultado).__name__
        print(f"\n✅ Función ejecutada sin excepciones")
        print(f"📦 Tipo de retorno: {tipo}")
        
        # Si es HTML Div, verificar si es error o datos reales
        if hasattr(resultado, 'children'):
            print(f"📝 Contenido HTML generado correctamente")
            
            # Verificar si contiene mensaje de error
            resultado_str = str(resultado)
            if "No se pudieron obtener datos" in resultado_str:
                print("\n❌ PROBLEMA: Retornó mensaje de error")
                print("   Revisar logs arriba para ver qué métrica falló")
            else:
                print("\n✅ ÉXITO: Retornó fichas con datos reales")
        else:
            print(f"📄 Contenido: {resultado}")
    else:
        print("\n⚠️ La función retornó None o vacío")
        
except Exception as e:
    print(f"\n❌ EXCEPCIÓN CAPTURADA:")
    print(f"   Tipo: {type(e).__name__}")
    print(f"   Mensaje: {str(e)}")
    import traceback
    print("\n📋 Traceback completo:")
    traceback.print_exc()

print("\n" + "=" * 80)
