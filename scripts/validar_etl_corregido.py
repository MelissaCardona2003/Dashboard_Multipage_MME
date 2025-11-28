#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║     VALIDACIÓN POST-ETL CORREGIDA: API vs SQLite             ║
║                                                              ║
║  Versión corregida que compara correctamente las unidades.  ║
║  Corrige el bug del script original que causaba falsos      ║
║  positivos al comparar GWh vs kWh sin conversión.           ║
║                                                              ║
║  Uso: python3 scripts/validar_etl_corregido.py              ║
╚══════════════════════════════════════════════════════════════╝
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import sqlite3
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple

from utils._xm import get_objetoAPI

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s: %(message)s')
logger = logging.getLogger(__name__)


class ValidadorETLCorregido:
    """Valida que los datos en SQLite coincidan con la API XM (con conversiones correctas)"""
    
    def __init__(self, db_path: str = 'portal_energetico.db'):
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.path.dirname(__file__), '..', db_path)
        
        self.db_path = db_path
        self.api = get_objetoAPI()
        if not self.api:
            logger.error("❌ No se pudo inicializar la API XM")
        self.resultados = {
            'metricas_validadas': 0,
            'metricas_correctas': 0,
            'metricas_incorrectas': 0,
            'errores': []
        }
    
    def conectar_sqlite(self):
        """Conecta a la base de datos SQLite"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.error(f"❌ Error al conectar a SQLite: {e}")
            return None
    
    def obtener_ultima_fecha_sqlite(self, conn, metrica: str, entidad: str) -> Tuple[datetime, float]:
        """Obtiene la última fecha y valor de SQLite"""
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT fecha, valor_gwh 
                FROM metrics 
                WHERE metrica = ? AND entidad = ?
                ORDER BY fecha DESC 
                LIMIT 1
            """, (metrica, entidad))
            
            row = cursor.fetchone()
            if row:
                fecha = row['fecha']
                if isinstance(fecha, str):
                    fecha_dt = datetime.strptime(fecha, '%Y-%m-%d')
                elif hasattr(fecha, 'to_pydatetime'):
                    fecha_dt = fecha.to_pydatetime()
                else:
                    fecha_dt = fecha
                return fecha_dt, row['valor_gwh']
            return None, None
        except Exception as e:
            logger.error(f"❌ Error al consultar SQLite: {e}")
            return None, None
    
    def convertir_api_a_gwh(self, df, metrica: str) -> float:
        """
        Convierte valores de API a GWh según el tipo de métrica.
        
        FIX PRINCIPAL: Esta función implementa las conversiones correctas
        que faltaban en el script original.
        """
        if df is None or df.empty:
            return None
        
        # Detectar tipo de datos en API
        hour_cols = [f'Values_Hour{i:02d}' for i in range(1, 25)]
        existing_hour_cols = [col for col in hour_cols if col in df.columns]
        
        # Gene y DemaCome: Agregar 24 horas (kWh) y convertir a GWh
        if metrica in ['Gene', 'DemaCome'] and len(existing_hour_cols) >= 20:
            valor_kwh = df[existing_hour_cols].sum(axis=1).iloc[0]
            valor_gwh = valor_kwh / 1_000_000  # kWh → GWh
            logger.debug(f"  Conversión {metrica}: {valor_kwh:,.2f} kWh → {valor_gwh:.2f} GWh")
            return valor_gwh
        
        # AporEner: Viene en Wh, convertir a GWh
        elif metrica == 'AporEner' and 'Value' in df.columns:
            valor_wh = df['Value'].iloc[0]
            valor_gwh = valor_wh / 1_000_000  # Wh → GWh
            logger.debug(f"  Conversión {metrica}: {valor_wh:,.2f} Wh → {valor_gwh:.2f} GWh")
            return valor_gwh
        
        # VoluUtilDiarEner y CapaUtilDiarEner: Ya vienen en kWh, convertir a GWh
        elif metrica in ['VoluUtilDiarEner', 'CapaUtilDiarEner'] and 'Value' in df.columns:
            # Sumar todos los embalses si hay múltiples
            if len(df) > 1:
                valor_kwh = df['Value'].sum()
            else:
                valor_kwh = df['Value'].iloc[0]
            valor_gwh = valor_kwh / 1_000_000  # kWh → GWh
            logger.debug(f"  Conversión {metrica}: {valor_kwh:,.2f} kWh → {valor_gwh:.2f} GWh")
            return valor_gwh
        
        # Fallback: Intentar columna Value
        elif 'Value' in df.columns:
            logger.warning(f"⚠️ Conversión desconocida para {metrica}, usando Value directamente")
            return df['Value'].iloc[0] / 1_000_000
        
        logger.error(f"❌ No se pudo convertir datos de {metrica}")
        return None
    
    def obtener_ultima_fecha_api(self, metrica: str, entidad: str) -> Tuple[datetime, float]:
        """Obtiene la última fecha y valor de la API XM (CON CONVERSIÓN CORRECTA)"""
        try:
            fecha_fin = datetime.now()
            fecha_inicio = fecha_fin - timedelta(days=7)
            
            logger.debug(f"  Consultando API: {metrica}/{entidad} desde {fecha_inicio.date()}")
            df = self.api.request_data(
                metrica, 
                entidad,
                fecha_inicio.strftime('%Y-%m-%d'),
                fecha_fin.strftime('%Y-%m-%d')
            )
            
            if df is None or df.empty:
                return None, None
            
            # Obtener última fecha disponible
            df = df.sort_values('Date', ascending=False)
            fecha = df.iloc[0]['Date']
            
            if isinstance(fecha, str):
                fecha_dt = datetime.strptime(fecha, '%Y-%m-%d')
            elif hasattr(fecha, 'to_pydatetime'):
                fecha_dt = fecha.to_pydatetime()
            else:
                fecha_dt = fecha
            
            # Filtrar solo la última fecha para conversión correcta
            df_ultima_fecha = df[df['Date'] == fecha].copy()
            
            # ✅ AQUÍ ESTÁ LA CORRECCIÓN PRINCIPAL
            valor_gwh = self.convertir_api_a_gwh(df_ultima_fecha, metrica)
            
            return fecha_dt, valor_gwh
            
        except Exception as e:
            logger.error(f"❌ Error al consultar API XM ({metrica}/{entidad}): {e}")
            import traceback
            traceback.print_exc()
            return None, None
    
    def validar_metrica(self, metrica: str, entidad: str, nombre_amigable: str) -> bool:
        """Valida una métrica específica comparando SQLite vs API"""
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 Validando: {nombre_amigable}")
        logger.info(f"   Métrica: {metrica}/{entidad}")
        logger.info(f"{'='*60}")
        
        self.resultados['metricas_validadas'] += 1
        
        conn = self.conectar_sqlite()
        if not conn:
            self.resultados['errores'].append(f"{nombre_amigable}: Error de conexión SQLite")
            return False
        
        try:
            # Obtener datos de SQLite
            fecha_sqlite, valor_sqlite = self.obtener_ultima_fecha_sqlite(conn, metrica, entidad)
            logger.info(f"📦 SQLite: fecha={fecha_sqlite.date() if fecha_sqlite else None}, valor={valor_sqlite:.2f} GWh" if valor_sqlite else "📦 SQLite: Sin datos")
            
            # Obtener datos de API (CON CONVERSIÓN CORRECTA)
            fecha_api, valor_api = self.obtener_ultima_fecha_api(metrica, entidad)
            logger.info(f"🌐 API XM:  fecha={fecha_api.date() if fecha_api else None}, valor={valor_api:.2f} GWh" if valor_api else "🌐 API XM: Sin datos")
            
            # Validar
            if fecha_sqlite is None or fecha_api is None:
                logger.warning(f"⚠️ {nombre_amigable}: Datos no disponibles")
                self.resultados['errores'].append(f"{nombre_amigable}: Datos no disponibles")
                return False
            
            # Comparar fechas
            fecha_sqlite_date = fecha_sqlite.date() if hasattr(fecha_sqlite, 'date') else fecha_sqlite
            fecha_api_date = fecha_api.date() if hasattr(fecha_api, 'date') else fecha_api
            
            if fecha_sqlite_date == fecha_api_date:
                logger.info(f"✅ {nombre_amigable}: Fechas coinciden")
                
                # Comparar valores (con tolerancia del 0.1%)
                if valor_sqlite is not None and valor_api is not None:
                    diferencia_pct = abs(valor_sqlite - valor_api) / valor_api * 100 if valor_api != 0 else 0
                    if diferencia_pct < 0.1:
                        logger.info(f"✅ {nombre_amigable}: Valores coinciden (diff: {diferencia_pct:.4f}%)")
                        self.resultados['metricas_correctas'] += 1
                        return True
                    else:
                        logger.error(f"❌ {nombre_amigable}: Valores difieren {diferencia_pct:.2f}%")
                        logger.error(f"   SQLite: {valor_sqlite:.2f} GWh")
                        logger.error(f"   API XM: {valor_api:.2f} GWh")
                        logger.error(f"   Diferencia absoluta: {abs(valor_sqlite - valor_api):.2f} GWh")
                        self.resultados['errores'].append(
                            f"{nombre_amigable}: Valores difieren {diferencia_pct:.2f}%"
                        )
                        self.resultados['metricas_incorrectas'] += 1
                        return False
            else:
                # Verificar si SQLite está adelantado (datos inventados)
                if fecha_sqlite_date > fecha_api_date:
                    logger.error(f"❌ {nombre_amigable}: ¡SQLite tiene fecha FUTURA!")
                    logger.error(f"   SQLite: {fecha_sqlite_date}, API: {fecha_api_date}")
                    self.resultados['errores'].append(
                        f"{nombre_amigable}: Fecha inventada (SQLite: {fecha_sqlite_date}, API: {fecha_api_date})"
                    )
                    self.resultados['metricas_incorrectas'] += 1
                    return False
                else:
                    dias_atraso = (fecha_api_date - fecha_sqlite_date).days
                    logger.warning(f"⚠️ {nombre_amigable}: SQLite {dias_atraso} días atrasado")
                    logger.warning(f"   SQLite: {fecha_sqlite_date}, API: {fecha_api_date}")
                    
                    if dias_atraso > 2:
                        self.resultados['errores'].append(
                            f"{nombre_amigable}: {dias_atraso} días atrasado"
                        )
                        self.resultados['metricas_incorrectas'] += 1
                        return False
                    else:
                        # Atraso menor a 2 días es aceptable
                        self.resultados['metricas_correctas'] += 1
                        return True
        
        except Exception as e:
            logger.error(f"❌ Error al validar {nombre_amigable}: {e}")
            import traceback
            traceback.print_exc()
            self.resultados['errores'].append(f"{nombre_amigable}: {str(e)}")
            self.resultados['metricas_incorrectas'] += 1
            return False
        finally:
            conn.close()
    
    def validar_todo(self) -> bool:
        """Valida todas las métricas críticas"""
        logger.info("\n" + "="*60)
        logger.info("🔍 VALIDACIÓN POST-ETL CORREGIDA: API XM vs SQLite")
        logger.info("="*60)
        logger.info(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Métricas críticas a validar
        metricas = [
            ('Gene', 'Sistema', 'Generación Sistema'),
            ('DemaCome', 'Sistema', 'Demanda Comercial'),
            ('AporEner', 'Sistema', 'Aportes Energía'),
            # Nota: VoluUtilDiarEner y CapaUtilDiarEner requieren lógica especial
            # para sumar múltiples embalses, se validan por separado
        ]
        
        resultados = []
        for metrica, entidad, nombre in metricas:
            resultado = self.validar_metrica(metrica, entidad, nombre)
            resultados.append(resultado)
        
        # Reporte final
        logger.info("\n" + "="*60)
        logger.info("📊 REPORTE FINAL DE VALIDACIÓN")
        logger.info("="*60)
        logger.info(f"✅ Métricas validadas: {self.resultados['metricas_validadas']}")
        logger.info(f"✅ Métricas correctas: {self.resultados['metricas_correctas']}")
        logger.info(f"❌ Métricas incorrectas: {self.resultados['metricas_incorrectas']}")
        
        if self.resultados['errores']:
            logger.info(f"\n🔴 ERRORES DETECTADOS ({len(self.resultados['errores'])}):")
            for error in self.resultados['errores']:
                logger.info(f"   - {error}")
        
        # Calcular tasa de éxito
        if self.resultados['metricas_validadas'] > 0:
            tasa_exito = (self.resultados['metricas_correctas'] / 
                         self.resultados['metricas_validadas'] * 100)
            logger.info(f"\n📈 Tasa de éxito: {tasa_exito:.1f}%")
        
        logger.info("="*60)
        
        # Retornar True si todas las métricas están correctas
        return all(resultados)


def main():
    """Función principal"""
    validador = ValidadorETLCorregido()
    exito = validador.validar_todo()
    
    # Código de salida
    sys.exit(0 if exito else 1)


if __name__ == '__main__':
    main()
