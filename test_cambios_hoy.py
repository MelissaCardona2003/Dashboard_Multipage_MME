#!/usr/bin/env python3
"""
Test de validación de cambios realizados hoy:
1. ETL procesa correctamente métricas catálogo (sin columna 'Value')
2. ETL procesa correctamente métricas numéricas (con columna 'Value')
3. Dashboard de distribución consulta datos correctamente
4. Dashboard de distribución renderiza sin errores
"""

import sqlite3
import sys
import requests
from datetime import datetime, timedelta

def test_metricas_catalogo():
    """Verificar que las métricas catálogo se guardaron correctamente"""
    print("\n=== TEST 1: Métricas Catálogo ===")
    
    db = sqlite3.connect('portal_energetico.db')
    cursor = db.cursor()
    
    # Verificar ListadoRecursos
    cursor.execute("SELECT COUNT(*) FROM catalogos WHERE catalogo = 'ListadoRecursos'")
    count = cursor.fetchone()[0]
    
    if count > 0:
        print(f"✅ ListadoRecursos: {count} registros")
    else:
        print(f"❌ ListadoRecursos: No hay datos")
        return False
    
    # Verificar ListadoEmbalses
    cursor.execute("SELECT COUNT(*) FROM catalogos WHERE catalogo = 'ListadoEmbalses'")
    count = cursor.fetchone()[0]
    
    if count > 0:
        print(f"✅ ListadoEmbalses: {count} registros")
    else:
        print(f"❌ ListadoEmbalses: No hay datos")
        return False
    
    db.close()
    return True


def test_metricas_numericas():
    """Verificar que las métricas numéricas se guardaron con conversión correcta"""
    print("\n=== TEST 2: Métricas Numéricas ===")
    
    db = sqlite3.connect('portal_energetico.db')
    cursor = db.cursor()
    
    # Verificar DemaReal
    cursor.execute("""
        SELECT COUNT(*), MIN(fecha), MAX(fecha)
        FROM metrics
        WHERE metrica = 'DemaReal'
    """)
    row = cursor.fetchone()
    
    if row[0] > 0:
        print(f"✅ DemaReal: {row[0]} registros (rango: {row[1]} a {row[2]})")
    else:
        print(f"❌ DemaReal: No hay datos")
        return False
    
    # Verificar que los valores están en GWh (no en Wh)
    cursor.execute("""
        SELECT valor_gwh, unidad
        FROM metrics
        WHERE metrica = 'DemaReal'
        LIMIT 5
    """)
    
    for valor, unidad in cursor.fetchall():
        if unidad != 'GWh':
            print(f"❌ ERROR: Unidad incorrecta: {unidad} (debería ser GWh)")
            return False
        if valor > 1000:  # Valores muy grandes indican que no se convirtió
            print(f"❌ ERROR: Valor muy grande: {valor} GWh (posiblemente no se convirtió)")
            return False
    
    print(f"✅ Unidades correctas: GWh")
    
    db.close()
    return True


def test_datos_distribucion():
    """Verificar que los datos de distribución están completos"""
    print("\n=== TEST 3: Datos de Distribución ===")
    
    db = sqlite3.connect('portal_energetico.db')
    cursor = db.cursor()
    
    # Verificar DemaRealReg
    cursor.execute("""
        SELECT COUNT(*), MIN(fecha), MAX(fecha)
        FROM metrics
        WHERE metrica = 'DemaRealReg' AND entidad = 'Sistema'
    """)
    row = cursor.fetchone()
    
    if row[0] > 0:
        print(f"✅ DemaRealReg: {row[0]} registros (rango: {row[1]} a {row[2]})")
    else:
        print(f"❌ DemaRealReg: No hay datos")
        return False
    
    # Verificar DemaRealNoReg
    cursor.execute("""
        SELECT COUNT(*), MIN(fecha), MAX(fecha)
        FROM metrics
        WHERE metrica = 'DemaRealNoReg' AND entidad = 'Sistema'
    """)
    row = cursor.fetchone()
    
    if row[0] > 0:
        print(f"✅ DemaRealNoReg: {row[0]} registros (rango: {row[1]} a {row[2]})")
    else:
        print(f"❌ DemaRealNoReg: No hay datos")
        return False
    
    # Verificar DemaCome
    cursor.execute("""
        SELECT COUNT(*), MIN(fecha), MAX(fecha)
        FROM metrics
        WHERE metrica = 'DemaCome' AND entidad = 'Sistema'
    """)
    row = cursor.fetchone()
    
    if row[0] > 0:
        print(f"✅ DemaCome: {row[0]} registros (rango: {row[1]} a {row[2]})")
    else:
        print(f"❌ DemaCome: No hay datos")
        return False
    
    db.close()
    return True


def test_dashboard_distribucion():
    """Verificar que el dashboard de distribución responde correctamente"""
    print("\n=== TEST 4: Dashboard de Distribución ===")
    
    try:
        # Test página principal de distribución
        response = requests.get('http://localhost:8050/distribucion', timeout=5)
        
        if response.status_code == 200:
            print(f"✅ Dashboard /distribucion responde correctamente (HTTP {response.status_code})")
        else:
            print(f"❌ Dashboard /distribucion error: HTTP {response.status_code}")
            return False
        
        # Test que el dashboard carga datos (verificar que el contenido no está vacío)
        if len(response.text) > 1000:  # Debe tener contenido HTML
            print(f"✅ Dashboard contiene contenido válido ({len(response.text)} bytes)")
        else:
            print(f"❌ Dashboard tiene contenido insuficiente ({len(response.text)} bytes)")
            return False
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ No se pudo conectar al dashboard (¿está corriendo?)")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False


def main():
    """Ejecutar todos los tests"""
    print("="*70)
    print("VALIDACIÓN DE CAMBIOS REALIZADOS HOY")
    print("="*70)
    
    tests = [
        ("Métricas Catálogo", test_metricas_catalogo),
        ("Métricas Numéricas", test_metricas_numericas),
        ("Datos de Distribución", test_datos_distribucion),
        ("Dashboard de Distribución", test_dashboard_distribucion),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ ERROR en {name}: {e}")
            results.append((name, False))
    
    # Resumen
    print("\n" + "="*70)
    print("RESUMEN DE TESTS")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nResultado final: {passed}/{total} tests pasaron")
    
    if passed == total:
        print("\n🎉 ¡TODOS LOS TESTS PASARON!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) fallaron")
        return 1


if __name__ == "__main__":
    sys.exit(main())
