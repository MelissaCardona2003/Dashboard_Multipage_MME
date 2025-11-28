#!/usr/bin/env python3
"""
Test ETL solo para métricas de distribución (DemaCome y DemaReal por Agente)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydataxm.pydataxm import ReadDB
from datetime import datetime, timedelta
import time
import logging
import pandas as pd
from utils import db_manager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def convertir_unidades(df, metric, conversion_type):
    """Convertir unidades de datos crudos de XM a GWh"""
    if df is None or df.empty:
        logging.warning(f"⚠️ {metric}: DataFrame vacío")
        return df
    
    if conversion_type is None:
        return df
    
    df = df.copy()
    
    try:
        if conversion_type == 'horas_a_diario':
            # Sumar valores horarios (Values_Hour01-24)
            hour_cols = [f'Values_Hour{i:02d}' for i in range(1, 25)]
            existing_cols = [col for col in hour_cols if col in df.columns]
            
            if existing_cols:
                df['Value'] = df[existing_cols].sum(axis=1) / 1_000_000  # kWh → GWh
                valor_despues = df['Value'].mean()
                logging.info(f"✅ {metric}: Agregado {len(existing_cols)} horas → {valor_despues:.2f} GWh promedio")
            elif 'Value' in df.columns:
                valor_antes = df['Value'].mean()
                df['Value'] = df['Value'] / 1_000_000
                valor_despues = df['Value'].mean()
                logging.info(f"✅ {metric}: Value (kWh→GWh) | {valor_antes:,.2f} → {valor_despues:.2f} GWh")
        
        return df
        
    except Exception as e:
        logging.error(f"❌ Error convirtiendo unidades para {metric}: {e}")
        return df


def test_etl_distribucion():
    """Test ETL solo para DemaCome y DemaReal por Agente"""
    
    logging.info("="*80)
    logging.info("TEST ETL: DISTRIBUCIÓN (DemaCome y DemaReal por Agente)")
    logging.info("="*80)
    
    # Inicializar API XM
    try:
        obj_api = ReadDB()
        logging.info("✅ Conexión a API XM inicializada")
    except Exception as e:
        logging.error(f"❌ Error conectando a API XM: {e}")
        return
    
    # Período de prueba: últimos 7 días
    fecha_fin = datetime.now().date() - timedelta(days=1)
    fecha_inicio = fecha_fin - timedelta(days=7)
    
    metricas_test = [
        {'metric': 'DemaCome', 'entity': 'Agente', 'conversion': 'horas_a_diario'},
        {'metric': 'DemaReal', 'entity': 'Agente', 'conversion': 'horas_a_diario'}
    ]
    
    for config in metricas_test:
        metric = config['metric']
        entity = config['entity']
        conversion = config['conversion']
        
        logging.info(f"\n{'='*80}")
        logging.info(f"📡 {metric}/{entity}")
        logging.info(f"{'='*80}")
        logging.info(f"Período: {fecha_inicio} a {fecha_fin}")
        
        try:
            # Consultar API XM
            start_time = time.time()
            df = obj_api.request_data(
                metric,
                entity,
                start_date=str(fecha_inicio),
                end_date=str(fecha_fin)
            )
            elapsed = time.time() - start_time
            
            if df is None or df.empty:
                logging.warning(f"❌ {metric}/{entity}: Sin datos de API")
                continue
            
            logging.info(f"✅ API respondió en {elapsed:.1f}s")
            logging.info(f"📊 Datos recibidos: {len(df)} filas")
            logging.info(f"📋 Columnas: {df.columns.tolist()}")
            
            # Mostrar muestra de datos
            if 'Values_code' in df.columns:
                agentes_unicos = df['Values_code'].nunique()
                logging.info(f"👥 Agentes únicos: {agentes_unicos}")
                logging.info(f"👥 Primeros 10 agentes: {sorted(df['Values_code'].unique()[:10].tolist())}")
            
            # Convertir unidades
            if conversion:
                df = convertir_unidades(df, metric, conversion)
            
            # Verificar que Value existe y tiene datos válidos
            if 'Value' in df.columns:
                logging.info(f"📊 Valor promedio: {df['Value'].mean():.4f} GWh")
                logging.info(f"📊 Valor mínimo: {df['Value'].min():.4f} GWh")
                logging.info(f"📊 Valor máximo: {df['Value'].max():.4f} GWh")
                
                # Contar valores muy bajos
                valores_bajos = (df['Value'] < 0.001).sum()
                if valores_bajos > 0:
                    logging.warning(f"⚠️ {valores_bajos} registros con valores < 0.001 GWh (serán filtrados)")
            
            # Preparar datos para inserción
            metrics_to_insert = []
            
            for _, row in df.iterrows():
                fecha = str(row['Date'])[:10]
                valor_gwh = float(row['Value'])
                
                # Filtrar valores muy bajos
                if valor_gwh < 0.001:
                    continue
                
                # Obtener código del agente
                recurso = None
                if 'Values_code' in df.columns:
                    recurso = row.get('Values_code')
                    if pd.notna(recurso):
                        recurso = str(recurso)
                
                if recurso is None:
                    logging.warning(f"⚠️ Fila sin código de agente, saltando")
                    continue
                
                metrics_to_insert.append((
                    fecha,
                    metric,
                    entity,
                    recurso,
                    valor_gwh,
                    'GWh'
                ))
            
            # Insertar en SQLite
            if metrics_to_insert:
                total_insertados = db_manager.upsert_metrics_bulk(metrics_to_insert)
                logging.info(f"✅ {metric}/{entity}: {total_insertados} registros guardados en SQLite")
                
                # Verificar inserción
                logging.info(f"\n🔍 Verificando datos insertados...")
                df_verify = db_manager.get_metric_data(
                    metrica=metric,
                    entidad=entity,
                    fecha_inicio=str(fecha_inicio),
                    fecha_fin=str(fecha_fin)
                )
                
                if df_verify is not None and not df_verify.empty:
                    agentes_guardados = df_verify['recurso'].nunique()
                    logging.info(f"✅ Verificación OK: {len(df_verify)} registros, {agentes_guardados} agentes")
                else:
                    logging.error(f"❌ Verificación FALLÓ: No se encontraron datos en SQLite")
            else:
                logging.warning(f"⚠️ No hay datos válidos para insertar")
                
        except Exception as e:
            logging.error(f"❌ Error procesando {metric}/{entity}: {e}")
            import traceback
            traceback.print_exc()
        
        time.sleep(1)
    
    # Resumen final
    logging.info(f"\n{'='*80}")
    logging.info("RESUMEN DE BASE DE DATOS")
    logging.info("="*80)
    
    db_stats = db_manager.get_database_stats()
    logging.info(f"Total registros: {db_stats.get('total_registros', 0):,}")
    logging.info(f"Métricas únicas: {db_stats.get('metricas_unicas', 0)}")
    logging.info(f"Rango fechas: {db_stats.get('fecha_minima')} a {db_stats.get('fecha_maxima')}")
    logging.info(f"Tamaño BD: {db_stats.get('tamano_db_mb', 0):.2f} MB")


if __name__ == "__main__":
    test_etl_distribucion()
