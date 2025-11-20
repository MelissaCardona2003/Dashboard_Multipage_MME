#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║           AUTO-CORRECCIÓN DE DATOS - SQLite                  ║
║                                                              ║
║  Detecta y corrige automáticamente problemas comunes:       ║
║  1. Duplicados                                               ║
║  2. Fechas futuras/inventadas                                ║
║  3. Normalización de recursos ('Sistema' → '_SISTEMA_')      ║
║  4. Valores fuera de rango                                   ║
║                                                              ║
║  Uso: python3 scripts/autocorreccion.py [--dry-run]         ║
╚══════════════════════════════════════════════════════════════╝
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import sqlite3
import argparse
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class AutoCorrector:
    """Corrige automáticamente problemas de datos en SQLite"""
    
    def __init__(self, db_path: str = 'data/portal_energetico.db', dry_run: bool = False):
        self.db_path = db_path
        self.dry_run = dry_run
        self.estadisticas = {
            'duplicados_eliminados': 0,
            'fechas_futuras_eliminadas': 0,
            'recursos_normalizados': 0,
            'valores_anomalos_eliminados': 0
        }
    
    def conectar(self):
        """Conecta a la base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.error(f"❌ Error al conectar a SQLite: {e}")
            return None
    
    def eliminar_duplicados(self, conn) -> int:
        """Elimina registros duplicados manteniendo el más reciente"""
        logger.info("\n" + "="*60)
        logger.info("🔄 ELIMINANDO DUPLICADOS")
        logger.info("="*60)
        
        try:
            cursor = conn.cursor()
            
            # Detectar duplicados
            cursor.execute("""
                SELECT metrica, recurso, fecha, COUNT(*) as count
                FROM metricas_temporales
                GROUP BY metrica, recurso, fecha
                HAVING COUNT(*) > 1
            """)
            
            duplicados = cursor.fetchall()
            logger.info(f"📊 Encontrados {len(duplicados)} grupos de duplicados")
            
            if not duplicados:
                logger.info("✅ No hay duplicados")
                return 0
            
            total_eliminados = 0
            
            for dup in duplicados:
                metrica = dup['metrica']
                recurso = dup['recurso']
                fecha = dup['fecha']
                count = dup['count']
                
                logger.info(f"   🔄 {metrica}/{recurso}/{fecha}: {count} duplicados")
                
                if not self.dry_run:
                    # Eliminar todos excepto el último (mayor id)
                    cursor.execute("""
                        DELETE FROM metricas_temporales
                        WHERE id NOT IN (
                            SELECT MAX(id)
                            FROM metricas_temporales
                            WHERE metrica = ? AND recurso = ? AND fecha = ?
                        )
                        AND metrica = ? AND recurso = ? AND fecha = ?
                    """, (metrica, recurso, fecha, metrica, recurso, fecha))
                    
                    eliminados = cursor.rowcount
                    total_eliminados += eliminados
            
            if not self.dry_run:
                conn.commit()
                logger.info(f"✅ Eliminados {total_eliminados} registros duplicados")
            else:
                logger.info(f"🔍 [DRY-RUN] Se eliminarían {len(duplicados)} grupos de duplicados")
            
            self.estadisticas['duplicados_eliminados'] = total_eliminados
            return total_eliminados
        
        except Exception as e:
            logger.error(f"❌ Error al eliminar duplicados: {e}")
            conn.rollback()
            return 0
    
    def eliminar_fechas_futuras(self, conn) -> int:
        """Elimina registros con fechas futuras (datos inventados)"""
        logger.info("\n" + "="*60)
        logger.info("🔮 ELIMINANDO FECHAS FUTURAS")
        logger.info("="*60)
        
        try:
            cursor = conn.cursor()
            
            # Fecha máxima permitida (mañana)
            fecha_maxima = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            
            # Detectar fechas futuras
            cursor.execute("""
                SELECT metrica, recurso, fecha, valor_gwh
                FROM metricas_temporales
                WHERE fecha > ?
                ORDER BY fecha DESC
            """, (fecha_maxima,))
            
            registros_futuros = cursor.fetchall()
            logger.info(f"📊 Encontrados {len(registros_futuros)} registros con fechas futuras")
            
            if not registros_futuros:
                logger.info("✅ No hay fechas futuras")
                return 0
            
            # Mostrar algunos ejemplos
            for reg in registros_futuros[:5]:
                logger.info(f"   ⚠️  {reg['metrica']}/{reg['recurso']}/{reg['fecha']}: {reg['valor_gwh']} GWh")
            
            if len(registros_futuros) > 5:
                logger.info(f"   ... y {len(registros_futuros) - 5} más")
            
            if not self.dry_run:
                # Eliminar fechas futuras
                cursor.execute("""
                    DELETE FROM metricas_temporales
                    WHERE fecha > ?
                """, (fecha_maxima,))
                
                eliminados = cursor.rowcount
                conn.commit()
                logger.info(f"✅ Eliminados {eliminados} registros con fechas futuras")
            else:
                logger.info(f"🔍 [DRY-RUN] Se eliminarían {len(registros_futuros)} registros")
            
            self.estadisticas['fechas_futuras_eliminadas'] = len(registros_futuros)
            return len(registros_futuros)
        
        except Exception as e:
            logger.error(f"❌ Error al eliminar fechas futuras: {e}")
            conn.rollback()
            return 0
    
    def normalizar_recursos(self, conn) -> int:
        """Normaliza el campo 'recurso' ('Sistema' → '_SISTEMA_')"""
        logger.info("\n" + "="*60)
        logger.info("🔧 NORMALIZANDO RECURSOS")
        logger.info("="*60)
        
        try:
            cursor = conn.cursor()
            
            # Detectar recursos no normalizados
            cursor.execute("""
                SELECT DISTINCT recurso
                FROM metricas_temporales
                WHERE LOWER(recurso) = 'sistema' AND recurso != '_SISTEMA_'
            """)
            
            recursos_no_normalizados = cursor.fetchall()
            logger.info(f"📊 Encontrados {len(recursos_no_normalizados)} recursos a normalizar")
            
            if not recursos_no_normalizados:
                logger.info("✅ Todos los recursos están normalizados")
                return 0
            
            for rec in recursos_no_normalizados:
                logger.info(f"   🔄 '{rec['recurso']}' → '_SISTEMA_'")
            
            if not self.dry_run:
                # Normalizar
                cursor.execute("""
                    UPDATE metricas_temporales
                    SET recurso = '_SISTEMA_'
                    WHERE LOWER(recurso) = 'sistema' AND recurso != '_SISTEMA_'
                """)
                
                actualizados = cursor.rowcount
                conn.commit()
                logger.info(f"✅ Normalizados {actualizados} registros")
            else:
                logger.info(f"🔍 [DRY-RUN] Se normalizarían registros con {len(recursos_no_normalizados)} variantes")
            
            self.estadisticas['recursos_normalizados'] = len(recursos_no_normalizados)
            return len(recursos_no_normalizados)
        
        except Exception as e:
            logger.error(f"❌ Error al normalizar recursos: {e}")
            conn.rollback()
            return 0
    
    def eliminar_valores_anomalos(self, conn) -> int:
        """Elimina valores claramente anómalos (negativos, extremos)"""
        logger.info("\n" + "="*60)
        logger.info("⚡ ELIMINANDO VALORES ANÓMALOS")
        logger.info("="*60)
        
        try:
            cursor = conn.cursor()
            
            # Detectar valores negativos
            cursor.execute("""
                SELECT metrica, recurso, fecha, valor_gwh
                FROM metricas_temporales
                WHERE valor_gwh < 0
            """)
            
            valores_negativos = cursor.fetchall()
            logger.info(f"📊 Encontrados {len(valores_negativos)} valores negativos")
            
            if valores_negativos:
                for val in valores_negativos[:5]:
                    logger.info(f"   ⚠️  {val['metrica']}/{val['recurso']}/{val['fecha']}: {val['valor_gwh']} GWh")
            
            # Detectar valores extremos (> 10,000 GWh en generación)
            cursor.execute("""
                SELECT metrica, recurso, fecha, valor_gwh
                FROM metricas_temporales
                WHERE metrica = 'Gene' AND valor_gwh > 10000
            """)
            
            valores_extremos = cursor.fetchall()
            logger.info(f"📊 Encontrados {len(valores_extremos)} valores extremos")
            
            total_anomalos = len(valores_negativos) + len(valores_extremos)
            
            if total_anomalos == 0:
                logger.info("✅ No hay valores anómalos")
                return 0
            
            if not self.dry_run:
                # Eliminar valores negativos
                cursor.execute("""
                    DELETE FROM metricas_temporales
                    WHERE valor_gwh < 0
                """)
                eliminados_neg = cursor.rowcount
                
                # Eliminar valores extremos
                cursor.execute("""
                    DELETE FROM metricas_temporales
                    WHERE metrica = 'Gene' AND valor_gwh > 10000
                """)
                eliminados_ext = cursor.rowcount
                
                conn.commit()
                logger.info(f"✅ Eliminados {eliminados_neg} negativos + {eliminados_ext} extremos = {eliminados_neg + eliminados_ext} total")
            else:
                logger.info(f"🔍 [DRY-RUN] Se eliminarían {total_anomalos} valores anómalos")
            
            self.estadisticas['valores_anomalos_eliminados'] = total_anomalos
            return total_anomalos
        
        except Exception as e:
            logger.error(f"❌ Error al eliminar valores anómalos: {e}")
            conn.rollback()
            return 0
    
    def ejecutar_todo(self) -> bool:
        """Ejecuta todas las correcciones"""
        logger.info("\n" + "="*60)
        logger.info("🔧 AUTO-CORRECCIÓN DE DATOS SQLite")
        logger.info("="*60)
        logger.info(f"Base de datos: {self.db_path}")
        logger.info(f"Modo: {'🔍 DRY-RUN (no se harán cambios)' if self.dry_run else '✅ MODO REAL'}")
        logger.info(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        conn = self.conectar()
        if not conn:
            return False
        
        try:
            # Ejecutar correcciones
            self.eliminar_fechas_futuras(conn)
            self.eliminar_duplicados(conn)
            self.normalizar_recursos(conn)
            self.eliminar_valores_anomalos(conn)
            
            # Reporte final
            logger.info("\n" + "="*60)
            logger.info("📊 REPORTE FINAL")
            logger.info("="*60)
            logger.info(f"🔮 Fechas futuras eliminadas: {self.estadisticas['fechas_futuras_eliminadas']}")
            logger.info(f"🔄 Duplicados eliminados: {self.estadisticas['duplicados_eliminados']}")
            logger.info(f"🔧 Recursos normalizados: {self.estadisticas['recursos_normalizados']}")
            logger.info(f"⚡ Valores anómalos eliminados: {self.estadisticas['valores_anomalos_eliminados']}")
            
            total_correcciones = sum(self.estadisticas.values())
            logger.info(f"\n✅ Total de correcciones: {total_correcciones}")
            logger.info("="*60)
            
            return True
        
        except Exception as e:
            logger.error(f"❌ Error durante auto-corrección: {e}")
            return False
        finally:
            conn.close()


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='Auto-corrección de datos SQLite')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Modo de prueba (no hace cambios reales)')
    parser.add_argument('--db', default='data/portal_energetico.db',
                       help='Ruta a la base de datos SQLite')
    
    args = parser.parse_args()
    
    corrector = AutoCorrector(db_path=args.db, dry_run=args.dry_run)
    exito = corrector.ejecutar_todo()
    
    sys.exit(0 if exito else 1)


if __name__ == '__main__':
    main()
