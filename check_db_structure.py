#!/usr/bin/env python3
"""
Verificar estructura de la base de datos
"""

import sqlite3

db_path = '/home/admonctrlxm/server/portal_energetico.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Obtener todas las tablas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tablas = cursor.fetchall()

print("TABLAS EN LA BASE DE DATOS:")
print("=" * 80)
for tabla in tablas:
    print(f"  - {tabla[0]}")
    
    # Mostrar estructura de cada tabla
    cursor.execute(f"PRAGMA table_info({tabla[0]})")
    columnas = cursor.fetchall()
    print(f"    Columnas:")
    for col in columnas:
        print(f"      - {col[1]} ({col[2]})")
    print()

conn.close()
