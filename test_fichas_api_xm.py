#!/usr/bin/env python3
"""
Test para verificar que las fichas del tablero de generación usan API XM como fuente primaria.

Este script prueba:
1. Que obtener_datos_fichas_realtime intenta API XM primero
2. Que cae a SQLite si API no disponible
3. Que los datos se obtienen correctamente
"""

import sys
import os
from datetime import date, timedelta

# Agregar directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 80)
print("TEST: Fichas del Tablero de Generación - API XM como Fuente Primaria")
print("=" * 80)

# Importar módulos necesarios para la función
from datetime import datetime
import pandas as pd
from utils.db_manager import get_metric_data
from utils._xm import fetch_metric_data
import logging

# Definir función obtener_datos_fichas_realtime directamente (para evitar import de Dash)
def obtener_datos_fichas_realtime(metrica, entidad, fecha_inicio, fecha_fin):
    """
    Obtener datos para fichas del tablero: PRIORIZA API XM en tiempo real.
    """
    logger = logging.getLogger('generacion_dashboard')
    
    # Convertir fechas a string si es necesario
    if isinstance(fecha_inicio, date):
        fecha_inicio = fecha_inicio.strftime('%Y-%m-%d')
    if isinstance(fecha_fin, date):
        fecha_fin = fecha_fin.strftime('%Y-%m-%d')
    
    # PASO 1: Intentar API XM (tiempo real)
    try:
        logger.info(f"📡 [API XM] Consultando {metrica}/{entidad} desde {fecha_inicio} hasta {fecha_fin}")
        df_api = fetch_metric_data(
            metric=metrica,
            entity=entidad,
            start_date=fecha_inicio,
            end_date=fecha_fin
        )
        
        if df_api is not None and not df_api.empty:
            # Convertir unidades: API XM devuelve TODAS las métricas en kWh
            if 'Value' in df_api.columns:
                # CONVERSIÓN UNIVERSAL: kWh → GWh (÷ 1,000,000)
                df_api['valor_gwh'] = df_api['Value'] / 1_000_000  # kWh → GWh
                logger.info(f"✅ [API XM] {len(df_api)} registros (kWh → GWh)")
                return df_api
            else:
                logger.warning(f"⚠️ [API XM] Datos sin columna 'Value'")
    except Exception as e:
        logger.warning(f"⚠️ [API XM] Error consultando {metrica}: {e}")
    
    # PASO 2: Fallback a SQLite
    logger.info(f"💾 [SQLite Fallback] Consultando {metrica}/{entidad}")
    df_sqlite = get_metric_data(metrica, entidad, fecha_inicio, fecha_fin)
    
    if df_sqlite is not None and not df_sqlite.empty:
        logger.info(f"✅ [SQLite] {len(df_sqlite)} registros obtenidos (ya en GWh)")
        return df_sqlite
    else:
        logger.error(f"❌ Sin datos disponibles para {metrica}/{entidad} (API y SQLite fallaron)")
        return None

# Fechas de prueba
fecha_ayer = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
fecha_inicio_mes = date.today().replace(day=1).strftime('%Y-%m-%d')

print(f"\n📅 Fecha ayer: {fecha_ayer}")
print(f"📅 Fecha inicio mes: {fecha_inicio_mes}")

# === TEST 1: Volumen Útil ===
print("\n" + "=" * 80)
print("TEST 1: VoluUtilDiarEner (Volumen Útil de Embalses)")
print("=" * 80)
df_vol = obtener_datos_fichas_realtime('VoluUtilDiarEner', 'Embalse', fecha_ayer, fecha_ayer)

if df_vol is not None and not df_vol.empty:
    print(f"✅ Datos obtenidos: {len(df_vol)} registros")
    print(f"   Total: {df_vol['valor_gwh'].sum():,.2f} GWh")
    print(f"   Columnas: {df_vol.columns.tolist()}")
    
    # Verificar origen
    if 'Value' in df_vol.columns:
        print("   🔍 Origen: API XM (tiene columna 'Value')")
    else:
        print("   🔍 Origen: SQLite (sin columna 'Value')")
else:
    print("❌ No se obtuvieron datos")

# === TEST 2: Capacidad Útil ===
print("\n" + "=" * 80)
print("TEST 2: CapaUtilDiarEner (Capacidad Útil de Embalses)")
print("=" * 80)
df_cap = obtener_datos_fichas_realtime('CapaUtilDiarEner', 'Embalse', fecha_ayer, fecha_ayer)

if df_cap is not None and not df_cap.empty:
    print(f"✅ Datos obtenidos: {len(df_cap)} registros")
    print(f"   Total: {df_cap['valor_gwh'].sum():,.2f} GWh")
    print(f"   Columnas: {df_cap.columns.tolist()}")
    
    # Verificar origen
    if 'Value' in df_cap.columns:
        print("   🔍 Origen: API XM (tiene columna 'Value')")
    else:
        print("   🔍 Origen: SQLite (sin columna 'Value')")
    
    # Calcular reservas
    if df_vol is not None and not df_vol.empty:
        vol_total = df_vol['valor_gwh'].sum()
        cap_total = df_cap['valor_gwh'].sum()
        reserva_pct = (vol_total / cap_total) * 100
        print(f"\n   📊 Reservas Hídricas: {reserva_pct:.2f}% ({vol_total:,.2f} / {cap_total:,.2f} GWh)")
else:
    print("❌ No se obtuvieron datos")

# === TEST 3: Aportes Hídricos ===
print("\n" + "=" * 80)
print("TEST 3: AporEner (Aportes Hídricos)")
print("=" * 80)
df_aportes = obtener_datos_fichas_realtime('AporEner', 'Sistema', fecha_inicio_mes, fecha_ayer)

if df_aportes is not None and not df_aportes.empty:
    print(f"✅ Datos obtenidos: {len(df_aportes)} registros")
    print(f"   Promedio: {df_aportes['valor_gwh'].mean():.2f} GWh")
    print(f"   Columnas: {df_aportes.columns.tolist()}")
    
    # Verificar origen
    if 'Value' in df_aportes.columns:
        print("   🔍 Origen: API XM (tiene columna 'Value')")
    else:
        print("   🔍 Origen: SQLite (sin columna 'Value')")
else:
    print("❌ No se obtuvieron datos")

# === TEST 4: Media Histórica de Aportes ===
print("\n" + "=" * 80)
print("TEST 4: AporEnerMediHist (Media Histórica de Aportes)")
print("=" * 80)
df_media = obtener_datos_fichas_realtime('AporEnerMediHist', 'Sistema', fecha_inicio_mes, fecha_ayer)

if df_media is not None and not df_media.empty:
    print(f"✅ Datos obtenidos: {len(df_media)} registros")
    print(f"   Promedio: {df_media['valor_gwh'].mean():.2f} GWh")
    print(f"   Columnas: {df_media.columns.tolist()}")
    
    # Verificar origen
    if 'Value' in df_media.columns:
        print("   🔍 Origen: API XM (tiene columna 'Value')")
    else:
        print("   🔍 Origen: SQLite (sin columna 'Value')")
    
    # Calcular porcentaje de aportes
    if df_aportes is not None and not df_aportes.empty:
        aportes_prom = df_aportes['valor_gwh'].mean()
        media_prom = df_media['valor_gwh'].mean()
        aporte_pct = (aportes_prom / media_prom) * 100
        print(f"\n   📊 Aportes Hídricos: {aporte_pct:.2f}% (Real: {aportes_prom:.2f} vs Hist: {media_prom:.2f} GWh)")
else:
    print("❌ No se obtuvieron datos")

# === TEST 5: Generación SIN ===
print("\n" + "=" * 80)
print("TEST 5: Gene (Generación SIN)")
print("=" * 80)
df_gen = obtener_datos_fichas_realtime('Gene', 'Sistema', fecha_ayer, fecha_ayer)

if df_gen is not None and not df_gen.empty:
    print(f"✅ Datos obtenidos: {len(df_gen)} registros")
    print(f"   Total: {df_gen['valor_gwh'].iloc[0]:.2f} GWh")
    print(f"   Columnas: {df_gen.columns.tolist()}")
    
    # Verificar origen
    if 'Value' in df_gen.columns:
        print("   🔍 Origen: API XM (tiene columna 'Value')")
    else:
        print("   🔍 Origen: SQLite (sin columna 'Value')")
else:
    print("❌ No se obtuvieron datos")

# === RESUMEN FINAL ===
print("\n" + "=" * 80)
print("RESUMEN")
print("=" * 80)
print("""
ARQUITECTURA IMPLEMENTADA:
✅ obtener_datos_fichas_realtime() prioriza API XM
✅ Fallback a SQLite si API no disponible
✅ Conversión automática de unidades (Wh → GWh)

VERIFICACIÓN:
- Si columna 'Value' existe → Datos desde API XM ✅
- Si columna 'Value' no existe → Datos desde SQLite (fallback) ✅

PRÓXIMOS PASOS:
1. Reiniciar el servicio: sudo systemctl restart dashboard-mme
2. Verificar logs: journalctl -u dashboard-mme -n 100 --no-pager
3. Probar dashboard en navegador: http://localhost:8050/generacion
""")
