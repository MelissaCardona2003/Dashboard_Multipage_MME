"""
╔══════════════════════════════════════════════════════════════╗
║               ENDPOINT DE HEALTH CHECK                       ║
║                                                              ║
║  Endpoint para monitorear la salud del sistema ETL-SQLite   ║
║  Verifica: SQLite disponible, datos actualizados, sin errores
╚══════════════════════════════════════════════════════════════╝
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any
import os


def verificar_salud_sistema(db_path: str = 'data/portal_energetico.db') -> Dict[str, Any]:
    """
    Verifica la salud del sistema completo
    
    Returns:
        Dict con status, checks individuales y mensaje
    """
    resultado = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'checks': {},
        'warnings': [],
        'errors': []
    }
    
    try:
        # 1. Verificar que existe la base de datos
        if not os.path.exists(db_path):
            resultado['checks']['database_exists'] = False
            resultado['errors'].append('Base de datos no encontrada')
            resultado['status'] = 'unhealthy'
            return resultado
        
        resultado['checks']['database_exists'] = True
        
        # Conectar a SQLite
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 2. Verificar tamaño de la base de datos
        db_size_mb = os.path.getsize(db_path) / (1024 * 1024)
        resultado['checks']['database_size_mb'] = round(db_size_mb, 2)
        
        if db_size_mb < 100:
            resultado['warnings'].append(f'Base de datos pequeña: {db_size_mb:.2f} MB')
        
        # 3. Verificar tablas principales
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tablas = [row['name'] for row in cursor.fetchall()]
        
        tablas_requeridas = ['metricas_temporales', 'catalogo_recursos']
        tablas_faltantes = [t for t in tablas_requeridas if t not in tablas]
        
        if tablas_faltantes:
            resultado['errors'].append(f'Tablas faltantes: {tablas_faltantes}')
            resultado['status'] = 'unhealthy'
        
        resultado['checks']['tables_exist'] = len(tablas_faltantes) == 0
        resultado['checks']['tables_found'] = len(tablas)
        
        # 4. Verificar cantidad de registros
        cursor.execute("SELECT COUNT(*) as count FROM metricas_temporales")
        total_registros = cursor.fetchone()['count']
        resultado['checks']['total_records'] = total_registros
        
        if total_registros < 100000:
            resultado['warnings'].append(f'Pocos registros: {total_registros}')
        
        # 5. Verificar frescura de los datos
        cursor.execute("""
            SELECT MAX(fecha) as fecha_max
            FROM metricas_temporales
            WHERE metrica = 'Gene' AND recurso = '_SISTEMA_'
        """)
        
        row = cursor.fetchone()
        if row and row['fecha_max']:
            fecha_max = datetime.strptime(row['fecha_max'], '%Y-%m-%d')
            dias_antiguedad = (datetime.now() - fecha_max).days
            
            resultado['checks']['latest_data_date'] = row['fecha_max']
            resultado['checks']['data_age_days'] = dias_antiguedad
            
            if dias_antiguedad > 3:
                resultado['warnings'].append(f'Datos desactualizados: {dias_antiguedad} días')
                resultado['status'] = 'degraded'
            elif dias_antiguedad > 7:
                resultado['errors'].append(f'Datos muy desactualizados: {dias_antiguedad} días')
                resultado['status'] = 'unhealthy'
        else:
            resultado['errors'].append('No se encontraron datos de generación')
            resultado['status'] = 'unhealthy'
        
        # 6. Verificar duplicados
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM (
                SELECT metrica, recurso, fecha, COUNT(*) as n
                FROM metricas_temporales
                GROUP BY metrica, recurso, fecha
                HAVING COUNT(*) > 1
            )
        """)
        
        duplicados = cursor.fetchone()['count']
        resultado['checks']['duplicate_records'] = duplicados
        
        if duplicados > 0:
            resultado['warnings'].append(f'Duplicados encontrados: {duplicados}')
        
        # 7. Verificar integridad de métricas críticas
        metricas_criticas = ['Gene', 'DemaCome', 'AporEner']
        metricas_faltantes = []
        
        for metrica in metricas_criticas:
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM metricas_temporales
                WHERE metrica = ? AND recurso = '_SISTEMA_'
            """, (metrica,))
            
            count = cursor.fetchone()['count']
            if count == 0:
                metricas_faltantes.append(metrica)
        
        if metricas_faltantes:
            resultado['errors'].append(f'Métricas críticas sin datos: {metricas_faltantes}')
            resultado['status'] = 'unhealthy'
        
        resultado['checks']['critical_metrics_ok'] = len(metricas_faltantes) == 0
        
        conn.close()
        
        # Mensaje resumen
        if resultado['status'] == 'healthy':
            resultado['message'] = '✅ Sistema operando normalmente'
        elif resultado['status'] == 'degraded':
            resultado['message'] = f"⚠️ Sistema con advertencias: {', '.join(resultado['warnings'])}"
        else:
            resultado['message'] = f"❌ Sistema con errores: {', '.join(resultado['errors'])}"
        
    except Exception as e:
        resultado['status'] = 'unhealthy'
        resultado['errors'].append(f'Error al verificar sistema: {str(e)}')
        resultado['message'] = f'❌ Error crítico: {str(e)}'
    
    return resultado


def generar_reporte_texto(salud: Dict[str, Any]) -> str:
    """Genera un reporte legible para humanos"""
    lineas = [
        "="*60,
        "📊 HEALTH CHECK - Portal Energético MME",
        "="*60,
        f"⏰ Timestamp: {salud['timestamp']}",
        f"🏥 Status: {salud['status'].upper()}",
        "",
        "VERIFICACIONES:",
    ]
    
    for check, valor in salud['checks'].items():
        emoji = "✅" if valor else "❌"
        lineas.append(f"  {emoji} {check}: {valor}")
    
    if salud['warnings']:
        lineas.append("")
        lineas.append("⚠️ ADVERTENCIAS:")
        for warning in salud['warnings']:
            lineas.append(f"  - {warning}")
    
    if salud['errors']:
        lineas.append("")
        lineas.append("❌ ERRORES:")
        for error in salud['errors']:
            lineas.append(f"  - {error}")
    
    lineas.append("")
    lineas.append(salud['message'])
    lineas.append("="*60)
    
    return "\n".join(lineas)
