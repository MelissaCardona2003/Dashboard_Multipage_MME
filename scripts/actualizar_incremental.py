#!/usr/bin/env python3
"""
Actualización incremental del ETL - Solo datos nuevos desde última fecha en BD
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import sqlite3
from datetime import datetime, timedelta
from utils._xm import get_objetoAPI
from utils.db_manager import upsert_metrics_bulk
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'portal_energetico.db')

def obtener_ultima_fecha(metrica, entidad):
    """Obtiene la última fecha disponible en BD para una métrica"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT MAX(fecha) FROM metrics 
            WHERE metrica = ? AND entidad = ?
        """, (metrica, entidad))
        result = cursor.fetchone()[0]
        conn.close()
        return result
    except:
        return None

def actualizar_metrica(api, metrica, entidad, nombre):
    """Actualiza una métrica específica desde última fecha hasta hoy"""
    logger.info(f"\n{'='*60}")
    logger.info(f"📡 {nombre} ({metrica}/{entidad})")
    logger.info(f"{'='*60}")
    
    # Obtener última fecha en BD
    ultima_fecha_str = obtener_ultima_fecha(metrica, entidad)
    
    if ultima_fecha_str:
        ultima_fecha = datetime.strptime(ultima_fecha_str, '%Y-%m-%d').date()
        fecha_inicio = ultima_fecha - timedelta(days=3)  # 3 días de overlap por seguridad
        logger.info(f"   Última fecha en BD: {ultima_fecha}")
    else:
        # Si no hay datos, traer últimos 7 días
        fecha_inicio = datetime.now().date() - timedelta(days=7)
        logger.info(f"   Sin datos previos, trayendo últimos 7 días")
    
    fecha_fin = datetime.now().date()
    
    logger.info(f"   Rango: {fecha_inicio} a {fecha_fin}")
    
    try:
        df = api.request_data(
            metrica, 
            entidad,
            fecha_inicio.strftime('%Y-%m-%d'),
            fecha_fin.strftime('%Y-%m-%d')
        )
        
        if df is None or df.empty:
            logger.warning(f"   ⚠️  Sin datos disponibles")
            return 0
        
        # Preparar datos para inserción
        metrics_data = []
        for _, row in df.iterrows():
            fecha = row['Date'] if isinstance(row['Date'], str) else row['Date'].strftime('%Y-%m-%d')
            valor = row.get('Values_Hour24', row.get('Values_Energy', row.get('Value', 0)))
            recurso_val = row.get('Values_code', '_SISTEMA_')
            
            # Convertir Wh a GWh si es necesario
            if valor > 1000:  # Probablemente en Wh
                valor = valor / 1e9
            
            metrics_data.append((fecha, metrica, entidad, recurso_val, valor, 'GWh'))
        
        # Insertar en BD
        registros = upsert_metrics_bulk(metrics_data)
        logger.info(f"   ✅ {registros} registros actualizados")
        
        # Mostrar rango de fechas actualizado
        if 'Date' in df.columns:
            fecha_min = df['Date'].min()
            fecha_max = df['Date'].max()
            logger.info(f"   📅 Rango actualizado: {fecha_min} a {fecha_max}")
        
        return registros
        
    except Exception as e:
        logger.error(f"   ❌ Error: {e}")
        return 0

def main():
    logger.info("\n" + "="*60)
    logger.info("⚡ ACTUALIZACIÓN INCREMENTAL - SOLO DATOS NUEVOS")
    logger.info("="*60)
    logger.info(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    api = get_objetoAPI()
    
    # Métricas críticas para las fichas del dashboard
    metricas = [
        ('VoluUtilDiarEner', 'Embalse', 'Volumen Útil Diario'),
        ('CapaUtilDiarEner', 'Embalse', 'Capacidad Útil Diario'),
        ('AporEner', 'Sistema', 'Aportes Energía Sistema'),
        ('AporEnerMediHist', 'Sistema', 'Aportes Media Histórica'),
        ('Gene', 'Sistema', 'Generación Sistema'),
        ('DemaCome', 'Sistema', 'Demanda Comercial'),
    ]
    
    total_registros = 0
    for metrica, entidad, nombre in metricas:
        registros = actualizar_metrica(api, metrica, entidad, nombre)
        total_registros += registros
    
    logger.info("\n" + "="*60)
    logger.info(f"✅ ACTUALIZACIÓN COMPLETADA")
    logger.info(f"Total registros actualizados: {total_registros}")
    logger.info(f"Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60)

if __name__ == '__main__':
    main()
