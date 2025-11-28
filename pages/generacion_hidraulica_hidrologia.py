
def get_plotly_modules():
    """Importar plotly solo cuando se necesite"""
    import plotly.express as px
    import plotly.graph_objects as go
    return px, go

from dash import dcc, html, Input, Output, State, callback, register_page, dash
import dash_table
import plotly.express as px
import dash_bootstrap_components as dbc
import pandas as pd
from datetime import date, timedelta, datetime
import warnings
import sys
import os
import time
from flask import Flask, jsonify
import dash
# Use the installed pydataxm package instead of local module
try:
    from pydataxm.pydataxm import ReadDB
    PYDATAXM_AVAILABLE = True
except ImportError:
    PYDATAXM_AVAILABLE = False
    # logger no está disponible aún aquí, se loggea después

# NOTA IMPORTANTE SOBRE UNIDADES DE MEDIDA:
# La métrica 'AporEner' de XM representa aportes de energía por río
# Su unidad de medida es kWh (kilovatio-hora), convertida a GWh para visualización
# Los aportes energéticos representan la energía potencial de los caudales

# Imports locales para componentes uniformes
from utils.components import crear_header, crear_navbar, crear_sidebar_universal, crear_boton_regresar
from utils.config import COLORS
from utils.embalses_coordenadas import REGIONES_COORDENADAS, obtener_coordenadas_region
from utils.logger import setup_logger
from utils.validators import validate_date_range, validate_string
from utils.exceptions import DateRangeError, InvalidParameterError, DataNotFoundError
# from .api_fallback import create_fallback_data, create_api_status_message, save_api_status

warnings.filterwarnings("ignore")

# Configurar logger para este módulo
logger = setup_logger(__name__)

register_page(
    __name__,
    path="/generacion/hidraulica/hidrologia",
    name="Hidrología",
    title="Hidrología - Ministerio de Minas y Energía de Colombia",
    order=6
)

# --- NUEVO: Fecha/hora de última actualización del código ---
LAST_UPDATE = time.strftime('%Y-%m-%d %H:%M:%S')

# Funciones auxiliares para formateo de datos
def format_number(value):
    """Formatear números con separadores de miles usando puntos"""
    if pd.isna(value) or not isinstance(value, (int, float)):
        return value
    
    # Formatear con separador de miles usando puntos (formato colombiano)
    return f"{value:,.2f}".replace(",", ".")

def format_date(date_value):
    """Formatear fechas para mostrar solo la fecha sin hora"""
    if pd.isna(date_value):
        return date_value
    
    if isinstance(date_value, str):
        try:
            # Intentar convertir string a datetime
            dt_value = pd.to_datetime(date_value)
            return dt_value.strftime('%Y-%m-%d')
        except Exception:
            return date_value
    elif hasattr(date_value, 'strftime'):
        return date_value.strftime('%Y-%m-%d')
    else:
        return date_value


# Inicializar API XM de forma perezosa usando el helper
from utils._xm import get_objetoAPI, obtener_datos_desde_sqlite, obtener_datos_inteligente
API_STATUS = None

# Verificar si la API está disponible al inicializar el módulo
_temp_api = get_objetoAPI()
if _temp_api is not None:
    logger.info("✅ API XM inicializada correctamente (lazy)")
    API_STATUS = {'status': 'online', 'message': 'API XM funcionando correctamente'}
else:
    API_STATUS = {'status': 'offline', 'message': 'pydataxm no está disponible'}
    logger.warning("⚠️ API XM no disponible (pydataxm no está disponible)")


# --- VALIDACIÓN DE FECHAS Y MANEJO DE ERRORES ---
def validar_rango_fechas(start_date, end_date):
    """
    Valida que el rango de fechas sea válido para la API de XM.
    La API de XM tiene limitaciones temporales hacia atrás.
    """
    from datetime import datetime, timedelta
    
    if not start_date or not end_date:
        return False, "Debe seleccionar fechas de inicio y fin."
    
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d') if isinstance(start_date, str) else start_date
        end_dt = datetime.strptime(end_date, '%Y-%m-%d') if isinstance(end_date, str) else end_date
        
        # Fecha mínima permitida (aproximadamente 2 años hacia atrás para datos hidrológicos)
        fecha_minima = datetime.now() - timedelta(days=730)
        fecha_maxima = datetime.now()
        
        if start_dt < fecha_minima:
            return False, f"⚠️ La fecha de inicio es muy antigua. La API de XM solo permite consultas desde {fecha_minima.strftime('%Y-%m-%d')} aproximadamente. Para datos históricos más antiguos, contacte directamente a XM."
        
        if end_dt > fecha_maxima:
            return False, f"⚠️ La fecha final no puede ser futura. Fecha máxima permitida: {fecha_maxima.strftime('%Y-%m-%d')}"
        
        if start_dt > end_dt:
            return False, "⚠️ La fecha de inicio debe ser anterior a la fecha final."
        
        # Validar que el rango no sea demasiado amplio (más de 1 año)
        dias_diferencia = (end_dt - start_dt).days
        if dias_diferencia > 365:
            return False, "⚠️ El rango de fechas es muy amplio. Por favor, seleccione un período de máximo 1 año para optimizar el rendimiento."
        
        return True, "Rango de fechas válido"
        
    except Exception as e:
        return False, f"Error validando fechas: {str(e)}"

def manejar_error_api(error, operacion="consulta"):
    """
    Maneja errores específicos de la API de XM y proporciona mensajes útiles.
    """
    error_str = str(error).lower()
    
    if "400" in error_str and "json" in error_str and "text/plain" in error_str:
        message = f"🔄 La API de XM retornó un error para esta {operacion}. Esto suele ocurrir cuando:" + "\n"
        message += "• Las fechas seleccionadas están fuera del rango disponible\n"
        message += "• Los datos para el período solicitado no están disponibles\n"
        message += "• Hay mantenimiento en los servidores de XM\n"
        message += "💡 Recomendaciones:\n"
        message += "• Intente con fechas más recientes (últimos 6 meses)\n"
        message += "• Reduzca el rango de fechas\n"
        message += "• Verifique el estado de la API de XM en www.xm.com.co"
        return message
    
    elif "timeout" in error_str or "connection" in error_str:
        return f"🌐 Error de conexión con la API de XM. Verifique su conexión a internet y vuelva a intentar."
    
    elif "unauthorized" in error_str or "403" in error_str:
        return f"🔐 Error de autorización con la API de XM. Contacte al administrador del sistema."
    
    else:
        return f"❌ Error inesperado en la {operacion}: {str(error)[:200]}..."


def get_reservas_hidricas(fecha):
    """
    Calcula las reservas hídricas del SIN para una fecha específica.
    Usa la función unificada para garantizar consistencia total.
    
    Args:
        fecha: Fecha en formato 'YYYY-MM-DD'
        
    Returns:
        tuple: (porcentaje, valor_GWh) o (None, None) si hay error
    """
# REMOVED DEBUG:     print(f"[DEBUG] get_reservas_hidricas llamada con fecha: {fecha}")
    
    # Usar la función unificada para el cálculo nacional
    resultado = calcular_volumen_util_unificado(fecha)
    if resultado:
        return resultado['porcentaje'], resultado['volumen_gwh']
    else:
        return None, None


def get_aportes_hidricos(fecha):
    """
    Calcula los aportes hídricos del SIN para una fecha específica.
    Replica exactamente el cálculo de XM: 
    (Promedio acumulado del mes de Aportes Energía / Promedio acumulado del mes de Media Histórica) * 100
    
    Args:
        fecha: Fecha en formato 'YYYY-MM-DD'
        
    Returns:
        tuple: (porcentaje, valor_GWh) o (None, None) si hay error
    """
    # Usar fetch_metric_data que tiene cache con datos históricos
# REMOVED DEBUG:     print(f"[DEBUG] get_aportes_hidricos llamada con fecha: {fecha}")

    try:
        # Calcular el rango desde el primer día del mes hasta la fecha final
        fecha_final = pd.to_datetime(fecha)
        fecha_inicio = fecha_final.replace(day=1)
        fecha_inicio_str = fecha_inicio.strftime('%Y-%m-%d')
        fecha_final_str = fecha_final.strftime('%Y-%m-%d')

        # Obtener aportes energía usando métrica principal de XM desde SQLite
        aportes_diarios, warning = obtener_datos_inteligente('AporEner', 'Sistema', fecha_inicio_str, fecha_final_str)

        # Si no funciona, intentar con métricas alternativas
        if aportes_diarios is None or aportes_diarios.empty:
            metricas_aportes = ['AportesDiariosEnergia', 'AportesEnergia']
            for metrica in metricas_aportes:
                try:
                    aportes_diarios, warning = obtener_datos_inteligente(metrica, 'Sistema', fecha_inicio_str, fecha_final_str)
                    if aportes_diarios is not None and not aportes_diarios.empty:
                        break
                except Exception:
                    continue

        # Obtener media histórica usando métrica principal de XM desde SQLite
        media_historica, warning = obtener_datos_inteligente('AporEnerMediHist', 'Sistema', fecha_inicio_str, fecha_final_str)

        # Si no funciona, intentar con métricas alternativas
        if media_historica is None or media_historica.empty:
            metricas_media = ['MediaHistoricaAportes', 'AportesMediaHistorica']
            for metrica in metricas_media:
                try:
                    media_historica, warning = obtener_datos_inteligente(metrica, 'Sistema', fecha_inicio_str, fecha_final_str)
                    if media_historica is not None and not media_historica.empty:
                        break
                except Exception:
                    continue

        if aportes_diarios is not None and not aportes_diarios.empty and media_historica is not None and not media_historica.empty:
            # CORRECCIÓN: Los aportes son ACUMULATIVOS, usar SUM no MEAN
            # Los aportes energéticos se suman (total de energía del período)
            aportes_valor = aportes_diarios['Value'].sum()
            media_valor = media_historica['Value'].sum()
            
            logger.debug(f"Aportes hídricos calculados", extra={
                'fecha': fecha,
                'aportes_total_gwh': round(aportes_valor, 2),
                'media_hist_gwh': round(media_valor, 2),
                'registros_aportes': len(aportes_diarios),
                'registros_media': len(media_historica)
            })
            
            if media_valor > 0:
                porcentaje = round((aportes_valor / media_valor) * 100, 2)
                return porcentaje, aportes_valor
        return None, None
    except Exception as e:
        logger.error(f"Error obteniendo aportes hídricos: {e}", exc_info=True)
        return None, None


# --- FUNCIÓN UNIFICADA PARA CÁLCULOS DE VOLUMEN ÚTIL ---
def calcular_volumen_util_unificado(fecha, region=None, embalse=None):
    """
    Función unificada para calcular el porcentaje de volumen útil usando la fórmula:
    suma VoluUtilDiarEner / suma CapaUtilDiarEner * 100
    
    Esta función garantiza que tanto las fichas como las tablas usen exactamente la misma lógica.
    
    Args:
        fecha: Fecha en formato 'YYYY-MM-DD' (solo se usa la fecha final)
        region: Nombre de la región hidrológica (opcional - si se especifica, filtra por región)
        embalse: Nombre del embalse específico (opcional - si se especifica, filtra por embalse)
        
    Returns:
        dict: {
            'porcentaje': float,  # Porcentaje de volumen útil
            'volumen_gwh': float, # Suma de VoluUtilDiarEner en GWh
            'capacidad_gwh': float, # Suma de CapaUtilDiarEner en GWh
            'embalses': list      # Lista de embalses incluidos en el cálculo
        } o None si hay error
    """
    logger.debug(f"Calculando volumen útil - Fecha: {fecha}, Región: {region}, Embalse: {embalse}")
    
    try:
        # Usar helper para buscar fecha con datos disponibles
        fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
        df_vol, fecha_vol = obtener_datos_desde_sqlite('VoluUtilDiarEner', 'Embalse', fecha_obj)
        df_cap, fecha_cap = obtener_datos_desde_sqlite('CapaUtilDiarEner', 'Embalse', fecha_obj)
        
        # Verificar que ambos tienen datos de la misma fecha
        if df_vol is not None and df_cap is not None and fecha_vol == fecha_cap:
            fecha_final = fecha_vol.strftime('%Y-%m-%d')
            logger.debug(f"Usando fecha con datos: {fecha_final}")
        else:
            df_vol, df_cap, fecha_final = None, None, None

        if df_vol is None or df_vol.empty or df_cap is None or df_cap.empty:
            logger.warning("No se pudieron obtener datos para calcular volumen útil")
            return None

        logger.debug(f"Datos obtenidos: {len(df_vol)} registros de volumen, {len(df_cap)} registros de capacidad")

        # Obtener información de embalses y regiones
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        embalses_info, warning = obtener_datos_inteligente('ListadoEmbalses','Sistema', yesterday, today)
        embalses_info['Values_Name'] = embalses_info['Values_Name'].str.strip().str.upper()
        embalses_info['Values_HydroRegion'] = embalses_info['Values_HydroRegion'].str.strip().str.title()
        embalse_region_dict = dict(zip(embalses_info['Values_Name'], embalses_info['Values_HydroRegion']))

        # Mapear región a cada embalse
        df_vol['Region'] = df_vol['Name'].map(embalse_region_dict)
        df_cap['Region'] = df_cap['Name'].map(embalse_region_dict)

        # Aplicar filtros según los parámetros
        if region:
            region_normalized = region.strip().title()
            df_vol = df_vol[df_vol['Region'] == region_normalized]
            df_cap = df_cap[df_cap['Region'] == region_normalized]
            logger.debug(f"Filtrado por región '{region_normalized}': {len(df_vol)} embalses con volumen, {len(df_cap)} con capacidad")

        if embalse:
            df_vol = df_vol[df_vol['Name'] == embalse]
            df_cap = df_cap[df_cap['Name'] == embalse]
            logger.debug(f"Filtrado por embalse '{embalse}': {len(df_vol)} registros de volumen, {len(df_cap)} de capacidad")

        if df_vol.empty or df_cap.empty:
            logger.warning("Sin datos después del filtrado")
            return None

        # Calcular totales usando la fórmula exacta
        # ✅ CORREGIDO: obtener_datos_desde_sqlite devuelve valores en Wh, convertir a GWh
        # Nota: Si en el futuro se cambia a obtener_datos_inteligente, NO dividir por 1e9
        vol_total_gwh = df_vol['Value'].sum() / 1e9
        cap_total_gwh = df_cap['Value'].sum() / 1e9

        embalses_incluidos = list(set(df_vol['Name'].tolist()) & set(df_cap['Name'].tolist()))

        logger.debug(f"Totales calculados: Volumen = {vol_total_gwh:.2f} GWh, Capacidad = {cap_total_gwh:.2f} GWh")
        logger.debug(f"Embalses incluidos: {embalses_incluidos}")

        if cap_total_gwh > 0:
            porcentaje = round((vol_total_gwh / cap_total_gwh) * 100, 2)
            logger.info(f"Porcentaje volumen útil calculado: {porcentaje}%")

            return {
                'porcentaje': porcentaje,
                'volumen_gwh': vol_total_gwh,
                'capacidad_gwh': cap_total_gwh,
                'embalses': embalses_incluidos
            }
        else:
            logger.warning("Capacidad total es 0, no se puede calcular porcentaje")
            return None

    except Exception as e:
        logger.error(f"Error en cálculo de volumen útil: {e}", exc_info=True)
        return None


def get_reservas_hidricas_por_region(fecha, region):
    """
    Calcula las reservas hídricas filtradas por región específica.
    Usa la función unificada para garantizar consistencia con las tablas.
    
    Args:
        fecha: Fecha en formato 'YYYY-MM-DD'
        region: Nombre de la región hidrológica
        
    Returns:
        tuple: (porcentaje, valor_GWh) o (None, None) si hay error
    """
# REMOVED DEBUG:     print(f"[DEBUG] get_reservas_hidricas_por_region llamada con fecha: {fecha}, región: {region}")
    
    resultado = calcular_volumen_util_unificado(fecha, region=region)
    if resultado:
        return resultado['porcentaje'], resultado['volumen_gwh']
    else:
        return None, None


def get_aportes_hidricos_por_region(fecha, region):
    """
    Calcula los aportes hídricos filtrados por región específica.
    Replica el método de XM: promedio acumulado mensual de aportes energía por región
    
    Args:
        fecha: Fecha en formato 'YYYY-MM-DD'
        region: Nombre de la región hidrológica
        
    Returns:
        tuple: (porcentaje, valor_GWh) o (None, None) si hay error
    """
# REMOVED DEBUG:     print(f"[DEBUG] get_aportes_hidricos_por_region llamada con fecha: {fecha}, región: {region}")
    
    try:
        # Calcular el rango desde el primer día del mes hasta la fecha final
        fecha_final = pd.to_datetime(fecha)
        fecha_inicio = fecha_final.replace(day=1)
        fecha_inicio_str = fecha_inicio.strftime('%Y-%m-%d')
        fecha_final_str = fecha_final.strftime('%Y-%m-%d')
        
        # Obtener aportes energía por río desde SQLite
        aportes_data, warning = obtener_datos_inteligente('AporEner', 'Rio', fecha_inicio_str, fecha_final_str)
        
        if aportes_data is not None and not aportes_data.empty:
            # Asignar región a cada río
            rio_region = ensure_rio_region_loaded()
            aportes_data['Region'] = aportes_data['Name'].map(rio_region)
            
            # Filtrar por región específica (normalizar región)
            region_normalized = region.strip().title()
            aportes_region = aportes_data[aportes_data['Region'] == region_normalized]
            
            if not aportes_region.empty:
                # CORRECCIÓN: Suma total del período (aportes acumulativos)
                aportes_total_region = aportes_region['Value'].sum()
                
                # Obtener media histórica para la región
                media_historica_data, warning = obtener_datos_inteligente('AporEnerMediHist', 'Rio', fecha_inicio_str, fecha_final_str)
                
                if media_historica_data is not None and not media_historica_data.empty:
                    media_historica_data['Region'] = media_historica_data['Name'].map(rio_region)
                    media_historica_region = media_historica_data[media_historica_data['Region'] == region_normalized]
                    
                    if not media_historica_region.empty:
                        # CORRECCIÓN: Suma total del período histórico
                        media_total_region = media_historica_region['Value'].sum()
                        
# REMOVED DEBUG:                         print(f"[DEBUG] Región {region_normalized}: Aportes = {aportes_total_region} GWh, Media histórica = {media_total_region} GWh")
                        
                        if media_total_region > 0:
                            # Fórmula exacta de XM por región
                            porcentaje = round((aportes_total_region / media_total_region) * 100, 2)
# REMOVED DEBUG:                             print(f"[DEBUG] Aportes región {region}: {porcentaje}%")
                            return porcentaje, aportes_total_region
        
# REMOVED DEBUG:         print(f"[DEBUG] Sin datos suficientes para calcular aportes de región {region}")
        return None, None
        
    except Exception as e:
        logger.error(f"Error obteniendo aportes hídricos por región: {e}", exc_info=True)
        return None, None


def get_aportes_hidricos_por_rio(fecha, rio):
    """
    Calcula los aportes hídricos de un río específico.
    
    Args:
        fecha: Fecha en formato 'YYYY-MM-DD'
        rio: Nombre del río
        
    Returns:
        tuple: (porcentaje, valor_m3s) o (None, None) si hay error
    """
# REMOVED DEBUG:     print(f"[DEBUG] get_aportes_hidricos_por_rio llamada con fecha: {fecha}, río: {rio}")
    
    try:
        # Obtener aportes del río específico desde SQLite
        aportes_data, warning = obtener_datos_inteligente('AporCaudal', 'Rio', fecha, fecha)
        
        if aportes_data is not None and not aportes_data.empty:
            # Buscar el río específico
            rio_data = aportes_data[aportes_data['Name'] == rio]
            
            if not rio_data.empty:
                aportes_rio = rio_data['Value'].iloc[0]
                
                # Para el porcentaje, comparar con la media de todos los ríos
                media_total_rios = aportes_data['Value'].mean()
                
                if media_total_rios > 0:
                    porcentaje = round((aportes_rio / media_total_rios) * 100, 2)
# REMOVED DEBUG:                     print(f"[DEBUG] Aportes río {rio}: {porcentaje}% (valor: {aportes_rio} m³/s)")
                    return porcentaje, aportes_rio
        
# REMOVED DEBUG:         print(f"[DEBUG] Sin datos para el río {rio}")
        return None, None
        
    except Exception as e:
        logger.error(f"Error obteniendo aportes hídricos por río: {e}", exc_info=True)
        return None, None


# Obtener la relación río-región directamente desde la API XM
def get_rio_region_dict():
    try:
        # Usar fecha actual para obtener listado más reciente desde SQLite
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        df, warning = obtener_datos_inteligente('ListadoRios', 'Sistema', yesterday, today)
        if 'Values_Name' in df.columns and 'Values_HydroRegion' in df.columns:
            # Normalizar nombres igual que antes
            df['Values_Name'] = df['Values_Name'].str.strip().str.upper()
            df['Values_HydroRegion'] = df['Values_HydroRegion'].str.strip().str.title()
            return dict(sorted(zip(df['Values_Name'], df['Values_HydroRegion'])))
        else:
            return {}
    except Exception as e:
        logger.error(f"Error obteniendo relación río-región desde la API: {e}", exc_info=True)
        return {}

# Inicializar como None, se cargará bajo demanda
RIO_REGION = None

def ensure_rio_region_loaded():
    """Carga RIO_REGION bajo demanda si aún no se ha cargado."""
    global RIO_REGION
    if RIO_REGION is None:
        RIO_REGION = get_rio_region_dict()
    return RIO_REGION

def get_region_options():
    """
    Obtiene las regiones que tienen ríos con datos de caudal activos.
    Filtra regiones que no tienen datos para evitar confusión al usuario.
    """
    rio_region = ensure_rio_region_loaded()
    try:
        # Obtener ríos con datos de caudal recientes desde SQLite (7 días optimizado)
        df, warning = obtener_datos_inteligente('AporCaudal', 'Rio', (date.today() - timedelta(days=7)).strftime('%Y-%m-%d'), date.today().strftime('%Y-%m-%d'))
        if 'Name' in df.columns:
            rios_con_datos = set(df['Name'].unique())
            # Filtrar solo regiones que tienen ríos con datos
            regiones_con_datos = set()
            for rio, region in rio_region.items():
                if rio in rios_con_datos:
                    regiones_con_datos.add(region)
            return sorted(regiones_con_datos)
        else:
            return sorted(set(rio_region.values()))
    except Exception as e:
        logger.error(f"Error filtrando regiones con datos: {e}", exc_info=True)
        return sorted(set(rio_region.values()))






# --- NUEVO: Función para obtener todos los ríos únicos desde la API ---
def get_all_rios_api():
    try:
        df, warning = obtener_datos_inteligente('AporCaudal', 'Rio', '2000-01-01', date.today().strftime('%Y-%m-%d'))
        if df is not None and 'Name' in df.columns:
            rios = sorted(df['Name'].dropna().unique())
            return rios
        else:
            return []
    except Exception:
        return []

def get_rio_options(region=None):
    try:
        df, warning = obtener_datos_inteligente('AporCaudal', 'Rio', (date.today() - timedelta(days=7)).strftime('%Y-%m-%d'), date.today().strftime('%Y-%m-%d'))
        if df is not None and 'Name' in df.columns:
            rios = sorted(df['Name'].dropna().unique())
            if region:
                rio_region = ensure_rio_region_loaded()
                rios = [r for r in rios if rio_region.get(r) == region]
            return rios
        else:
            return []
    except Exception as e:
        logger.error(f"Error obteniendo opciones de Río: {e}", exc_info=True)
        return []

regiones = []  # Se cargarán dinámicamente
rios = []      # Se cargarán dinámicamente

def crear_estilos_condicionales_para_tabla_estatica(start_date=None, end_date=None):
    """
    Crea estilos condicionales para la tabla estática basados en riesgo
    """
    try:
        # Obtener datos frescos para calcular estilos
        df_fresh = get_embalses_capacidad(None, start_date, end_date)
        if df_fresh.empty:
            return [
                {
                    "if": {"filter_query": "{Embalse} = \"TOTAL\""}, 
                    "backgroundColor": "#007bff",
                    "color": "white",
                    "fontWeight": "bold"
                }
            ]
        
        # Agregar riesgo y generar estilos
        df_con_riesgo = agregar_columna_riesgo_a_tabla(df_fresh)
        estilos = generar_estilos_condicionales_riesgo(df_con_riesgo)
        return estilos
        
    except Exception as e:
        logger.error(f"Error generando estilos condicionales: {e}", exc_info=True)
        return [
            {
                "if": {"filter_query": "{Embalse} = \"TOTAL\""}, 
                "backgroundColor": "#007bff",
                "color": "white",
                "fontWeight": "bold"
            }
        ]


# ============================================================================
# FUNCIONES PARA MAPA DE EMBALSES POR REGIÓN
# ============================================================================

def calcular_semaforo_embalse(participacion, volumen_pct):
    """
    Calcula el nivel de riesgo según la lógica del semáforo hidrológico de XM:
    
    Factor 1: Importancia Estratégica (participación > 10%)
    Factor 2: Disponibilidad Hídrica (% volumen útil)
    
    RIESGO ALTO (🔴): Embalses estratégicos (>10%) con volumen crítico (<30%)
    RIESGO MEDIO (🟡): Embalses estratégicos con volumen bajo (30-70%) o embalses pequeños con volumen crítico
    RIESGO BAJO (🟢): Embalses con volumen adecuado (≥70%) independientemente de su tamaño
    
    Args:
        participacion: % de participación en el sistema (0-100)
        volumen_pct: % de volumen útil disponible (0-100)
    
    Returns:
        tuple: (nivel_riesgo, color, mensaje)
    """
    es_estrategico = participacion >= 10
    
    if volumen_pct >= 70:
        return 'BAJO', '#28a745', '✅'
    elif volumen_pct >= 30:
        if es_estrategico:
            return 'MEDIO', '#ffc107', '⚡'
        else:
            return 'BAJO', '#28a745', '✅'
    else:  # volumen_pct < 30
        if es_estrategico:
            return 'ALTO', '#dc3545', '🚨'
        else:
            return 'MEDIO', '#ffc107', '⚡'

def obtener_datos_embalses_por_region():
    """
    Obtiene los datos de embalses agrupados por región hidrológica
    
    Returns:
        dict: {region: {embalses: [...], riesgo_max: str, color: str, lat: float, lon: float}}
    """
    try:
        # Obtener fecha actual y buscar últimos datos disponibles
        fecha_hoy = date.today()
        
        # Usar helper para buscar datos en los últimos 7 días
        df_vol, fecha_vol = obtener_datos_desde_sqlite('VoluUtilDiarEner', 'Embalse', fecha_hoy)
        df_cap, fecha_cap = obtener_datos_desde_sqlite('CapaUtilDiarEner', 'Embalse', fecha_hoy)
        df_listado, fecha_listado = obtener_datos_desde_sqlite('ListadoEmbalses', 'Sistema', fecha_hoy)
        
        # Verificar que todos tienen datos de la misma fecha
        if (df_vol is not None and df_cap is not None and df_listado is not None and 
            fecha_vol == fecha_cap == fecha_listado):
            fecha_str = fecha_vol.strftime('%Y-%m-%d')
            logger.info(f"Datos de embalses obtenidos para {fecha_str}")
        else:
            logger.error("No se pudieron obtener datos de embalses")
            return None
        
        # Detectar nombre de columnas (mismo código que en las tablas)
        col_value_vol = None
        col_value_cap = None
        col_name_vol = None
        
        # Buscar columna de valores
        for col in ['Values_code', 'Value', 'Values_Code']:
            if col in df_vol.columns:
                col_value_vol = col
                break
        
        for col in ['Values_code', 'Value', 'Values_Code']:
            if col in df_cap.columns:
                col_value_cap = col
                break
        
        # Buscar columna de nombre/código
        for col in ['Values_code', 'Values_Code', 'Name']:
            if col in df_vol.columns:
                col_name_vol = col
                break
        
        if not col_value_vol or not col_value_cap or not col_name_vol:
            logger.error(f"Columnas no encontradas. df_vol: {df_vol.columns.tolist()}")
            return None
        
        logger.debug(f"Columnas detectadas - vol_value: {col_value_vol}, cap_value: {col_value_cap}, name: {col_name_vol}")
        
        # Crear diccionario de región por embalse
        embalse_region = {}
        col_name_listado = None
        for col in ['Values_Code', 'Values_code', 'Name']:
            if col in df_listado.columns:
                col_name_listado = col
                break
        
        if col_name_listado and 'Values_HydroRegion' in df_listado.columns:
            for _, row in df_listado.iterrows():
                codigo = row[col_name_listado]
                region = row['Values_HydroRegion']
                embalse_region[codigo] = region
        else:
            logger.error(f"Columnas del listado: {df_listado.columns.tolist()}")
            return None
        
        # Hacer copias antes de renombrar para evitar modificar los originales
        df_vol_copy = df_vol.copy()
        df_cap_copy = df_cap.copy()
        
        # Renombrar columnas en las copias
        df_vol_copy = df_vol_copy.rename(columns={col_value_vol: 'volumen_wh', col_name_vol: 'codigo'})
        df_cap_copy = df_cap_copy.rename(columns={col_value_cap: 'capacidad_wh'})
        
        # Buscar columna de nombre/código en df_cap
        col_name_cap = None
        for col in ['Values_code', 'Values_Code', 'Name']:
            if col in df_cap.columns:
                col_name_cap = col
                break
        
        df_cap_copy = df_cap_copy.rename(columns={col_name_cap: 'codigo'})
        
        logger.debug(f"Columnas df_vol_copy: {df_vol_copy.columns.tolist()}")
        logger.debug(f"Columnas df_cap_copy: {df_cap_copy.columns.tolist()}")
        
        # Verificar que las columnas existen
        if 'volumen_wh' not in df_vol_copy.columns or 'codigo' not in df_vol_copy.columns:
            logger.error("Error: columnas faltantes en df_vol_copy")
            return None
        
        if 'capacidad_wh' not in df_cap_copy.columns or 'codigo' not in df_cap_copy.columns:
            logger.error("Error: columnas faltantes en df_cap_copy")
            return None
        
        df_merged = pd.merge(
            df_vol_copy[['codigo', 'volumen_wh']],
            df_cap_copy[['codigo', 'capacidad_wh']],
            on='codigo',
            how='inner'
        )
        
        # Calcular porcentajes
        df_merged['volumen_pct'] = (df_merged['volumen_wh'] / df_merged['capacidad_wh']) * 100
        capacidad_total = df_merged['capacidad_wh'].sum()
        df_merged['participacion'] = (df_merged['capacidad_wh'] / capacidad_total) * 100
        
        # Agregar región
        df_merged['region'] = df_merged['codigo'].map(embalse_region)
        
        # Agrupar por región
        regiones_data = {}
        for region in df_merged['region'].unique():
            if pd.isna(region) or region not in REGIONES_COORDENADAS:
                continue
            
            df_region = df_merged[df_merged['region'] == region]
            
            # Crear lista de embalses de la región
            embalses_lista = []
            riesgo_max = 'BAJO'
            orden_riesgo = {'ALTO': 3, 'MEDIO': 2, 'BAJO': 1}
            
            for _, row in df_region.iterrows():
                riesgo, color, icono = calcular_semaforo_embalse(row['participacion'], row['volumen_pct'])
                
                embalses_lista.append({
                    'codigo': row['codigo'],
                    'volumen_pct': row['volumen_pct'],
                    'volumen_gwh': row['volumen_wh'] / 1e9,
                    'capacidad_gwh': row['capacidad_wh'] / 1e9,
                    'participacion': row['participacion'],
                    'riesgo': riesgo,
                    'color': color,
                    'icono': icono
                })
                
                # Actualizar riesgo máximo de la región
                if orden_riesgo[riesgo] > orden_riesgo[riesgo_max]:
                    riesgo_max = riesgo
            
            # Determinar color de la región según el riesgo máximo
            color_region = {'ALTO': '#dc3545', 'MEDIO': '#ffc107', 'BAJO': '#28a745'}[riesgo_max]
            
            coords = REGIONES_COORDENADAS[region]
            
            regiones_data[region] = {
                'embalses': embalses_lista,
                'riesgo_max': riesgo_max,
                'color': color_region,
                'lat': coords['lat'],
                'lon': coords['lon'],
                'nombre': coords['nombre'],
                'total_embalses': len(embalses_lista)
            }
        
        return regiones_data
    
    except Exception as e:
        logger.error(f"Error obteniendo datos para mapa por región: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        return None

def crear_mapa_embalses_por_region():
    """
    Crea el mapa interactivo de Colombia con puntos por región hidrológica
    """
    import plotly.graph_objects as go
    
    regiones_data = obtener_datos_embalses_por_region()
    
    if regiones_data is None or len(regiones_data) == 0:
        return dbc.Alert([
            html.H5("⚠️ No hay datos disponibles", className="alert-heading"),
            html.P("No se pudieron cargar los datos de los embalses. Intente nuevamente más tarde.")
        ], color="warning")
    
    # Crear figura del mapa
    fig = go.Figure()
    
    # Agregar puntos por región
    for region, data in regiones_data.items():
        # Crear texto del tooltip con lista de embalses
        embalses_texto = "<br>".join([
            f"• {emb['codigo']}: {emb['volumen_pct']:.1f}% {emb['icono']}"
            for emb in sorted(data['embalses'], key=lambda x: x['volumen_pct'])[:10]  # Mostrar máximo 10
        ])
        
        if data['total_embalses'] > 10:
            embalses_texto += f"<br>... y {data['total_embalses'] - 10} más"
        
        hover_text = (
            f"<b>{data['nombre']}</b><br>" +
            f"Total embalses: {data['total_embalses']}<br>" +
            f"Riesgo máximo: <b>{data['riesgo_max']}</b><br><br>" +
            f"<b>Embalses:</b><br>{embalses_texto}"
        )
        
        # Tamaño según cantidad de embalses
        tamaño = min(15 + data['total_embalses'] * 3, 40)
        
        fig.add_trace(go.Scattergeo(
            lon=[data['lon']],
            lat=[data['lat']],
            text=[data['nombre']],
            mode='markers+text',
            marker=dict(
                size=tamaño,
                color=data['color'],
                line=dict(width=3, color='white'),
                symbol='circle'
            ),
            textposition='top center',
            textfont=dict(size=10, color='#2c3e50', family='Arial Black'),
            name=f"{data['nombre']} ({data['riesgo_max']})",
            hovertext=hover_text,
            hoverinfo='text',
            showlegend=True
        ))
    
    # Configurar el mapa centrado en Colombia
    fig.update_geos(
        center=dict(lon=-74, lat=4.5),
        projection_type='mercator',
        showcountries=True,
        countrycolor='lightgray',
        showcoastlines=True,
        coastlinecolor='gray',
        showland=True,
        landcolor='#f5f5f5',
        showlakes=True,
        lakecolor='lightblue',
        showrivers=True,
        rivercolor='lightblue',
        lonaxis_range=[-79, -66],
        lataxis_range=[-4.5, 13],
        bgcolor='#e8f4f8'
    )
    
    fig.update_layout(
        title={
            'text': '🗺️ Mapa de Embalses por Región Hidrológica',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18, 'color': COLORS['text_primary'], 'family': 'Arial Black'}
        },
        height=600,
        margin=dict(l=0, r=0, t=60, b=0),
        legend=dict(
            title=dict(text='Regiones', font=dict(size=12, family='Arial Black')),
            orientation='v',
            yanchor='top',
            y=0.98,
            xanchor='left',
            x=0.01,
            bgcolor='rgba(255,255,255,0.9)',
            bordercolor='gray',
            borderwidth=1,
            font=dict(size=10)
        ),
        hoverlabel=dict(
            bgcolor='white',
            font_size=11,
            font_family='Arial'
        )
    )
    
    return dcc.Graph(figure=fig, config={'displayModeBar': True, 'displaylogo': False})

def crear_tabla_embalses_por_region():
    """
    Crea la tabla detallada de embalses agrupada por región
    """
    regiones_data = obtener_datos_embalses_por_region()
    
    if regiones_data is None or len(regiones_data) == 0:
        return dbc.Alert("No hay datos disponibles", color="warning")
    
    # Ordenar regiones por riesgo máximo
    orden_riesgo = {'ALTO': 0, 'MEDIO': 1, 'BAJO': 2}
    regiones_ordenadas = sorted(
        regiones_data.items(),
        key=lambda x: (orden_riesgo[x[1]['riesgo_max']], x[0])
    )
    
    # Crear acordeón con una sección por región
    acordeon_items = []
    
    for region, data in regiones_ordenadas:
        # Ordenar embalses por volumen (menor a mayor)
        embalses_ordenados = sorted(data['embalses'], key=lambda x: x['volumen_pct'])
        
        # Crear filas de tabla para esta región
        filas_region = []
        for emb in embalses_ordenados:
            filas_region.append(
                html.Tr([
                    html.Td(html.Span(emb['icono'], style={'fontSize': '1.2rem'}), className="text-center"),
                    html.Td(emb['codigo'], style={'fontWeight': '600'}),
                    html.Td(f"{emb['volumen_pct']:.1f}%", 
                           style={'color': emb['color'], 'fontWeight': '700'}),
                    html.Td(f"{emb['volumen_gwh']:.0f} GWh"),
                    html.Td(f"{emb['capacidad_gwh']:.0f} GWh"),
                    html.Td(f"{emb['participacion']:.1f}%"),
                    html.Td(emb['riesgo'], 
                           style={
                               'color': emb['color'],
                               'fontWeight': 'bold',
                               'backgroundColor': emb['color'] + '20',
                               'padding': '5px 10px',
                               'borderRadius': '4px'
                           })
                ])
            )
        
        tabla_region = dbc.Table([
            html.Thead([
                html.Tr([
                    html.Th("", className="text-center", style={'width': '50px'}),
                    html.Th("Embalse"),
                    html.Th("Volumen %"),
                    html.Th("Volumen"),
                    html.Th("Capacidad"),
                    html.Th("Participación %"),
                    html.Th("Riesgo")
                ], style={'backgroundColor': data['color'], 'color': 'white', 'fontSize': '0.9rem'})
            ]),
            html.Tbody(filas_region)
        ], bordered=True, hover=True, responsive=True, striped=True, size='sm')
        
        # Título del acordeón con color según riesgo
        titulo_acordeon = html.Div([
            html.Span(f"📍 {data['nombre']}", style={'fontWeight': '600', 'fontSize': '1.1rem'}),
            html.Span(
                f" ({data['total_embalses']} embalses - Riesgo {data['riesgo_max']})",
                style={'color': data['color'], 'fontWeight': 'bold', 'marginLeft': '10px'}
            )
        ])
        
        acordeon_items.append(
            dbc.AccordionItem(
                tabla_region,
                title=titulo_acordeon,
                item_id=f"region-{region}"
            )
        )
    
    return dbc.Accordion(acordeon_items, start_collapsed=True, always_open=True)

# ============================================================================


def crear_fichas_sin_seguras(region=None, rio=None):
    """
    Versión segura de crear_fichas_sin para uso en layout inicial
    con soporte para filtros por región y río.
    """
    try:
        logger.debug("[DEBUG] crear_fichas_sin_seguras ejecutándose...")
        return crear_fichas_sin(region=region, rio=rio)
    except Exception as e:
# REMOVED DEBUG:         print(f"❌ [ERROR] Error en crear_fichas_sin_seguras: {e}")
        import traceback
        traceback.print_exc()
        
        # Devolver fichas temporales con datos de prueba
        return crear_fichas_temporales()

def crear_fichas_temporales():
    """Crear fichas temporales con datos de prueba basados en valores reales de XM"""
    return dbc.Row([
        # Ficha Reservas Hídricas
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-water fa-2x mb-2", style={"color": COLORS['success']}),
                        html.H5("Reservas Hídricas", className="card-title text-center", 
                               style={"fontWeight": "600", "color": COLORS['text_primary']}),
                        html.H3("82.48%", className="text-center mb-1",
                               style={"fontWeight": "bold", "color": COLORS['success'], "fontSize": "2.5rem"}),
                        html.P("14.139.8265 GWh", className="text-center text-muted mb-1",
                              style={"fontSize": "1.1rem", "fontWeight": "500"}),
                        html.Small("SIN Completo • Datos de prueba", 
                                  className="text-muted d-block text-center",
                                  style={"fontSize": "0.8rem"})
                    ], className="text-center")
                ])
            ], className="h-100", style={
                "border": f"1px solid {COLORS['border']}",
                "boxShadow": f"0 2px 4px {COLORS['shadow_sm']}",
                "borderRadius": "8px"
            })
        ], width=12, md=6, className="mb-3"),
        
        # Ficha Aportes Hídricos  
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-tint fa-2x mb-2", style={"color": COLORS['success']}),
                        html.H5("Aportes Hídricos", className="card-title text-center",
                               style={"fontWeight": "600", "color": COLORS['text_primary']}),
                        html.H3("101.2%", className="text-center mb-1",
                               style={"fontWeight": "bold", "color": COLORS['success'], "fontSize": "2.5rem"}),
                        html.P("208.28 GWh", className="text-center text-muted mb-1",
                              style={"fontSize": "1.1rem", "fontWeight": "500"}),
                        html.Small("SIN Completo • Datos de prueba", 
                                  className="text-muted d-block text-center",
                                  style={"fontSize": "0.8rem"})
                    ], className="text-center")
                ])
            ], className="h-100", style={
                "border": f"1px solid {COLORS['border']}",
                "boxShadow": f"0 2px 4px {COLORS['shadow_sm']}",
                "borderRadius": "8px"
            })
        ], width=12, md=6, className="mb-3")
    ])

# Función original con fallback mejorado (comentada temporalmente)
# Esta función será restaurada una vez que se resuelvan los problemas de API

def crear_fichas_sin(fecha=None, region=None, rio=None):
    """
    Crea las fichas KPI de Reservas Hídricas y Aportes Hídricos del SIN
    según los cálculos oficiales de XM.
    
    Nota: Si se especifica región o río, se muestran valores específicos para ese filtro.
    Si no se especifica filtro, se muestran valores del SIN completo.
    
    Args:
        fecha: Fecha para los cálculos (usar fecha de consulta)
        region: Región hidrológica específica (opcional)
        rio: Río específico (opcional)
    """
    # Usar solo la fecha final para los cálculos (ignorar fecha inicial)
    fecha_calculo = fecha if fecha else (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')

    # Determinar el contexto de los cálculos SOLO usando la fecha final
    if rio and rio != "__ALL__":
        contexto = f"Río {rio}"
# REMOVED DEBUG:         logger.debug(f"[DEBUG] crear_fichas_sin llamada con fecha_calculo: {fecha_calculo} (RÍO: {rio})")
        reservas_pct, reservas_gwh = None, None
        aportes_pct, aportes_m3s = get_aportes_hidricos_por_rio(fecha_calculo, rio)
        reservas_pct_str = "N/A"
        reservas_gwh_str = "No aplica para río individual"
        aportes_pct_str = f"{aportes_pct:.2f}%" if aportes_pct is not None else "N/D"
        aportes_gwh_str = f"{aportes_m3s:,.1f} m³/s".replace(",", ".") if aportes_m3s is not None else "N/D"
    elif region and region != "__ALL_REGIONS__":
        contexto = f"Región {region}"
# REMOVED DEBUG:         logger.debug(f"[DEBUG] crear_fichas_sin llamada con fecha_calculo: {fecha_calculo} (REGIÓN: {region})")
        reservas_pct, reservas_gwh = get_reservas_hidricas_por_region(fecha_calculo, region)
        aportes_pct, aportes_gwh = get_aportes_hidricos_por_region(fecha_calculo, region)
        reservas_pct_str = f"{reservas_pct:.2f}%" if reservas_pct is not None else "N/D"
        reservas_gwh_str = f"{reservas_gwh:,.0f} GWh".replace(",", ".") if reservas_gwh is not None else "N/D"
        aportes_pct_str = f"{aportes_pct:.2f}%" if aportes_pct is not None else "N/D"
        aportes_gwh_str = f"{aportes_gwh:,.0f} GWh".replace(",", ".") if aportes_gwh is not None else "N/D"
    else:
        contexto = "SIN Completo"
# REMOVED DEBUG:         logger.debug(f"[DEBUG] crear_fichas_sin llamada con fecha_calculo: {fecha_calculo} (SIN COMPLETO)")
        reservas_pct, reservas_gwh = get_reservas_hidricas(fecha_calculo)
        aportes_pct, aportes_gwh = get_aportes_hidricos(fecha_calculo)
        reservas_pct_str = f"{reservas_pct:.2f}%" if reservas_pct is not None else "N/D"
        reservas_gwh_str = f"{reservas_gwh:,.0f} GWh".replace(",", ".") if reservas_gwh is not None else "N/D"
        aportes_pct_str = f"{aportes_pct:.2f}%" if aportes_pct is not None else "N/D"
        aportes_gwh_str = f"{aportes_gwh:,.0f} GWh".replace(",", ".") if aportes_gwh is not None else "N/D"

    # Determinar colores según porcentajes
    color_reservas = COLORS['success'] if reservas_pct and reservas_pct >= 60 else (COLORS['warning'] if reservas_pct and reservas_pct >= 40 else COLORS['danger'])
    color_aportes = COLORS['success'] if aportes_pct and aportes_pct >= 80 else (COLORS['warning'] if aportes_pct and aportes_pct >= 60 else COLORS['info'])

    # Si no hay reservas por río, usar color neutro
    if reservas_pct is None and rio and rio != "__ALL__":
        color_reservas = COLORS['secondary']

    return dbc.Row([
        # Ficha Reservas Hídricas
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-water fa-2x mb-2", style={"color": color_reservas}),
                        html.H5("Reservas Hídricas", className="card-title text-center", 
                               style={"fontWeight": "600", "color": COLORS['text_primary']}),
                        html.H3(reservas_pct_str, className="text-center mb-1",
                               style={"fontWeight": "bold", "color": color_reservas, "fontSize": "2.5rem"}),
                        html.P(reservas_gwh_str, className="text-center text-muted mb-1",
                              style={"fontSize": "1.1rem", "fontWeight": "500"}),
                        html.Small(f"{contexto} • {fecha_calculo}", 
                                  className="text-muted d-block text-center",
                                  style={"fontSize": "0.8rem"})
                    ], className="text-center")
                ])
            ], className="h-100", style={
                "border": f"1px solid {COLORS['border']}",
                "boxShadow": f"0 2px 4px {COLORS['shadow_sm']}",
                "borderRadius": "8px"
            })
        ], md=6, className="mb-3"),

        # Ficha Aportes Hídricos
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-tint fa-2x mb-2", style={"color": color_aportes}),
                        html.H5("Aportes Hídricos", className="card-title text-center",
                               style={"fontWeight": "600", "color": COLORS['text_primary']}),
                        html.H3(aportes_pct_str, className="text-center mb-1",
                               style={"fontWeight": "bold", "color": color_aportes, "fontSize": "2.5rem"}),
                        html.P(aportes_gwh_str, className="text-center text-muted mb-1",
                              style={"fontSize": "1.1rem", "fontWeight": "500"}),
                        html.Small(f"{contexto} • {fecha_calculo}", 
                                  className="text-muted d-block text-center",
                                  style={"fontSize": "0.8rem"})
                    ], className="text-center")
                ])
            ], className="h-100", style={
                "border": f"1px solid {COLORS['border']}",
                "boxShadow": f"0 2px 4px {COLORS['shadow_sm']}",
                "borderRadius": "8px"
            })
        ], md=6, className="mb-3")
    ], className="mb-4")

layout = html.Div([
    # Sidebar desplegable
    crear_sidebar_universal(),
    
    # Header uniforme
    # Header específico para generación hidráulica
    crear_header(
        titulo_pagina="Generación Hidráulica",
        descripcion_pagina="Monitoreo de recursos hídricos y análisis de generación hidroeléctrica",
        icono_pagina="fas fa-water",
        color_tema=COLORS['energia_hidraulica']
    ),
    # Barra de navegación eliminada
    
    # Container principal
    dbc.Container([
        # Botón de regreso
        crear_boton_regresar(),
        
        dbc.Row([
            # Contenido principal (ahora ocupa todo el ancho)
            dbc.Col([
                # Panel de controles en tabs
                dbc.Tabs([
                    dbc.Tab(label="🌊 Consulta de Caudales", tab_id="tab-consulta"),
                ], id="hidro-tabs", active_tab="tab-consulta", className="mb-4"),
                
                # Contenido dinámico
                html.Div(id="hidrologia-tab-content")
            ], width=12)  # Ahora ocupa todo el ancho
        ])
    ], fluid=True)
], style={'backgroundColor': COLORS['bg_main'], 'minHeight': '100vh'})

# Modal global para tablas de datos
modal_rio_table = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle(id="modal-title-dynamic", children="Detalle de datos hidrológicos"), close_button=True),
    dbc.ModalBody([
        html.Div(id="modal-description", className="mb-3", style={"fontSize": "0.9rem", "color": "#666"}),
        html.Div(id="modal-table-content")
    ]),
], id="modal-rio-table", is_open=False, size="xl", backdrop=True, centered=True, style={"zIndex": 2000})

# Agregar modal al layout final
layout_with_modal = html.Div([layout, modal_rio_table])
layout = layout_with_modal

# Layout del panel de controles (lo que antes estaba en el layout principal)
def crear_panel_controles():
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.I(className="fas fa-sliders-h me-2", style={"color": COLORS['primary']}),
                html.Strong("Panel de Consulta de Caudales", style={"fontSize": "1.1rem", "color": COLORS['text_primary']})
            ], className="mb-3 d-flex align-items-center"),
            
            dbc.Alert([
                html.I(className="fas fa-exclamation-circle me-2"),
                html.Strong("📅 Limitaciones de fechas: "),
                "La API de XM funciona mejor con fechas recientes (últimos 2 años). Fechas muy antiguas pueden generar errores o no tener datos disponibles."
            ], color="info", className="mb-3", style={"fontSize": "0.85rem"}),
            
            dbc.Row([
                dbc.Col([
                    html.Label([
                        html.I(className="fas fa-map-marked-alt me-2"),
                        "Región Hidrológica"
                    ], className="fw-bold mb-2 d-flex align-items-center"),
                    dcc.Dropdown(
                        id="region-dropdown",
                        options=[{"label": "🌍 Todas las regiones", "value": "__ALL_REGIONS__"}],
                        placeholder="Selecciona una región hidrológica...",
                        className="form-control-modern mb-0",
                        style={"fontSize": "0.95rem"}
                    )
                ], lg=3, md=6, sm=12),
                
                dbc.Col([
                    html.Label([
                        html.I(className="fas fa-water me-2"),
                        "Río para Análisis"
                    ], className="fw-bold mb-2 d-flex align-items-center"),
                    dcc.Dropdown(
                        id="rio-dropdown",
                        options=[],  # Se cargarán dinámicamente según la región
                        placeholder="Selecciona un río para consultar...",
                        className="form-control-modern mb-0",
                        style={"fontSize": "0.95rem"}
                    )
                ], lg=3, md=6, sm=12),
                
                dbc.Col([
                    html.Label([
                        html.I(className="fas fa-calendar-alt me-2"),
                        "Fecha de Inicio"
                    ], className="fw-bold mb-2 d-flex align-items-center"),
                    dcc.DatePickerSingle(
                        id="start-date",
                        date=date.today() - timedelta(days=365),  # 1 año - Requisito ingenieros (batching protege de timeouts)
                        display_format="DD/MM/YYYY",
                        className="form-control-modern",
                        style={"width": "100%"}
                    )
                ], lg=2, md=6, sm=12),
                
                dbc.Col([
                    html.Label([
                        html.I(className="fas fa-calendar-check me-2"),
                        "Fecha Final"
                    ], className="fw-bold mb-2 d-flex align-items-center"),
                    dcc.DatePickerSingle(
                        id="end-date",
                        date=date.today(),  # Por defecto: hoy (se actualizará dinámicamente)
                        display_format="DD/MM/YYYY",
                        className="form-control-modern",
                        style={"width": "100%"}
                    ),
                    html.Small([
                        html.I(className="fas fa-info-circle me-1"),
                        "La fecha máxima se ajusta automáticamente según datos disponibles"
                    ], className="text-muted d-block mt-1", style={"fontSize": "0.7rem"})
                ], lg=2, md=6, sm=12),
                
                dbc.Col([
                    html.Label("\u00A0", className="d-block"),
                    dbc.Button([
                        html.I(className="fas fa-chart-line me-2"),
                        "Consultar Caudales"
                    ],
                    id="query-button",
                    color="primary",
                    className="w-100 btn-modern",
                    style={"marginTop": "0.5rem", "background": f"linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%)", "border": "none"}
                    ),
                    # Mensaje informativo sobre tiempo de carga
                    html.Small([
                        html.I(className="fas fa-info-circle me-1"),
                        "La consulta puede tomar unos segundos dependiendo del rango de fechas"
                    ], className="text-muted d-block mt-1", style={"fontSize": "0.75rem"})
                ], lg=2, md=12, sm=12)
            ], className="g-3 align-items-end")
        ], className="p-4")
    ], className="shadow-sm")

# Callback para actualizar dinámicamente el max_date_allowed basado en datos reales
@callback(
    [Output("end-date", "max_date_allowed"),
     Output("end-date", "date")],
    Input("ultima-fecha-con-datos", "data"),
    prevent_initial_call=False
)
def update_max_date_dynamically(ultima_fecha_str):
    """
    Actualiza dinámicamente la fecha máxima permitida basándose en la última fecha
    con datos reales disponibles en la base de datos (desde el store).
    """
    try:
        from datetime import date, timedelta, datetime
        
        if ultima_fecha_str:
            # Usar la fecha del store
            fecha_obj = datetime.strptime(ultima_fecha_str, '%Y-%m-%d').date()
            logger.info(f"✅ [UPDATE_MAX_DATE] Usando fecha del store: {fecha_obj}")
        else:
            # Fallback: buscar directamente
            logger.warning(f"⚠️ [UPDATE_MAX_DATE] Store vacío, buscando fecha...")
            fecha_busqueda = date.today()
            fecha_obj = None
            intentos = 0
            max_intentos = 7
            
            while intentos < max_intentos and fecha_obj is None:
                df_vol_test, fecha_obj = obtener_datos_desde_sqlite('VoluUtilDiarEner', 'Embalse', fecha_busqueda)
                if fecha_obj is None:
                    fecha_busqueda = fecha_busqueda - timedelta(days=1)
                    intentos += 1
            
            if fecha_obj is None:
                fecha_obj = date.today() - timedelta(days=1)
                logger.warning(f"⚠️ [UPDATE_MAX_DATE] No se encontraron datos, usando fallback: {fecha_obj}")
        
        logger.info(f"🔧 [UPDATE_MAX_DATE] Configurando max_date_allowed={fecha_obj}, date={fecha_obj}")
        return fecha_obj, fecha_obj
        
    except Exception as e:
        logger.error(f"❌ [UPDATE_MAX_DATE] Error actualizando fecha máxima: {e}")
        return date.today() - timedelta(days=1), date.today() - timedelta(days=1)

# Callback para manejar tabs
@callback(
    Output("hidrologia-tab-content", "children"),
    Input("hidro-tabs", "active_tab")
)
def render_hidro_tab_content(active_tab):
    if active_tab == "tab-consulta":
        # Mostrar por defecto la gráfica y tablas de embalse junto con las fichas KPI
        # Usar el rango por defecto: 1 año (365 días) - Requisito ingenieros + batching automático
        fecha_final = date.today()
        fecha_inicio = fecha_final - timedelta(days=365)  # 1 año - batching divide en chunks seguros
        fecha_inicio_str = fecha_inicio.strftime('%Y-%m-%d')
        fecha_final_str = fecha_final.strftime('%Y-%m-%d')
        # Importante: show_default_view requiere start_date y end_date
        try:
            # Usar la función auxiliar definida en update_content
            # Debemos replicar la lógica aquí para obtener el contenido por defecto
            def show_default_view(start_date, end_date):
                objetoAPI = get_objetoAPI()
                es_valido, mensaje = validar_rango_fechas(start_date, end_date)
                if not es_valido:
                    return dbc.Alert([
                        html.H6("Fechas no válidas", className="alert-heading"),
                        html.P(mensaje),
                        html.Hr(),
                        html.P("Ajuste el rango de fechas y vuelva a intentar.", className="mb-0")
                    ], color="warning", className="text-start")
                try:
                    # ✅ OPTIMIZADO: Consulta inteligente SQLite (>=2020) vs API (<2020)
                    # La conversión kWh→GWh se hace automáticamente
                    data, warning_msg = obtener_datos_inteligente('AporEner', 'Rio', start_date, end_date)
                    if warning_msg:
                        logger.info(f"⚠️ {warning_msg}")
                    
                    if data is None or data.empty:
                        return dbc.Alert([
                            html.H6("Sin datos", className="alert-heading"),
                            html.P(f"No hay datos disponibles para el período {start_date} a {end_date}."),
                            html.Hr(),
                            html.P("Intente con fechas más recientes.", className="mb-0")
                        ], color="warning", className="text-start")
                    rio_region = ensure_rio_region_loaded()
                    data['Region'] = data['Name'].map(rio_region)
                    if 'Name' in data.columns and 'Value' in data.columns:
                        region_df = data.groupby(['Region', 'Date'])['Value'].sum().reset_index()
                        region_df = region_df[region_df['Region'].notna()]
                        # Aquí deberías llamar a la función que genera la gráfica y la tabla de embalses
                        # Si tienes una función como get_tabla_regiones_embalses, úsala aquí
                        # Por simplicidad, devolvemos un placeholder
                        return html.Div([
                            html.H4("[Gráfica y tablas de embalse aquí]", style={"color": COLORS['primary']})
                        ])
                except Exception as e:
                    return dbc.Alert([
                        html.H6("Error cargando datos", className="alert-heading"),
                        html.P(str(e)),
                    ], color="danger", className="text-start")
            resultados_embalse = show_default_view(fecha_inicio_str, fecha_final_str)
        except Exception as e:
            resultados_embalse = dbc.Alert([
                html.H6("Error cargando datos", className="alert-heading"),
                html.P(str(e)),
            ], color="danger", className="text-start")
        return html.Div([
            crear_panel_controles(),
            dcc.Loading(
                id="loading-hidro",
                type="circle",
                children=html.Div([
                    # Fichas eliminadas - ahora están en la página de Generación
                    html.Div(id="hidro-results-content-dynamic", className="mt-4", children=resultados_embalse)
                ], id="hidro-results-content", className="mt-4"),
                color=COLORS['primary'],
                loading_state={'is_loading': False}
            )
        ])
    elif active_tab == "tab-analisis":
        return html.Div([
            dbc.Card([
                dbc.CardBody([
                    html.H4([
                        html.I(className="fas fa-chart-area me-2", style={"color": COLORS['primary']}),
                        "Análisis Hidrológico Avanzado"
                    ], className="mb-4"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("📊 Análisis de Variabilidad", className="mb-3"),
                                    html.P("Análisis estadístico de variabilidad de caudales por región y temporada.", className="text-muted")
                                ])
                            ], className="h-100")
                        ], md=6),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("⚡ Correlaciones Energéticas", className="mb-3"),
                                    html.P("Relación entre caudales y generación hidroeléctrica en Colombia.", className="text-muted")
                                ])
                            ], className="h-100")
                        ], md=6)
                    ])
                ])
            ], className="shadow-sm")
        ])
    elif active_tab == "tab-tendencias":
        return html.Div([
            dbc.Card([
                dbc.CardBody([
                    html.H4([
                        html.I(className="fas fa-trending-up me-2", style={"color": COLORS['primary']}),
                        "Tendencias Climáticas e Hidrológicas"
                    ], className="mb-4"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("🌡️ Variabilidad Climática", className="mb-3"),
                                    html.P("Análisis de patrones climáticos y su impacto en los recursos hídricos.", className="text-muted")
                                ])
                            ], className="h-100")
                        ], md=6),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("📈 Proyecciones Futuras", className="mb-3"),
                                    html.P("Modelos predictivos para planificación de recursos hídricos.", className="text-muted")
                                ])
                            ], className="h-100")
                        ], md=6)
                    ])
                ])
            ], className="shadow-sm")
        ])
    else:
        return html.Div([
            crear_panel_controles(),
            html.Div(id="hidro-results-content", className="mt-4")
        ])

# Callback para actualizar ríos según región seleccionada
@callback(
    Output("rio-dropdown", "options"),
    [Input("region-dropdown", "value")]
)
def update_rio_options(region):
    # Si se selecciona "Todas las regiones", mostrar todos los ríos disponibles
    if region == "__ALL_REGIONS__":
        rios_region = get_rio_options()  # Obtener todos los ríos sin filtro de región
    else:
        rios_region = get_rio_options(region)
    
    options = [{"label": "Todos los ríos", "value": "__ALL__"}]
    options += [{"label": r, "value": r} for r in rios_region]
    return options


# ===== CALLBACK ELIMINADO - Las fichas KPI ahora están en la página de Generación =====
# El callback update_fichas_kpi ha sido removido ya que las fichas de 
# Reservas Hídricas y Aportes Hídricos ahora se muestran en pages/generacion.py
# ===================================================================================


# Callback principal para consultar y mostrar datos filtrando por río y fechas
@callback(
    Output("hidro-results-content-dynamic", "children"),
    [Input("query-button", "n_clicks")],
    [State("rio-dropdown", "value"),
     State("start-date", "date"),
     State("end-date", "date"),
     State("region-dropdown", "value")]
)
def update_content(n_clicks, rio, start_date, end_date, region):
    # Debug básico del callback
    if n_clicks and n_clicks > 0:
        print(f"� Consultando datos: región={region}, río={rio}, fechas={start_date} a {end_date}")

    # Normalizar el valor de la región para evitar problemas de formato/case
    region_normalized = region.strip().title() if region and region != "__ALL_REGIONS__" else region
    
    # Función para crear mapa de embalses usando datos ya calculados
    def crear_mapa_embalses_directo(regiones_totales, df_completo_embalses):
        """Crea el mapa mostrando CADA EMBALSE como un círculo/bolita individual de color sobre mapa real de Colombia."""
        try:
            import plotly.graph_objects as go
            import random
            from math import sin, cos, radians
            import requests
            
            if regiones_totales is None or regiones_totales.empty:
                return dbc.Alert("No hay datos de regiones disponibles", color="warning")
            
            if df_completo_embalses is None or df_completo_embalses.empty:
                return dbc.Alert("No hay datos de embalses disponibles", color="warning")
            
            logger.info("Creando mapa con bolitas individuales por embalse sobre mapa real de Colombia...")
            logger.debug(f"Total embalses en df_completo_embalses: {len(df_completo_embalses)}")
            
            # Crear figura con mapa base de Colombia
            fig = go.Figure()
            
            # PRIMERO: Cargar GeoJSON local de departamentos de Colombia y mapeo de regiones naturales
            try:
                import json
                import os
                
                logger.info("Cargando mapa de departamentos de Colombia...")
                
                # Rutas a archivos locales
                geojson_path = os.path.join(os.path.dirname(__file__), '..', 'utils', 'departamentos_colombia.geojson')
                regiones_path = os.path.join(os.path.dirname(__file__), '..', 'utils', 'regiones_naturales_colombia.json')
                
                # Cargar GeoJSON de departamentos
                with open(geojson_path, 'r', encoding='utf-8') as f:
                    colombia_geojson = json.load(f)
                
                # Cargar mapeo de regiones naturales
                with open(regiones_path, 'r', encoding='utf-8') as f:
                    regiones_config = json.load(f)
                
                # Crear diccionario inverso: departamento -> región
                DEPARTAMENTOS_A_REGIONES = {}
                for region_key, region_data in regiones_config['regiones'].items():
                    for depto in region_data['departamentos']:
                        DEPARTAMENTOS_A_REGIONES[depto] = {
                            'region': region_data['nombre'],
                            'color': region_data['color'],
                            'border': region_data['border']
                        }
                
                logger.info(f"Cargadas {len(regiones_config['regiones'])} regiones naturales")
                logger.info(f"Mapeados {len(DEPARTAMENTOS_A_REGIONES)} departamentos")
                
                # Agregar el mapa de Colombia como fondo con colores por región natural
                departamentos_dibujados = 0
                for feature in colombia_geojson['features']:
                    # Obtener nombre del departamento y normalizarlo PRIMERO
                    nombre_dpto_original = feature['properties'].get('NOMBRE_DPT', '')
                    nombre_dpto = nombre_dpto_original.upper().strip()
                    
                    # Normalizar nombres especiales
                    if 'BOGOTA' in nombre_dpto or 'D.C' in nombre_dpto or 'D.C.' in nombre_dpto:
                        nombre_dpto = 'CUNDINAMARCA'  # D.C. pertenece a región Andina
                    elif 'SAN ANDRES' in nombre_dpto or 'ARCHIPIELAGO' in nombre_dpto:
                        nombre_dpto = 'SAN ANDRES Y PROVIDENCIA'  # Región Insular
                    elif 'NARIÑO' in nombre_dpto_original or 'NARINO' in nombre_dpto:
                        nombre_dpto = 'NARIÑO'
                    elif 'BOYACÁ' in nombre_dpto_original or 'BOYACA' in nombre_dpto:
                        nombre_dpto = 'BOYACA'
                    elif 'CÓRDOBA' in nombre_dpto_original or 'CORDOBA' in nombre_dpto:
                        nombre_dpto = 'CORDOBA'
                    elif 'BOLÍVAR' in nombre_dpto_original or 'BOLIVAR' in nombre_dpto:
                        nombre_dpto = 'BOLIVAR'
                    elif 'CAQUETÁ' in nombre_dpto_original or 'CAQUETA' in nombre_dpto:
                        nombre_dpto = 'CAQUETA'
                    elif 'VAUPÉS' in nombre_dpto_original or 'VAUPES' in nombre_dpto:
                        nombre_dpto = 'VAUPES'
                    elif 'GUAINÍA' in nombre_dpto_original or 'GUAINIA' in nombre_dpto:
                        nombre_dpto = 'GUAINIA'
                    elif 'QUINDÍO' in nombre_dpto_original or 'QUINDIO' in nombre_dpto:
                        nombre_dpto = 'QUINDIO'
                    
                    # Determinar color según región natural
                    if nombre_dpto in DEPARTAMENTOS_A_REGIONES:
                        info_region = DEPARTAMENTOS_A_REGIONES[nombre_dpto]
                        fillcolor = info_region['color']
                        bordercolor = info_region['border']
                        region_nombre = info_region['region']
                        hovertext = f"<b>{nombre_dpto_original}</b><br>{region_nombre}"
                    else:
                        # Departamentos sin región asignada (mostrar en gris claro)
                        fillcolor = 'rgba(220, 220, 220, 0.2)'
                        bordercolor = '#999999'
                        hovertext = f"<b>{nombre_dpto_original}</b><br>(Sin región asignada)"
                        logger.warning(f"Departamento '{nombre_dpto}' no está en mapeo de regiones")
                    
                    # Manejar tanto Polygon como MultiPolygon (departamentos con múltiples territorios)
                    geometry_type = feature['geometry']['type']
                    
                    if geometry_type == 'Polygon':
                        # Un solo polígono - dibujar directamente
                        coords_list = [feature['geometry']['coordinates'][0]]
                    elif geometry_type == 'MultiPolygon':
                        # Múltiples polígonos - dibujar TODOS
                        coords_list = [poly[0] for poly in feature['geometry']['coordinates']]
                    else:
                        continue
                    
                    # Dibujar cada polígono del departamento
                    for coords in coords_list:
                        lons = [c[0] for c in coords]
                        lats = [c[1] for c in coords]
                        
                        fig.add_trace(go.Scattergeo(
                            lon=lons,
                            lat=lats,
                            mode='lines',
                            line=dict(width=1.5, color=bordercolor),
                            fill='toself',
                            fillcolor=fillcolor,
                            hoverinfo='text',
                            hovertext=hovertext,
                            showlegend=False
                        ))
                    
                    departamentos_dibujados += 1
                
                logger.info(f"Mapa de Colombia cargado: {departamentos_dibujados} departamentos con regiones naturales")
            except FileNotFoundError as e:
                logger.warning(f"No se encontró archivo GeoJSON local: {e}")
                logger.debug("Continuando sin mapa base...")
            except Exception as e:
                logger.warning(f"Error al cargar mapa de Colombia: {e}")
                logger.debug("Continuando sin mapa base...")
            
            # SEGUNDO: Procesar CADA embalse directamente de df_completo_embalses
            leyenda_mostrada = {'ALTO': False, 'MEDIO': False, 'BAJO': False}
            embalses_mapeados = 0
            embalses_por_region = {}
            
            # df_completo_embalses ya tiene: 'Embalse', 'Región', 'Participación (%)', 'Volumen Útil (%)'
            for idx, row in df_completo_embalses.iterrows():
                # Extraer datos del embalse
                nombre_embalse = str(row.get('Embalse', '')).strip()
                region_embalse = str(row.get('Región', '')).strip()
                
                if not nombre_embalse or not region_embalse:
                    continue
                
                # Normalizar nombre de región a mayúsculas para matching
                region_normalizada = region_embalse.upper()
                
                # Verificar que la región existe en nuestras coordenadas
                if region_normalizada not in REGIONES_COORDENADAS:
                    logger.warning(f"Región '{region_embalse}' no está en REGIONES_COORDENADAS")
                    continue
                
                # Contar embalses por región
                if region_normalizada not in embalses_por_region:
                    embalses_por_region[region_normalizada] = 0
                embalses_por_region[region_normalizada] += 1
                
                # Obtener participación y volumen desde el DataFrame
                participacion = float(row.get('Participación (%)', 0))
                volumen_pct = float(row.get('Volumen Útil (%)', 0))
                
                # Calcular riesgo usando la misma función que las tablas
                riesgo, color, icono = calcular_semaforo_embalse(participacion, volumen_pct)
                
                # Obtener coordenadas del centro de la región
                coords_region = REGIONES_COORDENADAS[region_normalizada]
                lat_centro = coords_region['lat']
                lon_centro = coords_region['lon']
                
                # Calcular posición del embalse (distribución aleatoria pero consistente)
                seed_value = hash(nombre_embalse + region_normalizada) % 100000
                random.seed(seed_value)
                
                # Radio de distribución
                radio_lat = 0.5
                radio_lon = 0.6
                
                angulo = random.uniform(0, 360)
                distancia = random.uniform(0.4, 1.0)
                
                offset_lat = distancia * radio_lat * sin(radians(angulo))
                offset_lon = distancia * radio_lon * cos(radians(angulo))
                
                lat_embalse = lat_centro + offset_lat
                lon_embalse = lon_centro + offset_lon
                
                # Crear texto del hover
                hover_text = (
                    f"<b>{nombre_embalse}</b><br>" +
                    f"Región: {coords_region['nombre']}<br>" +
                    f"Participación: {participacion:.2f}%<br>" +
                    f"Volumen Útil: {volumen_pct:.1f}%<br>" +
                    f"<b>Riesgo: {riesgo}</b> {icono}"
                )
                
                # Tamaño del círculo proporcional a participación
                tamaño = max(12, min(10 + participacion * 0.8, 35))
                
                # Controlar leyenda (mostrar solo una vez por cada nivel de riesgo)
                mostrar_leyenda = not leyenda_mostrada[riesgo]
                if mostrar_leyenda:
                    leyenda_mostrada[riesgo] = True
                    nombre_leyenda = f"{icono} Riesgo {riesgo}"
                else:
                    nombre_leyenda = nombre_embalse
                
                # Agregar el punto/círculo al mapa
                fig.add_trace(go.Scattergeo(
                    lon=[lon_embalse],
                    lat=[lat_embalse],
                    mode='markers',
                    marker=dict(
                        size=tamaño,
                        color=color,
                        line=dict(width=2, color='white'),
                        symbol='circle',
                        opacity=0.9
                    ),
                    name=nombre_leyenda,
                    hovertext=hover_text,
                    hoverinfo='text',
                    showlegend=mostrar_leyenda,
                    legendgroup=riesgo
                ))
                
                embalses_mapeados += 1
                logger.debug(f"  ✓ {nombre_embalse} ({region_embalse}): {riesgo} - Vol: {volumen_pct:.1f}%, Part: {participacion:.1f}%")
            
            if embalses_mapeados == 0:
                logger.warning("No se pudieron mapear embalses")
                return dbc.Alert("No se pudieron mapear los embalses", color="warning")
            
            # Configurar el mapa enfocado solo en Colombia
            fig.update_geos(
                projection_type='mercator',
                scope='south america',
                center=dict(lon=-73.5, lat=4.5),
                showcoastlines=True,
                coastlinecolor='#333333',
                coastlinewidth=2,
                showland=True,
                landcolor='#f5f5f5',
                showcountries=True,
                countrycolor='#000000',
                countrywidth=2.5,
                showlakes=True,
                lakecolor='#b3d9ff',
                showrivers=False,
                lonaxis_range=[-79.5, -66.5],
                lataxis_range=[-4.5, 13],
                bgcolor='#ffffff',
                resolution=50
            )
            
            fig.update_layout(
                title={
                    'text': f'🗺️ Mapa de {embalses_mapeados} Embalses - Semáforo de Riesgo Hidrológico',
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': COLORS['text_primary'], 'family': 'Arial Black'}
                },
                height=700,
                margin=dict(l=10, r=10, t=60, b=10),
                paper_bgcolor='white',
                geo=dict(
                    projection_scale=5.5
                ),
                legend=dict(
                    title=dict(text='Nivel de Riesgo', font=dict(size=12, family='Arial Black')),
                    orientation='v',
                    yanchor='top',
                    y=0.98,
                    xanchor='left',
                    x=0.01,
                    bgcolor='rgba(255,255,255,0.95)',
                    bordercolor='#cccccc',
                    borderwidth=2,
                    font=dict(size=11)
                ),
                hoverlabel=dict(
                    bgcolor='white',
                    font_size=12,
                    font_family='Arial',
                    bordercolor='#666666'
                )
            )
            
            logger.info(f"Mapa creado exitosamente: {embalses_mapeados} embalses en {len(embalses_por_region)} regiones")
            logger.debug(f"Distribución por región: {embalses_por_region}")
            return dcc.Graph(figure=fig, config={'displayModeBar': True, 'displaylogo': False})
            
        except Exception as e:
            logger.error(f"Error creando mapa: {e}", exc_info=True)
            import traceback
            traceback.print_exc()
            return dbc.Alert(f"Error al crear el mapa: {str(e)}", color="danger")
    
    # Función auxiliar para mostrar la vista por defecto (panorámica nacional)
    def show_default_view(start_date, end_date):
        objetoAPI = get_objetoAPI()
        # Validar rango de fechas
        es_valido, mensaje = validar_rango_fechas(start_date, end_date)
        if not es_valido:
            return dbc.Alert([
                html.H6("Fechas no válidas", className="alert-heading"),
                html.P(mensaje),
                html.Hr(),
                html.P("Ajuste el rango de fechas y vuelva a intentar.", className="mb-0")
            ], color="warning", className="text-start")
        
        try:
            # ✅ OPTIMIZADO: Consulta inteligente SQLite (>=2020) vs API (<2020)
            # La conversión kWh→GWh se hace automáticamente
            data, warning_msg = obtener_datos_inteligente('AporEner', 'Rio', start_date, end_date)
            if warning_msg:
                logger.info(f"⚠️ {warning_msg}")
            
            if data is None or data.empty:
                return dbc.Alert([
                    html.H6("Sin datos", className="alert-heading"),
                    html.P(f"No hay datos disponibles para el período {start_date} a {end_date}."),
                    html.Hr(),
                    html.P("Intente con fechas más recientes.", className="mb-0")
                ], color="warning", className="text-start")
            # Calcular porcentaje vs histórico para la ficha KPI
            porcentaje_vs_historico = None
            total_real = None
            total_historico = None
            try:
                # CORRECCIÓN: Sumar todos los aportes del período (acumulativo)
                daily_totals_real = data.groupby('Date')['Value'].sum().reset_index()
                total_real = daily_totals_real['Value'].sum()  # SUMA TOTAL, no promedio
                
                # Obtener media histórica y agrupar por fecha
                media_hist_data, _ = obtener_datos_inteligente('AporEnerMediHist', 'Rio', start_date, end_date)
                if media_hist_data is not None and not media_hist_data.empty:
                    # Agrupar media histórica por fecha y sumar
                    daily_totals_hist = media_hist_data.groupby('Date')['Value'].sum().reset_index()
                    total_historico = daily_totals_hist['Value'].sum()  # SUMA TOTAL, no promedio
                    if total_historico > 0:
                        # ✅ FIX CRÍTICO: Convertir a float Python nativo inmediatamente después del cálculo
                        # Esto previene que numpy.float64 cause problemas en f-strings
                        porcentaje_vs_historico = float((total_real / total_historico) * 100)
                        logger.debug(f"Ficha KPI - Comparación: Real total={float(total_real):.2f} GWh vs Histórico={float(total_historico):.2f} GWh ({porcentaje_vs_historico:.1f}%)")
            except Exception as e:
                logger.warning(f"No se pudo calcular porcentaje vs histórico: {e}")
            
            # Agregar información de región
            rio_region = ensure_rio_region_loaded()
            data['Region'] = data['Name'].map(rio_region)
            if 'Name' in data.columns and 'Value' in data.columns:
                # Agrupar por región y fecha para crear series temporales
                region_df = data.groupby(['Region', 'Date'])['Value'].sum().reset_index()
                region_df = region_df[region_df['Region'].notna()]
                
                # 🔍 Buscar la última fecha con datos reales de embalses (no usar end_date ciegamente)
                fecha_embalse_obj = None
                try:
                    # Intentar con la fecha solicitada primero
                    df_vol_test, fecha_encontrada = obtener_datos_desde_sqlite('VoluUtilDiarEner', 'Embalse', 
                                                                                datetime.strptime(end_date, '%Y-%m-%d').date())
                    if fecha_encontrada:
                        fecha_embalse_obj = fecha_encontrada
                        logger.info(f"✅ Fecha real con datos de embalses: {fecha_embalse_obj}")
                    else:
                        # Si no hay datos para end_date, buscar hacia atrás
                        fecha_embalse_obj = datetime.strptime(end_date, '%Y-%m-%d').date() - timedelta(days=1)
                        logger.warning(f"⚠️ No hay datos para {end_date}, usando fecha anterior: {fecha_embalse_obj}")
                except Exception as e:
                    logger.error(f"❌ Error buscando fecha con datos: {e}")
                    fecha_embalse_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                fecha_embalse = fecha_embalse_obj.strftime('%Y-%m-%d') if fecha_embalse_obj else end_date
                regiones_totales, df_completo_embalses = get_tabla_regiones_embalses(fecha_embalse, fecha_embalse)
                return html.Div([
                    html.H5("💧 Estado Promedio de las Hidroeléctricas en el 2025", className="text-center mb-2"),
                    
                    # Ficha KPI destacada con el porcentaje vs histórico
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.Div([
                                        html.H3([
                                            # Ya convertido a float en el cálculo (línea 1833)
                                            porcentaje_vs_historico is not None and f"{porcentaje_vs_historico - 100:+.1f}%" or "Calculando...",
                                        ], className="mb-0", style={"fontSize": "2.5rem", "fontWeight": "bold", 
                                                                    "color": "#28a745" if porcentaje_vs_historico and porcentaje_vs_historico >= 100 
                                                                           else "#dc3545" if porcentaje_vs_historico and porcentaje_vs_historico < 90
                                                                           else "#17a2b8"}),
                                        html.P("vs Histórico", className="text-muted mb-2", style={"fontSize": "0.9rem"}),
                                        html.P([
                                            porcentaje_vs_historico and (
                                                "Condiciones más húmedas que el promedio histórico" if porcentaje_vs_historico >= 100 
                                                else "Condiciones más secas que el promedio histórico" if porcentaje_vs_historico < 90
                                                else "Condiciones cercanas al promedio histórico"
                                            ) or ""
                                        ], className="small mb-1", style={"fontSize": "0.85rem"}),
                                        html.P([
                                            html.I(className="fas fa-calendar-alt me-1", style={"fontSize": "0.7rem"}),
                                            html.Span("Media histórica: 1995-2024", className="text-muted", style={"fontSize": "0.75rem", "fontStyle": "italic"})
                                        ], className="mb-2"),
                                        # Nota técnica con los valores usados en el cálculo
                                        html.Div([
                                            html.Hr(className="my-2", style={"opacity": "0.3"}),
                                            html.P([
                                                html.I(className="fas fa-calculator me-1", style={"fontSize": "0.65rem"}),
                                                html.Span("Valores de cálculo:", className="fw-bold", style={"fontSize": "0.7rem"})
                                            ], className="mb-1"),
                                            html.Div([
                                                html.Small([
                                                    "Aportes reales: ",
                                                    html.Span(f"{float(total_real):,.2f} GWh" if total_real is not None else "N/A", 
                                                             className="fw-bold text-primary")
                                                ], className="d-block", style={"fontSize": "0.7rem"}),
                                                html.Small([
                                                    "Media histórica: ",
                                                    html.Span(f"{float(total_historico):,.2f} GWh" if total_historico is not None else "N/A", 
                                                             className="fw-bold text-info")
                                                ], className="d-block", style={"fontSize": "0.7rem"})
                                            ])
                                        ], className="text-center", style={"backgroundColor": "rgba(0,0,0,0.02)", "borderRadius": "5px", "padding": "8px"})
                                    ], className="text-center")
                                ], className="py-3")
                            ], className="shadow-sm border-0", style={"borderLeft": "4px solid " + (
                                "#28a745" if porcentaje_vs_historico and porcentaje_vs_historico >= 100 
                                else "#dc3545" if porcentaje_vs_historico and porcentaje_vs_historico < 90
                                else "#17a2b8"
                            )})
                        ], md=12, className="mb-3")
                    ]) if porcentaje_vs_historico is not None else html.Div(),
                    
                    # Descripción actualizada y concisa
                    html.H5("🇨🇴 Contribución Energética por Región Hidrológica de Colombia", className="text-center mb-2 mt-3"),
                    html.P("Series temporales de aportes hidroeléctricos por región. Los datos muestran la evolución diaria de la generación hídrica expresada en GWh (gigavatios-hora), comparada con la media histórica. Haga clic en cualquier punto de la gráfica para ver el detalle agregado por región.", 
                          className="text-center text-muted mb-3", style={"fontSize": "0.9rem"}),
                    
                    # Card con la gráfica temporal y guía colapsable
                    dbc.Card([
                        dbc.CardBody([
                            # Botón colapsable para la guía de lectura
                            dbc.Button(
                                [
                                    html.I(className="fas fa-chart-line me-2"),
                                    html.Span("Ver guía de lectura de la gráfica", id="guia-grafica-button-text"),
                                    html.I(className="fas fa-chevron-down ms-2", id="guia-grafica-chevron")
                                ],
                                id="toggle-guia-grafica",
                                color="secondary",
                                outline=True,
                                size="sm",
                                className="mb-3 w-100",
                                style={"fontSize": "0.85rem"}
                            ),
                            
                            # Contenido colapsable de la guía
                            dbc.Collapse(
                                dbc.Alert([
                                    html.Div([
                                        html.Strong("📊 Línea negra: ", className="text-dark"),
                                        html.Span("Aportes reales del período seleccionado", className="small")
                                    ], className="mb-2"),
                                    html.Div([
                                        html.Strong("📈 Línea punteada coloreada: ", className="text-primary"),
                                        html.Span("Media histórica con color dinámico: ", className="small"),
                                        html.Span("🟢 Verde = Húmedo (>100%), ", className="small", style={"color": "#28a745", "fontWeight": "bold"}),
                                        html.Span("🔵 Cyan = Normal (90-100%), ", className="small", style={"color": "#17a2b8", "fontWeight": "bold"}),
                                        html.Span("🟡 Amarillo = Moderadamente seco (70-90%), ", className="small", style={"color": "#ffc107", "fontWeight": "bold"}),
                                        html.Span("🔴 Rojo = Muy seco (<70%)", className="small", style={"color": "#dc3545", "fontWeight": "bold"})
                                    ], className="mb-2"),
                                    html.Hr(className="my-2"),
                                    html.Div([
                                        html.I(className="bi bi-cursor-fill me-2"),
                                        html.Span("Haz clic en cualquier punto para ver detalles por región", className="small text-muted fst-italic")
                                    ])
                                ], color="light", className="mb-3", style={"padding": "0.75rem"}),
                                id="collapse-guia-grafica",
                                is_open=False
                            ),
                            
                            # Gráfica temporal
                            create_total_timeline_chart(data, "Aportes totales nacionales")
                        ])
                    ], className="mb-3"),
                    dcc.Store(id="region-data-store", data=data.to_dict('records')),
                    dcc.Store(id="embalses-completo-data", data=df_completo_embalses.to_dict('records')),
                    html.Hr(),
                    html.H5("⚡ Capacidad Útil Diaria de Energía por Región Hidrológica", className="text-center mt-4 mb-2"),
                    
                    # Nota informativa sobre la fecha de los datos
                    dbc.Alert([
                        html.I(className="fas fa-calendar-alt me-2"),
                        html.Strong(f"Fecha de los datos de embalses: "),
                        html.Span(f"{fecha_embalse}", id="fecha-datos-embalses", style={"fontWeight": "bold"}),
                        html.Br(),
                        html.Small("Los datos mostrados corresponden a la última fecha disponible con información completa de todos los embalses.", className="text-muted")
                    ], color="info", className="text-center mb-3", style={"fontSize": "0.9rem"}),
                    
                    html.P("📋 Interfaz jerárquica expandible: Haga clic en cualquier región para desplegar sus embalses. Cada región muestra dos tablas lado a lado con participación porcentual y capacidad detallada en GWh. Los datos están ordenados de mayor a menor valor. Los símbolos ⊞ indican regiones contraídas y ⊟ regiones expandidas.", className="text-center text-muted mb-3", style={"fontSize": "0.9rem"}),
                    
                    # Botón para expandir/colapsar Sistema de Semáforo
                    dbc.Row([
                        dbc.Col([
                            dbc.Button(
                                [
                                    html.I(className="fas fa-traffic-light me-2"),
                                    html.Span("Ver información detallada del Sistema Semáforo de Riesgo Hidrológico", id="semaforo-button-text"),
                                    html.I(className="fas fa-chevron-down ms-2", id="semaforo-chevron")
                                ],
                                id="toggle-semaforo-info",
                                color="info",
                                outline=True,
                                className="mb-3 w-100",
                                style={"fontSize": "0.95rem", "fontWeight": "500"}
                            )
                        ], md=12)
                    ]),
                    
                    # Contenido colapsable del Sistema de Semáforo
                    dbc.Collapse(
                        dbc.Row([
                            dbc.Col([
                                dbc.Alert([
                                    html.H6([
                                        html.I(className="fas fa-traffic-light me-2"),
                                        "🚦 Sistema Inteligente de Semáforo de Riesgo Hidrológico"
                                    ], className="alert-heading mb-3"),
                                    html.P("Este sistema analiza automáticamente cada embalse combinando dos factores críticos para determinar su nivel de riesgo operativo:", className="mb-3", style={"fontSize": "0.95rem"}),
                                    
                                    # Explicación de los factores
                                    dbc.Row([
                                        dbc.Col([
                                            html.Div([
                                                html.H6("📊 Factor 1: Importancia Estratégica", className="text-primary mb-2"),
                                                html.P("Participación del embalse en el sistema energético nacional. Los embalses con mayor participación (>10%) son considerados estratégicos para la estabilidad del sistema.", 
                                                      className="mb-2", style={"fontSize": "0.85rem"})
                                            ])
                                        ], md=6),
                                        dbc.Col([
                                            html.Div([
                                                html.H6("💧 Factor 2: Disponibilidad Hídrica", className="text-info mb-2"),
                                                html.P("Porcentaje de volumen útil disponible. Indica cuánta agua tiene el embalse por encima de su nivel mínimo técnico para generar energía.", 
                                                      className="mb-2", style={"fontSize": "0.85rem"})
                                            ])
                                        ], md=6)
                                    ], className="mb-3"),
                                    
                                    html.Hr(),
                                    html.H6("🎯 Lógica de Clasificación de Riesgo:", className="mb-2"),
                                    dbc.Row([
                                        dbc.Col([
                                            html.Div([
                                                html.Span("🔴 RIESGO ALTO", className="fw-bold", style={"color": "#dc3545", "fontSize": "1rem"}),
                                                html.Br(),
                                                html.Small("Embalses estratégicos (participación ≥10%) con volumen crítico (<30%)", 
                                                         className="text-muted", style={"fontSize": "0.8rem"}),
                                                html.Br(),
                                                html.Small("⚠️ Requiere atención inmediata - Riesgo de desabastecimiento", 
                                                         className="text-danger", style={"fontSize": "0.75rem", "fontWeight": "bold"})
                                            ], className="p-2 border-start border-danger border-3")
                                        ], md=4),
                                        dbc.Col([
                                            html.Div([
                                                html.Span("🟡 RIESGO MEDIO", className="fw-bold", style={"color": "#ffc107", "fontSize": "1rem"}),
                                                html.Br(),
                                                html.Small("Embalses estratégicos con volumen bajo (30-70%) o embalses pequeños con volumen crítico", 
                                                         className="text-muted", style={"fontSize": "0.8rem"}),
                                                html.Br(),
                                                html.Small("⚡ Monitoreo continuo - Situación de precaución", 
                                                         className="text-warning", style={"fontSize": "0.75rem", "fontWeight": "bold"})
                                            ], className="p-2 border-start border-warning border-3")
                                        ], md=4),
                                        dbc.Col([
                                            html.Div([
                                                html.Span("🟢 RIESGO BAJO", className="fw-bold", style={"color": "#198754", "fontSize": "1rem"}),
                                                html.Br(),
                                                html.Small("Embalses con volumen adecuado (≥70%) independientemente de su tamaño", 
                                                         className="text-muted", style={"fontSize": "0.8rem"}),
                                                html.Br(),
                                                html.Small("✅ Situación estable - Operación normal", 
                                                         className="text-success", style={"fontSize": "0.75rem", "fontWeight": "bold"})
                                            ], className="p-2 border-start border-success border-3")
                                        ], md=4)
                                    ], className="mb-3"),
                                    
                                    html.Hr(),
                                    html.Div([
                                        html.Strong("💡 Nota Técnica: ", className="text-primary"),
                                        html.Span("El sistema prioriza la seguridad energética nacional. Un embalse pequeño con bajo volumen puede ser menos crítico que un embalse estratégico en la misma condición.", 
                                                 style={"fontSize": "0.85rem"})
                                    ], className="bg-light p-2 rounded")
                                ], color="info", className="mb-3")
                            ], md=12)
                        ]),
                        id="collapse-semaforo-info",
                        is_open=False
                    ),
                    
                    # ========== MAPA DE EMBALSES POR REGIÓN ==========
                    dbc.Row([
                        dbc.Col([
                            html.H5([
                                html.I(className="fas fa-map-marked-alt me-2", style={'color': COLORS['primary']}),
                                "Mapa de Embalses por Región Hidrológica"
                            ], className="mb-3"),
                            dcc.Loading(
                                id="loading-mapa-embalses",
                                type="circle",
                                children=crear_mapa_embalses_directo(regiones_totales, df_completo_embalses)
                            )
                        ], width=12)
                    ], className="mb-4"),
                    # ================================================
                    
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader([
                                    html.I(className="bi bi-pie-chart me-2", style={"color": "#667eea"}),
                                    html.Strong("📊 Participación Porcentual por Región")
                                ], style={"background": "linear-gradient(135deg, #e3f2fd 0%, #f3f4f6 100%)",
                                         "border": "none", "borderRadius": "8px 8px 0 0"}),
                                dbc.CardBody([
                                    html.P("Distribución porcentual de la capacidad energética entre regiones y sus embalses. Haga clic en los botones [+]/[-] para expandir/contraer cada región.", 
                                          className="text-muted mb-3", style={"fontSize": "0.85rem"}),
                                    html.Div([
                                        # Botones superpuestos para cada región
                                        html.Div(id="participacion-toggle-buttons", style={
                                            'position': 'absolute', 
                                            'zIndex': 10, 
                                            'pointerEvents': 'none'
                                        }),
                                        # Tabla principal
                                        html.Div(id="tabla-participacion-jerarquica-container", children=[
                                            html.Div("Cargando datos...", className="text-center text-muted")
                                        ])
                                    ], style={'position': 'relative'})
                                ], className="p-3")
                            ], className="card-modern h-100")
                        ], md=6),
                        
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader([
                                    html.I(className="bi bi-battery-full me-2", style={"color": "#28a745"}),
                                    html.Strong("💧 Volumen Útil por Región")
                                ], style={"background": "linear-gradient(135deg, #e8f5e8 0%, #f3f4f6 100%)",
                                         "border": "none", "borderRadius": "8px 8px 0 0"}),
                                dbc.CardBody([
                                    html.P("Valores específicos de porcentaje de volumen útil disponible por región y embalses. El 'Volumen Útil (%)' indica el porcentaje del volumen almacenado por encima del Nivel Mínimo Técnico, representando la disponibilidad energética real de cada embalse. Haga clic en los botones [+]/[-] para expandir/contraer cada región.", 
                                          className="text-muted mb-3", style={"fontSize": "0.85rem"}),
                                    html.Div([
                                        # Botones superpuestos para cada región
                                        html.Div(id="capacidad-toggle-buttons", style={
                                            'position': 'absolute', 
                                            'zIndex': 10, 
                                            'pointerEvents': 'none'
                                        }),
                                        # Tabla principal
                                        html.Div(id="tabla-capacidad-jerarquica-container", children=[
                                            html.Div("Cargando datos...", className="text-center text-muted")
                                        ])
                                    ], style={'position': 'relative'})
                                ], className="p-3")
                            ], className="card-modern h-100")
                        ], md=6)
                    ], className="g-3"),
                    
                    # Stores para manejar los datos jerárquicos y estados de expansión
                    dcc.Store(id="participacion-jerarquica-data", data=[]),
                    dcc.Store(id="capacidad-jerarquica-data", data=[]),
                    dcc.Store(id="regiones-expandidas", data=[]),
                    dcc.Store(id="ultima-fecha-con-datos", data=None)  # Store para la última fecha con datos
                ])
            else:
                return dbc.Alert("No se pueden procesar los datos obtenidos.", color="warning")
        except Exception as e:
            error_message = manejar_error_api(e, "consulta de vista general")
            return dbc.Alert([
                html.H6("Error en vista general", className="alert-heading"),
                html.Pre(error_message, style={"white-space": "pre-wrap", "font-family": "inherit"}),
                html.Hr(),
                html.P("Intente con un rango de fechas más reciente.", className="mb-0")
            ], color="danger", className="text-start")
    
    # Verificar si los filtros están vacíos o en valores por defecto
    filtros_vacios = (
        (region is None or region == "__ALL_REGIONS__") and 
        (rio is None or rio == "__ALL__")
    )
    
    # Si no se ha hecho clic, o faltan fechas, o todos los filtros están vacíos pero hay fechas
    if not n_clicks or not start_date or not end_date:
        # Mostrar datos por defecto de todas las regiones al cargar la página
        if start_date and end_date and not n_clicks:
            return show_default_view(start_date, end_date)
        else:
            return dbc.Alert("Selecciona una región, fechas y/o río, luego haz clic en Consultar.", color="info", className="text-center")
    
    # Si se hizo clic pero todos los filtros están vacíos, mostrar vista por defecto
    if filtros_vacios:
        return show_default_view(start_date, end_date)
    
    objetoAPI = get_objetoAPI()
    # Validar fechas antes de proceder
    es_valido, mensaje = validar_rango_fechas(start_date, end_date)
    if not es_valido:
        return dbc.Alert([
            html.H6("Fechas no válidas", className="alert-heading"),
            html.P(mensaje),
            html.Hr(),
            html.P("Corrija las fechas y vuelva a intentar.", className="mb-0")
        ], color="warning", className="text-start")

    try:
        # ✅ OPTIMIZADO: Consulta inteligente SQLite (>=2020) vs API (<2020)
        # La conversión a GWh se hace automáticamente
        data, warning_msg = obtener_datos_inteligente('AporEner', 'Rio', start_date, end_date)
        if warning_msg:
            logger.info(f"⚠️ {warning_msg}")
        
        # LOGGING: Verificar que datos ya vienen en GWh
        if data is not None and not data.empty:
            logger.info(f"🔍 AporEner recibido: {len(data)} registros, Total: {data['Value'].sum():.2f} GWh")
        
        if data is None or data.empty:
            return dbc.Alert([
                html.H6("Sin datos disponibles", className="alert-heading"),
                html.P(f"No hay datos para el período {start_date} a {end_date} con los filtros seleccionados."),
                html.Hr(),
                html.P("Intente con fechas más recientes o diferentes filtros.", className="mb-0")
            ], color="warning", className="text-start")

        # Si hay un río específico seleccionado (y no es 'Todos los ríos'), mostrar la serie temporal diaria de ese río
        if rio and rio != "__ALL__":
            data_rio = data[data['Name'] == rio]
            if data_rio.empty:
                return dbc.Alert("No se encontraron datos para el río seleccionado.", color="warning")
            plot_df = data_rio.copy()
            if 'Date' in plot_df.columns and 'Value' in plot_df.columns:
                plot_df = plot_df[['Date', 'Value']].rename(columns={'Date': 'Fecha', 'Value': 'GWh'})
            return html.Div([
                html.H5(f"⚡ Río {rio} - Serie Temporal Completa de Aportes de Energía", className="text-center mb-2"),
                html.P(f"Análisis detallado del río {rio} incluyendo gráfico de tendencias temporales y tabla de datos diarios. Los valores están expresados en gigavatios-hora (GWh) y representan el aporte energético del río.", className="text-center text-muted mb-3", style={"fontSize": "0.9rem"}),
                
                # Gráfico arriba (ancho completo para mejor visualización)
                dbc.Row([
                    dbc.Col([
                        html.H6("📈 Evolución Temporal", className="text-center mb-2"),
                        create_line_chart(plot_df, rio_name=rio, start_date=start_date, end_date=end_date)
                    ], md=12)
                ], className="mb-4"),
                
                # Tabla debajo (ancho completo)
                dbc.Row([
                    dbc.Col([
                        html.H6("📊 Datos Detallados", className="text-center mb-2"),
                        create_data_table(plot_df)
                    ], md=12)
                ])
            ])

        # Si no hay río seleccionado o es 'Todos los ríos', mostrar barra de contribución total por río
        # Si hay región seleccionada, filtrar por región, si no, mostrar todas las regiones
        rio_region = ensure_rio_region_loaded()
        data['Region'] = data['Name'].map(rio_region)
        
        # LOGGING: Ver datos ANTES de filtrar por región
        logger.info(f"🔍 ANTES filtro - Total data: {len(data)} registros, Suma: {data['Value'].sum():.2f} GWh")
        
        if region and region != "__ALL_REGIONS__":
            logger.info(f"🔍 [FILTRO REGIÓN] Filtrando región '{region_normalized}'")
            logger.info(f"🔍 Regiones únicas en data: {sorted(data['Region'].dropna().unique().tolist())}")
            data_filtered = data[data['Region'] == region_normalized]
            logger.info(f"🔍 DESPUÉS filtro - data_filtered: {len(data_filtered)} registros, Suma: {data_filtered['Value'].sum():.2f} GWh")
            title_suffix = f"en la región {region_normalized}"
            # Obtener datos frescos de embalses con la nueva columna
            embalses_df_fresh = get_embalses_capacidad(region_normalized, start_date, end_date)
            logger.debug(f"[DEBUG FILTRO] Embalses encontrados para región: {len(embalses_df_fresh) if not embalses_df_fresh.empty else 0}")
            
            # Guardar datos SIN formatear - las tablas harán el formateo
            embalses_df_formatted = embalses_df_fresh.copy() if not embalses_df_fresh.empty else pd.DataFrame()
                
            # Obtener embalses de la región específica
            try:
                objetoAPI = get_objetoAPI()
                # Usar fecha actual para obtener listado más reciente
                today = datetime.now().strftime('%Y-%m-%d')
                yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                embalses_info, warning = obtener_datos_inteligente('ListadoEmbalses','Sistema', yesterday, today)
                embalses_info['Values_Name'] = embalses_info['Values_Name'].str.strip().str.upper()
                embalses_info['Values_HydroRegion'] = embalses_info['Values_HydroRegion'].str.strip().str.title()
                embalses_region = embalses_info[embalses_info['Values_HydroRegion'] == region_normalized]['Values_Name'].sort_values().unique()
            except Exception as e:
                logger.error(f"Error obteniendo embalses para el filtro: {e}", exc_info=True)
                embalses_region = []
        else:
            # Si no hay región específica o es "Todas las regiones", mostrar vista nacional
            if region == "__ALL_REGIONS__":
                # Mostrar la vista panorámica nacional igual que al cargar la página
                region_df = data.groupby(['Region', 'Date'])['Value'].sum().reset_index()
                region_df = region_df[region_df['Region'].notna()]  # Filtrar regiones válidas
                
                return html.Div([
                    html.H5("🇨🇴 Contribución Energética por Región Hidrológica de Colombia", className="text-center mb-2"),
                    html.P("Vista panorámica nacional: Series temporales comparativas de aportes de caudal por región hidrológica. Haga clic en cualquier punto para ver el detalle agregado diario de la región. Los datos incluyen todos los ríos monitoreados en el período seleccionado, agrupados por región para análisis comparativo nacional.", className="text-center text-muted mb-3", style={"fontSize": "0.9rem"}),
                    
                    dbc.Row([
                        dbc.Col([
                            create_total_timeline_chart(data, "Aportes totales nacionales")
                        ], md=12)
                    ]),
                    dcc.Store(id="region-data-store", data=data.to_dict('records')),
                    html.Hr(),
                ])
            
            data_filtered = data
            title_suffix = "- Todas las regiones"
            # Obtener datos frescos de embalses con la nueva columna  
            embalses_df_fresh = get_embalses_capacidad(None, start_date, end_date)
            # Guardar datos SIN formatear - las tablas harán el formateo
            embalses_df_formatted = embalses_df_fresh.copy() if not embalses_df_fresh.empty else pd.DataFrame()
                
            embalses_region = embalses_df_fresh['Embalse'].unique() if not embalses_df_fresh.empty else []

        if data_filtered.empty:
            return dbc.Alert("No se encontraron datos para la región seleccionada." if region else "No se encontraron datos.", color="warning")
        
        # Asegurar que embalses_df_formatted esté definido - SIN formatear
        if 'embalses_df_formatted' not in locals():
            embalses_df_formatted = embalses_df_fresh.copy() if not embalses_df_fresh.empty else pd.DataFrame()
            
        if 'Name' in data_filtered.columns and 'Value' in data_filtered.columns:
            # Para región específica, crear gráfica temporal de esa región
            if region and region != "__ALL_REGIONS__":
                # Para región específica, pasar datos SIN agregar para que create_total_timeline_chart
                # pueda hacer el filtrado correcto de la media histórica
                region_temporal_data = data_filtered[['Date', 'Name', 'Value']].copy()
                
                return html.Div([
                    html.H5(f"🏞️ Evolución Temporal de Aportes de Caudal - Región {region_normalized}", className="text-center mb-2"),
                    html.P(f"Serie temporal de aportes de caudal para la región {region_normalized}. La gráfica muestra la evolución diaria de los aportes de caudal de todos los ríos de esta región durante el período seleccionado.", className="text-center text-muted mb-3", style={"fontSize": "0.9rem"}),
                    
                    dbc.Row([
                        dbc.Col([
                            create_total_timeline_chart(region_temporal_data, f"Aportes región {region_normalized}", region_filter=region_normalized)
                        ], md=12)
                    ]),
                    dcc.Store(id="region-data-store", data=data_filtered.to_dict('records')),
                    html.Hr(),
                    html.H5(f"⚡ Sistema de Análisis Hidrológico por Embalse {title_suffix}", className="text-center mt-4 mb-2"),
                    html.P(f"Análisis detallado con sistema de semáforo de riesgo para monitoreo energético. Los indicadores combinan participación porcentual y volumen útil disponible para identificar situaciones críticas.", className="text-center text-muted mb-3", style={"fontSize": "0.9rem"}),
                    
                    # Botón para expandir/colapsar Sistema de Semáforo (región específica)
                    dbc.Row([
                        dbc.Col([
                            dbc.Button(
                                [
                                    html.I(className="fas fa-traffic-light me-2"),
                                    html.Span("Ver información detallada del Sistema Semáforo de Riesgo Hidrológico", id="semaforo-region-button-text"),
                                    html.I(className="fas fa-chevron-down ms-2", id="semaforo-region-chevron")
                                ],
                                id="toggle-semaforo-region-info",
                                color="info",
                                outline=True,
                                className="mb-3 w-100",
                                style={"fontSize": "0.95rem", "fontWeight": "500"}
                            )
                        ], md=12)
                    ]),
                    
                    # Contenido colapsable del Sistema de Semáforo (región específica)
                    dbc.Collapse(
                        dbc.Row([
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardHeader([
                                        html.I(className="fas fa-traffic-light me-2", style={"color": "#28a745"}),
                                        html.Strong("🚦 Sistema Inteligente de Semáforo de Riesgo Hidrológico")
                                    ], style={"background": "linear-gradient(135deg, #e8f5e8 0%, #f3f4f6 100%)",
                                             "border": "none", "borderRadius": "8px 8px 0 0"}),
                                    dbc.CardBody([
                                        html.P("Este sistema evalúa automáticamente el riesgo operativo de cada embalse mediante un análisis inteligente que combina:", 
                                              className="mb-3", style={"fontSize": "0.9rem"}),
                                        
                                        dbc.Row([
                                            dbc.Col([
                                                html.Div([
                                                    html.H6("� Importancia Estratégica", className="text-primary mb-2"),
                                                    html.P("¿Qué tan crítico es este embalse para el sistema energético nacional?", 
                                                          className="text-muted", style={"fontSize": "0.85rem"}),
                                                    html.Ul([
                                                        html.Li("Embalses grandes (≥10% participación): Estratégicos", style={"fontSize": "0.8rem"}),
                                                        html.Li("Embalses pequeños (<10% participación): Locales", style={"fontSize": "0.8rem"})
                                                    ])
                                                ])
                                            ], md=6),
                                            dbc.Col([
                                                html.Div([
                                                    html.H6("� Estado del Recurso Hídrico", className="text-info mb-2"),
                                                    html.P("¿Cuánta agua útil tiene disponible para generar energía?", 
                                                          className="text-muted", style={"fontSize": "0.85rem"}),
                                                    html.Ul([
                                                        html.Li("Crítico: <30% del volumen útil", style={"fontSize": "0.8rem"}),
                                                        html.Li("Precaución: 30-70% del volumen útil", style={"fontSize": "0.8rem"}),
                                                        html.Li("Óptimo: ≥70% del volumen útil", style={"fontSize": "0.8rem"})
                                                    ])
                                                ])
                                            ], md=6)
                                        ], className="mb-3"),
                                        
                                        html.Hr(),
                                        html.H6("🎯 Resultados del Análisis:", className="mb-2"),
                                        dbc.Row([
                                            dbc.Col([
                                                html.Div([
                                                    html.Span("�", style={"fontSize": "1.5rem"}),
                                                    html.Strong(" ALTO RIESGO", className="ms-2", style={"color": "#dc3545"}),
                                                    html.Br(),
                                                    html.Small("Embalse estratégico + Agua crítica", className="text-danger fw-bold")
                                                ], className="text-center p-2 border border-danger rounded")
                                            ], md=4),
                                            dbc.Col([
                                                html.Div([
                                                    html.Span("🟡", style={"fontSize": "1.5rem"}),
                                                    html.Strong(" RIESGO MEDIO", className="ms-2", style={"color": "#ffc107"}),
                                                    html.Br(),
                                                    html.Small("Situaciones intermedias", className="text-warning fw-bold")
                                                ], className="text-center p-2 border border-warning rounded")
                                            ], md=4),
                                            dbc.Col([
                                                html.Div([
                                                    html.Span("🟢", style={"fontSize": "1.5rem"}),
                                                    html.Strong(" BAJO RIESGO", className="ms-2", style={"color": "#198754"}),
                                                    html.Br(),
                                                    html.Small("Agua suficiente disponible", className="text-success fw-bold")
                                                ], className="text-center p-2 border border-success rounded")
                                            ], md=4)
                                        ])
                                    ], className="p-3")
                                ], className="card-modern mb-4")
                            ], md=12)
                        ]),
                        id="collapse-semaforo-region-info",
                        is_open=False
                    ),
                    
                    # Tablas jerárquicas con semáforo - filtradas por región
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader([
                                    html.I(className="bi bi-pie-chart me-2", style={"color": "#667eea"}),
                                    html.Strong(f"📊 Participación Porcentual por Embalse {title_suffix}")
                                ], style={"background": "linear-gradient(135deg, #e3f2fd 0%, #f3f4f6 100%)",
                                         "border": "none", "borderRadius": "8px 8px 0 0"}),
                                dbc.CardBody([
                                    html.P(f"Distribución porcentual de la capacidad energética entre embalses de {region}. Los indicadores de semáforo muestran el nivel de riesgo de cada embalse basado en su importancia y volumen disponible.", 
                                          className="text-muted mb-3", style={"fontSize": "0.85rem"}),
                                    html.Div([
                                        # Contenedor para la tabla con semáforo de región específica
                                        html.Div(id="tabla-participacion-region-filtrada", children=[
                                            create_region_filtered_participacion_table(region, start_date, end_date)
                                        ])
                                    ])
                                ], className="p-3")
                            ], className="card-modern h-100")
                        ], md=6),
                        
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader([
                                    html.I(className="bi bi-battery-full me-2", style={"color": "#28a745"}),
                                    html.Strong(f"💧 Volumen Útil por Embalse {title_suffix}")
                                ], style={"background": "linear-gradient(135deg, #e8f5e8 0%, #f3f4f6 100%)",
                                         "border": "none", "borderRadius": "8px 8px 0 0"}),
                                dbc.CardBody([
                                    html.P(f"Valores específicos de porcentaje de volumen útil disponible por embalse en {region}. El 'Volumen Útil (%)' indica el porcentaje del volumen almacenado por encima del Nivel Mínimo Técnico, representando la disponibilidad energética real de cada embalse.", 
                                          className="text-muted mb-3", style={"fontSize": "0.85rem"}),
                                    html.Div([
                                        # Contenedor para la tabla con semáforo de región específica
                                        html.Div(id="tabla-capacidad-region-filtrada", children=[
                                            create_region_filtered_capacidad_table(region, start_date, end_date)
                                        ])
                                    ])
                                ], className="p-3")
                            ], className="card-modern h-100")
                        ], md=6)
                    ]),
                    dcc.Store(id="embalse-cap-data", data=embalses_df_formatted.to_dict('records')),
                    dcc.Store(id="participacion-data", data=get_participacion_embalses(embalses_df_fresh).to_dict('records'))
                ])
            else:
                # Para caso sin región específica o vista general, mostrar también gráfica temporal
                national_temporal_data = data_filtered.groupby('Date')['Value'].sum().reset_index()
                national_temporal_data['Region'] = 'Nacional'
                
                return html.Div([
                    html.H5(f"🇨🇴 Evolución Temporal de Aportes de Caudal Nacionales", className="text-center mb-2"),
                    html.P(f"Serie temporal agregada de aportes de caudal a nivel nacional. La gráfica muestra la evolución diaria de los aportes de caudal de todas las regiones de Colombia durante el período seleccionado.", className="text-center text-muted mb-3", style={"fontSize": "0.9rem"}),
                    
                    dbc.Row([
                        dbc.Col([
                            create_total_timeline_chart(national_temporal_data, "Aportes nacionales")
                        ], md=12)
                    ]),
                    dcc.Store(id="region-data-store", data=data_filtered.to_dict('records')),
                    html.Hr(),
                    html.H5(f"⚡ Análisis de Embalses - Volumen Útil por Embalse", className="text-center mt-4 mb-2"),
                    html.P(f"Análisis detallado del estado de los embalses nacionales. Los datos muestran la participación porcentual basada en capacidad energética y el porcentaje de volumen útil disponible por embalse.", className="text-center text-muted mb-3", style={"fontSize": "0.9rem"}),
                    dbc.Row([
                        dbc.Col([
                            html.H6("📊 Participación Porcentual por Embalse", className="text-center mb-2"),
                            html.P("Distribución porcentual de la capacidad energética entre embalses. La tabla incluye una fila TOTAL que suma exactamente 100%.", className="text-muted mb-2", style={"fontSize": "0.8rem"}),
                            dash_table.DataTable(
                                id="tabla-participacion-embalse",
                                data=get_participacion_embalses(embalses_df_fresh).to_dict('records'),
                                columns=[
                                    {"name": "Embalse", "id": "Embalse"},
                                    {"name": "Participación (%)", "id": "Participación (%)"},
                                    {"name": "🚨 Riesgo", "id": "Riesgo"}
                                ],
                                style_cell={'textAlign': 'left', 'padding': '6px', 'fontFamily': 'Arial', 'fontSize': 14},
                                style_header={'backgroundColor': '#e3e3e3', 'fontWeight': 'bold'},
                                style_data={'backgroundColor': '#f8f8f8'},
                                style_data_conditional=crear_estilos_condicionales_para_tabla_estatica(start_date, end_date),
                                page_action="none"
                            ),
                        ], md=4),
                        dbc.Col([
                            html.H6("💧 Volumen Útil por Embalse", className="text-center mb-2"),
                            html.P("Porcentajes de volumen útil disponible por embalse. Use el filtro para buscar embalses específicos.", className="text-muted mb-2", style={"fontSize": "0.8rem"}),
                            dcc.Dropdown(
                                id="embalse-cap-dropdown",
                                options=[{"label": e.title(), "value": e} for e in embalses_region],
                                placeholder="🔍 Buscar embalse específico...",
                                className="mb-2"
                            ),
                            dash_table.DataTable(
                                id="tabla-capacidad-embalse-2",
                                data=get_embalses_data_for_table(None, start_date, end_date),
                                columns=[
                                    {"name": "Embalse", "id": "Embalse"},
                                    {"name": "Volumen Útil (%)", "id": "Volumen Útil (%)"},
                                    {"name": "🚨 Riesgo", "id": "Riesgo"}
                                ],
                                style_cell={"textAlign": "left", "padding": "6px", "fontFamily": "Arial", "fontSize": 14},
                                style_header={"backgroundColor": "#e3e3e3", "fontWeight": "bold"},
                                style_data={"backgroundColor": "#f8f8f8"},
                                style_data_conditional=crear_estilos_condicionales_para_tabla_estatica(start_date, end_date),
                                page_action="none"
                            ),
                        ], md=8)
                    ]),
                    dcc.Store(id="embalse-cap-data", data=embalses_df_formatted.to_dict('records')),
                    dcc.Store(id="participacion-data", data=get_participacion_embalses(embalses_df_fresh).to_dict('records'))
                ])
        else:
            return dbc.Alert("No se pueden graficar los datos de la región." if region else "No se pueden graficar los datos.", color="warning")
    except Exception as e:
        # ✅ FIX: Log completo del error con traceback
        import traceback
        logger.error(f"❌ ERROR EN UPDATE_CONTENT: {str(e)}")
        logger.error(f"❌ TRACEBACK COMPLETO:\n{traceback.format_exc()}")
        error_message = manejar_error_api(e, "consulta de datos hidrológicos")
        return dbc.Alert([
            html.H6("Error en consulta", className="alert-heading"),
            html.Pre(error_message, style={"white-space": "pre-wrap", "font-family": "inherit"}),
            html.Hr(),
            html.P("Revise los parámetros de consulta e intente nuevamente.", className="mb-0")
        ], color="danger", className="text-start")

# Callback para inicializar las tablas jerárquicas al cargar la página
@callback(
    [Output("participacion-jerarquica-data", "data"),
     Output("capacidad-jerarquica-data", "data"),
     Output("ultima-fecha-con-datos", "data")],
    [Input("start-date", "date"), Input("end-date", "date")],
    prevent_initial_call=False
)
def initialize_hierarchical_tables(start_date, end_date):
    """Inicializar las tablas jerárquicas con datos de regiones al cargar la página"""
    try:
        objetoAPI = get_objetoAPI()
        logger.debug(f"DEBUG INIT: Inicializando tablas jerárquicas con fechas {start_date} - {end_date}")
        
        # 🔍 Buscar la última fecha con datos disponibles (no asumir que hoy tiene datos)
        from datetime import date, timedelta
        fecha_busqueda = date.today()
        fecha_obj = None
        intentos = 0
        max_intentos = 7  # Buscar hasta 7 días atrás
        
        while intentos < max_intentos and fecha_obj is None:
            df_vol_test, fecha_obj = obtener_datos_desde_sqlite('VoluUtilDiarEner', 'Embalse', fecha_busqueda)
            if fecha_obj is None:
                logger.debug(f"🔍 No hay datos para {fecha_busqueda}, intentando día anterior...")
                fecha_busqueda = fecha_busqueda - timedelta(days=1)
                intentos += 1
        
        if fecha_obj is None:
            logger.error(f"❌ DEBUG INIT: No se encontraron fechas con datos en los últimos {max_intentos} días")
            return [], []
        
        fecha_con_datos = fecha_obj.strftime('%Y-%m-%d')
        logger.info(f"✅ DEBUG INIT: Última fecha con datos disponibles: {fecha_con_datos}")
        
        regiones_totales, df_completo_embalses = get_tabla_regiones_embalses(None, fecha_con_datos)
        logger.debug(f"DEBUG INIT: Regiones obtenidas: {len(regiones_totales) if not regiones_totales.empty else 0}")
        
        if regiones_totales.empty:
            logger.warning("DEBUG INIT: No hay regiones, retornando listas vacías")
            return [], []
        
        # Crear datos para tabla de participación (solo regiones inicialmente)
        participacion_data = []
        capacidad_data = []
        
        logger.debug(f"DEBUG INIT: Procesando {len(regiones_totales)} regiones")
        
        for _, row in regiones_totales.iterrows():
            # ✅ CORREGIDO: Usar directamente la columna 'Participación (%)' calculada en get_tabla_regiones_embalses
            participacion_pct = row.get('Participación (%)', 0)
            participacion_data.append({
                'nombre': f"▶️ {row['Región']}",
                'participacion': f"{participacion_pct:.2f}%",
                'tipo': 'region',
                'region_name': row['Región'],
                'expandida': False,
                'id': f"region_{row['Región']}"
            })
            # Volumen útil (%) para la tabla de capacidad
            volumen_util_valor = row.get('Volumen Útil (%)', 0)
            capacidad_data.append({
                'nombre': f"▶️ {row['Región']}",
                'capacidad': f"{volumen_util_valor:.1f}%",
                'tipo': 'region',
                'region_name': row['Región'],
                'expandida': False,
                'id': f"region_{row['Región']}"
            })
        
        # Agregar fila TOTAL al final
        participacion_data.append({
            'nombre': 'TOTAL SISTEMA',
            'participacion': '100.0%',
            'tipo': 'total',
            'region_name': '',
            'expandida': False,
            'id': 'total'
        })
        
        # ✅ CORREGIDO: Calcular volumen útil nacional directamente desde regiones_totales
        # Esto garantiza consistencia total con los datos mostrados en las regiones
        total_volumen_gwh = regiones_totales['Volumen Util (GWh)'].sum()
        total_capacidad_gwh = regiones_totales['Total (GWh)'].sum()
        
        if total_capacidad_gwh > 0:
            promedio_volumen_general = round((total_volumen_gwh / total_capacidad_gwh) * 100, 1)
        else:
            promedio_volumen_general = 0.0
        
        logger.debug(f"Volumen útil nacional: Vol={total_volumen_gwh:.2f} GWh, Cap={total_capacidad_gwh:.2f} GWh, %={promedio_volumen_general:.1f}%")
        
        capacidad_data.append({
            'nombre': 'TOTAL SISTEMA',
            'capacidad': f"{promedio_volumen_general:.1f}%",
            'tipo': 'total',
            'region_name': '',
            'expandida': False,
            'id': 'total'
        })
        
        # Datos completos para los stores (incluye embalses)
        participacion_completa = participacion_data.copy()
        capacidad_completa = capacidad_data.copy()
        
        # Agregar datos de embalses a los stores completos COMBINANDO ambos valores
        for region_name in regiones_totales['Región'].unique():
            embalses_region = get_embalses_by_region(region_name, df_completo_embalses)
            
            if not embalses_region.empty:
                logger.info(f"🔍 [INIT_TABLES] Procesando región: {region_name}, {len(embalses_region)} embalses")
                for _, embalse_row in embalses_region.iterrows():
                    embalse_name = embalse_row['Región'].replace('    └─ ', '')
                    volumen_embalse = embalse_row.get('Volumen Útil (%)', 0)
                    participacion_embalse = embalse_row.get('Participación (%)', 0)
                    
                    # 🔍 LOG CRÍTICO: Valores RAW antes de formatear
                    logger.info(f"🔍 [RAW] {embalse_name}: Volumen={volumen_embalse} (tipo={type(volumen_embalse).__name__}), Participación={participacion_embalse} (tipo={type(participacion_embalse).__name__})")
                    
                    # 🔍 Convertir a float para evitar corrupción
                    try:
                        participacion_float = float(embalse_row['Participación (%)'])
                        volumen_float = float(volumen_embalse) if volumen_embalse is not None else 0.0
                    except (ValueError, TypeError) as e:
                        logger.error(f"❌ Error convirtiendo valores a float para {embalse_name}: {e}")
                        participacion_float = 0.0
                        volumen_float = 0.0
                    
                    # 🔍 LOG CRÍTICO: Valores después de conversión a float
                    logger.info(f"🔍 [FLOAT] {embalse_name}: Volumen={volumen_float:.2f}%, Participación={participacion_float:.2f}%")
                    
                    # 🔍 Formatear CONSISTENTEMENTE
                    participacion_formatted = f"{participacion_float:.2f}%"
                    volumen_formatted = f"{volumen_float:.1f}%"
                    
                    # 🔍 LOG CRÍTICO: Valores formateados
                    logger.info(f"🔍 [FORMATTED] {embalse_name}: Volumen={volumen_formatted}, Participación={participacion_formatted}")
                    
                    # ESTRUCTURA UNIFICADA: Agregar AMBOS valores a la misma entrada
                    # Para participación_completa
                    participacion_completa.append({
                        'nombre': f"    └─ {embalse_name}",
                        'participacion': participacion_formatted,
                        'capacidad': volumen_formatted,
                        'participacion_valor': participacion_float,
                        'volumen_valor': volumen_float,
                        'tipo': 'embalse',
                        'region_name': region_name,
                        'expandida': False,
                        'id': f"embalse_{region_name}_{embalse_name}"
                    })
                    
                    # Para capacidad_completa - MISMOS VALORES pero estructura diferente
                    capacidad_completa.append({
                        'nombre': f"    └─ {embalse_name}",
                        'capacidad': volumen_formatted,
                        'participacion': participacion_formatted,
                        'participacion_valor': participacion_float,
                        'volumen_valor': volumen_float,
                        'tipo': 'embalse',
                        'region_name': region_name,
                        'expandida': False,
                        'id': f"embalse_{region_name}_{embalse_name}"
                    })
                    
                    # 🔍 LOG CRÍTICO: Verificar que ambos stores tienen EXACTAMENTE los mismos valores
                    logger.info(f"🔍 [STORE_VERIFICATION] {embalse_name} - PARTICIPACION_STORE: vol={participacion_completa[-1]['capacidad']}, part={participacion_completa[-1]['participacion']}")
                    logger.info(f"🔍 [STORE_VERIFICATION] {embalse_name} - CAPACIDAD_STORE: vol={capacidad_completa[-1]['capacidad']}, part={capacidad_completa[-1]['participacion']}")
        
        # Retornar: datos completos para stores + última fecha con datos
        return participacion_completa, capacidad_completa, fecha_con_datos
        
    except Exception as e:
        logger.error(f"Error inicializando tablas jerárquicas: {e}", exc_info=True)
        return [], [], None

def build_hierarchical_table_view(data_complete, expanded_regions, view_type="participacion"):
    """Construir vista de tabla jerárquica con botones integrados y sistema de semáforo CORREGIDO"""
    if not data_complete:
        return dash_table.DataTable(
            data=[],
            columns=[
                {"name": "Región / Embalse", "id": "nombre"},
                {"name": "Participación (%)" if view_type == "participacion" else "Volumen Útil (%)", "id": "valor"}
            ]
        )
    
    table_data = []
    processed_regions = set()
    style_data_conditional = []
    
    # Obtener todas las regiones únicas
    all_regions = set()
    for item in data_complete:
        if item.get('tipo') == 'region':
            region_name = item.get('region_name')
            if region_name:
                all_regions.add(region_name)
    
    # Crear lista de regiones con sus valores para ordenar de mayor a menor
    region_items = []
    for item in data_complete:
        if item.get('tipo') == 'region':
            region_name = item.get('region_name')
            if region_name and region_name not in processed_regions:
                # Obtener el valor para ordenar
                valor_str = item.get('participacion', item.get('capacidad', '0'))
                try:
                    # Extraer valor numérico del string (ej: "25.5%" -> 25.5)
                    if isinstance(valor_str, str):
                        valor_num = float(valor_str.replace('%', '').replace(',', '').strip())
                    else:
                        valor_num = float(valor_str) if valor_str else 0
                except (ValueError, AttributeError, TypeError) as e:
                    logger.debug(f"No se pudo convertir valor a numérico: {valor_str} - {e}")
                    valor_num = 0
                
                region_items.append({
                    'item': item,
                    'region_name': region_name,
                    'valor_num': valor_num
                })
                processed_regions.add(region_name)
    
    # Ordenar regiones por valor de mayor a menor
    region_items.sort(key=lambda x: x['valor_num'], reverse=True)
    
    # Procesar cada región en orden descendente
    for region_data in region_items:
        region_item = region_data['item']
        region_name = region_data['region_name']
        
        is_expanded = region_name in expanded_regions
        
        # Fila de región con botón integrado en el nombre
        button_icon = "⊟" if is_expanded else "⊞"  # Símbolos más elegantes
        table_data.append({
            "nombre": f"{button_icon} {region_name}",
            "valor": region_item.get('participacion', region_item.get('capacidad', ''))
        })
        
        # Si está expandida, agregar embalses ordenados de mayor a menor
        if is_expanded:
            # SOLUCIÓN DIRECTA: Crear diccionario unificado directamente desde data_complete
            embalses_unificados = {}
            
            for item in data_complete:
                if (item.get('tipo') == 'embalse' and 
                    item.get('region_name') == region_name):
                    embalse_name = item.get('nombre', '').replace('    └─ ', '').strip()
                    
                    if embalse_name not in embalses_unificados:
                        # CREAR ENTRADA COMPLETA con todos los datos necesarios
                        embalses_unificados[embalse_name] = {
                            'nombre': embalse_name,
                            'participacion_valor': item.get('participacion_valor', 0),
                            'volumen_valor': item.get('volumen_valor', 0),
                            'valor_display': item.get('participacion' if view_type == "participacion" else 'capacidad', ''),
                            'valor_num': 0
                        }
                        
                        # Calcular valor numérico para ordenar
                        valor_str = embalses_unificados[embalse_name]['valor_display']
                        try:
                            if isinstance(valor_str, str):
                                embalses_unificados[embalse_name]['valor_num'] = float(valor_str.replace('%', '').replace(',', '').strip())
                            else:
                                embalses_unificados[embalse_name]['valor_num'] = float(valor_str) if valor_str else 0
                        except (ValueError, AttributeError, TypeError) as e:
                            logger.debug(f"No se pudo convertir valor a numérico: {valor_str} - {e}")
                            embalses_unificados[embalse_name]['valor_num'] = 0
            
            # Convertir a lista y ordenar
            embalses_lista = list(embalses_unificados.values())
            embalses_lista.sort(key=lambda x: x.get('valor_num', 0), reverse=True)
            
            # 🔍 LOG: Verificar datos antes de construir tabla
            logger.info(f"🔍 [BUILD_TABLE] Región={region_name}, View={view_type}, Embalses={len(embalses_lista)}")
            
            # Procesar cada embalse con datos ya unificados
            for embalse_data in embalses_lista:
                embalse_name = embalse_data['nombre']
                valor_embalse = embalse_data['valor_display']
                participacion_val = embalse_data.get('participacion_valor', 0)
                volumen_val = embalse_data.get('volumen_valor', 0)
                
                # 🔍 LOG CRÍTICO: Valores que se mostrarán en la tabla
                logger.info(f"🔍 [TABLE_DISPLAY] {embalse_name} ({view_type}): Display={valor_embalse}, Part={participacion_val}%, Vol={volumen_val}%")
                
# REMOVED DEBUG:                 logger.info(f"SEMÁFORO CORREGIDO: {embalse_name} - Participación={participacion_val}%, Volumen={volumen_val}%")
                
                # Clasificar riesgo con ambos valores CORRECTOS
                nivel_riesgo = clasificar_riesgo_embalse(participacion_val, volumen_val)
# REMOVED DEBUG:                 logger.info(f"RESULTADO SEMÁFORO: {embalse_name} - Riesgo: {nivel_riesgo}")
                
                # Agregar fila del embalse
                row_index = len(table_data)
                table_data.append({
                    "nombre": f"    └─ {embalse_name}",
                    "valor": valor_embalse
                })
                
                # Agregar estilo condicional para el semáforo solo en tabla de participación
                if view_type == "participacion":
                    estilo = obtener_estilo_riesgo(nivel_riesgo)
                    style_data_conditional.append({
                        'if': {'row_index': row_index},
                        **estilo
                    })
    
    # Agregar fila TOTAL
    total_item = None
    for item in data_complete:
        if item.get('tipo') == 'total':
            total_item = item
            break
    
    if total_item:
        table_data.append({
            "nombre": "TOTAL SISTEMA",
            "valor": total_item.get('participacion', total_item.get('capacidad', ''))
        })
    
    # Crear tabla con estructura de 2 columnas
    return dash_table.DataTable(
        id=f"tabla-{view_type}-jerarquica-display",
        data=table_data,
        columns=[
            {"name": "Región / Embalse", "id": "nombre"},
            {"name": "Participación (%)" if view_type == "participacion" else "Volumen Útil (%)", "id": "valor"}
        ],
        style_cell={
            'textAlign': 'left',
            'padding': '8px',
            'fontFamily': 'Inter, Arial, sans-serif',
            'fontSize': 13,
            'backgroundColor': '#f8f9fa',
            'border': '1px solid #dee2e6'
        },
        style_header={
            'backgroundColor': '#667eea' if view_type == 'participacion' else '#28a745',
            'color': 'white',
            'fontWeight': 'bold',
            'fontSize': 14,
            'textAlign': 'center',
            'border': f'1px solid {"#5a6cf0" if view_type == "participacion" else "#218838"}'
        },
        style_data_conditional=style_data_conditional + [
            {
                'if': {'filter_query': '{nombre} contains "⊞" || {nombre} contains "⊟"'},
                'backgroundColor': '#e3f2fd' if view_type == 'participacion' else '#e8f5e8',
                'fontWeight': 'bold',
                'cursor': 'pointer',
                'border': f'2px solid {"#2196f3" if view_type == "participacion" else "#28a745"}'
            },
            {
                'if': {'filter_query': '{nombre} = "TOTAL SISTEMA"'},
                'backgroundColor': '#007bff',
                'color': 'white',
                'fontWeight': 'bold'
            }
        ],
        page_action="none"
    )

# Callback para manejar clics en las regiones y expandir/colapsar embalses
@callback(
    [Output("tabla-participacion-jerarquica-container", "children"),
     Output("tabla-capacidad-jerarquica-container", "children"),
     Output("regiones-expandidas", "data")],
    [Input("tabla-participacion-jerarquica-display", "active_cell"),
     Input("tabla-capacidad-jerarquica-display", "active_cell")],
    [State("participacion-jerarquica-data", "data"),
     State("capacidad-jerarquica-data", "data"),
     State("regiones-expandidas", "data")],
    prevent_initial_call=True
)
def toggle_region_from_table(active_cell_part, active_cell_cap, participacion_complete, capacidad_complete, regiones_expandidas):
    """Manejar clics en los nombres de región con botones integrados"""
    try:
        if not participacion_complete or not capacidad_complete:
            return dash.no_update, dash.no_update, regiones_expandidas or []
        
        if regiones_expandidas is None:
            regiones_expandidas = []
        
        # Obtener el clic activo
        active_cell = active_cell_part or active_cell_cap
        if not active_cell:
            return dash.no_update, dash.no_update, regiones_expandidas
        
        # Solo responder a clics en la columna "nombre"
        if active_cell.get('column_id') != 'nombre':
            return dash.no_update, dash.no_update, regiones_expandidas
        
        # Obtener el nombre de la celda clicada directamente de la tabla correcta
        # Determinar qué tabla fue clicada y usar esa para obtener los datos
        if active_cell_part:
            # Clic en tabla de participación
            current_table = build_hierarchical_table_view(participacion_complete, regiones_expandidas, "participacion")
            table_source = "participacion"
        else:
            # Clic en tabla de capacidad
            current_table = build_hierarchical_table_view(capacidad_complete, regiones_expandidas, "capacidad")
            table_source = "capacidad"
        
        # Obtener los datos de la tabla actual
        table_data = current_table.data if hasattr(current_table, 'data') else []
        
        # Verificar qué fila se clicó
        row_id = active_cell['row']
        if row_id < len(table_data):
            clicked_row = table_data[row_id]
            clicked_name = clicked_row.get('nombre', '')
            
            # Determinar el tipo de fila basándose en el formato del nombre
            is_region = (clicked_name.startswith('⊞ ') or clicked_name.startswith('⊟ ')) and not clicked_name.startswith('    └─ ')
            
            # Solo procesar si es una región
            if is_region:
                # Extraer el nombre de la región del texto (remover símbolos ⊞/⊟)
                region_name = clicked_name.replace('⊞ ', '').replace('⊟ ', '').strip()
                
                # Toggle la región
                if region_name in regiones_expandidas:
                    regiones_expandidas.remove(region_name)
                else:
                    regiones_expandidas.append(region_name)
        
        # Reconstruir las vistas con sistema de semáforo
        participacion_view = build_hierarchical_table_view(participacion_complete, regiones_expandidas, "participacion")
        capacidad_view = build_hierarchical_table_view(capacidad_complete, regiones_expandidas, "capacidad")
        
        return participacion_view, capacidad_view, regiones_expandidas
        
    except Exception as e:
# REMOVED DEBUG:         print(f"❌ Error en toggle_region_from_table: {e}")
        import traceback
        traceback.print_exc()
        return dash.no_update, dash.no_update, regiones_expandidas or []

# Callback para inicializar las vistas HTML desde los stores
@callback(
    [Output("tabla-participacion-jerarquica-container", "children", allow_duplicate=True),
     Output("tabla-capacidad-jerarquica-container", "children", allow_duplicate=True)],
    [Input("participacion-jerarquica-data", "data"),
     Input("capacidad-jerarquica-data", "data")],
    [State("regiones-expandidas", "data")],
    prevent_initial_call='initial_duplicate'
)
def update_html_tables_from_stores(participacion_complete, capacidad_complete, regiones_expandidas):
    """Actualizar las vistas HTML basándose en los stores"""
    try:
        logger.debug(f"DEBUG STORES: Actualizando tablas HTML")
        logger.debug(f"DEBUG STORES: participacion_complete: {len(participacion_complete) if participacion_complete else 0} items")
        logger.debug(f"DEBUG STORES: capacidad_complete: {len(capacidad_complete) if capacidad_complete else 0} items")
        logger.debug(f"DEBUG STORES: regiones_expandidas: {regiones_expandidas}")
        
        if not participacion_complete or not capacidad_complete:
            logger.warning("DEBUG STORES: Datos incompletos, retornando mensajes de error")
            return (
                html.Div("No hay datos de participación disponibles", className="text-center text-muted p-3"),
                html.Div("No hay datos de capacidad disponibles", className="text-center text-muted p-3")
            )
        
        if not regiones_expandidas:
            regiones_expandidas = []
        
        # Construir vistas de tabla iniciales (todas las regiones colapsadas)
        logger.debug(f"DEBUG STORES: Construyendo vista de participación")
        participacion_view = build_hierarchical_table_view(participacion_complete, regiones_expandidas, "participacion")
        logger.debug(f"DEBUG STORES: Construyendo vista de capacidad")
        capacidad_view = build_hierarchical_table_view(capacidad_complete, regiones_expandidas, "capacidad")
        
# REMOVED DEBUG:         logger.info(f"DEBUG STORES: Vistas construidas exitosamente")
        return participacion_view, capacidad_view
        
    except Exception as e:
# REMOVED DEBUG:         print(f"❌ Error en update_html_tables_from_stores: {e}")
        import traceback
        traceback.print_exc()
        return (
            html.Div("Error al cargar datos de participación", className="text-center text-danger p-3"),
            html.Div("Error al cargar datos de capacidad", className="text-center text-danger p-3")
        )
        
    except Exception as e:
        logger.error(f"Error en update_tables_from_stores: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        return [], []

# Clientside callback para toggle del Sistema Semáforo (más confiable para contenido dinámico)
import dash
from dash import clientside_callback, ClientsideFunction

# JavaScript para manejar el toggle
dash.clientside_callback(
    """
    function(n_clicks, is_open) {
        if (!n_clicks) {
            return window.dash_clientside.no_update;
        }
        const new_state = !is_open;
        const button_text = new_state ? "Ocultar información del Sistema Semáforo" : "Ver información detallada del Sistema Semáforo de Riesgo Hidrológico";
        const chevron_class = new_state ? "fas fa-chevron-up ms-2" : "fas fa-chevron-down ms-2";
        return [new_state, button_text, chevron_class];
    }
    """,
    [Output("collapse-semaforo-info", "is_open"),
     Output("semaforo-button-text", "children"),
     Output("semaforo-chevron", "className")],
    [Input("toggle-semaforo-info", "n_clicks")],
    [State("collapse-semaforo-info", "is_open")]
)

# Clientside callback para la vista de región
dash.clientside_callback(
    """
    function(n_clicks, is_open) {
        if (!n_clicks) {
            return window.dash_clientside.no_update;
        }
        const new_state = !is_open;
        const button_text = new_state ? "Ocultar información del Sistema Semáforo" : "Ver información detallada del Sistema Semáforo de Riesgo Hidrológico";
        const chevron_class = new_state ? "fas fa-chevron-up ms-2" : "fas fa-chevron-down ms-2";
        return [new_state, button_text, chevron_class];
    }
    """,
    [Output("collapse-semaforo-region-info", "is_open"),
     Output("semaforo-region-button-text", "children"),
     Output("semaforo-region-chevron", "className")],
    [Input("toggle-semaforo-region-info", "n_clicks")],
    [State("collapse-semaforo-region-info", "is_open")]
)

# Clientside callback para la guía de lectura de la gráfica
dash.clientside_callback(
    """
    function(n_clicks, is_open) {
        if (!n_clicks) {
            return window.dash_clientside.no_update;
        }
        const new_state = !is_open;
        const button_text = new_state ? "Ocultar guía de lectura" : "Ver guía de lectura de la gráfica";
        const chevron_class = new_state ? "fas fa-chevron-up ms-2" : "fas fa-chevron-down ms-2";
        return [new_state, button_text, chevron_class];
    }
    """,
    [Output("collapse-guia-grafica", "is_open"),
     Output("guia-grafica-button-text", "children"),
     Output("guia-grafica-chevron", "className")],
    [Input("toggle-guia-grafica", "n_clicks")],
    [State("collapse-guia-grafica", "is_open")]
)

# Callback adicional para cargar datos por defecto al iniciar la página
# TEMPORALMENTE DESHABILITADO PARA EVITAR CONFLICTOS
# @callback(
#     Output("hidro-results-content", "children", allow_duplicate=True),
#     [Input("start-date", "date"), Input("end-date", "date")],
#     prevent_initial_call='initial_duplicate'
# )
# def load_default_data(start_date, end_date):
#     """Cargar datos por defecto al inicializar la página"""
#     # FUNCIÓN TEMPORALMENTE DESHABILITADA PARA EVITAR CONFLICTOS DE CALLBACK
#     pass

# --- Función para calcular participación porcentual de embalses ---
def get_participacion_embalses(df_embalses):
    """
    Calcula la participación porcentual de cada embalse respecto al total e incluye columna de riesgo.
    """
    if df_embalses.empty or 'Capacidad_GWh_Internal' not in df_embalses.columns:
        return pd.DataFrame(columns=['Embalse', 'Participación (%)', 'Riesgo'])
    
    df_participacion = df_embalses.copy()
    total = df_participacion['Capacidad_GWh_Internal'].sum()
    
    if total > 0:
        # Calcular porcentajes sin redondear primero
        porcentajes = (df_participacion['Capacidad_GWh_Internal'] / total * 100)
        
        # Ajustar el último valor para que la suma sea exactamente 100%
        porcentajes_redondeados = porcentajes.round(2)
        diferencia = 100 - porcentajes_redondeados.sum()
        
        # Si hay diferencia por redondeo, ajustar el valor más grande
        if abs(diferencia) > 0.001:
            idx_max = porcentajes_redondeados.idxmax()
            porcentajes_redondeados.loc[idx_max] += diferencia
            
        df_participacion['Participación (%)'] = porcentajes_redondeados.round(2)
    else:
        df_participacion['Participación (%)'] = 0
    
    # 🆕 Agregar columna de riesgo usando las funciones existentes
    df_con_riesgo = agregar_columna_riesgo_a_tabla(df_participacion)
    
    # Ordenar de mayor a menor por participación
    df_con_riesgo = df_con_riesgo.sort_values('Participación (%)', ascending=False)
    
    # Solo devolver las columnas necesarias (SIN capacidad, CON riesgo)
    df_final = df_con_riesgo[['Embalse', 'Participación (%)', 'Riesgo']].reset_index(drop=True)
    
    # Agregar fila TOTAL
    total_row = pd.DataFrame({
        'Embalse': ['TOTAL'],
        'Participación (%)': [100.0],
        'Riesgo': ['⚡']  # 🆕 Ícono especial para TOTAL
    })
    
    df_final = pd.concat([df_final, total_row], ignore_index=True)
    
    return df_final

# --- Función para clasificar riesgo según participación y volumen útil ---
def clasificar_riesgo_embalse(participacion, volumen_util):
    """
    Clasifica el riesgo de un embalse basado en participación y volumen útil
    
    Args:
        participacion (float): Participación porcentual en el sistema (0-100)
        volumen_util (float): Volumen útil disponible (0-100)
    
    Returns:
        str: 'high', 'medium', 'low'
    """
    # MATRIZ DE RIESGO CORREGIDA: Combinar participación Y volumen
    
    # Caso 1: Embalses muy importantes (participación >= 15%)
    if participacion >= 15:
        if volumen_util < 30:
            return 'high'  # Embalse importante con poco volumen = ALTO RIESGO
        elif volumen_util < 70:
            return 'medium'  # Embalse importante con volumen moderado = RIESGO MEDIO
        else:
            return 'low'  # Embalse importante con buen volumen = BAJO RIESGO
    
    # Caso 2: Embalses importantes (participación >= 10%)
    elif participacion >= 10:
        if volumen_util < 20:
            return 'high'  # Embalse importante con muy poco volumen = ALTO RIESGO
        elif volumen_util < 60:
            return 'medium'  # Embalse importante con volumen bajo-moderado = RIESGO MEDIO
        else:
            return 'low'  # Embalse importante con buen volumen = BAJO RIESGO
    
    # Caso 3: Embalses moderadamente importantes (participación >= 5%)
    elif participacion >= 5:
        if volumen_util < 15:
            return 'high'  # Embalse moderado con muy poco volumen = ALTO RIESGO
        elif volumen_util < 50:
            return 'medium'  # Embalse moderado con volumen bajo = RIESGO MEDIO
        else:
            return 'low'  # Embalse moderado con volumen adecuado = BAJO RIESGO
    
    # Caso 4: Embalses menos importantes (participación < 5%)
    else:
        if volumen_util < 25:
            return 'medium'  # Embalse pequeño con poco volumen = RIESGO MEDIO
        else:
            return 'low'  # Embalse pequeño con volumen adecuado = BAJO RIESGO

def obtener_estilo_riesgo(nivel_riesgo):
    """
    Obtiene el estilo CSS para el nivel de riesgo
    
    Args:
        nivel_riesgo (str): 'high', 'medium', 'low'
    
    Returns:
        dict: Estilo CSS para DataTable
    """
    estilos = {
        'high': {
            'backgroundColor': '#fee2e2',  # Rojo claro
            'color': '#991b1b',           # Rojo oscuro
            'fontWeight': 'bold'
        },
        'medium': {
            'backgroundColor': '#fef3c7',  # Amarillo claro
            'color': '#92400e',           # Amarillo oscuro
            'fontWeight': 'bold'
        },
        'low': {
            'backgroundColor': '#d1fae5',  # Verde claro
            'color': '#065f46'            # Verde oscuro
        }
    }
    return estilos.get(nivel_riesgo, estilos['low'])

def obtener_pictograma_riesgo(nivel_riesgo):
    """
    Obtiene el pictograma para el nivel de riesgo
    
    Args:
        nivel_riesgo (str): 'high', 'medium', 'low'
    
    Returns:
        str: Emoji o símbolo para el nivel de riesgo
    """
    pictogramas = {
        'high': '🔴',     # Círculo rojo
        'medium': '🟡',   # Círculo amarillo  
        'low': '🟢'       # Círculo verde
    }
    return pictogramas.get(nivel_riesgo, '🟢')

def agregar_columna_riesgo_a_tabla(df_embalses):
    """
    Agrega la columna de riesgo con pictogramas a una tabla de embalses
    
    Args:
        df_embalses (DataFrame): DataFrame con datos de embalses que debe incluir:
                                - 'Embalse': nombre del embalse
                                - 'Capacidad_GWh_Internal': para calcular participación
                                - 'Volumen Útil (%)': para evaluar riesgo
    
    Returns:
        DataFrame: DataFrame con columna 'Riesgo' agregada
    """
    if df_embalses.empty:
        return df_embalses
    
    # Crear una copia para no modificar el original
    df_con_riesgo = df_embalses.copy()
    
    # Calcular participación si no existe
    if 'Participación (%)' not in df_con_riesgo.columns and 'Capacidad_GWh_Internal' in df_con_riesgo.columns:
        # Filtrar filas que no sean TOTAL para calcular participación
        df_no_total = df_con_riesgo[df_con_riesgo['Embalse'] != 'TOTAL'].copy()
        if not df_no_total.empty:
            total_capacidad = df_no_total['Capacidad_GWh_Internal'].sum()
            if total_capacidad > 0:
                df_con_riesgo.loc[df_no_total.index, 'Participación (%)'] = (
                    df_no_total['Capacidad_GWh_Internal'] / total_capacidad * 100
                ).round(2)
            else:
                df_con_riesgo.loc[df_no_total.index, 'Participación (%)'] = 0
    
    # Inicializar columna de riesgo
    df_con_riesgo['Riesgo'] = ''
    
    # Calcular riesgo para cada embalse (excepto TOTAL)
    for idx, row in df_con_riesgo.iterrows():
        if row['Embalse'] != 'TOTAL':
            participacion = row.get('Participación (%)', 0)
            
            # Extraer valor numérico del volumen útil (puede estar como "45.2%", 45.2, o None)
            volumen_util = row.get('Volumen Útil (%)', 0)
            
            # Manejar diferentes tipos de datos
            if volumen_util is None or (isinstance(volumen_util, str) and volumen_util == 'N/D'):
                volumen_util = 0
            elif isinstance(volumen_util, str):
                # Si es string como "45.2%", extraer el número
                try:
                    volumen_util = float(volumen_util.replace('%', '').replace(',', '.').strip())
                except (ValueError, AttributeError):
                    volumen_util = 0
            elif pd.isna(volumen_util):
                volumen_util = 0
            else:
                # Ya es un número, asegurarse de que sea float
                volumen_util = float(volumen_util)
            
            # Clasificar riesgo
            nivel_riesgo = clasificar_riesgo_embalse(participacion, volumen_util)
            pictograma = obtener_pictograma_riesgo(nivel_riesgo)
            
            df_con_riesgo.at[idx, 'Riesgo'] = pictograma
        else:
            # Para la fila TOTAL, usar un ícono especial
            df_con_riesgo.at[idx, 'Riesgo'] = '⚡'
    
    return df_con_riesgo

def generar_estilos_condicionales_riesgo(df_con_riesgo):
    """
    Genera los estilos condicionales para colorear las filas según el nivel de riesgo
    
    Args:
        df_con_riesgo (DataFrame): DataFrame que incluye columnas de riesgo
    
    Returns:
        list: Lista de estilos condicionales para DataTable
    """
    estilos_condicionales = []
    
    # Recorrer cada fila para crear estilos específicos por embalse
    for idx, row in df_con_riesgo.iterrows():
        embalse = row['Embalse']
        
        if embalse != 'TOTAL':
            participacion = row.get('Participación (%)', 0)
            
            # Extraer valor numérico del volumen útil
            volumen_util = row.get('Volumen Útil (%)', 0)
            
            # Manejar diferentes tipos de datos
            if volumen_util is None or (isinstance(volumen_util, str) and volumen_util == 'N/D'):
                volumen_util = 0
            elif isinstance(volumen_util, str):
                try:
                    volumen_util = float(volumen_util.replace('%', '').replace(',', '.').strip())
                except (ValueError, AttributeError):
                    volumen_util = 0
            elif pd.isna(volumen_util):
                volumen_util = 0
            else:
                volumen_util = float(volumen_util)
            
            # Clasificar riesgo
            nivel_riesgo = clasificar_riesgo_embalse(participacion, volumen_util)
            estilo_riesgo = obtener_estilo_riesgo(nivel_riesgo)
            
            # Crear estilo condicional para este embalse específico
            estilo_embalse = {
                'if': {'filter_query': f'{{Embalse}} = "{embalse}"'},
                'backgroundColor': estilo_riesgo['backgroundColor'],
                'color': estilo_riesgo['color'],
                'fontWeight': estilo_riesgo.get('fontWeight', 'normal')
            }
            estilos_condicionales.append(estilo_embalse)
    
    # Estilo para la fila TOTAL
    estilo_total = {
        'if': {'filter_query': '{Embalse} = "TOTAL"'},
        'backgroundColor': '#007bff',
        'color': 'white',
        'fontWeight': 'bold'
    }
    estilos_condicionales.append(estilo_total)
    
    return estilos_condicionales

# --- Función para crear tabla con participación porcentual y semáforo ---
def get_tabla_con_participacion(df_embalses):
    """
    Crea una tabla que combina la capacidad útil con la participación porcentual.
    """
    if df_embalses.empty or 'Capacidad_GWh_Internal' not in df_embalses.columns:
        return pd.DataFrame(columns=['Embalse', 'Participación (%)'])
    
    df_resultado = df_embalses.copy()
    total = df_resultado['Capacidad_GWh_Internal'].sum()
    
    if total > 0:
        # Calcular porcentajes sin redondear primero
        porcentajes = (df_resultado['Capacidad_GWh_Internal'] / total * 100)
        
        # Ajustar el último valor para que la suma sea exactamente 100%
        porcentajes_redondeados = porcentajes.round(2)
        diferencia = 100 - porcentajes_redondeados.sum()
        
        # Si hay diferencia por redondeo, ajustar el valor más grande
        if abs(diferencia) > 0.001:
            idx_max = porcentajes_redondeados.idxmax()
            porcentajes_redondeados.loc[idx_max] += diferencia
            
        df_resultado['Participación (%)'] = porcentajes_redondeados.round(2)
    else:
        df_resultado['Participación (%)'] = 0
    
    # Ordenar de mayor a menor por participación
    df_resultado = df_resultado.sort_values('Participación (%)', ascending=False)
    
    return df_resultado[['Embalse', 'Participación (%)', 'Volumen Útil (%)']].reset_index(drop=True)

# --- Función para crear tabla jerárquica de regiones con embalses ---
def get_tabla_regiones_embalses(start_date=None, end_date=None):
    """
    Crea una tabla jerárquica que muestra primero las regiones y permite expandir para ver embalses.
    """
    try:
        objetoAPI = get_objetoAPI()
        # Obtener todos los embalses con su información de región
        # Usar fecha actual para obtener listado más reciente
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        embalses_info, warning = obtener_datos_inteligente('ListadoEmbalses','Sistema', yesterday, today)
        embalses_info['Values_Name'] = embalses_info['Values_Name'].str.strip().str.upper()
        embalses_info['Values_HydroRegion'] = embalses_info['Values_HydroRegion'].str.strip().str.title()

        # Usar solo la fecha final para todos los cálculos (como en las fichas)
        fecha_solicitada = end_date if end_date else start_date
        fecha_obj = datetime.strptime(fecha_solicitada if fecha_solicitada else today, '%Y-%m-%d').date()

        # Usar helper para buscar fecha con datos disponibles
        df_vol_test, fecha_encontrada = obtener_datos_desde_sqlite('VoluUtilDiarEner', 'Embalse', fecha_obj)
        df_cap_test, _ = obtener_datos_desde_sqlite('CapaUtilDiarEner', 'Embalse', fecha_obj)
        
        if fecha_encontrada is None or df_vol_test is None or df_cap_test is None:
            logger.warning("No se encontraron datos en ninguna fecha reciente")
            return pd.DataFrame(), pd.DataFrame()
        
        fecha = fecha_encontrada.strftime('%Y-%m-%d')
        logger.debug(f"[DEBUG] Usando fecha con datos disponibles para cálculo de embalses: {fecha} ({len(df_vol_test)} embalses con volumen)")

        if not fecha:
            logger.warning("No se encontraron datos en ninguna fecha reciente")
            return pd.DataFrame(), pd.DataFrame()

        # DataFrame detallado de embalses usando la fecha con datos
        logger.debug(f"Construyendo tabla de embalses para fecha: {fecha}")
        embalses_detalle = []

        # OPTIMIZADO: Usar obtener_datos_inteligente (SQLite)
        df_vol, warning_vol = obtener_datos_inteligente('VoluUtilDiarEner', 'Embalse', fecha, fecha)
        df_cap, warning_cap = obtener_datos_inteligente('CapaUtilDiarEner', 'Embalse', fecha, fecha)

        # ✅ NO CONVERTIR: obtener_datos_inteligente ya devuelve valores en GWh cuando viene de SQLite
        # Los datos de la API XM vienen en Wh, pero se convierten en obtener_datos_inteligente
        # Por lo tanto, 'Value' ya está en GWh aquí
        df_vol['Value_GWh'] = df_vol['Value']
        df_cap['Value_GWh'] = df_cap['Value']

        # Combinar con información de regiones
        for _, embalse_info in embalses_info.iterrows():
            embalse_name = embalse_info['Values_Name']
            region_name = embalse_info['Values_HydroRegion']

            # Buscar datos de este embalse
            vol_data = df_vol[df_vol['Name'] == embalse_name]
            cap_data = df_cap[df_cap['Name'] == embalse_name]

            if not vol_data.empty and not cap_data.empty:
                vol_gwh = vol_data['Value_GWh'].iloc[0]
                cap_gwh = cap_data['Value_GWh'].iloc[0]
                pct = (vol_gwh / cap_gwh * 100) if cap_gwh > 0 else 0

                embalses_detalle.append({
                    'Embalse': embalse_name,
                    'Región': region_name,
                    'VoluUtilDiarEner (GWh)': vol_gwh,
                    'CapaUtilDiarEner (GWh)': cap_gwh,
                    'Volumen Útil (%)': pct
                })

        df_embalses = pd.DataFrame(embalses_detalle)
# REMOVED DEBUG:         logger.info(f"DataFrame de embalses creado con {len(df_embalses)} embalses")
        logger.debug("Primeras filas df_embalses:")
        logger.debug(f"\n{df_embalses[['Región', 'VoluUtilDiarEner (GWh)', 'CapaUtilDiarEner (GWh)']].head(10)}")

        # Procesar datos si tenemos embalses
        if not df_embalses.empty:
            # Calcular participación porcentual dentro de cada región (según la fórmula solicitada)
            df_embalses['Capacidad_GWh_Internal'] = df_embalses['CapaUtilDiarEner (GWh)']

            # Calcular participación por región
            for region in df_embalses['Región'].unique():
                mask = df_embalses['Región'] == region
                total_cap_region = df_embalses.loc[mask, 'Capacidad_GWh_Internal'].sum()
                if total_cap_region > 0:
                    df_embalses.loc[mask, 'Participación (%)'] = (
                        df_embalses.loc[mask, 'Capacidad_GWh_Internal'] / total_cap_region * 100
                    ).round(2)
                else:
                    df_embalses.loc[mask, 'Participación (%)'] = 0.0

            # Crear tabla resumen por región usando los datos YA OBTENIDOS (no llamar a función externa)
            regiones_resumen = []
            regiones_unicas = [r for r in df_embalses['Región'].unique() if r and r.strip() and r.strip().lower() not in ['sin nacional', 'rios estimados', '']]
            
            for region in regiones_unicas:
                # Filtrar embalses de esta región
                embalses_region = df_embalses[df_embalses['Región'] == region]
                
                if not embalses_region.empty:
                    # Calcular totales directamente de los datos que ya tenemos
                    total_capacidad = embalses_region['CapaUtilDiarEner (GWh)'].sum()
                    total_volumen = embalses_region['VoluUtilDiarEner (GWh)'].sum()
                    
                    # Calcular porcentaje
                    if total_capacidad > 0:
                        porcentaje_volumen = (total_volumen / total_capacidad) * 100
                    else:
                        porcentaje_volumen = 0.0
                    
                    regiones_resumen.append({
                        'Región': region,
                        'Total (GWh)': round(total_capacidad, 2),
                        'Volumen Util (GWh)': round(total_volumen, 2),
                        'Volumen Útil (%)': round(porcentaje_volumen, 1)
                    })
                else:
                    regiones_resumen.append({
                        'Región': region,
                        'Total (GWh)': 0.00,
                        'Volumen Util (GWh)': 0.00,
                        'Volumen Útil (%)': 0.00
                    })
            
            regiones_totales = pd.DataFrame(regiones_resumen)
            
            # 🆕 Calcular participación porcentual de cada región respecto al total nacional
            # La participación se basa en la capacidad útil total de cada región
            total_capacidad_nacional = regiones_totales['Total (GWh)'].sum()
            
            if total_capacidad_nacional > 0:
                regiones_totales['Participación (%)'] = (
                    regiones_totales['Total (GWh)'] / total_capacidad_nacional * 100
                ).round(2)
            else:
                regiones_totales['Participación (%)'] = 0.0
            
            logger.debug(f"Tabla de regiones creada con {len(regiones_totales)} regiones")
            logger.debug(f"Participación por región: {regiones_totales[['Región', 'Participación (%)']].to_dict('records')}")
        else:
            # Si no hay datos, crear DataFrame vacío con estructura correcta
            regiones_totales = pd.DataFrame(columns=['Región', 'Total (GWh)', 'Volumen Util (GWh)', 'Volumen Útil (%)', 'Participación (%)'])
            logger.warning("No se pudieron obtener datos de embalses para las fechas disponibles")

        # (No agregar fila TOTAL SISTEMA aquí, se agregará manualmente en la tabla de participación)
        return regiones_totales, df_embalses
    except Exception as e:
        print(f"[ERROR] get_tabla_regiones_embalses: {e}")
        return pd.DataFrame(), pd.DataFrame()

def create_collapsible_regions_table(start_date=None, end_date=None):
    """
    Crea una tabla expandible elegante con regiones que se pueden plegar/desplegar para ver embalses.
    """
    try:
        # Usar fecha actual si no se proporcionan parámetros
        if not end_date:
            end_date = date.today().strftime('%Y-%m-%d')
        
        regiones_totales, df_completo_embalses = get_tabla_regiones_embalses(start_date, end_date)
        
        if regiones_totales.empty:
            return dbc.Alert("No se encontraron datos de regiones.", color="warning", className="text-center")
        
        # Crear componentes colapsables elegantes para cada región
        region_components = []
        
        for idx, region_row in regiones_totales.iterrows():
            region_name = region_row['Región']
            total_gwh = region_row['Total (GWh)']
            participacion = region_row['Participación (%)']
            
            # Obtener embalses de la región
            embalses_region = get_embalses_by_region(region_name, df_completo_embalses)
            
            # Contar embalses para mostrar en el header
            num_embalses = len(embalses_region) if not embalses_region.empty else 0
            
            # Crear contenido de embalses con las dos tablas lado a lado
            if not embalses_region.empty:
                # Preparar datos para las tablas con formateo
                embalses_data_formatted = []
                embalses_data_raw = []  # Para cálculos
                for _, embalse_row in embalses_region.iterrows():
                    embalse_name = embalse_row['Región'].replace('    └─ ', '')
                    embalse_capacidad = embalse_row['Total (GWh)']
                    embalse_participacion = embalse_row['Participación (%)']
                    
                    # Para la tabla de capacidad ya no incluimos la columna de GWh
                    embalses_data_formatted.append({
                        'Embalse': embalse_name,
                        'Participación (%)': embalse_participacion
                    })
                    
                    embalses_data_raw.append({
                        'Embalse': embalse_name,
                        'Capacidad_GWh_Internal': embalse_capacidad,  # Sin formatear para cálculos
                        'Participación (%)': embalse_participacion
                    })
                
                # Calcular total para la tabla de capacidad
                total_capacidad = sum([row['Capacidad_GWh_Internal'] for row in embalses_data_raw])
                
                # Crear tabla de participación porcentual
                tabla_participacion = dash_table.DataTable(
                    data=[{
                        'Embalse': row['Embalse'],
                        'Participación (%)': row['Participación (%)']
                    } for row in embalses_data_formatted] + [{'Embalse': 'TOTAL', 'Participación (%)': '100.0%'}],
                    columns=[
                        {"name": "Embalse", "id": "Embalse"},
                        {"name": "Participación (%)", "id": "Participación (%)"}
                    ],
                    style_cell={
                        'textAlign': 'left',
                        'padding': '8px',
                        'fontFamily': 'Inter, Arial, sans-serif',
                        'fontSize': 13,
                        'backgroundColor': '#f8f9fa',
                        'border': '1px solid #dee2e6'
                    },
                    style_header={
                        'backgroundColor': '#667eea',
                        'color': 'white',
                        'fontWeight': 'bold',
                        'fontSize': 14,
                        'textAlign': 'center',
                        'border': '1px solid #5a6cf0'
                    },
                    style_data_conditional=[
                        {
                            'if': {'filter_query': '{Embalse} = "TOTAL"'},
                            'backgroundColor': '#007bff',
                            'color': 'white',
                            'fontWeight': 'bold'
                        }
                    ],
                    page_action="none"
                )
                
                # Crear tabla de capacidad detallada
                # Crear DataFrame temporal para obtener las columnas correctas
                temp_df = pd.DataFrame([{
                    'Embalse': row['Embalse'],
                    'Participación (%)': row['Participación (%)']
                } for row in embalses_data_formatted])
                
                tabla_capacidad = dash_table.DataTable(
                    data=embalses_data_formatted + [{
                        'Embalse': 'TOTAL',
                        'Participación (%)': ''
                    }],
                    columns=create_embalse_table_columns(temp_df),
                    style_cell={
                        'textAlign': 'left',
                        'padding': '8px',
                        'fontFamily': 'Inter, Arial, sans-serif',
                        'fontSize': 13,
                        'backgroundColor': '#f8f9fa',
                        'border': '1px solid #dee2e6'
                    },
                    style_header={
                        'backgroundColor': '#28a745',
                        'color': 'white',
                        'fontWeight': 'bold',
                        'fontSize': 14,
                        'textAlign': 'center',
                        'border': '1px solid #218838'
                    },
                    style_data_conditional=[
                        {
                            'if': {'filter_query': '{Embalse} = "TOTAL"'},
                            'backgroundColor': '#007bff',
                            'color': 'white',
                            'fontWeight': 'bold'
                        }
                    ],
                    page_action="none"
                )
                
                embalses_content = html.Div([
                    html.Div([
                        html.I(className="bi bi-building me-2", style={"color": "#28a745"}),
                        html.Strong(f"Análisis Detallado - {region_name}", 
                                  className="text-success", style={"fontSize": "1.1rem"})
                    ], className="mb-4 d-flex align-items-center"),
                    
                    # Las dos tablas lado a lado
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader([
                                    html.I(className="bi bi-pie-chart me-2", style={"color": "#667eea"}),
                                    html.Strong("📊 Participación Porcentual por Embalse")
                                ], style={"background": "linear-gradient(135deg, #e3f2fd 0%, #f3f4f6 100%)",
                                         "border": "none", "borderRadius": "8px 8px 0 0"}),
                                dbc.CardBody([
                                    html.P("Distribución porcentual de la capacidad energética entre embalses. La tabla incluye una fila TOTAL que suma exactamente 100%.", 
                                          className="text-muted mb-3", style={"fontSize": "0.85rem"}),
                                    tabla_participacion
                                ], className="p-3")
                            ], className="card-modern h-100")
                        ], md=6),
                        
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader([
                                    html.I(className="bi bi-battery-full me-2", style={"color": "#28a745"}),
                                    html.Strong("🏭 Capacidad Detallada por Embalse")
                                ], style={"background": "linear-gradient(135deg, #e8f5e8 0%, #f3f4f6 100%)",
                                         "border": "none", "borderRadius": "8px 8px 0 0"}),
                                dbc.CardBody([
                                    html.P(f"Valores específicos de capacidad útil diaria en GWh para los {num_embalses} embalses de la región.", 
                                          className="text-muted mb-3", style={"fontSize": "0.85rem"}),
                                    tabla_capacidad
                                ], className="p-3")
                            ], className="card-modern h-100")
                        ], md=6)
                    ], className="g-3")
                ])
            else:
                embalses_content = dbc.Alert([
                    html.I(className="bi bi-exclamation-triangle me-2"),
                    f"No se encontraron embalses para la región {region_name}."
                ], color="light", className="text-center my-3 alert-modern")
            
            # Crear card principal elegante para la región
            region_card = dbc.Card([
                # Header clickeable de la región
                dbc.CardHeader([
                    dbc.Button([
                        html.Div([
                            html.Div([
                                html.I(className="bi bi-chevron-right me-3", 
                                       id={"type": "chevron-region", "index": idx},
                                       style={"fontSize": "1.1rem", "color": "#007bff", "transition": "transform 0.3s ease"}),
                                html.I(className="bi bi-geo-alt-fill me-2", style={"color": "#28a745"}),
                                html.Strong(region_name, style={"fontSize": "1.1rem", "color": "#2d3748"})
                            ], className="d-flex align-items-center"),
                            html.Div([
                                dbc.Badge(f"{format_number(total_gwh)} GWh", color="primary", className="me-2 px-2 py-1"),
                                dbc.Badge(f"{participacion}%", color="success", className="px-2 py-1"),
                                html.Small(f" • {num_embalses} embalse{'s' if num_embalses != 1 else ''}", 
                                         className="text-muted ms-2")
                            ], className="d-flex align-items-center mt-1")
                        ], className="d-flex justify-content-between align-items-start w-100")
                    ], 
                    id={"type": "toggle-region", "index": idx},
                    className="w-100 text-start border-0 bg-transparent p-0",
                    style={"background": "transparent !important"}
                    )
                ], className="border-0 bg-gradient", 
                style={
                    "background": f"linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)",
                    "borderRadius": "12px 12px 0 0",
                    "padding": "1rem"
                }),
                
                # Contenido colapsable
                dbc.Collapse([
                    dbc.CardBody([
                        html.Hr(className="mt-0 mb-3", style={"borderColor": "#dee2e6"}),
                        embalses_content
                    ], className="pt-0", style={"backgroundColor": "#fdfdfe"})
                ],
                id={"type": "collapse-region", "index": idx},
                is_open=False
                )
            ], className="mb-3 shadow-sm",
            style={
                "border": "1px solid #e3e6f0",
                "borderRadius": "12px",
                "transition": "all 0.3s ease",
                "overflow": "hidden"
            })
            
            region_components.append(region_card)
        
        return html.Div([
            # Header explicativo elegante
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="bi bi-info-circle-fill me-2", style={"color": "#0d6efd"}),
                        html.Strong("⚡ Capacidad Útil Diaria de Energía por Región Hidrológica", style={"fontSize": "1.2rem"})
                    ], className="d-flex align-items-center mb-2"),
                    html.P([
                        "Haz clic en cualquier región para expandir y ver sus tablas detalladas. ",
                        html.Strong("Cada región muestra dos tablas lado a lado:", className="text-primary"),
                        " participación porcentual de embalses y capacidad energética detallada en GWh."
                    ], className="mb-0 text-dark", style={"fontSize": "0.95rem"})
                ], className="py-3")
            ], className="mb-4", 
            style={
                "background": "linear-gradient(135deg, #e3f2fd 0%, #f3f4f6 100%)",
                "border": "1px solid #bbdefb",
                "borderRadius": "12px"
            }),
            
            # Container de regiones
            html.Div(region_components, id="regions-container")
        ])
        
    except Exception as e:
        print(f"Error creando tabla colapsable: {e}")
        return dbc.Alert(f"Error al crear tabla: {str(e)}", color="danger")


# Callback elegante para manejar el pliegue/despliegue de regiones
@callback(
    [Output({"type": "collapse-region", "index": dash.dependencies.MATCH}, "is_open"),
     Output({"type": "chevron-region", "index": dash.dependencies.MATCH}, "className")],
    [Input({"type": "toggle-region", "index": dash.dependencies.MATCH}, "n_clicks")],
    [State({"type": "collapse-region", "index": dash.dependencies.MATCH}, "is_open")]
)
def toggle_region_collapse(n_clicks, is_open):
    """
    Callback elegante para manejar el toggle de una región específica usando pattern-matching
    """
    if not n_clicks:
        return False, "bi bi-chevron-right me-3"
    
    new_state = not is_open
    if new_state:
        # Expandido - rotar chevron hacia abajo
        return True, "bi bi-chevron-down me-3"
    else:
        # Contraído - chevron hacia la derecha
        return False, "bi bi-chevron-right me-3"


def get_embalses_by_region(region, df_completo):
    """
    Obtiene los embalses de una región específica con participación dentro de esa región.
    """
    # Usar la columna correcta 'Región' en lugar de 'Values_HydroRegion'
    embalses_region = df_completo[df_completo['Región'] == region].copy()
    if embalses_region.empty:
        return pd.DataFrame()
    
    total_region = embalses_region['Capacidad_GWh_Internal'].sum()
    if total_region > 0:
        embalses_region['Participación (%)'] = (embalses_region['Capacidad_GWh_Internal'] / total_region * 100).round(2)
        # Ajustar para que sume exactamente 100%
        diferencia = 100 - embalses_region['Participación (%)'].sum()
        if abs(diferencia) > 0.001:
            idx_max = embalses_region['Participación (%)'].idxmax()
            embalses_region.loc[idx_max, 'Participación (%)'] += diferencia
            embalses_region['Participación (%)'] = embalses_region['Participación (%)'].round(2)
    else:
        embalses_region['Participación (%)'] = 0
    
    # Formatear para mostrar como sub-elementos - usar la columna correcta 'Embalse'
    if 'Embalse' in embalses_region.columns:
        # Agregar columna de volumen útil si está disponible
        columns_to_include = ['Embalse', 'Capacidad_GWh_Internal', 'Participación (%)']
        if 'Volumen Útil (%)' in embalses_region.columns:
            columns_to_include.append('Volumen Útil (%)')
        
        resultado = embalses_region[columns_to_include].copy()
        resultado = resultado.rename(columns={
            'Embalse': 'Región', 
            'Capacidad_GWh_Internal': 'Total (GWh)',
            'Volumen Útil (%)': 'Volumen Útil (%)'
        })
        resultado['Región'] = '    └─ ' + resultado['Región'].astype(str)  # Identar embalses
        resultado['Tipo'] = 'embalse'
        return resultado
    else:
        logger.warning(f"Columnas disponibles en df_completo: {embalses_region.columns.tolist()}")
        return pd.DataFrame()
def get_embalses_data_for_table(region=None, start_date=None, end_date=None):
    """
    Función simple que obtiene datos de embalses con columnas formateados para la tabla.
    Retorna Embalse, Volumen Útil (%) y Riesgo para visualización, manteniendo cálculos internos.
    """
    try:
        # Obtener datos frescos con todas las columnas para cálculos
        df_fresh = get_embalses_capacidad(region, start_date, end_date)
        
        # 🔍 LOG: Datos obtenidos
        logger.info(f"🔍 [get_embalses_data_for_table] Región={region}, Registros={len(df_fresh)}")
        
        if df_fresh.empty:
            return []
        
        # Agregar columna de riesgo usando los datos completos
        df_con_riesgo = agregar_columna_riesgo_a_tabla(df_fresh)
        
        # Crear datos formateados para la tabla (solo columnas visibles)
        table_data = []
        
        for _, row in df_con_riesgo.iterrows():
            if row['Embalse'] != 'TOTAL':  # Procesar solo embalses, no TOTAL
                volumen_val = row['Volumen Útil (%)']
                
                # 🔍 LOG CRÍTICO: Valor RAW de Volumen Útil
                logger.info(f"🔍 [TABLE_DATA] {row['Embalse']}: Volumen RAW={volumen_val} (tipo={type(volumen_val).__name__})")
                
                # Solo formatear si es numérico, no reformatear strings
                if isinstance(volumen_val, str):
                    volumen_formatted = volumen_val  # Ya está formateado
                elif pd.notna(volumen_val) and isinstance(volumen_val, (int, float)):
                    volumen_formatted = f"{float(volumen_val):.1f}%"
                else:
                    volumen_formatted = "N/D"
                
                # 🔍 LOG CRÍTICO: Valor formateado final
                logger.info(f"🔍 [TABLE_DATA] {row['Embalse']}: Volumen FORMATTED={volumen_formatted}")
                
                formatted_row = {
                    'Embalse': row['Embalse'],
                    'Volumen Útil (%)': volumen_formatted,
                    'Riesgo': row['Riesgo']
                }
                table_data.append(formatted_row)
        
        # Agregar fila TOTAL (mantener cálculo interno de capacidad pero no mostrarla)
        total_capacity = df_fresh['Capacidad_GWh_Internal'].sum()
        valid_volume_data = df_fresh[df_fresh['Volumen Útil (%)'].notna()]
        avg_volume = valid_volume_data['Volumen Útil (%)'].mean() if not valid_volume_data.empty else None
        
        total_row = {
            'Embalse': 'TOTAL',
            'Volumen Útil (%)': f"{avg_volume:.1f}%" if avg_volume is not None else "N/D",
            'Riesgo': '⚡'  # Ícono especial para TOTAL
        }
        table_data.append(total_row)
        
# REMOVED DEBUG:         logger.info(f"DATOS TABLA PREPARADOS: {len(table_data)} filas con columna de riesgo")
        return table_data
        
    except Exception as e:
# REMOVED DEBUG:         print(f"❌ Error en get_embalses_data_for_table: {e}")
        return []

def get_embalses_capacidad(region=None, start_date=None, end_date=None):
    """
    Obtiene la capacidad útil diaria de energía por embalse desde la API XM (CapaUtilDiarEner) 
    y calcula el porcentaje de volumen útil usando la función unificada.
    Si se pasa una región, filtra los embalses de esa región.
    Solo incluye embalses que tienen datos de capacidad activos.
    
    IMPORTANTE: Usa solo end_date (fecha final) para los cálculos de volumen útil.
    """
    try:
        objetoAPI = get_objetoAPI()
# REMOVED DEBUG:         logger.debug(f"DEBUG CAPACIDAD: Iniciando con región={region}, fechas={start_date} a {end_date}")
        
        # Si no se proporcionan fechas, usar fecha actual
        if not start_date or not end_date:
            today = datetime.now().strftime('%Y-%m-%d')
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            start_date, end_date = yesterday, today
        
        # USAR SOLO LA FECHA FINAL para los cálculos de volumen útil
        fecha_para_calculo = end_date
        
        # OPTIMIZADO: Usar obtener_datos_inteligente (SQLite)
        df_capacidad, warning = obtener_datos_inteligente('CapaUtilDiarEner','Embalse', fecha_para_calculo, fecha_para_calculo)
        print(f"� DEBUG CAPACIDAD: Datos de capacidad obtenidos: {len(df_capacidad) if df_capacidad is not None else 0} registros")
        
        # Si no hay datos para la fecha exacta, buscar fecha anterior con datos (igual que la función unificada)
        if df_capacidad is None or df_capacidad.empty:
            logger.debug("DEBUG CAPACIDAD: Buscando fecha anterior con datos...")
            # Usar helper para buscar fecha con datos disponibles
            fecha_obj = datetime.strptime(fecha_para_calculo, '%Y-%m-%d').date()
            df_capacidad, fecha_encontrada = obtener_datos_desde_sqlite('CapaUtilDiarEner', 'Embalse', fecha_obj)
            
            if fecha_encontrada is None or df_capacidad is None:
                print("❌ DEBUG CAPACIDAD: No se encontraron datos en los últimos 7 días")
                return pd.DataFrame()
            
            fecha_para_calculo = fecha_encontrada.strftime('%Y-%m-%d')
            logger.debug(f"DEBUG CAPACIDAD: Usando fecha con datos: {fecha_para_calculo}")
        
        logger.debug(f"DEBUG CAPACIDAD: Datos finales obtenidos: {len(df_capacidad)} registros")
        
        if 'Name' in df_capacidad.columns and 'Value' in df_capacidad.columns:
            # Obtener información de región para embalses
            today = datetime.now().strftime('%Y-%m-%d')
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            embalses_info, warning = obtener_datos_inteligente('ListadoEmbalses','Sistema', yesterday, today)
            embalses_info['Values_Name'] = embalses_info['Values_Name'].str.strip().str.upper()
            embalses_info['Values_HydroRegion'] = embalses_info['Values_HydroRegion'].str.strip().str.title()
            embalse_region_dict = dict(zip(embalses_info['Values_Name'], embalses_info['Values_HydroRegion']))
            
# REMOVED DEBUG:             logger.debug(f"DEBUG CAPACIDAD: Mapeado región-embalse: {len(embalse_region_dict)} embalses")
# REMOVED DEBUG:             logger.debug(f"DEBUG CAPACIDAD: Regiones disponibles: {set(embalse_region_dict.values())}")
            if region:
                embalses_en_region = [e for e, r in embalse_region_dict.items() if r == region]
# REMOVED DEBUG:                 logger.debug(f"DEBUG CAPACIDAD: Embalses en región {region}: {embalses_en_region}")
            
            # Solo incluir embalses que tienen datos de capacidad
            embalses_con_datos = set(df_capacidad['Name'].unique())
            embalse_region_dict_filtrado = {
                embalse: region_emb for embalse, region_emb in embalse_region_dict.items() 
                if embalse in embalses_con_datos
            }
# REMOVED DEBUG:             logger.debug(f"DEBUG CAPACIDAD: Embalses con datos de capacidad: {len(embalses_con_datos)}")
# REMOVED DEBUG:             logger.debug(f"DEBUG CAPACIDAD: Embalses filtrados: {len(embalse_region_dict_filtrado)}")
            
            # Procesar datos de capacidad
            df_capacidad['Region'] = df_capacidad['Name'].map(embalse_region_dict_filtrado)
            if region:
                region_normalized = region.strip().title()
                antes_filtro = len(df_capacidad)
                df_capacidad = df_capacidad[df_capacidad['Region'] == region_normalized]
# REMOVED DEBUG:                 logger.debug(f"DEBUG CAPACIDAD: Filtro por región '{region}' -> '{region_normalized}' - antes: {antes_filtro}, después: {len(df_capacidad)}")
            
            # CORRECCIÓN: Convertir de Wh a GWh (dividir por 1e9)
            df_capacidad['Value'] = df_capacidad['Value'] / 1e9
            
            df_capacidad_grouped = df_capacidad.groupby('Name')['Value'].sum().reset_index()
            df_capacidad_grouped = df_capacidad_grouped.rename(columns={'Name': 'Embalse', 'Value': 'Capacidad_GWh_Internal'})
            
            logger.debug(f"DEBUG CAPACIDAD CORREGIDA: Valores después de conversión a GWh:")
            print(df_capacidad_grouped.head().to_string())
            
            # Obtener datos de VOLUMEN ÚTIL (misma lógica que get_tabla_regiones_embalses)
            df_volumen, warning_vol = obtener_datos_inteligente('VoluUtilDiarEner','Embalse', fecha_para_calculo, fecha_para_calculo)
            
            if df_volumen is None or df_volumen.empty:
                # Buscar fecha anterior con datos
                fecha_obj = datetime.strptime(fecha_para_calculo, '%Y-%m-%d').date()
                df_volumen, fecha_vol = obtener_datos_desde_sqlite('VoluUtilDiarEner', 'Embalse', fecha_obj)
                if fecha_vol:
                    fecha_para_calculo_vol = fecha_vol.strftime('%Y-%m-%d')
                    logger.debug(f"Usando fecha alternativa para volumen: {fecha_para_calculo_vol}")
            
            # Procesar datos de volumen
            df_final = df_capacidad_grouped.copy()
            
            if df_volumen is not None and not df_volumen.empty and 'Name' in df_volumen.columns and 'Value' in df_volumen.columns:
                # Convertir de Wh a GWh y agrupar por embalse
                df_volumen['Value_GWh'] = df_volumen['Value'] / 1e9
                df_volumen_grouped = df_volumen.groupby('Name')['Value_GWh'].sum().reset_index()
                df_volumen_grouped = df_volumen_grouped.rename(columns={'Name': 'Embalse'})
                
                # Merge con capacidad
                df_final = df_final.merge(df_volumen_grouped, on='Embalse', how='left')
                
                # Calcular porcentaje: (Volumen / Capacidad) * 100 - IGUAL que en get_tabla_regiones_embalses
                df_final['Volumen Útil (%)'] = df_final.apply(
                    lambda row: round((row['Value_GWh'] / row['Capacidad_GWh_Internal'] * 100), 1)
                    if pd.notna(row.get('Value_GWh')) and row['Capacidad_GWh_Internal'] > 0 
                    else None,
                    axis=1
                )
                
                # Limpiar columna temporal
                df_final = df_final.drop(columns=['Value_GWh'])
                
                logger.info(f"✅ Volumen útil calculado: {df_final['Volumen Útil (%)'].notna().sum()}/{len(df_final)} embalses")
            else:
                df_final['Volumen Útil (%)'] = None
                logger.warning("⚠️ No hay datos de volumen útil disponibles")

            # IMPORTANTE: NO formatear aquí, dejar valores numéricos (o None)
            # El formateo se hace solo una vez en las funciones que crean las tablas
            
# REMOVED DEBUG:             logger.debug(f"Columnas finales: {list(df_final.columns)}")
# REMOVED DEBUG:             logger.debug(f"Primeras filas del DataFrame final:")
            print(df_final.head())

# REMOVED DEBUG:             logger.debug(f"DEBUG CAPACIDAD: Retornando DataFrame con {len(df_final)} filas")
            return df_final.sort_values('Embalse')
        else:
            # Si no hay datos de capacidad, mostrar DataFrame vacío pero con columnas correctas
            return pd.DataFrame(columns=['Embalse', 'Capacidad_GWh_Internal', 'Volumen Útil (%)'])
    except Exception as e:
        logger.error(f"Error obteniendo datos de embalses: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        return pd.DataFrame(columns=['Embalse', 'Capacidad_GWh_Internal', 'Volumen Útil (%)'])

def create_embalse_table_columns(df):
    """Crea las columnas para la tabla de embalses dinámicamente según las columnas disponibles"""
    columns = []
    logger.debug(f"Creando columnas para tabla - DataFrame tiene: {list(df.columns) if not df.empty else 'VACÍO'}")
    if not df.empty:
        for col in df.columns:
            if col == "Embalse":
                columns.append({"name": "Embalse", "id": "Embalse"})
# REMOVED DEBUG:                 logger.info(f"Agregada columna: Embalse")
            elif col == "Volumen Útil (%)":
                columns.append({"name": "Volumen Útil (%)", "id": "Volumen Útil (%)"})
# REMOVED DEBUG:                 logger.info(f"Agregada columna: Volumen Útil (%)")
            elif col == "Participación (%)":
                columns.append({"name": "Participación (%)", "id": "Participación (%)"})
# REMOVED DEBUG:                 logger.info(f"Agregada columna: Participación (%)")
            elif col == "Riesgo":
                columns.append({"name": "🚨 Riesgo", "id": "Riesgo"})
# REMOVED DEBUG:                 logger.info(f"Agregada columna: Riesgo")
            # Nota: La columna 'Capacidad_GWh_Internal' ha sido eliminada de las tablas jerárquicas
    logger.debug(f"Total de columnas creadas: {len(columns)}")
    return columns

def create_initial_embalse_table():
    """Crea la tabla inicial de embalses con la nueva columna"""
    try:
        logger.info("Creando tabla inicial de embalses...")
        
        # Obtener datos directamente usando fechas actuales
        df = get_embalses_capacidad()
# REMOVED DEBUG:         logger.debug(f"Datos iniciales obtenidos: {df.shape[0]} filas, columnas: {list(df.columns)}")
        
        if df.empty:
            return dbc.Alert("No hay datos de embalses para mostrar.", color="warning")
        
        # Formatear datos (mantener la capacidad para cálculos internos)
        df_formatted = df.copy()
        
        if 'Volumen Útil (%)' in df.columns:
            # Solo formatear valores numéricos, no reformatear strings
            df_formatted['Volumen Útil (%)'] = df['Volumen Útil (%)'].apply(
                lambda x: x if isinstance(x, str) else (f"{x:.1f}%" if pd.notna(x) and isinstance(x, (int, float)) else "N/D")
            )
            logger.info("Columna 'Volumen Útil (%)' formateada en tabla inicial")
        
        # Calcular totales para la fila TOTAL (usando los datos originales)
        total_capacity = df['Capacidad_GWh_Internal'].sum() if 'Capacidad_GWh_Internal' in df.columns else 0
        total_row_data = {
            'Embalse': ['TOTAL']
        }
        
        if 'Volumen Útil (%)' in df.columns:
            valid_data = df[df['Volumen Útil (%)'].notna()]
            avg_volume_pct = valid_data['Volumen Útil (%)'].mean() if not valid_data.empty else None
            total_row_data['Volumen Útil (%)'] = [f"{avg_volume_pct:.1f}%" if avg_volume_pct is not None else "N/D"]
        
        total_row = pd.DataFrame(total_row_data)
        
        # Crear DataFrame para mostrar (sin columna de capacidad)
        display_columns = ['Embalse']
        if 'Volumen Útil (%)' in df_formatted.columns:
            display_columns.append('Volumen Útil (%)')
        
        df_display = df_formatted[display_columns].copy()
        df_display = pd.concat([df_display, total_row], ignore_index=True)
        
        # 🆕 AGREGAR COLUMNA DE RIESGO CON PICTOGRAMAS
        df_display_con_riesgo = agregar_columna_riesgo_a_tabla(df.copy())  # Usar df original con capacidad
        
        # Crear DataFrame final para mostrar solo con las columnas necesarias + riesgo
        final_columns = ['Embalse']
        if 'Volumen Útil (%)' in df_display_con_riesgo.columns:
            # Formatear volumen útil para mostrar
            df_display_con_riesgo['Volumen Útil (%)'] = df_display_con_riesgo['Volumen Útil (%)'].apply(
                lambda x: f"{x:.1f}%" if pd.notna(x) and x != 'N/D' and not isinstance(x, str) else (x if isinstance(x, str) else "N/D")
            )
            final_columns.append('Volumen Útil (%)')
        final_columns.append('Riesgo')
        
        # Agregar fila TOTAL con riesgo
        total_row_riesgo = {
            'Embalse': 'TOTAL',
            'Volumen Útil (%)': total_row_data['Volumen Útil (%)'][0] if 'Volumen Útil (%)' in total_row_data else 'N/D',
            'Riesgo': '⚡'
        }
        
        # Filtrar solo embalses (sin TOTAL) y agregar TOTAL al final
        df_embalses_only = df_display_con_riesgo[df_display_con_riesgo['Embalse'] != 'TOTAL'][final_columns].copy()
        df_total_row = pd.DataFrame([total_row_riesgo])
        df_final_display = pd.concat([df_embalses_only, df_total_row], ignore_index=True)
        
# REMOVED DEBUG:         logger.debug(f"DataFrame final para tabla inicial: {df_final_display.shape[0]} filas, columnas: {list(df_final_display.columns)}")
        
        return create_dynamic_embalse_table(df_final_display)
        
    except Exception as e:
# REMOVED DEBUG:         print(f"❌ Error creando tabla inicial: {e}")
        import traceback
        traceback.print_exc()
        return dbc.Alert(f"Error: {str(e)}", color="danger")

def create_dynamic_embalse_table(df_formatted):
    """Crea una tabla de embalses dinámicamente con todas las columnas disponibles"""
    logger.debug(f"INICIO create_dynamic_embalse_table - DataFrame: {df_formatted.shape if not df_formatted.empty else 'VACÍO'}")
    
    if df_formatted.empty:
        logger.warning("DataFrame vacío - retornando alerta")
        return dbc.Alert("No hay datos de embalses para mostrar.", color="warning")
    
    logger.debug(f"Creando tabla dinámica de embalses con {len(df_formatted)} filas y columnas: {list(df_formatted.columns)}")
    
    # Crear columnas dinámicamente
    columns = create_embalse_table_columns(df_formatted)
    logger.debug(f"Columnas creadas: {len(columns)}")
    
    # 🆕 Generar estilos condicionales basados en riesgo
    estilos_condicionales = []
    if 'Riesgo' in df_formatted.columns:
        estilos_condicionales = generar_estilos_condicionales_riesgo(df_formatted)
        logger.debug(f"Estilos condicionales de riesgo generados: {len(estilos_condicionales)}")
    else:
        # Estilo básico para TOTAL si no hay columna de riesgo
        estilos_condicionales = [
            {
                'if': {'filter_query': '{Embalse} = "TOTAL"'},
                'backgroundColor': '#007bff',
                'color': 'white',
                'fontWeight': 'bold'
            }
        ]
    
    # Crear la tabla
    table = dash_table.DataTable(
        id="tabla-capacidad-embalse",
        data=df_formatted.to_dict('records'),
        columns=columns,
        style_cell={'textAlign': 'left', 'padding': '6px', 'fontFamily': 'Arial', 'fontSize': 14},
        style_header={'backgroundColor': '#e3e3e3', 'fontWeight': 'bold'},
        style_data={'backgroundColor': '#f8f8f8'},
        style_data_conditional=estilos_condicionales,
        page_action="none"
    )
    
# REMOVED DEBUG:     logger.info(f"Tabla DataTable creada exitosamente con ID: {table.id}")
    return table
    
def create_data_table(data):
    """Tabla paginada de datos de caudal con participación porcentual y total siempre visible"""
    if data is None or data.empty:
        return dbc.Alert("No hay datos para mostrar en la tabla.", color="warning")
    
    # Crear una copia del dataframe para modificar
    df_with_participation = data.copy()
    
    # Formatear fechas si existe columna de fecha
    date_columns = [col for col in df_with_participation.columns if 'fecha' in col.lower() or 'date' in col.lower()]
    for col in date_columns:
        df_with_participation[col] = df_with_participation[col].apply(format_date)
    
    # Si tiene columna 'GWh', calcular participación
    total_value = 0
    if 'GWh' in df_with_participation.columns:
        # Filtrar filas que no sean TOTAL para calcular el porcentaje
        df_no_total = df_with_participation[df_with_participation['GWh'] != 'TOTAL'].copy()
        if not df_no_total.empty:
            # Asegurar que los valores son numéricos
            df_no_total['GWh'] = pd.to_numeric(df_no_total['GWh'], errors='coerce')
            total_value = df_no_total['GWh'].sum()
            
            if total_value > 0:
                # Calcular porcentajes
                porcentajes = (df_no_total['GWh'] / total_value * 100).round(2)
                
                # Ajustar para que sume exactamente 100%
                diferencia = 100 - porcentajes.sum()
                if abs(diferencia) > 0.001 and len(porcentajes) > 0:
                    idx_max = porcentajes.idxmax()
                    porcentajes.loc[idx_max] += diferencia
                
                # Agregar la columna de participación
                df_with_participation.loc[df_no_total.index, 'Participación (%)'] = porcentajes.round(2)
            else:
                df_with_participation['Participación (%)'] = 0
        else:
            df_with_participation['Participación (%)'] = 0
    
    # Formatear columnas numéricas (GWh, capacidades, etc.)
    numeric_columns = [col for col in df_with_participation.columns 
                      if any(keyword in col.lower() for keyword in ['gwh', 'capacidad', 'caudal', 'valor', 'value'])]
    
    for col in numeric_columns:
        if col != 'Participación (%)':  # No formatear porcentajes
            df_with_participation[col] = df_with_participation[col].apply(
                lambda x: format_number(x) if pd.notnull(x) and x != 'TOTAL' else x
            )
    
    # Crear tabla paginada con total siempre visible
    return html.Div([
        # Tabla principal con paginación
        dash_table.DataTable(
            data=df_with_participation.to_dict('records'),
            columns=[{"name": i, "id": i} for i in df_with_participation.columns],
            style_cell={
                'textAlign': 'left', 
                'padding': '8px', 
                'fontFamily': 'Inter, Arial, sans-serif', 
                'fontSize': '13px',
                'whiteSpace': 'normal',
                'height': 'auto'
            },
            style_header={
                'backgroundColor': '#2c3e50', 
                'fontWeight': 'bold',
                'color': 'white',
                'border': '1px solid #34495e'
            },
            style_data={
                'backgroundColor': '#f8f9fa',
                'border': '1px solid #dee2e6'
            },
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': '#ffffff'
                }
            ],
            page_size=10,  # Mostrar 10 filas por página
            page_action='native',  # Paginación nativa
            page_current=0,
            style_table={
                'maxHeight': '400px',
                'overflowY': 'auto',
                'overflowX': 'auto'
            }
        ),
        
        # Fila de TOTAL siempre visible en la parte inferior
        html.Div([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.Strong("📊 TOTAL: ", style={"fontSize": "1.1rem", "color": "#2c3e50"}),
                        html.Span(f"{format_number(total_value)} GWh", 
                                 style={"fontSize": "1.1rem", "fontWeight": "bold", "color": "#007bff"}),
                        html.Span(" | ", style={"margin": "0 10px", "color": "#6c757d"}),
                        html.Strong("Registros: ", style={"fontSize": "1rem", "color": "#2c3e50"}),
                        html.Span(f"{len(df_with_participation)}", 
                                 style={"fontSize": "1rem", "fontWeight": "bold", "color": "#28a745"})
                    ], className="d-flex align-items-center justify-content-center")
                ], className="py-2")
            ], className="mt-2", style={"backgroundColor": "#e3f2fd", "border": "2px solid #007bff"})
        ])
    ])

def create_line_chart(data, rio_name=None, start_date=None, end_date=None):
    """Gráfico de líneas moderno de energía con media histórica"""
    if data is None or data.empty:
        return dbc.Alert("No se pueden crear gráficos con estos datos.", color="warning", className="alert-modern")
    
    # Buscar columnas de fecha y valor (pueden tener nombres diferentes)
    date_col = None
    value_col = None
    
    # Detectar columna de fecha
    for col in data.columns:
        if any(keyword in col.lower() for keyword in ['fecha', 'date']):
            date_col = col
            break
    
    # Detectar columna de valor
    for col in data.columns:
        if any(keyword in col.lower() for keyword in ['m³/s', 'caudal', 'value', 'gwh']):
            value_col = col
            break
    
    if date_col and value_col:
        # Determinar la etiqueta del eje Y basada en el nombre de la columna
        if 'm³/s' in value_col:
            y_label = "Caudal (m³/s)"
        elif 'gwh' in value_col.lower():
            y_label = "Energía (GWh)"
        else:
            y_label = value_col
        
        # Crear figura base con plotly graph objects
        px, go = get_plotly_modules()
        fig = go.Figure()
        
        # Agregar línea de valores reales (negra para consistencia)
        fig.add_trace(go.Scatter(
            x=data[date_col],
            y=data[value_col],
            mode='lines+markers',
            name='Aportes Reales',
            line=dict(width=3, color='black'),
            marker=dict(size=8, color='black', line=dict(width=2, color='white')),
            hovertemplate=f'<b>Fecha:</b> %{{x}}<br><b>{y_label}:</b> %{{y:.2f}}<extra></extra>'
        ))
        
        # Obtener media histórica si tenemos nombre de río y fechas
        tiene_media = False
        if rio_name and start_date and end_date:
            try:
                # Convertir fechas a string si es necesario
                if hasattr(start_date, 'strftime'):
                    fecha_inicio_str = start_date.strftime('%Y-%m-%d')
                else:
                    fecha_inicio_str = str(start_date)
                
                if hasattr(end_date, 'strftime'):
                    fecha_fin_str = end_date.strftime('%Y-%m-%d')
                else:
                    fecha_fin_str = str(end_date)
                
                # Obtener media histórica
                media_hist_data, _ = obtener_datos_inteligente('AporEnerMediHist', 'Rio', fecha_inicio_str, fecha_fin_str)
                
                if media_hist_data is not None and not media_hist_data.empty:
                    # Filtrar por el río específico
                    media_hist_rio = media_hist_data[media_hist_data['Name'] == rio_name]
                    
                    if not media_hist_rio.empty and 'Value' in media_hist_rio.columns:
                        # ⚠️ NO convertir - fetch_metric_data YA convierte a GWh automáticamente
                        
                        # Combinar datos reales e históricos para colorear según estado
                        # Necesitamos preparar los datos reales en formato adecuado
                        datos_reales = data[[date_col, value_col]].copy()
                        datos_reales.columns = ['Date', 'Value_real']
                        datos_reales['Date'] = pd.to_datetime(datos_reales['Date'])
                        
                        media_hist_rio['Date'] = pd.to_datetime(media_hist_rio['Date'])
                        
                        # Merge para comparación
                        merged_data = datos_reales.merge(
                            media_hist_rio[['Date', 'Value']], 
                            on='Date', 
                            how='inner'
                        )
                        merged_data.rename(columns={'Value': 'Value_hist'}, inplace=True)
                        
                        if not merged_data.empty:
                            # Calcular porcentaje
                            merged_data['porcentaje'] = (merged_data['Value_real'] / merged_data['Value_hist']) * 100
                            
                            # Agregar línea histórica con colores dinámicos
                            for i in range(len(merged_data) - 1):
                                # ✅ FIX: Convertir a float antes de usar en formato
                                porcentaje = float(merged_data.iloc[i]['porcentaje'])
                                
                                # Determinar color según porcentaje
                                if porcentaje >= 100:
                                    color = '#28a745'  # Verde - Húmedo
                                    estado = 'Húmedo'
                                elif porcentaje >= 90:
                                    color = '#17a2b8'  # Cyan - Normal
                                    estado = 'Normal'
                                elif porcentaje >= 70:
                                    color = '#ffc107'  # Amarillo - Moderadamente seco
                                    estado = 'Moderadamente seco'
                                else:
                                    color = '#dc3545'  # Rojo - Muy seco
                                    estado = 'Muy seco'
                                
                                # Agregar segmento de línea
                                fig.add_trace(go.Scatter(
                                    x=merged_data['Date'].iloc[i:i+2],
                                    y=merged_data['Value_hist'].iloc[i:i+2],
                                    mode='lines',
                                    name='Media Histórica' if i == 0 else None,
                                    showlegend=(i == 0),
                                    line=dict(width=3, color=color, dash='dash'),
                                    hovertemplate=f'<b>Fecha:</b> %{{x}}<br><b>Media Histórica:</b> %{{y:.2f}} GWh<br><b>Estado:</b> {estado} ({porcentaje:.1f}%)<extra></extra>',
                                    legendgroup='media_historica'
                                ))
                            tiene_media = True
                        else:
                            # Fallback: línea azul simple si no hay datos para comparar
                            fig.add_trace(go.Scatter(
                                x=media_hist_rio['Date'],
                                y=media_hist_rio['Value'],
                                mode='lines',
                                name='Media Histórica',
                                line=dict(width=3, color='#1e90ff', dash='dash'),
                                hovertemplate=f'<b>Fecha:</b> %{{x}}<br><b>Media Histórica:</b> %{{y:.2f}} GWh<extra></extra>'
                            ))
                            tiene_media = True
            except Exception as e:
                logger.warning(f"No se pudo obtener media histórica para río {rio_name}: {e}")
        
        # Aplicar tema moderno
        fig.update_layout(
            height=500,  # Aumentado de 400 a 500 para mejor visualización
            margin=dict(l=20, r=20, t=40, b=20),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Inter, Arial, sans-serif", size=12),
            title_font_size=16,
            xaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128,128,128,0.2)',
                showline=True,
                linewidth=2,
                linecolor='rgba(128,128,128,0.3)',
                title="Fecha"
            ),
            yaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128,128,128,0.2)',
                showline=True,
                linewidth=2,
                linecolor='rgba(128,128,128,0.3)',
                title=y_label
            ),
            showlegend=tiene_media,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        return dbc.Card([
            dbc.CardHeader([
                html.Div([
                    html.Div([
                        html.I(className="bi bi-graph-up-arrow me-2", style={"color": "#667eea"}),
                        html.Strong("Evolución Temporal", style={"fontSize": "1.1rem"})
                    ], className="d-flex align-items-center"),
                ]),
                html.Div([
                    html.P([
                        "📊 ", html.Strong("Línea negra:"), " Aportes reales del río. ",
                    ], className="mb-1 text-muted", style={"fontSize": "0.85rem"}),
                    html.P([
                        "📈 ", html.Strong("Línea punteada coloreada:"), " Media histórica: ",
                        html.Span("🟢 Verde", style={"color": "#28a745", "fontWeight": "bold"}), " (>100%), ",
                        html.Span("🔵 Cyan", style={"color": "#17a2b8", "fontWeight": "bold"}), " (90-100%), ",
                        html.Span("🟡 Amarillo", style={"color": "#ffc107", "fontWeight": "bold"}), " (70-90%), ",
                        html.Span("🔴 Rojo", style={"color": "#dc3545", "fontWeight": "bold"}), " (<70%)."
                    ], className="mb-0 text-muted", style={"fontSize": "0.85rem"}),
                ], className="mt-2")
            ]),
            dbc.CardBody([
                dcc.Graph(figure=fig)
            ], className="p-2")
        ], className="card-modern chart-container")
    else:
        return dbc.Alert("No se pueden crear gráficos con estos datos.", color="warning", className="alert-modern")

def create_bar_chart(data, metric_name):
    """Crear gráfico de líneas moderno por región o río"""
    # Detectar columnas categóricas y numéricas
    cat_cols = [col for col in data.columns if data[col].dtype == 'object']
    num_cols = [col for col in data.columns if data[col].dtype in ['float64', 'int64']]
    
    if not cat_cols or not num_cols:
        return dbc.Alert("No se pueden crear gráficos de líneas con estos datos.", 
                        color="warning", className="alert-modern")
    
    cat_col = cat_cols[0]
    num_col = num_cols[0]
    
    # Si los datos tienen información de región, crear líneas por región
    if 'Region' in data.columns:
        # Agrupar por región y fecha para crear series temporales por región
        if 'Date' in data.columns:
            # Datos diarios por región - series temporales
            fig = px.line(
                data,
                x='Date',
                y='Value', 
                color='Region',
                title="Aportes Energéticos por Región Hidrológica",
                labels={'Value': "Energía (GWh)", 'Date': "Fecha", 'Region': "Región"},
                markers=True,
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            # Asegurar que cada línea tenga información de región para el click
            fig.for_each_trace(lambda t: t.update(legendgroup=t.name, customdata=[t.name] * len(t.x)))
        else:
            # Datos agregados por región - convertir a líneas también
            region_data = data.groupby('Region')[num_col].sum().reset_index()
            region_data = region_data.sort_values(by=num_col, ascending=False)
            
            fig = px.line(
                region_data,
                x='Region',
                y=num_col,
                title="Contribución Total por Región Hidrológica",
                labels={num_col: "Energía (GWh)", 'Region': "Región"},
                markers=True,
                color_discrete_sequence=['#667eea']
            )
    else:
        # Agrupar y ordenar datos de mayor a menor - usar líneas en lugar de barras
        grouped_data = data.groupby(cat_col)[num_col].sum().reset_index()
        grouped_data = grouped_data.sort_values(by=num_col, ascending=False)
        
        fig = px.line(
            grouped_data.head(15),  # Top 15 para mejor visualización
            x=cat_col,
            y=num_col,
            title="Aportes Energéticos por Río",
            labels={num_col: "Energía (GWh)", cat_col: "Río"},
            markers=True,
            color_discrete_sequence=['#667eea']
        )
    
    # Aplicar estilo moderno
    fig.update_layout(
        height=550,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter, Arial, sans-serif", size=12),
        title=dict(
            font_size=16,
            x=0.5,
            xanchor='center',
            font_color='#2d3748'
        ),
        xaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(128,128,128,0.2)',
            showline=True,
            linewidth=2,
            linecolor='rgba(128,128,128,0.3)',
            tickangle=-45
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(128,128,128,0.2)',
            showline=True,
            linewidth=2,
            linecolor='rgba(128,128,128,0.3)'
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Mejorar el estilo para todos los gráficos de líneas
    fig.update_traces(
        marker=dict(size=10, line=dict(width=2, color='white')),
        line=dict(width=4),
        hovertemplate='<b>%{fullData.name}</b><br>Valor: %{y:.2f} GWh<extra></extra>'
    )
    
    chart_title = "Aportes de Energía por Región" if 'Region' in data.columns else "Aportes de Energía por Río"
    
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.I(className="bi bi-graph-up me-2", style={"color": "#667eea"}),
                html.Strong(chart_title, style={"fontSize": "1.2rem"})
            ], className="d-flex align-items-center"),
            html.Small("Haz clic en cualquier punto para ver detalles", className="text-muted")
        ]),
        dbc.CardBody([
            dcc.Graph(id="rio-detail-graph", figure=fig, clear_on_unhover=True)
        ], className="p-2")
    ], className="card-modern chart-container shadow-lg")

def create_latest_value_kpi(data, metric_name):
    """Crear card KPI que muestra el valor más reciente de la serie temporal"""
    if data is None or data.empty:
        return dbc.Alert("No hay datos disponibles", color="warning", className="mb-3")
    
    # Verificar que tengamos las columnas necesarias
    if 'Date' not in data.columns or 'Value' not in data.columns:
        return dbc.Alert("Faltan columnas necesarias", color="warning", className="mb-3")
    
    # Agrupar por fecha y sumar todos los valores
    daily_totals = data.groupby('Date')['Value'].sum().reset_index()
    daily_totals = daily_totals.sort_values('Date')
    
    if daily_totals.empty:
        return dbc.Alert("No hay datos procesados", color="warning", className="mb-3")
    
    # Obtener el valor más reciente
    latest_date = daily_totals['Date'].iloc[-1]
    latest_value = daily_totals['Value'].iloc[-1]
    
    # Formatear fecha
    if hasattr(latest_date, 'strftime'):
        formatted_date = latest_date.strftime('%d/%m/%Y')
    else:
        formatted_date = str(latest_date)
    
    # Formatear valor
    formatted_value = f"{latest_value:,.0f}".replace(",", ".")
    
    # Calcular tendencia si hay datos suficientes
    trend_icon = ""
    trend_color = "#6c757d"
    trend_text = ""
    trend_bg = "#f8f9fa"
    
    if len(daily_totals) >= 2:
        previous_value = daily_totals['Value'].iloc[-2]
        if previous_value != 0:  # Evitar división por cero
            change = latest_value - previous_value
            change_pct = (change / abs(previous_value) * 100)  # Usar valor absoluto para evitar negativos extraños
            
            if change > 0:
                trend_icon = "bi bi-arrow-up-circle-fill"
                trend_color = "#28a745"
                trend_text = f"+{change_pct:.1f}%"
                trend_bg = "#d4edda"
            elif change < 0:
                trend_icon = "bi bi-arrow-down-circle-fill"
                trend_color = "#dc3545"
                trend_text = f"{change_pct:.1f}%"
                trend_bg = "#f8d7da"
            else:
                trend_icon = "bi bi-dash-circle-fill"
                trend_color = "#6c757d"
                trend_text = "0.0%"
                trend_bg = "#e2e3e5"
        else:
            trend_icon = "bi bi-info-circle-fill"
            trend_color = "#17a2b8"
            trend_text = "N/A"
            trend_bg = "#d1ecf1"
    
    return dbc.Card([
        dbc.CardBody([
            # Contenedor principal centrado
            html.Div([
                # Encabezado con ícono
                html.Div([
                    html.I(className="bi bi-lightning-charge-fill me-2", 
                           style={"fontSize": "1.8rem", "color": "#007bff"}),
                    html.H5("Último Registro", className="text-dark mb-0", 
                            style={"fontSize": "1.1rem", "fontWeight": "600"})
                ], className="d-flex align-items-center justify-content-center mb-4"),
                
                # Contenedor principal con valor y tendencia lado a lado
                dbc.Row([
                    dbc.Col([
                        # Valor principal y unidad
                        html.Div([
                            html.H1(f"{formatted_value}", 
                                    className="mb-1", 
                                    style={
                                        "fontWeight": "800", 
                                        "color": "#2d3748", 
                                        "fontSize": "3.5rem",
                                        "lineHeight": "1",
                                        "textAlign": "center"
                                    }),
                            
                            # Unidad centrada
                            html.P("GWh", 
                                   className="text-primary mb-0", 
                                   style={
                                       "fontSize": "1.3rem", 
                                       "fontWeight": "500",
                                       "textAlign": "center"
                                   }),
                        ], className="text-center")
                    ], md=8),
                    
                    dbc.Col([
                        # Indicador de tendencia al lado
                        html.Div([
                            html.Div([
                                html.I(className=trend_icon, 
                                       style={
                                           "fontSize": "2rem", 
                                           "color": trend_color,
                                           "marginBottom": "5px"
                                       }) if trend_icon else None,
                                html.H5(trend_text, 
                                        className="mb-1", 
                                        style={
                                            "color": trend_color, 
                                            "fontWeight": "700",
                                            "fontSize": "1.2rem"
                                        }) if trend_text else None,
                                html.Small("vs anterior",
                                         className="text-muted",
                                         style={"fontSize": "0.75rem"})
                            ], className="text-center p-2 rounded-3",
                               style={
                                   "backgroundColor": trend_bg,
                                   "border": f"2px solid {trend_color}20"
                               })
                        ], className="d-flex align-items-center justify-content-center h-100")
                    ], md=4)
                ], className="mb-3", align="center"),
                
                # Fecha centrada abajo
                html.Div([
                    html.I(className="bi bi-calendar-date me-2", 
                           style={"color": "#6c757d", "fontSize": "1.1rem"}),
                    html.Span(formatted_date, 
                             style={"fontSize": "1rem", "color": "#6c757d"})
                ], className="d-flex align-items-center justify-content-center")
                
            ], className="px-3")
        ], className="py-4 px-4")
    ], className="shadow border-0 mb-4 mx-auto", 
       style={
           "background": "linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%)",
           "borderRadius": "20px",
           "border": "1px solid #e9ecef",
           "maxWidth": "500px",
           "minHeight": "200px"
       })

def get_porcapor_data(fecha_inicio, fecha_fin):
    """Obtener datos de la métrica PorcApor - Aportes % por río"""
    try:
        objetoAPI = get_objetoAPI()
# REMOVED DEBUG:         logger.debug(f"Consultando PorcApor desde {fecha_inicio} hasta {fecha_fin}")
        data, warning = obtener_datos_inteligente('PorcApor', 'Rio', fecha_inicio, fecha_fin)
        if not data.empty:
            # Multiplicar por 100 para convertir a porcentaje
            if 'Value' in data.columns:
                data['Value'] = data['Value'] * 100
# REMOVED DEBUG:             logger.info(f"Datos PorcApor obtenidos: {len(data)} registros")
            return data
        else:
            logger.warning("No se encontraron datos de PorcApor")
            return pd.DataFrame()
    except Exception as e:
# REMOVED DEBUG:         print(f"❌ Error obteniendo datos PorcApor: {e}")
        return pd.DataFrame()

def create_porcapor_kpi(fecha_inicio, fecha_fin, region=None, rio=None):
    """Crear tarjeta KPI específica para la métrica PorcApor (Aportes % por río)
    
    Args:
        fecha_inicio: Fecha de inicio del rango
        fecha_fin: Fecha de fin del rango  
        region: Región para filtrar (opcional)
        rio: Río para filtrar (opcional)
    """
    data = get_porcapor_data(fecha_inicio, fecha_fin)
    
    if data is None or data.empty:
        return dbc.Alert("No hay datos de PorcApor disponibles", color="warning", className="mb-3")
    
    # Verificar que tengamos las columnas necesarias
    if 'Date' not in data.columns or 'Value' not in data.columns:
        return dbc.Alert(f"Faltan columnas necesarias en PorcApor. Columnas disponibles: {list(data.columns)}", color="warning", className="mb-3")
    
    # Filtrar por río específico si se especifica
    if rio and rio != "__ALL__":
        data_filtered = data[data['Name'] == rio]
        if data_filtered.empty:
            return dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.H6("📊 Aportes % por Sistema", className="text-center mb-2"),
                        html.Hr(),
                        html.P(f"No hay datos de participación porcentual para el río {rio} en este período.", 
                               className="text-center text-muted mb-2"),
                        html.P("Este río puede estar temporalmente fuera de operación o en mantenimiento.", 
                               className="text-center text-muted small mb-2"),
                        html.P("💡 Selecciona otro río con datos activos como DESV. BATATAS, DESV. CHIVOR, etc.", 
                               className="text-center text-info small")
                    ])
                ])
            ], className="text-center shadow-sm mb-3")
        title_suffix = f" - {rio}"
    else:
        # Filtrar por región si se especifica y no es "todas las regiones"
        if region and region != "__ALL_REGIONS__":
            # Agregar información de región usando el mapeo RIO_REGION
            region_normalized = region.strip().title()
            rio_region = ensure_rio_region_loaded()
            data['Region'] = data['Name'].map(rio_region) 
            data_filtered = data[data['Region'] == region_normalized]
            if data_filtered.empty:
                return dbc.Alert(f"No hay datos de PorcApor para la región {region_normalized}", color="warning", className="mb-3")
            title_suffix = f" - {region_normalized}"
        else:
            data_filtered = data
            title_suffix = ""
    
    # Agrupar por fecha y calcular promedio de los ríos filtrados
    daily_avg = data_filtered.groupby('Date')['Value'].mean().reset_index()
    daily_avg = daily_avg.sort_values('Date')
    
    if daily_avg.empty:
        return dbc.Alert("No hay datos procesados de PorcApor", color="warning", className="mb-3")
    
    # Obtener el valor más reciente
    latest_date = daily_avg['Date'].iloc[-1]
    latest_value = daily_avg['Value'].iloc[-1]
    formatted_date = pd.to_datetime(latest_date).strftime('%d/%m/%Y')
    
    # Formatear el valor como porcentaje
    formatted_value = f"{latest_value:.1f}"
    
    # Calcular tendencia si hay al menos 2 registros
    if len(daily_avg) >= 2:
        previous_value = daily_avg['Value'].iloc[-2]
        change_percent = ((latest_value - previous_value) / previous_value) * 100
        
        if change_percent > 0:
            trend_icon = "bi bi-arrow-up-circle-fill"
            trend_color = "#28a745"
            trend_text = f"+{change_percent:.1f}%"
            trend_bg = "#d4edda"
        elif change_percent < 0:
            trend_icon = "bi bi-arrow-down-circle-fill"
            trend_color = "#dc3545"
            trend_text = f"{change_percent:.1f}%"
            trend_bg = "#f8d7da"
        else:
            trend_icon = "bi bi-dash-circle-fill"
            trend_color = "#ffc107"
            trend_text = "0.0%"
            trend_bg = "#fff3cd"
    else:
        trend_icon = "bi bi-info-circle-fill"
        trend_color = "#17a2b8"
        trend_text = "N/A"
        trend_bg = "#d1ecf1"

    return dbc.Card([
        dbc.CardBody([
            # Contenedor principal centrado
            html.Div([
                # Encabezado con ícono
                html.Div([
                    html.I(className="bi bi-percent me-2", 
                           style={"fontSize": "1.8rem", "color": "#28a745"}),
                    html.H5(f"Aportes % por Sistema{title_suffix}", className="text-dark mb-0", 
                            style={"fontSize": "1.1rem", "fontWeight": "600"})
                ], className="d-flex align-items-center justify-content-center mb-4"),
                
                # Contenedor principal con valor y tendencia lado a lado
                dbc.Row([
                    dbc.Col([
                        # Valor principal y unidad
                        html.Div([
                            html.H1(f"{formatted_value}", 
                                    className="mb-1", 
                                    style={
                                        "fontWeight": "800", 
                                        "color": "#2d3748", 
                                        "fontSize": "3.5rem",
                                        "lineHeight": "1",
                                        "textAlign": "center"
                                    }),
                            
                            # Unidad centrada
                            html.P("%", 
                                   className="text-success mb-0", 
                                   style={
                                       "fontSize": "1.3rem", 
                                       "fontWeight": "500",
                                       "textAlign": "center"
                                   }),
                        ], className="text-center")
                    ], md=8),
                    
                    dbc.Col([
                        # Indicador de tendencia al lado
                        html.Div([
                            html.Div([
                                html.I(className=trend_icon, 
                                       style={
                                           "fontSize": "2rem", 
                                           "color": trend_color,
                                           "marginBottom": "5px"
                                       }) if trend_icon else None,
                                html.H5(trend_text, 
                                        className="mb-1", 
                                        style={
                                            "color": trend_color, 
                                            "fontWeight": "700",
                                            "fontSize": "1.2rem"
                                        }) if trend_text else None,
                                html.Small("vs anterior",
                                         className="text-muted",
                                         style={"fontSize": "0.75rem"})
                            ], className="text-center p-2 rounded-3",
                               style={
                                   "backgroundColor": trend_bg,
                                   "border": f"2px solid {trend_color}20"
                               })
                        ], className="d-flex align-items-center justify-content-center h-100")
                    ], md=4)
                ], className="mb-3", align="center"),
                
                # Fecha centrada abajo
                html.Div([
                    html.I(className="bi bi-calendar-date me-2", 
                           style={"color": "#6c757d", "fontSize": "1.1rem"}),
                    html.Span(formatted_date, 
                             style={"fontSize": "1rem", "color": "#6c757d"})
                ], className="d-flex align-items-center justify-content-center")
                
            ], className="px-3")
        ], className="py-4 px-4")
    ], className="shadow border-0 mb-4 mx-auto", 
       style={
           "background": "linear-gradient(135deg, #e8f5e8 0%, #f0f8f0 100%)",
           "borderRadius": "20px",
           "border": "1px solid #28a745",
           "maxWidth": "500px",
           "minHeight": "200px"
       })

def create_total_timeline_chart(data, metric_name, region_filter=None, rio_filter=None):
    """Crear gráfico de línea temporal con total nacional/regional/río por día incluyendo media histórica filtrada"""
    if data is None or data.empty:
        return dbc.Alert("No se pueden crear gráficos con estos datos.", 
                        color="warning", className="alert-modern")
    
    # Verificar que tengamos las columnas necesarias
    if 'Date' not in data.columns or 'Value' not in data.columns:
        return dbc.Alert("No se encuentran las columnas necesarias (Date, Value).", 
                        color="warning", className="alert-modern")
    
    # LOGGING: Ver qué datos recibimos ANTES de agrupar
    try:
        logger.info(f"🔍 create_total_timeline_chart recibió {len(data)} registros")
        logger.info(f"🔍 Columnas: {list(data.columns)}")
        logger.info(f"🔍 Fechas únicas: {data['Date'].nunique()}")
        logger.info(f"🔍 Suma total de Value ANTES de agrupar: {data['Value'].sum():.2f} GWh")
    except Exception as log_error:
        logger.warning(f"⚠️ Error en logging: {log_error}")
    
    # Agrupar por fecha y sumar todos los valores
    daily_totals = data.groupby('Date')['Value'].sum().reset_index()
    daily_totals = daily_totals.sort_values('Date')
    
    logger.info(f"🔍 DESPUÉS de agrupar: {len(daily_totals)} fechas, Total: {daily_totals['Value'].sum():.2f} GWh")
    
    # Obtener media histórica y calcular indicador
    tiene_media = False  # ✅ Inicializar antes del try
    media_hist_totals = None  # ✅ Inicializar para evitar NameError fuera del try
    porcentaje_vs_historico = None
    promedio_real = None
    promedio_historico = None
    
    try:
        # ✅ FIX: Convertir a string de forma segura (puede ser datetime o string)
        fecha_min = daily_totals['Date'].min()
        fecha_max = daily_totals['Date'].max()
        
        if hasattr(fecha_min, 'strftime'):
            fecha_inicio = fecha_min.strftime('%Y-%m-%d')
        else:
            fecha_inicio = str(fecha_min)
            
        if hasattr(fecha_max, 'strftime'):
            fecha_fin = fecha_max.strftime('%Y-%m-%d')
        else:
            fecha_fin = str(fecha_max)
        
        logger.debug(f"Consultando AporEnerMediHist desde {fecha_inicio} hasta {fecha_fin}")
        
        # Obtener datos de media histórica de energía por río
        media_hist_data, warning_msg = obtener_datos_inteligente('AporEnerMediHist', 'Rio', fecha_inicio, fecha_fin)
        if warning_msg:
            logger.info(f"⚠️ {warning_msg}")
        
        logger.debug(f"Datos recibidos de AporEnerMediHist: {len(media_hist_data) if media_hist_data is not None else 0} registros")
        if media_hist_data is not None and not media_hist_data.empty:
            logger.debug(f"Columnas disponibles: {media_hist_data.columns.tolist()}")
            logger.debug(f"Primeras 3 filas completas:")
            print(media_hist_data.head(3))
            logger.debug(f"Valores de muestra ANTES de conversión: {media_hist_data['Value'].head(3).tolist()}")
            logger.debug(f"Rango de valores: min={media_hist_data['Value'].min()}, max={media_hist_data['Value'].max()}")
            logger.debug(f"Nombres de ríos únicos: {media_hist_data['Name'].unique()[:5].tolist() if 'Name' in media_hist_data.columns else 'Sin columna Name'}")
        
        if media_hist_data is not None and not media_hist_data.empty and 'Value' in media_hist_data.columns:
            # ✅ La conversión kWh→GWh ahora se hace automáticamente en fetch_metric_data()
            # Los valores ya vienen en GWh desde el cache
            valor_promedio = media_hist_data['Value'].mean()
            logger.debug(f"AporEnerMediHist promedio: {valor_promedio:.2f} GWh")
            logger.debug(f"Valores de muestra: {media_hist_data['Value'].head(3).tolist()}")
            
            # ✅ FIX: Filtrar registros con Name NULL ANTES de intentar mapear regiones
            if 'Name' in media_hist_data.columns:
                registros_antes = len(media_hist_data)
                media_hist_data = media_hist_data[media_hist_data['Name'].notna()]
                registros_despues = len(media_hist_data)
                if registros_antes != registros_despues:
                    logger.info(f"🔍 Filtrados {registros_antes - registros_despues} registros con Name=NULL (quedan {registros_despues})")
            
            # FILTRAR por región o río si se especifica
            if region_filter:
                # Agregar mapeo de región
                rio_region = ensure_rio_region_loaded()
                # CORRECCIÓN: Normalizar nombres ANTES de mapear
                media_hist_data['Name_Upper'] = media_hist_data['Name'].str.strip().str.upper()
                media_hist_data['Region'] = media_hist_data['Name_Upper'].map(rio_region)
                
                # ✅ FIX: Normalizar region_filter para que coincida con formato de RIO_REGION (Title Case)
                region_filter_normalized = region_filter.strip().title() if isinstance(region_filter, str) else region_filter
                
                # Filtrar por región
                antes_filtro = len(media_hist_data)
                logger.info(f"🔍 ANTES filtro región '{region_filter}' (normalizado: '{region_filter_normalized}'): {antes_filtro} registros")
                logger.info(f"🔍 Regiones disponibles: {sorted(media_hist_data['Region'].dropna().unique())}")
                media_hist_data = media_hist_data[media_hist_data['Region'] == region_filter_normalized]
                logger.info(f"🔍 DESPUÉS filtro región '{region_filter_normalized}': {len(media_hist_data)} registros")
                if media_hist_data.empty:
                    logger.error(f"❌ ERROR: No hay datos históricos después del filtro para región '{region_filter_normalized}'")
                    logger.error(f"   Regiones disponibles eran: {sorted(media_hist_data['Region'].dropna().unique()) if 'Region' in media_hist_data.columns else 'N/A'}")
            elif rio_filter:
                # Filtrar por río específico
                antes_filtro = len(media_hist_data)
                media_hist_data = media_hist_data[media_hist_data['Name'] == rio_filter]
                logger.debug(f"Media histórica filtrada por río '{rio_filter}': {antes_filtro} → {len(media_hist_data)} registros")
            
            # Agrupar por fecha y sumar
            if not media_hist_data.empty:
                media_hist_totals = media_hist_data.groupby('Date')['Value'].sum().reset_index()
                media_hist_totals = media_hist_totals.sort_values('Date')
                tiene_media = True
                
                logger.info(f"✅ Media histórica agregada por fecha: {len(media_hist_totals)} días")
                logger.info(f"✅ tiene_media = {tiene_media} - LA LÍNEA DEBERÍA APARECER")
                logger.debug(f"Valores agregados de muestra: {media_hist_totals['Value'].head(3).tolist()}")
                logger.debug(f"Total agregado: min={media_hist_totals['Value'].min():.2f}, max={media_hist_totals['Value'].max():.2f}, suma={media_hist_totals['Value'].sum():.2f} GWh")
                
                # CORRECCIÓN: Calcular porcentaje con SUMA TOTAL del período (no promedio)
                total_real = daily_totals['Value'].sum()  # SUMA TOTAL
                total_historico = media_hist_totals['Value'].sum()  # SUMA TOTAL
                
                # ✅ FIX: Convertir a float explícitamente para evitar error de formato
                total_real = float(total_real)
                total_historico = float(total_historico)
                
                logger.info(f"📊 CÁLCULO PORCENTAJE: Real={total_real:.2f} GWh, Histórico={total_historico:.2f} GWh")
                
                if total_historico > 0:
                    # ✅ FIX CRÍTICO: Convertir a float Python nativo inmediatamente
                    porcentaje_vs_historico = float((total_real / total_historico) * 100)
                    logger.info(f"✅ Porcentaje calculado: {porcentaje_vs_historico:.1f}%")
                else:
                    logger.error(f"❌ ERROR: total_historico = 0, no se puede calcular porcentaje")
                    porcentaje_vs_historico = None
            else:
                tiene_media = False
                logger.warning(f"No hay datos después del filtrado")
        else:
            tiene_media = False
            logger.warning(f"No se recibieron datos válidos de AporEnerMediHist")
    except Exception as e:
        logger.error(f"❌ ERROR obteniendo media histórica: {e}")
        logger.error(f"   Tipo de error: {type(e).__name__}")
        logger.error(f"   Detalles: {str(e)}")
        import traceback
        traceback.print_exc()
        tiene_media = False
        # Mostrar mensaje más visible en consola
        print(f"\n⚠️ ADVERTENCIA: No se pudo cargar línea de media histórica")
        print(f"   Razón: {str(e)}")
        print(f"   La gráfica se mostrará solo con datos reales\n")
    
    # Crear figura base
    from plotly.subplots import make_subplots
    px, go = get_plotly_modules()
    
    fig = go.Figure()
    
    # Agregar línea de valores reales (negra)
    fig.add_trace(go.Scatter(
        x=daily_totals['Date'],
        y=daily_totals['Value'],
        mode='lines+markers',
        name='Aportes Reales',
        line=dict(width=3, color='black'),
        marker=dict(size=8, color='black', line=dict(width=2, color='white')),
        hovertemplate=(
            '<b>📅 Fecha:</b> %{x|%d/%m/%Y}<br>'
            '<b>⚡ Aportes Reales:</b> %{y:.2f} GWh<br>'
            '<b>━━━━━━━━━━━━━━━━</b><br>'
            '<i>Pasa el cursor sobre la línea histórica<br>para ver la comparación detallada</i>'
            '<extra></extra>'
        )
    ))
    
    # Agregar línea de media histórica con colores dinámicos según estado hidrológico
    logger.info(f"🎨 DIBUJANDO GRÁFICA: tiene_media={tiene_media}, media_hist_totals={'EXISTE' if media_hist_totals is not None else 'NULL'}")
    if tiene_media and media_hist_totals is not None:
        logger.info(f"✅ INICIANDO DIBUJO de línea de media histórica con {len(media_hist_totals)} puntos")
        # Combinar datos reales e históricos por fecha para comparación
        merged_data = daily_totals.merge(
            media_hist_totals, 
            on='Date', 
            how='inner', 
            suffixes=('_real', '_hist')
        )
        logger.info(f"🔗 Datos combinados: {len(merged_data)} fechas coincidentes")
        
        if not merged_data.empty:
            # Calcular porcentaje: (real / histórico) * 100
            merged_data['porcentaje'] = (merged_data['Value_real'] / merged_data['Value_hist']) * 100
            
            # Crear segmentos de línea coloreados según estado
            # Verde: > 100% (húmedo), Cyan: 90-100% (normal), Naranja: 70-90% (seco moderado), Rojo: < 70% (muy seco)
            for i in range(len(merged_data) - 1):
                # ✅ FIX: Convertir a float explícitamente para evitar errores de formato
                porcentaje = float(merged_data.iloc[i]['porcentaje'])
                valor_real = float(merged_data.iloc[i]['Value_real'])
                valor_hist = float(merged_data.iloc[i]['Value_hist'])
                
                # Calcular variación porcentual (formato estándar)
                variacion = float(porcentaje - 100)
                signo = '+' if variacion >= 0 else ''
                
                # Determinar color según porcentaje
                if porcentaje >= 100:
                    color = '#28a745'  # Verde - Húmedo
                    estado = 'Húmedo'
                    emoji = '💧'
                elif porcentaje >= 90:
                    color = '#17a2b8'  # Cyan - Normal
                    estado = 'Normal'
                    emoji = '✓'
                elif porcentaje >= 70:
                    color = '#ffc107'  # Amarillo/Naranja - Moderadamente seco
                    estado = 'Moderadamente seco'
                    emoji = '⚠️'
                else:
                    color = '#dc3545'  # Rojo - Muy seco
                    estado = 'Muy seco'
                    emoji = '🔴'
                
                # Tooltip mejorado con formato estándar de variación porcentual
                hover_text = (
                    f'<b>📅 Fecha:</b> %{{x|%d/%m/%Y}}<br>'
                    f'<b>📊 Media Histórica:</b> %{{y:.2f}} GWh<br>'
                    f'<b>⚡ Aportes Reales:</b> {valor_real:.2f} GWh<br>'
                    f'<b>━━━━━━━━━━━━━━━━</b><br>'
                    f'<b>{emoji} Estado:</b> {estado}<br>'
                    f'<b>📈 Variación:</b> {signo}{variacion:.1f}% vs histórico<br>'
                    f'<b>📐 Fórmula:</b> ({valor_real:.1f} / {valor_hist:.1f}) × 100 = {porcentaje:.1f}%<br>'
                    f'<b>🧮 Diferencia:</b> {porcentaje:.1f}% - 100% = {signo}{variacion:.1f}%'
                    f'<extra></extra>'
                )
                
                # Agregar segmento de línea
                fig.add_trace(go.Scatter(
                    x=merged_data['Date'].iloc[i:i+2],
                    y=merged_data['Value_hist'].iloc[i:i+2],
                    mode='lines',
                    name='Media Histórica' if i == 0 else None,  # Solo mostrar leyenda una vez
                    showlegend=(i == 0),
                    line=dict(width=3, color=color, dash='dash'),
                    hovertemplate=hover_text,
                    legendgroup='media_historica'
                ))
        else:
            # Fallback: línea azul simple si no hay datos para comparar
            fig.add_trace(go.Scatter(
                x=media_hist_totals['Date'],
                y=media_hist_totals['Value'],
                mode='lines',
                name='Media Histórica',
                line=dict(width=3, color='#1e90ff', dash='dash'),
                hovertemplate='<b>Fecha:</b> %{x}<br><b>Media Histórica:</b> %{y:.2f} GWh<extra></extra>'
            ))
    else:
        logger.warning(f"⚠️ NO SE DIBUJÓ línea de media histórica: tiene_media={tiene_media}, media_hist_totals={'None' if media_hist_totals is None else f'{len(media_hist_totals)} registros'}")
    
    # Determinar título dinámico según filtros
    if rio_filter:
        titulo_grafica = f"Aportes de Energía - Río {rio_filter}"
    elif region_filter:
        titulo_grafica = f"Aportes de Energía - Región {region_filter}"
    else:
        titulo_grafica = "Total Nacional de Aportes de Energía por Día"
    
    # Estilo moderno
    fig.update_layout(
        height=500,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter, Arial, sans-serif", size=12),
        title=dict(
            text=titulo_grafica,
            font_size=16,
            x=0.5,
            xanchor='center',
            font_color='#2d3748'
        ),
        xaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(128,128,128,0.2)',
            showline=True,
            linewidth=2,
            linecolor='rgba(128,128,128,0.3)',
            title="Fecha"
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(128,128,128,0.2)',
            showline=True,
            linewidth=2,
            linecolor='rgba(128,128,128,0.3)',
            title="Energía (GWh)"
        ),
        showlegend=tiene_media,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Crear indicador visual de comparación
    indicador_badge = None
    if porcentaje_vs_historico is not None:
        # ✅ FIX: Asegurar que porcentaje_vs_historico sea float
        try:
            porcentaje_vs_historico = float(porcentaje_vs_historico)
        except (ValueError, TypeError):
            logger.error(f"❌ No se pudo convertir porcentaje_vs_historico a float: {porcentaje_vs_historico}")
            porcentaje_vs_historico = None
    
    if porcentaje_vs_historico is not None:
        # Determinar color y emoji según el porcentaje
        if porcentaje_vs_historico >= 100:
            # Por encima del histórico (húmedo)
            color_badge = "success"
            icono = "💧"
            diferencia = float(porcentaje_vs_historico - 100)
            texto_badge = f"{icono} +{diferencia:.1f}% vs Histórico"
            texto_contexto = "Condiciones más húmedas que el promedio histórico"
        elif porcentaje_vs_historico >= 90:
            # Cerca del histórico (normal)
            color_badge = "info"
            icono = "✓"
            diferencia = float(100 - porcentaje_vs_historico)
            texto_badge = f"{icono} -{diferencia:.1f}% vs Histórico"
            texto_contexto = "Condiciones cercanas al promedio histórico"
        elif porcentaje_vs_historico >= 70:
            # Moderadamente bajo (alerta)
            color_badge = "warning"
            icono = "⚠️"
            diferencia = float(100 - porcentaje_vs_historico)
            texto_badge = f"{icono} -{diferencia:.1f}% vs Histórico"
            texto_contexto = "Condiciones más secas que el promedio histórico"
        else:
            # Muy bajo (crítico)
            color_badge = "danger"
            icono = "🔴"
            diferencia = float(100 - porcentaje_vs_historico)
            texto_badge = f"{icono} -{diferencia:.1f}% vs Histórico"
            texto_contexto = "Condiciones significativamente más secas que el histórico"
        
        indicador_badge = html.Div([
            dbc.Badge(
                texto_badge,
                color=color_badge,
                className="me-2",
                style={"fontSize": "0.9rem", "fontWeight": "600"}
            ),
            html.Small(texto_contexto, className="text-muted", style={"fontSize": "0.85rem"})
        ], className="d-flex align-items-center mt-2")
    
    # Determinar título del header según filtro
    if rio_filter:
        titulo_header = f"Río {rio_filter}"
    elif region_filter:
        titulo_header = f"Región {region_filter}"
    else:
        titulo_header = "Total Nacional por Día"
    
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.Div([
                    html.I(className="bi bi-graph-up me-2", style={"color": "#000"}),
                    html.Strong(titulo_header, style={"fontSize": "1.2rem"})
                ], className="d-flex align-items-center"),
                indicador_badge if indicador_badge else None,
            ])
        ]),
        dbc.CardBody([
            dcc.Graph(id="total-timeline-graph", figure=fig, clear_on_unhover=True)
        ], className="p-2")
    ], className="card-modern chart-container shadow-lg")
# Callback para mostrar el modal con la tabla diaria al hacer click en un punto de la línea
@callback(
    [Output("modal-rio-table", "is_open"), Output("modal-table-content", "children"), 
     Output("modal-title-dynamic", "children"), Output("modal-description", "children")],
    [Input("total-timeline-graph", "clickData"), Input("modal-rio-table", "is_open")],
    [State("region-data-store", "data")],
    prevent_initial_call=True
)
def show_modal_table(timeline_clickData, is_open, region_data):
    ctx = dash.callback_context
    
    logger.debug(f"CALLBACK EJECUTADO! Triggered: {[prop['prop_id'] for prop in ctx.triggered]}")
    logger.debug(f"Timeline click data: {timeline_clickData}")
    
    # Determinar qué fue clicado
    clickData = None
    graph_type = None
    
    if ctx.triggered:
        trigger_id = ctx.triggered[0]["prop_id"]
        
        if trigger_id.startswith("total-timeline-graph") and timeline_clickData:
            clickData = timeline_clickData
            graph_type = "timeline"
            logger.debug(f"Click detected! clickData: {clickData}")
        elif trigger_id.startswith("modal-rio-table"):
            return False, None, "", ""
    
    # Si se hace click en un punto del timeline, mostrar el modal con la tabla
    if clickData and graph_type == "timeline":
        point_data = clickData["points"][0]
        
        # Detectar en qué línea/curva se hizo clic
        curve_number = point_data.get('curveNumber', 0)
        trace_name = point_data.get('fullData', {}).get('name', 'Aportes Reales')
        
        logger.debug(f"Curva clickeada: {curve_number}, Nombre: {trace_name}")
        
        # Si se hizo clic en la Media Histórica (curva 1)
        if curve_number == 1 or 'Media Histórica' in str(trace_name):
            logger.debug("Click en MEDIA HISTÓRICA detectado")
            
            # Obtener la fecha clicada
            selected_date = point_data['x']
            total_value = point_data['y']
            
            # Obtener datos de media histórica
            try:
                # Necesitamos obtener la media histórica del backend
                objetoAPI = get_objetoAPI()
                
                # Obtener el rango de fechas del store de datos
                df_store = pd.DataFrame(region_data) if region_data else pd.DataFrame()
                if not df_store.empty:
                    fecha_inicio = df_store['Date'].min()
                    fecha_fin = df_store['Date'].max()
                    
                    if isinstance(fecha_inicio, str):
                        fecha_inicio_str = fecha_inicio
                    else:
                        fecha_inicio_str = fecha_inicio.strftime('%Y-%m-%d')
                    
                    if isinstance(fecha_fin, str):
                        fecha_fin_str = fecha_fin
                    else:
                        fecha_fin_str = fecha_fin.strftime('%Y-%m-%d')
                    
                    # Obtener media histórica
                    media_hist_data, _ = obtener_datos_inteligente('AporEnerMediHist', 'Rio', fecha_inicio_str, fecha_fin_str)
                    
                    if media_hist_data is not None and not media_hist_data.empty:
                        # ⚠️ NO convertir - fetch_metric_data YA convierte a GWh automáticamente en _xm.py
                        
                        # Agregar información de región
                        rio_region = ensure_rio_region_loaded()
                        media_hist_data['Region'] = media_hist_data['Name'].map(rio_region)
                        
                        # Filtrar por la fecha seleccionada
                        selected_date_dt = pd.to_datetime(selected_date)
                        media_hist_data['Date'] = pd.to_datetime(media_hist_data['Date'])
                        df_date = media_hist_data[media_hist_data['Date'] == selected_date_dt].copy()
                        
                        if not df_date.empty:
                            # Agrupar por región
                            region_summary = df_date.groupby('Region')['Value'].sum().reset_index()
                            region_summary = region_summary.sort_values('Value', ascending=False)
                            region_summary = region_summary.rename(columns={'Region': 'Región', 'Value': 'Energía (GWh)'})
                            
                            # Calcular participación porcentual
                            total = region_summary['Energía (GWh)'].sum()
                            
                            if total > 0:
                                region_summary['Participación (%)'] = (region_summary['Energía (GWh)'] / total * 100).round(2)
                                diferencia = 100 - region_summary['Participación (%)'].sum()
                                if abs(diferencia) > 0.001:
                                    idx_max = region_summary['Participación (%)'].idxmax()
                                    region_summary.loc[idx_max, 'Participación (%)'] += diferencia
                                    region_summary['Participación (%)'] = region_summary['Participación (%)'].round(2)
                            else:
                                region_summary['Participación (%)'] = 0
                            
                            # Formatear números
                            region_summary['Energía (GWh)'] = region_summary['Energía (GWh)'].apply(format_number)
                            
                            # Agregar fila total
                            total_row = {
                                'Región': 'TOTAL',
                                'Energía (GWh)': format_number(total),
                                'Participación (%)': '100.0%'
                            }
                            
                            data_with_total = region_summary.to_dict('records') + [total_row]
                            
                            # Crear tabla
                            table = dash_table.DataTable(
                                data=data_with_total,
                                columns=[
                                    {"name": "Región", "id": "Región"},
                                    {"name": "Energía (GWh)", "id": "Energía (GWh)"},
                                    {"name": "Participación (%)", "id": "Participación (%)"}
                                ],
                                style_cell={'textAlign': 'left', 'padding': '8px', 'fontFamily': 'Inter, Arial', 'fontSize': 14},
                                style_header={'backgroundColor': '#1e90ff', 'color': 'white', 'fontWeight': 'bold'},
                                style_data={'backgroundColor': '#f0f8ff'},
                                style_data_conditional=[
                                    {
                                        'if': {'filter_query': '{Región} = "TOTAL"'},
                                        'backgroundColor': '#1e90ff',
                                        'color': 'white',
                                        'fontWeight': 'bold'
                                    }
                                ],
                                page_action="none",
                                export_format="xlsx",
                                export_headers="display"
                            )
                            
                            formatted_date = format_date(selected_date)
                            total_regions = len(region_summary)
                            title = f"📘 Media Histórica del {formatted_date} - Total Nacional: {format_number(total_value)} GWh"
                            description = f"Detalle de media histórica por región hidrológica para el día {formatted_date}. Se muestran los aportes energéticos históricos promedio de {total_regions} regiones, con su respectiva participación porcentual sobre el total nacional de {format_number(total_value)} GWh."
                            
                            return True, table, title, description
                        
            except Exception as e:
                print(f"❌ Error obteniendo media histórica: {e}")
                import traceback
                traceback.print_exc()
            
            return False, None, "Error", "No se pudieron obtener los datos de media histórica."
        
        # Si se hizo clic en Aportes Reales (curva 0) - código original
        df = pd.DataFrame(region_data) if region_data else pd.DataFrame()
# REMOVED DEBUG:         logger.debug(f"DEBUG: region_data recibido: {type(region_data)}, length: {len(region_data) if region_data else 'None'}")
        logger.debug(f"DataFrame creado - shape: {df.shape}, columns: {df.columns.tolist() if not df.empty else 'DataFrame vacío'}")
        
        if df.empty:
# REMOVED DEBUG:             print(f"❌ DEBUG: DataFrame está vacío - retornando mensaje de error")
            return False, None, "Sin datos", "No hay información disponible para mostrar."
        
        # Obtener la fecha clicada
        selected_date = point_data['x']
        total_value = point_data['y']
        logger.debug(f"DEBUG: Fecha seleccionada: {selected_date}, Total: {total_value}")
        logger.debug(f"DEBUG: Tipo de fecha seleccionada: {type(selected_date)}")
        
        # Ver qué fechas están disponibles en el DataFrame
        unique_dates = df['Date'].unique()[:10]  # Primeras 10 fechas únicas
        logger.debug(f"Primeras fechas disponibles en DataFrame: {unique_dates}")
        logger.debug(f"Tipo de fechas en DataFrame: {type(df['Date'].iloc[0]) if not df.empty else 'N/A'}")
        
        # Filtrar datos de esa fecha específica
        df_date = df[df['Date'] == selected_date].copy()
        logger.debug(f"Datos filtrados por fecha - shape: {df_date.shape}")
        
        # Si no hay datos, intentar convertir la fecha a diferentes formatos
        if df_date.empty:
            logger.debug(f" Intentando conversiones de fecha...")
            # Intentar convertir la fecha seleccionada a datetime
            try:
                from datetime import datetime
                if isinstance(selected_date, str):
                    selected_date_dt = pd.to_datetime(selected_date)
                    logger.debug(f" Fecha convertida a datetime: {selected_date_dt}")
                    # Intentar filtrar con la fecha convertida
                    df_date = df[df['Date'] == selected_date_dt].copy()
                    logger.debug(f" Datos filtrados con fecha convertida - shape: {df_date.shape}")
                
                # Si aún no hay datos, intentar convertir las fechas del DataFrame
                if df_date.empty:
                    logger.debug(f" Convirtiendo fechas del DataFrame...")
                    df['Date'] = pd.to_datetime(df['Date'])
                    df_date = df[df['Date'] == selected_date_dt].copy()
                    logger.debug(f" Datos filtrados después de conversión DF - shape: {df_date.shape}")
                    
            except Exception as e:
                logger.error(f"Error en conversión de fechas: {e}")
                pass
        
# REMOVED DEBUG:         logger.debug(f"DEBUG: Primeras filas de df_date: {df_date.head(3).to_dict() if not df_date.empty else 'No hay datos'}")
        
        if df_date.empty:
# REMOVED DEBUG:             print(f"❌ DEBUG: No hay datos para la fecha {selected_date}")
            return False, None, f"Sin datos para {selected_date}", f"No se encontraron datos para la fecha {selected_date}."
        
        # Agrupar por región para esa fecha
        region_summary = df_date.groupby('Region')['Value'].sum().reset_index()
        region_summary = region_summary.sort_values('Value', ascending=False)
        region_summary = region_summary.rename(columns={'Region': 'Región', 'Value': 'Energía (GWh)'})
# REMOVED DEBUG:         logger.debug(f"DEBUG: region_summary creado - shape: {region_summary.shape}")
        logger.debug(f"region_summary contenido: {region_summary.to_dict() if not region_summary.empty else 'Vacío'}")
        
        # Calcular participación porcentual
        total = region_summary['Energía (GWh)'].sum()
        logger.debug(f"Total calculado: {total}")
        
        if total > 0:
            region_summary['Participación (%)'] = (region_summary['Energía (GWh)'] / total * 100).round(2)
            # Ajustar para que sume exactamente 100%
            diferencia = 100 - region_summary['Participación (%)'].sum()
            if abs(diferencia) > 0.001:
                idx_max = region_summary['Participación (%)'].idxmax()
                region_summary.loc[idx_max, 'Participación (%)'] += diferencia
                region_summary['Participación (%)'] = region_summary['Participación (%)'].round(2)
        else:
            region_summary['Participación (%)'] = 0
        
        # Formatear números
        region_summary['Energía (GWh)'] = region_summary['Energía (GWh)'].apply(format_number)
        
        # Agregar fila total
        total_row = {
            'Región': 'TOTAL',
            'Energía (GWh)': format_number(total),
            'Participación (%)': '100.0%'
        }
        
        data_with_total = region_summary.to_dict('records') + [total_row]
        
        # Crear tabla
        table = dash_table.DataTable(
            data=data_with_total,
            columns=[
                {"name": "Región", "id": "Región"},
                {"name": "Energía (GWh)", "id": "Energía (GWh)"},
                {"name": "Participación (%)", "id": "Participación (%)"}
            ],
            style_cell={'textAlign': 'left', 'padding': '8px', 'fontFamily': 'Inter, Arial', 'fontSize': 14},
            style_header={'backgroundColor': '#1e40af', 'color': 'white', 'fontWeight': 'bold'},
            style_data={'backgroundColor': '#f8f9fa'},
            style_data_conditional=[
                {
                    'if': {'filter_query': '{Región} = "TOTAL"'},
                    'backgroundColor': '#2563eb',
                    'color': 'white',
                    'fontWeight': 'bold'
                }
            ],
            page_action="none",
            export_format="xlsx",
            export_headers="display"
        )
        
        # Crear título y descripción
        formatted_date = format_date(selected_date)
        total_regions = len(region_summary) - 1 if len(region_summary) > 0 else 0
        title = f"⚡ Detalles del {formatted_date} - Total Nacional: {format_number(total_value)} GWh"
        description = f"Detalle por región hidrológica para el día {formatted_date}. Se muestran los aportes de energía de {total_regions} regiones que registraron actividad en esta fecha, con su respectiva participación porcentual sobre el total nacional de {format_number(total_value)} GWh."
        
# REMOVED DEBUG:         logger.info(f"DEBUG: Título: {title}")
# REMOVED DEBUG:         logger.info(f"DEBUG: Descripción: {description}")
# REMOVED DEBUG:         logger.info(f"DEBUG: Retornando modal abierto con tabla de {len(data_with_total)} filas")
        
        return True, table, title, description
    
    # Si se cierra el modal
    elif ctx.triggered and ctx.triggered[0]["prop_id"].startswith("modal-rio-table"):
        return False, None, "", ""
    
    # Por defecto, modal cerrado
# REMOVED DEBUG:     logger.warning(f"DEBUG: No se detectó ningún click válido - modal cerrado por defecto")
    return False, None, "", ""

def create_stats_summary(data):
    """Crear resumen estadístico"""
    numeric_data = data.select_dtypes(include=['float64', 'int64'])
    
    if numeric_data.empty:
        return dbc.Alert("No hay datos numéricos para análisis estadístico.", color="warning")
    
    stats = numeric_data.describe()
    
    return dbc.Card([
        dbc.CardHeader([
            html.H6([
                html.I(className="bi bi-calculator me-2"),
                "Resumen Estadístico"
            ], className="mb-0")
        ]),
        dbc.CardBody([
            dash_table.DataTable(
                data=stats.round(2).reset_index().to_dict('records'),
                columns=[{"name": i, "id": i} for i in stats.reset_index().columns],
                style_cell={
                    'textAlign': 'center',
                    'padding': '10px',
                    'fontFamily': 'Arial'
                },
                style_header={
                    'backgroundColor': '#3498db',
                    'color': 'white',
                    'fontWeight': 'bold'
                },
                style_data={'backgroundColor': '#f8f9fa'}
            )
        ])
    ], className="mt-3")

# === FUNCIONES PARA TABLAS FILTRADAS POR REGIÓN CON SEMÁFORO ===

def create_region_filtered_participacion_table(region, start_date, end_date):
    """
    Crea una tabla de participación porcentual filtrada por región específica,
    incluyendo el sistema de semáforo de riesgo.
    """
    try:
# REMOVED DEBUG:         logger.debug(f"DEBUG PARTICIPACIÓN: Iniciando para región={region}, fechas={start_date} a {end_date}")
        
        # Obtener datos de embalses filtrados por región
        df_embalses = get_embalses_capacidad(region, start_date, end_date)
# REMOVED DEBUG:         logger.debug(f"DEBUG PARTICIPACIÓN: get_embalses_capacidad retornó {len(df_embalses)} filas")
# REMOVED DEBUG:         logger.debug(f"DEBUG PARTICIPACIÓN: Embalses encontrados: {df_embalses['Embalse'].tolist() if not df_embalses.empty else 'NINGUNO'}")
        
        if df_embalses.empty:
# REMOVED DEBUG:             print(f"❌ ERROR PARTICIPACIÓN: No hay datos para región {region}")
            return html.Div("No hay datos disponibles para esta región.", className="text-center text-muted")
        
        # Calcular participación porcentual
        df_participacion = get_participacion_embalses(df_embalses)
# REMOVED DEBUG:         logger.debug(f"DEBUG PARTICIPACIÓN: get_participacion_embalses retornó {len(df_participacion)} filas")
        
        # Crear datos para la tabla con semáforo
        table_data = []
        for _, row in df_participacion.iterrows():
            if row['Embalse'] == 'TOTAL':
                continue  # Saltamos el total para procesarlo al final
            
            embalse_name = row['Embalse']
            participacion_valor = row['Participación (%)']
            
            # Manejar tanto valores numéricos como strings con formato
            if isinstance(participacion_valor, str) and '%' in participacion_valor:
                participacion_num = float(participacion_valor.replace('%', ''))
                participacion_str = participacion_valor
            else:
                participacion_num = float(participacion_valor)
                participacion_str = f"{participacion_num:.2f}%"
            
            # Obtener volumen útil del embalse
            embalse_data = df_embalses[df_embalses['Embalse'] == embalse_name]
            volumen_util_raw = embalse_data['Volumen Útil (%)'].iloc[0] if not embalse_data.empty else 0
            
            # Convertir volumen_util a número (no reformatear si ya es string)
            if volumen_util_raw is None or (isinstance(volumen_util_raw, str) and volumen_util_raw == 'N/D'):
                volumen_util = 0
            elif isinstance(volumen_util_raw, str):
                # Si ya es string con %, extraer solo el número para cálculos de riesgo
                try:
                    volumen_util = float(volumen_util_raw.replace('%', '').replace(',', '.').strip())
                except (ValueError, AttributeError):
                    volumen_util = 0
            elif pd.isna(volumen_util_raw):
                volumen_util = 0
            else:
                volumen_util = float(volumen_util_raw)
            
            # Clasificar riesgo
            nivel_riesgo = clasificar_riesgo_embalse(participacion_num, volumen_util)
            estilo_riesgo = obtener_estilo_riesgo(nivel_riesgo)
            
# REMOVED DEBUG:             logger.info(f"SEMÁFORO REGIÓN {region}: {embalse_name} - Participación={participacion_num}%, Volumen={volumen_util}%")
# REMOVED DEBUG:             logger.info(f"RESULTADO SEMÁFORO REGIÓN {region}: {embalse_name} - Riesgo: {nivel_riesgo}")
            
            table_data.append({
                'Embalse': embalse_name,
                'Participación (%)': participacion_str,
                'Riesgo': "🔴" if nivel_riesgo == "high" else "🟡" if nivel_riesgo == "medium" else "🟢"
            })
        
        # Agregar fila TOTAL
        total_row = df_participacion[df_participacion['Embalse'] == 'TOTAL']
        if not total_row.empty:
            total_participacion = total_row['Participación (%)'].iloc[0]
            if isinstance(total_participacion, str) and '%' in total_participacion:
                total_str = total_participacion
            else:
                total_str = f"{float(total_participacion):.2f}%"
            
            table_data.append({
                'Embalse': 'TOTAL',
                'Participación (%)': total_str,
                'Riesgo': "⚡"  # Icono especial para el total
            })
        
# REMOVED DEBUG:         logger.debug(f"DEBUG PARTICIPACIÓN: Datos finales de tabla: {len(table_data)} filas")
        
        # Crear DataTable con semáforo
        return dash_table.DataTable(
            data=table_data,
            columns=[
                {"name": "Embalse", "id": "Embalse"},
                {"name": "Participación (%)", "id": "Participación (%)"},
                {"name": "🚦 Riesgo", "id": "Riesgo"}
            ],
            style_cell={'textAlign': 'left', 'padding': '8px', 'fontFamily': 'Inter, Arial', 'fontSize': 13},
            style_header={'backgroundColor': '#e3e3e3', 'fontWeight': 'bold'},
            style_data={'backgroundColor': '#f8f8f8'},
            style_data_conditional=[
                # Estilos de semáforo con pictogramas
                {
                    'if': {'filter_query': '{Riesgo} = 🔴'},
                    'backgroundColor': '#ffebee',
                    'color': '#c62828',
                    'fontWeight': 'bold',
                    'textAlign': 'center'
                },
                {
                    'if': {'filter_query': '{Riesgo} = 🟡'},
                    'backgroundColor': '#fff8e1',
                    'color': '#f57c00',
                    'fontWeight': 'bold',
                    'textAlign': 'center'
                },
                {
                    'if': {'filter_query': '{Riesgo} = 🟢'},
                    'backgroundColor': '#e8f5e8',
                    'color': '#2e7d32',
                    'fontWeight': 'bold',
                    'textAlign': 'center'
                },
                # Estilo para fila TOTAL
                {
                    'if': {'filter_query': '{Embalse} = "TOTAL"'},
                    'backgroundColor': '#007bff',
                    'color': 'white',
                    'fontWeight': 'bold'
                }
            ],
            page_action="none",
            export_format="xlsx",
            export_headers="display"
        )
        
    except Exception as e:
        logger.error(f"❌ Error en create_region_filtered_participacion_table: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        return html.Div(f"Error al cargar los datos: {str(e)}", className="text-center text-danger")

def create_region_filtered_capacidad_table(region, start_date, end_date):
    """
    Crea una tabla de capacidad útil filtrada por región específica,
    incluyendo el sistema de semáforo de riesgo.
    """
    try:
        # Obtener datos de embalses filtrados por región
        df_embalses = get_embalses_capacidad(region, start_date, end_date)
        
        if df_embalses.empty:
            return html.Div("No hay datos disponibles para esta región.", className="text-center text-muted")
        
        # Calcular participación para el semáforo
        df_participacion = get_participacion_embalses(df_embalses)
        
        # Crear datos para la tabla con semáforo
        table_data = []
        
        for _, row in df_embalses.iterrows():
            embalse_name = row['Embalse']
            capacidad = row['Capacidad_GWh_Internal']  # Solo para cálculos internos
            volumen_util_raw = row['Volumen Útil (%)']
            
            # Convertir volumen_util a número y preservar formato original si ya está formateado
            volumen_util_formatted = None
            if volumen_util_raw is None or (isinstance(volumen_util_raw, str) and volumen_util_raw == 'N/D'):
                volumen_util = 0
                volumen_util_formatted = "N/D"
            elif isinstance(volumen_util_raw, str):
                # Si ya es string, preservar formato original y extraer número
                try:
                    volumen_util = float(volumen_util_raw.replace('%', '').replace(',', '.').strip())
                    volumen_util_formatted = volumen_util_raw  # Usar formato original
                except (ValueError, AttributeError):
                    volumen_util = 0
                    volumen_util_formatted = "N/D"
            elif pd.isna(volumen_util_raw):
                volumen_util = 0
                volumen_util_formatted = "N/D"
            else:
                volumen_util = float(volumen_util_raw)
                volumen_util_formatted = None  # Formatear después
            
            # Obtener participación del embalse
            participacion_row = df_participacion[df_participacion['Embalse'] == embalse_name]
            participacion_num = 0
            if not participacion_row.empty:
                participacion_valor = participacion_row['Participación (%)'].iloc[0]
                # Manejar tanto valores numéricos como strings con formato
                if isinstance(participacion_valor, str) and '%' in participacion_valor:
                    participacion_num = float(participacion_valor.replace('%', ''))
                else:
                    participacion_num = float(participacion_valor)
            
            # Clasificar riesgo
            nivel_riesgo = clasificar_riesgo_embalse(participacion_num, volumen_util)
            
# REMOVED DEBUG:             logger.info(f"SEMÁFORO CAPACIDAD REGIÓN {region}: {embalse_name} - Participación={participacion_num}%, Volumen={volumen_util}%")
# REMOVED DEBUG:             logger.info(f"RESULTADO CAPACIDAD REGIÓN {region}: {embalse_name} - Riesgo: {nivel_riesgo}")
            
            # NO incluir la columna de capacidad GWh en la tabla
            table_data.append({
                'Embalse': embalse_name,
                'Volumen Útil (%)': volumen_util_formatted if volumen_util_formatted else (f"{volumen_util:.1f}%" if pd.notna(volumen_util) else "N/D"),
                'Riesgo': "🔴" if nivel_riesgo == "high" else "🟡" if nivel_riesgo == "medium" else "🟢"
            })
        
        # Agregar fila TOTAL (sin mostrar capacidad)
        total_capacity = df_embalses['Capacidad_GWh_Internal'].sum()  # Solo para cálculos
        valid_volume_data = df_embalses[df_embalses['Volumen Útil (%)'].notna()]
        avg_volume = valid_volume_data['Volumen Útil (%)'].mean() if not valid_volume_data.empty else None
        
        table_data.append({
            'Embalse': 'TOTAL',
            'Volumen Útil (%)': f"{avg_volume:.1f}%" if avg_volume is not None else "N/D",
            'Riesgo': "⚡"  # Icono especial para el total
        })
        
        # Crear DataTable con semáforo (SIN columna de GWh)
        return dash_table.DataTable(
            data=table_data,
            columns=[
                {"name": "Embalse", "id": "Embalse"},
                {"name": "Volumen Útil (%)", "id": "Volumen Útil (%)"},
                {"name": "🚦 Riesgo", "id": "Riesgo"}
            ],
            style_cell={'textAlign': 'left', 'padding': '8px', 'fontFamily': 'Inter, Arial', 'fontSize': 13},
            style_header={'backgroundColor': '#e3e3e3', 'fontWeight': 'bold'},
            style_data={'backgroundColor': '#f8f8f8'},
            style_data_conditional=[
                # Estilos de semáforo
                {
                    'if': {'filter_query': '{Riesgo} = 🔴'},
                    'backgroundColor': '#ffebee',
                    'color': '#c62828',
                    'textAlign': 'center',
                    'fontWeight': 'bold'
                },
                {
                    'if': {'filter_query': '{Riesgo} = 🟡'},
                    'backgroundColor': '#fff8e1',
                    'color': '#f57c00',
                    'textAlign': 'center',
                    'fontWeight': 'bold'
                },
                {
                    'if': {'filter_query': '{Riesgo} = 🟢'},
                    'backgroundColor': '#e8f5e8',
                    'color': '#2e7d32',
                    'textAlign': 'center',
                    'fontWeight': 'bold'
                },
                # Estilo para fila TOTAL
                {
                    'if': {'filter_query': '{Embalse} = "TOTAL"'},
                    'backgroundColor': '#007bff',
                    'color': 'white',
                    'fontWeight': 'bold'
                }
            ],
            page_action="none",
            export_format="xlsx",
            export_headers="display"
        )
        
    except Exception as e:
        logger.error(f"❌ Error en create_region_filtered_capacidad_table: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        return html.Div(f"Error al cargar los datos: {str(e)}", className="text-center text-danger")

# NOTA: Los callbacks de tabla de embalses fueron eliminados para implementación directa en layout

# Callback para cargar opciones de regiones dinámicamente
@callback(
    Output('region-dropdown', 'options'),
    Input('region-dropdown', 'id')  # Se ejecuta al cargar la página
)
def load_region_options(_):
    """Carga las opciones de regiones dinámicamente para evitar bloqueos durante la importación."""
    try:
        regiones_disponibles = get_region_options()
        options = [{"label": "🌍 Todas las regiones", "value": "__ALL_REGIONS__"}]
        options += [{"label": f"🏔️ {r}", "value": r} for r in regiones_disponibles]
        return options
    except Exception as e:
        logger.error(f"Error cargando opciones de regiones: {e}", exc_info=True)
        return [{"label": "🌍 Todas las regiones", "value": "__ALL_REGIONS__"}]

# Callback para cargar el mapa de embalses por región
@callback(
    Output('mapa-embalses-container', 'children'),
    Input('participacion-jerarquica-data', 'data')  # Se ejecuta cuando se cargan los datos de las tablas
)
def cargar_mapa_embalses(data):
    """Genera el mapa mostrando CADA EMBALSE como un punto individual dentro de su región."""
    try:
        logger.info("Generando mapa con puntos por embalse...")
        
        if not data or len(data) == 0:
            return dbc.Alert([
                html.H5("⚠️ No hay datos disponibles", className="alert-heading"),
                html.P("Esperando datos de embalses...")
            ], color="info")
        
        # Filtrar solo embalses (no regiones ni total)
        embalses_data = [d for d in data if d.get('tipo') == 'embalse']
        
        if len(embalses_data) == 0:
            return dbc.Alert([
                html.H5("⚠️ No hay datos de embalses", className="alert-heading"),
                html.P("No se encontraron datos de embalses en las tablas.")
            ], color="warning")
        
        logger.info(f"Procesando {len(embalses_data)} embalses individuales...")
        
        # Agrupar embalses por región
        import random
        from math import cos, radians
        
        regiones_embalses = {}
        for emb in embalses_data:
            region = emb.get('region_name')
            if not region or region not in REGIONES_COORDENADAS:
                continue
            
            if region not in regiones_embalses:
                regiones_embalses[region] = []
            
            # Obtener valores
            participacion = emb.get('participacion_valor', 0)
            volumen_pct = emb.get('volumen_valor', 0)
            nombre_embalse = emb.get('nombre', '').replace('    └─ ', '')
            
            # Calcular riesgo con LA MISMA función del semáforo
            riesgo, color, icono = calcular_semaforo_embalse(participacion, volumen_pct)
            
            regiones_embalses[region].append({
                'nombre': nombre_embalse,
                'participacion': participacion,
                'volumen_pct': volumen_pct,
                'riesgo': riesgo,
                'color': color,
                'icono': icono
            })
        
        # Crear el mapa con Plotly
        import plotly.graph_objects as go
        
        fig = go.Figure()
        
        # Contador para leyenda (solo mostrar una vez cada color)
        leyenda_mostrada = {'ALTO': False, 'MEDIO': False, 'BAJO': False}
        
        # Para cada región, distribuir los embalses en un área alrededor del centro de la región
        for region, embalses in regiones_embalses.items():
            coords = REGIONES_COORDENADAS[region]
            lat_centro = coords['lat']
            lon_centro = coords['lon']
            
            # Calcular un radio de dispersión proporcional al número de embalses
            # Más embalses = mayor área de dispersión
            num_embalses = len(embalses)
            radio_lat = 0.3 + (num_embalses * 0.05)  # Radio en grados de latitud
            radio_lon = 0.4 + (num_embalses * 0.06)  # Radio en grados de longitud
            
            logger.debug(f"{region}: {num_embalses} embalses")
            
            # Distribuir cada embalse en posiciones aleatorias dentro del área de la región
            for i, emb in enumerate(embalses):
                # Generar posición aleatoria dentro de un círculo alrededor del centro
                # Usar semilla basada en el nombre para que sea consistente entre recargas
                seed_value = hash(emb['nombre']) % 10000
                random.seed(seed_value)
                
                # Ángulo aleatorio y distancia aleatoria desde el centro
                angulo = random.uniform(0, 360)
                distancia = random.uniform(0.2, 1.0)  # 20% a 100% del radio
                
                # Calcular offset
                from math import sin, cos, radians
                offset_lat = distancia * radio_lat * sin(radians(angulo))
                offset_lon = distancia * radio_lon * cos(radians(angulo))
                
                lat_embalse = lat_centro + offset_lat
                lon_embalse = lon_centro + offset_lon
                
                # Crear tooltip con información del embalse
                hover_text = (
                    f"<b>{emb['nombre']}</b><br>" +
                    f"Región: {coords['nombre']}<br>" +
                    f"Participación: {emb['participacion']:.2f}%<br>" +
                    f"Volumen Útil: {emb['volumen_pct']:.1f}%<br>" +
                    f"<b>Riesgo: {emb['riesgo']}</b> {emb['icono']}"
                )
                
                # Tamaño según participación (más grande = más importante)
                tamaño = min(8 + emb['participacion'] * 0.5, 25)
                
                # Mostrar en leyenda solo la primera vez que aparece cada nivel de riesgo
                mostrar_leyenda = not leyenda_mostrada[emb['riesgo']]
                if mostrar_leyenda:
                    leyenda_mostrada[emb['riesgo']] = True
                    nombre_leyenda = f"{emb['icono']} Riesgo {emb['riesgo']}"
                else:
                    nombre_leyenda = f"{emb['nombre']}"
                
                # Agregar punto al mapa
                fig.add_trace(go.Scattergeo(
                    lon=[lon_embalse],
                    lat=[lat_embalse],
                    mode='markers',
                    marker=dict(
                        size=tamaño,
                        color=emb['color'],
                        line=dict(width=1, color='white'),
                        symbol='circle',
                        opacity=0.85
                    ),
                    name=nombre_leyenda,
                    hovertext=hover_text,
                    hoverinfo='text',
                    showlegend=mostrar_leyenda,
                    legendgroup=emb['riesgo']  # Agrupar por nivel de riesgo
                ))
        
        # Configurar el mapa centrado en Colombia
        fig.update_geos(
            center=dict(lon=-74, lat=4.5),
            projection_type='mercator',
            showcountries=True,
            countrycolor='lightgray',
            showcoastlines=True,
            coastlinecolor='gray',
            showland=True,
            landcolor='#f5f5f5',
            showlakes=True,
            lakecolor='lightblue',
            showrivers=True,
            rivercolor='lightblue',
            lonaxis_range=[-79, -66],
            lataxis_range=[-4.5, 13],
            bgcolor='#e8f4f8'
        )
        
        fig.update_layout(
            title={
                'text': f'🗺️ Mapa de {len(embalses_data)} Embalses - Semáforo de Riesgo Hidrológico',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 16, 'color': COLORS['text_primary'], 'family': 'Arial Black'}
            },
            height=600,
            margin=dict(l=0, r=0, t=60, b=0),
            legend=dict(
                title=dict(text='Nivel de Riesgo', font=dict(size=12, family='Arial Black')),
                orientation='v',
                yanchor='top',
                y=0.98,
                xanchor='left',
                x=0.01,
                bgcolor='rgba(255,255,255,0.9)',
                bordercolor='gray',
                borderwidth=1,
                font=dict(size=11)
            ),
            hoverlabel=dict(
                bgcolor='white',
                font_size=12,
                font_family='Arial'
            )
        )
        
        total_embalses = len(embalses_data)
        total_regiones = len(regiones_embalses)
        logger.info(f"Mapa generado: {total_embalses} embalses en {total_regiones} regiones")
        
        return dcc.Graph(figure=fig, config={'displayModeBar': True, 'displaylogo': False})
        
    except Exception as e:
        print(f"❌ Error generando mapa de embalses: {e}")
        import traceback
        traceback.print_exc()
        return html.Div([
            html.I(className="fas fa-exclamation-triangle me-2"),
            f"Error al generar el mapa: {str(e)}"
        ], className="alert alert-danger")