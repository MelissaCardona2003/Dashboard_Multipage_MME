#!/usr/bin/env python3
"""
Sistema de PRECALENTAMIENTO AUTOMÁTICO de cache v2.0
Precalcula datos en horarios estratégicos SIN necesidad de supervisión

HORARIOS DE EJECUCIÓN (via cron):
- 06:30 AM: Después de actualización diaria de XM
- 12:30 PM: Actualización de mediodía  
- 20:30 PM: Actualización nocturna

OBJETIVO: Usuario SIEMPRE encuentra datos pre-calculados (carga <5s)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import date, timedelta, datetime
import logging
import time

# Importar solo las utilidades necesarias (sin Dash)
from utils._xm import get_objetoAPI, fetch_metric_data
from utils.cache_manager import get_cache_key, get_from_cache, save_to_cache
from utils.utils_xm import fetch_gene_recurso_chunked

# Configurar logging
log_file = os.path.join(os.path.dirname(__file__), '..', 'logs', 'precalentamiento_cache.log')
os.makedirs(os.path.dirname(log_file), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# ==========================================
# CONFIGURACIÓN
# ==========================================

# Rangos de fechas que usuarios consultan frecuentemente
RANGOS_COMUNES = [
    7,     # Última semana
    30,    # Último mes (MÁS COMÚN)
    90,    # Último trimestre
    365,   # Último año
    730,   # Dos años
]

# Tipos de fuente para precalcular
TIPOS_FUENTE = ['HIDRAULICA', 'TERMICA', 'EOLICA', 'SOLAR', 'BIOMASA']

# Métricas hídricas importantes para hidrología
METRICAS_HIDRICAS = [
    ('AporEner', 'Sistema'),
    ('Gene', 'Sistema'),
    ('DemaCome', 'Sistema'),
]

# Métricas para indicadores de generacion.py (CRÍTICAS - se cargan en página principal)
METRICAS_INDICADORES_GENERACION = [
    ('VoluUtilDiarEner', 'Embalse'),     # Para Reservas Hídricas %
    ('CapaUtilDiarEner', 'Embalse'),     # Para Reservas Hídricas %
    ('AporEner', 'Sistema'),              # Para Aportes Hídricos %
    ('AporEnerMediHist', 'Sistema'),     # Para Aportes Hídricos %
    ('Gene', 'Sistema'),                  # Para Generación SIN (OPTIMIZADO - antes era Gene/Recurso)
]

# ==========================================
# FUNCIONES DE PRECALENTAMIENTO
# ==========================================

def precalentar_generacion_por_fuentes():
    """
    Precalentar generación agregada por tipo de fuente
    Esta es la función MÁS PESADA de la página
    """
    logger.info("=" * 80)
    logger.info("🔥 PRECALENTANDO: Generación por Fuentes")
    logger.info("=" * 80)
    
    objetoAPI = get_objetoAPI()
    if not objetoAPI:
        logger.error("❌ API XM no disponible")
        return False
    
    total_exitosos = 0
    total_intentos = 0
    
    for dias in RANGOS_COMUNES:
        fecha_fin = date.today()
        fecha_inicio = fecha_fin - timedelta(days=dias)
        
        logger.info(f"\n📅 Rango: {dias} días ({fecha_inicio} → {fecha_fin})")
        
        for tipo_fuente in TIPOS_FUENTE:
            total_intentos += 1
            
            try:
                # Generar cache_key exactamente como lo hace la página
                cache_key = get_cache_key(
                    'generacion_agregada_tipo',
                    fecha_inicio.strftime('%Y-%m-%d'),
                    fecha_fin.strftime('%Y-%m-%d'),
                    tipo_fuente
                )
                
                # Verificar si ya existe en cache válido
                cached_data = get_from_cache(cache_key, allow_expired=False)
                if cached_data is not None:
                    logger.info(f"  ⚡ {tipo_fuente}: Ya en cache (skip)")
                    total_exitosos += 1
                    continue
                
                # Consultar y procesar datos
                logger.info(f"  🔄 {tipo_fuente}: Procesando...")
                start_time = time.time()
                
                # 1. Obtener ListadoRecursos (con cache)
                cache_key_recursos = get_cache_key('listado_recursos', tipo_fuente)
                recursos = get_from_cache(cache_key_recursos, allow_expired=False)
                
                if recursos is None:
                    # Consultar ListadoRecursos
                    fecha_recursos_fin = date.today() - timedelta(days=14)
                    fecha_recursos_inicio = fecha_recursos_fin - timedelta(days=7)
                    
                    recursos = objetoAPI.request_data(
                        "ListadoRecursos", 
                        "Sistema",
                        fecha_recursos_inicio.strftime('%Y-%m-%d'),
                        fecha_recursos_fin.strftime('%Y-%m-%d')
                    )
                    
                    if recursos is None or recursos.empty:
                        logger.warning(f"  ⚠️ {tipo_fuente}: Sin recursos")
                        continue
                    
                    # Filtrar por tipo
                    if 'Values_Type' in recursos.columns:
                        if tipo_fuente.upper() == 'BIOMASA':
                            terminos = ['BIOMASA', 'COGENER', 'BAGAZO']
                            mask = recursos['Values_Type'].astype(str).str.upper().apply(
                                lambda x: any(t in x for t in terminos)
                            )
                            recursos = recursos[mask].copy()
                        else:
                            recursos = recursos[
                                recursos['Values_Type'].str.contains(tipo_fuente, na=False, case=False)
                            ].copy()
                    
                    if recursos.empty:
                        logger.warning(f"  ⚠️ {tipo_fuente}: Sin recursos después de filtrar")
                        continue
                    
                    # Guardar en cache
                    save_to_cache(cache_key_recursos, recursos, cache_type='listado_recursos')
                
                # 2. Detectar códigos válidos
                candidatas_col = [c for c in recursos.columns if 'code' in c.lower() and c.startswith('Values_')]
                
                codigos = []
                for col in candidatas_col:
                    cods = (recursos[col].dropna().astype(str).str.strip()
                           .loc[lambda s: s.str.match(r'^[A-Z0-9]{3,6}$', na=False)]
                           .unique().tolist())
                    if len(cods) > 0:
                        codigos = cods
                        break
                
                if not codigos:
                    logger.warning(f"  ⚠️ {tipo_fuente}: Sin códigos válidos")
                    continue
                
                logger.info(f"  📊 {tipo_fuente}: {len(codigos)} plantas")
                
                # 3. Obtener generación con chunking
                df_generacion = fetch_gene_recurso_chunked(
                    objetoAPI,
                    fecha_inicio,
                    fecha_fin,
                    codigos,
                    batch_size=50,
                    chunk_days=30
                )
                
                if df_generacion is None or df_generacion.empty:
                    logger.warning(f"  ⚠️ {tipo_fuente}: Sin datos de generación")
                    continue
                
                # 4. Preparar formato de salida
                df_generacion['Tipo'] = tipo_fuente.capitalize()
                df_generacion['Tipo_Original'] = tipo_fuente.upper()
                df_generacion.rename(columns={'Date': 'Fecha', 'Value_GWh': 'Generacion_GWh'}, inplace=True)
                
                resultado = df_generacion[['Fecha', 'Generacion_GWh', 'Tipo', 'Codigo', 'Tipo_Original']].copy()
                
                # 5. GUARDAR EN CACHE
                save_to_cache(
                    cache_key,
                    resultado,
                    cache_type='generacion_plantas',
                    metric_name=f'generacion_{tipo_fuente.lower()}'
                )
                
                elapsed = time.time() - start_time
                total_gwh = resultado['Generacion_GWh'].sum()
                logger.info(f"  ✅ {tipo_fuente}: {len(resultado)} registros, {total_gwh:.2f} GWh en {elapsed:.1f}s")
                total_exitosos += 1
                
                # Pausa breve para no saturar API
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"  ❌ {tipo_fuente}: Error - {e}")
                continue
    
    logger.info(f"\n{'=' * 80}")
    logger.info(f"✅ Generación por Fuentes: {total_exitosos}/{total_intentos} exitosos")
    logger.info(f"{'=' * 80}\n")
    
    return total_exitosos > 0


def precalentar_metricas_hidricas():
    """Precalentar métricas hídricas importantes"""
    logger.info("=" * 80)
    logger.info("🔥 PRECALENTANDO: Métricas Hídricas")
    logger.info("=" * 80)
    
    total_exitosos = 0
    total_intentos = 0
    
    for dias in [30, 90, 365]:  # Solo rangos comunes para métricas
        fecha_fin = date.today()
        fecha_inicio = fecha_fin - timedelta(days=dias)
        
        logger.info(f"\n📅 Rango: {dias} días ({fecha_inicio} → {fecha_fin})")
        
        for metrica, entidad in METRICAS_HIDRICAS:
            total_intentos += 1
            
            try:
                # Usar fetch_metric_data (ya tiene cache y fallback)
                df = fetch_metric_data(metrica, entidad, fecha_inicio, fecha_fin)
                
                if df is not None and not df.empty:
                    logger.info(f"  ✅ {metrica}/{entidad}: {len(df)} registros")
                    total_exitosos += 1
                else:
                    logger.warning(f"  ⚠️ {metrica}/{entidad}: Sin datos")
                
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"  ❌ {metrica}/{entidad}: Error - {e}")
                continue
    
    logger.info(f"\n{'=' * 80}")
    logger.info(f"✅ Métricas Hídricas: {total_exitosos}/{total_intentos} exitosos")
    logger.info(f"{'=' * 80}\n")
    
    return total_exitosos > 0


def precalentar_indicadores_generacion():
    """
    Precalentar indicadores de la página principal de Generación (generacion.py)
    Estos indicadores son CRÍTICOS porque se cargan SIEMPRE al entrar a la sección de generación
    
    INDICADORES:
    1. Reservas Hídricas % = (VoluUtilDiarEner / CapaUtilDiarEner) * 100
    2. Aportes Hídricos % = (AporEner / AporEnerMediHist) * 100
    3. Generación SIN [GWh] = Suma de Gene/Recurso (todas las plantas × 24 horas)
    """
    logger.info("=" * 80)
    logger.info("🔥 PRECALENTANDO: Indicadores Generación (Página Principal)")
    logger.info("=" * 80)
    
    total_exitosos = 0
    total_intentos = 0
    
    # Buscar datos en los últimos 7 días (como hace generacion.py)
    fecha_fin = date.today() - timedelta(days=1)
    
    for dias_atras in range(7):
        fecha_prueba = fecha_fin - timedelta(days=dias_atras)
        fecha_str = fecha_prueba.strftime('%Y-%m-%d')
        
        logger.info(f"\n📅 Consultando datos para: {fecha_str}")
        
        # 1. Precalentar Reservas Hídricas (VoluUtilDiarEner y CapaUtilDiarEner)
        logger.info(f"  🔄 Reservas Hídricas...")
        for metrica in ['VoluUtilDiarEner', 'CapaUtilDiarEner']:
            total_intentos += 1
            try:
                df = fetch_metric_data(metrica, 'Embalse', fecha_str, fecha_str)
                if df is not None and not df.empty:
                    logger.info(f"    ✅ {metrica}: {len(df)} registros")
                    total_exitosos += 1
                else:
                    logger.warning(f"    ⚠️ {metrica}: Sin datos")
                time.sleep(0.3)
            except Exception as e:
                logger.error(f"    ❌ {metrica}: Error - {e}")
        
        # 2. Precalentar Aportes Hídricos (mes actual)
        fecha_inicio_mes = fecha_prueba.replace(day=1)
        mes_str_inicio = fecha_inicio_mes.strftime('%Y-%m-%d')
        
        logger.info(f"  🔄 Aportes Hídricos (mes actual: {mes_str_inicio} → {fecha_str})...")
        for metrica in ['AporEner', 'AporEnerMediHist']:
            total_intentos += 1
            try:
                df = fetch_metric_data(metrica, 'Sistema', mes_str_inicio, fecha_str)
                if df is not None and not df.empty:
                    logger.info(f"    ✅ {metrica}: {len(df)} registros")
                    total_exitosos += 1
                else:
                    logger.warning(f"    ⚠️ {metrica}: Sin datos")
                time.sleep(0.3)
            except Exception as e:
                logger.error(f"    ❌ {metrica}: Error - {e}")
        
        # 3. Precalentar Generación SIN (Gene/Sistema) - OPTIMIZADO
        logger.info(f"  🔄 Generación SIN (Gene/Sistema - OPTIMIZADO)...")
        total_intentos += 1
        try:
            df = fetch_metric_data('Gene', 'Sistema', fecha_str, fecha_str)
            if df is not None and not df.empty:
                # Detectar columna de valor
                col_value = 'Value' if 'Value' in df.columns else 'Values_code' if 'Values_code' in df.columns else None
                
                if col_value:
                    # fetch_metric_data YA convierte a GWh
                    gen_gwh = df[col_value].sum()
                    logger.info(f"    ✅ Gene/Sistema: {gen_gwh:.2f} GWh")
                    total_exitosos += 1
                else:
                    logger.warning(f"    ⚠️ Gene/Sistema: Sin columna de valor")
            else:
                logger.warning(f"    ⚠️ Gene/Sistema: Sin datos")
            time.sleep(0.3)
        except Exception as e:
            logger.error(f"    ❌ Gene/Sistema: Error - {e}")
        
        # Si encontramos datos para esta fecha, no necesitamos seguir buscando
        if total_exitosos > 0:
            logger.info(f"\n  ✅ Datos encontrados para {fecha_str}, no es necesario buscar más atrás")
            break
    
    logger.info(f"\n{'=' * 80}")
    logger.info(f"✅ Indicadores Generación: {total_exitosos}/{total_intentos} exitosos")
    logger.info(f"{'=' * 80}\n")
    
    return total_exitosos > 0


# ==========================================
# EJECUCIÓN PRINCIPAL
# ==========================================

def main():
    """Ejecutar precalentamiento completo"""
    logger.info("\n" + "=" * 80)
    logger.info("🔥🔥🔥 INICIANDO PRECALENTAMIENTO AUTOMÁTICO v2.0 🔥🔥🔥")
    logger.info("=" * 80)
    logger.info(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Rangos a precalentar: {RANGOS_COMUNES}")
    logger.info("=" * 80 + "\n")
    
    start_total = time.time()
    resultados = {}
    
    # 1. Precalentar Indicadores de Generación (PÁGINA PRINCIPAL - PRIORIDAD MÁXIMA)
    try:
        resultados['indicadores_generacion'] = precalentar_indicadores_generacion()
    except Exception as e:
        logger.error(f"❌ Error en indicadores generación: {e}")
        resultados['indicadores_generacion'] = False
    
    # 2. Precalentar Generación por Fuentes (MÁS IMPORTANTE)
    try:
        resultados['generacion_fuentes'] = precalentar_generacion_por_fuentes()
    except Exception as e:
        logger.error(f"❌ Error en generación fuentes: {e}")
        resultados['generacion_fuentes'] = False
    
    # 3. Precalentar Métricas Hídricas
    try:
        resultados['metricas_hidricas'] = precalentar_metricas_hidricas()
    except Exception as e:
        logger.error(f"❌ Error en métricas hídricas: {e}")
        resultados['metricas_hidricas'] = False
    
    # RESUMEN FINAL
    elapsed_total = time.time() - start_total
    exitosos = sum(1 for v in resultados.values() if v)
    
    logger.info("\n" + "=" * 80)
    logger.info("📊 RESUMEN DE PRECALENTAMIENTO")
    logger.info("=" * 80)
    logger.info(f"⏱️  Tiempo total: {elapsed_total:.1f}s ({elapsed_total/60:.1f} min)")
    logger.info(f"✅ Procesos exitosos: {exitosos}/{len(resultados)}")
    logger.info("")
    for proceso, exito in resultados.items():
        estado = "✅ OK" if exito else "❌ FAIL"
        logger.info(f"  {estado} - {proceso}")
    logger.info("=" * 80)
    logger.info("✅ Sistema listo - usuarios encontrarán datos pre-calculados")
    logger.info("=" * 80 + "\n")
    
    return exitosos > 0


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.critical(f"💥 ERROR CRÍTICO: {e}", exc_info=True)
        sys.exit(1)
