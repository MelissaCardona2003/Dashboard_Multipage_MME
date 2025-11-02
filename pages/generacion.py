from dash import dcc, html, Input, Output, State, callback, register_page
import dash_bootstrap_components as dbc
from datetime import date, timedelta, datetime
import pandas as pd
import plotly.express as px

# Imports locales para componentes uniformes
from utils.components import crear_header, crear_sidebar_universal, crear_boton_regresar
from utils.config import COLORS
from utils._xm import get_objetoAPI, fetch_metric_data
from utils.cache_manager import cached_function

# Importar pydataxm si está disponible
try:
    from pydataxm.pydataxm import ReadDB
    PYDATAXM_AVAILABLE = True
except ImportError:
    PYDATAXM_AVAILABLE = False

register_page(
    __name__,
    path="/generacion",
    name="Generación",
    title="Generación Eléctrica - Ministerio de Minas y Energía",
    order=2
)

# Definir las tecnologías de generación - Hidrología y Generación por Fuente
GENERACION_TECHNOLOGIES = [
    {"name": "Hidrología", "path": "/generacion/hidraulica/hidrologia", "icon": "fas fa-tint", "color": COLORS['energia_hidraulica'], "description": "Análisis de caudales, aportes, niveles de embalses y mapa de riesgo hidrológico"},
    {"name": "Generación por Fuente", "path": "/generacion/fuentes", "icon": "fas fa-layer-group", "color": COLORS['primary'], "description": "Análisis unificado por tipo de fuente: Eólica, Solar, Térmica y Biomasa"}
]

def formatear_fecha_espanol(fecha_obj):
    """Convierte un objeto date a formato español (ej: '21 de octubre')"""
    meses = {
        1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
        5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
        9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
    }
    return f"{fecha_obj.day} de {meses[fecha_obj.month]}"

def obtener_metricas_hidricas():
    """
    Obtener métricas de reservas, aportes hídricos y generación total con cache.
    
    METODOLOGÍA OFICIAL XM:
    1. Reservas Hídricas = (Volumen Útil Diario Energía / Capacidad Útil Energía) * 100
    2. Aportes Hídricos = (Promedio mensual de Aportes Energía / Promedio mensual de Media Histórica) * 100
    3. Generación SIN = Suma de generación diaria del sistema
    """
    try:
        fecha_fin = date.today() - timedelta(days=1)
        
        # === 1. RESERVAS HÍDRICAS ===
        # Buscar fecha con datos disponibles (hasta 7 días atrás)
        reserva_pct, reserva_gwh, fecha_reserva = None, None, None
        for dias_atras in range(7):
            fecha_prueba = fecha_fin - timedelta(days=dias_atras)
            fecha_str = fecha_prueba.strftime('%Y-%m-%d')
            
            # Obtener Volumen Útil Diario Energía y Capacidad Útil
            df_vol = fetch_metric_data('VoluUtilDiarEner', 'Embalse', fecha_str, fecha_str)
            df_cap = fetch_metric_data('CapaUtilDiarEner', 'Embalse', fecha_str, fecha_str)
            
            if df_vol is not None and not df_vol.empty and df_cap is not None and not df_cap.empty:
                # Detectar nombre de columna de valor (puede ser 'Value' o 'Values_code')
                col_value = 'Value' if 'Value' in df_vol.columns else 'Values_code' if 'Values_code' in df_vol.columns else None
                
                if col_value:
                    # Convertir de Wh a GWh (la API devuelve en Wh)
                    vol_total_gwh = df_vol[col_value].sum() / 1e9
                    cap_total_gwh = df_cap[col_value].sum() / 1e9
                    
                    if cap_total_gwh > 0:
                        reserva_pct = round((vol_total_gwh / cap_total_gwh) * 100, 2)
                        reserva_gwh = vol_total_gwh
                        fecha_reserva = fecha_prueba
                        print(f"✅ Reservas calculadas: {reserva_pct}% ({reserva_gwh:.0f} GWh) - Fecha: {fecha_str}")
                        break
        
        # === 2. APORTES HÍDRICOS ===
        # Calcular promedio del mes actual hasta la fecha
        aporte_pct, aporte_gwh, fecha_aporte = None, None, None
        fecha_inicio_mes = fecha_fin.replace(day=1)
        fecha_inicio_str = fecha_inicio_mes.strftime('%Y-%m-%d')
        fecha_fin_str = fecha_fin.strftime('%Y-%m-%d')
        
        df_aportes = fetch_metric_data('AporEner', 'Sistema', fecha_inicio_str, fecha_fin_str)
        df_media_hist = fetch_metric_data('AporEnerMediHist', 'Sistema', fecha_inicio_str, fecha_fin_str)
        
        if df_aportes is not None and not df_aportes.empty and df_media_hist is not None and not df_media_hist.empty:
            # Detectar nombre de columna de valor
            col_value_ap = 'Value' if 'Value' in df_aportes.columns else 'Values_code' if 'Values_code' in df_aportes.columns else None
            col_value_mh = 'Value' if 'Value' in df_media_hist.columns else 'Values_code' if 'Values_code' in df_media_hist.columns else None
            
            if col_value_ap and col_value_mh:
                # Promedio acumulado del mes
                aportes_promedio = df_aportes[col_value_ap].mean()
                media_promedio = df_media_hist[col_value_mh].mean()
                
                if media_promedio > 0:
                    aporte_pct = round((aportes_promedio / media_promedio) * 100, 2)
                    # Mostrar la Media Histórica en GWh (igual que XM)
                    # Convertir de Wh a GWh (dividir por 1,000,000)
                    aporte_gwh = media_promedio / 1e6
                    fecha_aporte = fecha_fin
                    print(f"✅ Aportes calculados: {aporte_pct}% (Media histórica: {aporte_gwh:.2f} GWh) - Promedio del mes")
        
        # === 3. GENERACIÓN SIN ===
        # METODOLOGÍA CORRECTA: Sumar generación de TODAS las plantas (Gene/Recurso)
        # Esto asegura que el valor coincida con la suma de todas las fuentes
        gen_gwh, fecha_gen = None, None
        
        # Buscar datos en los últimos 7 días
        for dias_atras in range(7):
            fecha_prueba = fecha_fin - timedelta(days=dias_atras)
            fecha_str = fecha_prueba.strftime('%Y-%m-%d')
            
            # Obtener generación por recurso (todas las plantas)
            df_generacion = fetch_metric_data('Gene', 'Recurso', fecha_str, fecha_str)
            
            if df_generacion is not None and not df_generacion.empty:
                print(f"\n{'='*60}")
                print(f"📊 Generación obtenida para {fecha_str}: {len(df_generacion)} plantas")
                print(f"   Columnas disponibles: {df_generacion.columns.tolist()}")
                
                # Buscar columnas horarias (Values_Hour00, Values_Hour01, ..., Values_Hour23)
                horas_cols = [col for col in df_generacion.columns if 'Hour' in str(col) and 'Values' in str(col)]
                
                if horas_cols:
                    print(f"   ✅ Encontradas {len(horas_cols)} columnas horarias: {horas_cols[:3]}...{horas_cols[-3:]}")
                    
                    # Tomar una muestra para ver los valores
                    print(f"\n   🔍 ANÁLISIS DE VALORES (primera planta como ejemplo):")
                    primera_fila = df_generacion.iloc[0]
                    print(f"   Planta: {primera_fila.get('Values_code', 'N/A')}")
                    valores_ejemplo = [primera_fila[col] for col in horas_cols[:5]]
                    print(f"   Valores primeras 5 horas: {valores_ejemplo}")
                    suma_una_planta = sum([primera_fila[col] if pd.notna(primera_fila[col]) else 0 for col in horas_cols])
                    print(f"   Suma 24 horas (1 planta): {suma_una_planta:,.2f}")
                    
                    # Sumar todas las plantas y todas las 24 horas
                    gen_total_sin_conversion = 0
                    for col in horas_cols:
                        gen_total_sin_conversion += df_generacion[col].fillna(0).sum()
                    
                    print(f"\n   📊 SUMA TOTAL SIN CONVERSIÓN:")
                    print(f"   Total bruto: {gen_total_sin_conversion:,.2f}")
                    print(f"   Total / 1000 (kWh→GWh): {gen_total_sin_conversion/1000:,.2f} GWh")
                    print(f"   Total / 1000000 (Wh→GWh): {gen_total_sin_conversion/1000000:,.2f} GWh")
                    
                    # Determinar la conversión correcta basada en el rango de valores
                    # Si la suma está en millones, probablemente es Wh
                    # Si la suma está en miles/cientos de miles, probablemente es kWh
                    # Un día de generación típico en Colombia es ~200-250 GWh
                    if gen_total_sin_conversion > 100000000:  # > 100 millones, probablemente Wh
                        gen_gwh = gen_total_sin_conversion / 1000000
                        unidad_original = "Wh"
                    elif gen_total_sin_conversion > 100000:  # > 100 mil, probablemente kWh
                        gen_gwh = gen_total_sin_conversion / 1000
                        unidad_original = "kWh"
                    else:  # Ya está en GWh o MWh
                        gen_gwh = gen_total_sin_conversion
                        unidad_original = "GWh/MWh"
                    
                    fecha_gen = fecha_prueba
                    print(f"\n   ✅ CONVERSIÓN APLICADA:")
                    print(f"   Unidad detectada: {unidad_original}")
                    print(f"   GENERACIÓN SIN TOTAL: {gen_gwh:.2f} GWh")
                    print(f"{'='*60}\n")
                    print(f"✅ Generación SIN calculada: {gen_gwh:.2f} GWh (suma de {len(df_generacion)} plantas × 24 horas) - Fecha: {fecha_str}")
                    break
                else:
                    print(f"⚠️ No se encontraron columnas horarias en Gene/Recurso para {fecha_str}")
        
        if gen_gwh is None:
            print("⚠️ No se pudo calcular la generación total del SIN")

        
        return crear_fichas_hidricas_con_datos(
            reserva_pct, reserva_gwh, fecha_reserva,
            aporte_pct, aporte_gwh, fecha_aporte,
            gen_gwh, fecha_gen
        )
        
    except Exception as e:
        print(f"⚠️ Error obteniendo métricas hídricas: {e}")
        import traceback
        traceback.print_exc()
        return html.Div("No se pudieron obtener datos de XM. Intente más tarde.", 
                       style={"color": "red", "padding": "20px", "textAlign": "center"})

def crear_fichas_hidricas_con_datos(reserva_pct, reserva_gwh, fecha_reserva,
                                    aporte_pct, aporte_gwh, fecha_aporte,
                                    gen_gwh, fecha_gen):
    """Crear fichas usando datos reales calculados con metodología XM"""
    
    # Formatear fechas
    fecha_texto_reserva = formatear_fecha_espanol(fecha_reserva) if fecha_reserva else "N/D"
    fecha_texto_aporte = formatear_fecha_espanol(fecha_aporte) if fecha_aporte else "N/D"
    fecha_texto_gen = formatear_fecha_espanol(fecha_gen) if fecha_gen else "N/D"
    
    # Valores por defecto si no hay datos
    if reserva_pct is None:
        reserva_pct, reserva_gwh = 0, 0
    if aporte_pct is None:
        aporte_pct, aporte_gwh = 0, 0
    if gen_gwh is None:
        gen_gwh = 0
    
    return dbc.Row([
        # Ficha 1: Reservas Hídricas
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-water fa-2x mb-3", 
                              style={'color': '#86D293'}),
                        html.H6("Reservas Hídricas [%]", 
                               className="text-muted mb-2",
                               style={'fontSize': '0.85rem'}),
                        html.H3(f"{reserva_pct:.2f}", 
                               className="mb-1",
                               style={
                                   'color': '#86D293',
                                   'fontWeight': 'bold',
                                   'fontSize': '2rem'
                               }),
                        html.P(f"{reserva_gwh:,.0f} GWh", 
                              className="text-muted mb-2",
                              style={'fontSize': '0.8rem'}),
                        html.P(fecha_texto_reserva, 
                              className="text-muted mb-0",
                              style={'fontSize': '0.75rem'})
                    ], style={'textAlign': 'center'})
                ], style={
                    'background': 'linear-gradient(135deg, #86D293 0%, #6BC47D 100%)',
                    'borderRadius': '12px',
                    'color': 'white',
                    'padding': '1.5rem'
                })
            ], className="xm-card h-100")
        ], lg=4, md=6, className="mb-4"),
        
        # Ficha 2: Aportes Hídricos
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-tint fa-2x mb-3", 
                              style={'color': '#4DA6FF'}),
                        html.H6("Aportes Hídricos [%]", 
                               className="text-muted mb-2",
                               style={'fontSize': '0.85rem'}),
                        html.H3(f"{aporte_pct:.2f}", 
                               className="mb-1",
                               style={
                                   'color': '#4DA6FF',
                                   'fontWeight': 'bold',
                                   'fontSize': '2rem'
                               }),
                        html.P(f"{aporte_gwh:.2f} GWh", 
                              className="text-muted mb-2",
                              style={'fontSize': '0.8rem'}),
                        html.P(fecha_texto_aporte, 
                              className="text-muted mb-0",
                              style={'fontSize': '0.75rem'})
                    ], style={'textAlign': 'center'})
                ], style={
                    'background': 'linear-gradient(135deg, #4DA6FF 0%, #3D8FE8 100%)',
                    'borderRadius': '12px',
                    'color': 'white',
                    'padding': '1.5rem'
                })
            ], className="xm-card h-100")
        ], lg=4, md=6, className="mb-4"),
        
        # Ficha 3: Generación SIN
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-bolt fa-2x mb-3", 
                              style={'color': '#FFB84D'}),
                        html.H6("Generación SIN", 
                               className="text-muted mb-2",
                               style={'fontSize': '0.85rem'}),
                        html.H3(f"{gen_gwh:.2f}", 
                               className="mb-1",
                               style={
                                   'color': '#FFB84D',
                                   'fontWeight': 'bold',
                                   'fontSize': '2rem'
                               }),
                        html.P("GWh/día", 
                              className="text-muted mb-2",
                              style={'fontSize': '0.8rem'}),
                        html.P(fecha_texto_gen, 
                              className="text-muted mb-0",
                              style={'fontSize': '0.75rem'})
                    ], style={'textAlign': 'center'})
                ], style={
                    'background': 'linear-gradient(135deg, #FFB84D 0%, #FFA726 100%)',
                    'borderRadius': '12px',
                    'color': 'white',
                    'padding': '1.5rem'
                })
            ], className="xm-card h-100")
        ], lg=4, md=6, className="mb-4")
    ])

def crear_fichas_hidricas_fallback():
    """Crear fichas de Reservas, Aportes y Generación Total con datos de fallback"""
    def crear_fichas_hidricas_fallback():
        # Eliminada función de fallback. Si no hay datos, mostrar mensaje de error.
        return html.Div("No se pudieron obtener datos reales de XM. Intente más tarde.", style={"color": "red"})
    
    # Código original comentado temporalmente
    """
    try:
        if not PYDATAXM_AVAILABLE:
            return crear_fichas_generacion_xm_fallback()
        
        objetoAPI = ReadDB()
        fecha_actual = date.today()
        fecha_disponible = None
        
        # Buscar fecha con datos disponibles (hasta 3 días atrás para ser más rápido)
        for i in range(3):
            fecha_prueba = fecha_actual - timedelta(days=i)
            print(f"🔍 Buscando datos de generación XM para {fecha_prueba.strftime('%Y-%m-%d')}")
            
            try:
                # Intentar obtener datos de generación por recurso con timeout
                df_gene = objetoAPI.request_data(
                    "Gene",
                    "Recurso",
                    fecha_prueba.strftime("%Y-%m-%d"),
                    fecha_prueba.strftime("%Y-%m-%d")
                )
                
                if df_gene is not None and not df_gene.empty:
                    fecha_disponible = fecha_prueba
                    print(f"✅ Datos de generación encontrados para {fecha_disponible.strftime('%Y-%m-%d')}")
                    break
                else:
                    print(f"❌ Sin datos para {fecha_prueba.strftime('%Y-%m-%d')}")
            except Exception as e:
                print(f"⚠️ Error al consultar {fecha_prueba.strftime('%Y-%m-%d')}: {str(e)[:100]}")
                continue
        
        if fecha_disponible is None:
            print(f"❌ No hay datos de generación disponibles en los últimos 3 días, usando fallback")
            return crear_fichas_generacion_xm_fallback()
        
        # Obtener datos de generación por recurso
        df_gene = objetoAPI.request_data(
            "Gene",
            "Recurso",
            fecha_disponible.strftime("%Y-%m-%d"),
            fecha_disponible.strftime("%Y-%m-%d")
        )
        
        # Definir recursos renovables y no renovables
        recursos_renovables = ['HIDRAULICA', 'EOLICA', 'SOLAR', 'BIOMASA']
        recursos_no_renovables = ['TERMICA', 'GAS', 'CARBON']
        
        # Calcular generación por tipo
        generacion_renovable_kwh = 0
        generacion_no_renovable_kwh = 0
        
        # Sumar las columnas de horas (Values_Hour_1 a Values_Hour_24)
        horas_cols = [col for col in df_gene.columns if col.startswith('Values_Hour')]
        
        for idx, row in df_gene.iterrows():
            recurso = row.get('Id', '').upper()
            gen_total = row[horas_cols].sum() if horas_cols else 0
            
            if any(r in recurso for r in recursos_renovables):
                generacion_renovable_kwh += gen_total
            elif any(r in recurso for r in recursos_no_renovables):
                generacion_no_renovable_kwh += gen_total
        
        # Convertir de kWh a GWh
        generacion_renovable_gwh = generacion_renovable_kwh / 1000000
        generacion_no_renovable_gwh = generacion_no_renovable_kwh / 1000000
        generacion_total_gwh = generacion_renovable_gwh + generacion_no_renovable_gwh
        
        # Calcular porcentajes
        porcentaje_renovable = (generacion_renovable_gwh / generacion_total_gwh * 100) if generacion_total_gwh > 0 else 0
        porcentaje_no_renovable = (generacion_no_renovable_gwh / generacion_total_gwh * 100) if generacion_total_gwh > 0 else 0
        
        print(f"Generación Renovable: {generacion_renovable_gwh:.2f} GWh ({porcentaje_renovable:.2f}%)")
        print(f"Generación No Renovable: {generacion_no_renovable_gwh:.2f} GWh ({porcentaje_no_renovable:.2f}%)")
        print(f"Generación Total: {generacion_total_gwh:.2f} GWh")
        
        return crear_fichas_generacion_xm(
            porcentaje_renovable,
            porcentaje_no_renovable,
            generacion_total_gwh,
            fecha_disponible
        )
        
    except Exception as e:
        print(f"❌ Error obteniendo datos de generación XM: {str(e)[:200]}")
        return crear_fichas_generacion_xm_fallback()
    """

def crear_fichas_generacion_xm(porcentaje_renovable, porcentaje_no_renovable, generacion_total_gwh, fecha):
    """Crear las 3 fichas de generación XM con datos reales"""
    fecha_texto = formatear_fecha_espanol(fecha)
    
    return dbc.Row([
        # Ficha Generación Renovable %
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-leaf fa-2x mb-2", style={"color": "#86D293"}),
                        html.H6("Generación Renovable [%]", className="card-title text-center mb-2", 
                               style={"fontWeight": "700", "color": "#2C3E50", "fontSize": "0.85rem"}),
                        html.H3(f"{porcentaje_renovable:.2f}", className="text-center mb-1",
                               style={"fontWeight": "800", "color": "#86D293", "fontSize": "2.5rem", "letterSpacing": "-1px"}),
                        html.Small(f"{fecha_texto}", 
                                  className="text-muted d-block text-center",
                                  style={"fontSize": "0.7rem", "opacity": "0.7"})
                    ], className="text-center")
                ], className="py-2")
            ], className="h-100 xm-card", style={
                "border": "none",
                "borderRadius": "16px",
                "background": "linear-gradient(135deg, #ffffff 0%, #f0fdf4 100%)",
                "--card-color": "#86D293"
            })
        ], width=12, lg=4, md=4, className="mb-3"),
        
        # Ficha Generación No Renovable %
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-industry fa-2x mb-2", style={"color": "#FF6B6B"}),
                        html.H6("Generación No Renovable [%]", className="card-title text-center mb-2",
                               style={"fontWeight": "700", "color": "#2C3E50", "fontSize": "0.85rem"}),
                        html.H3(f"{porcentaje_no_renovable:.2f}", className="text-center mb-1",
                               style={"fontWeight": "800", "color": "#FF6B6B", "fontSize": "2.5rem", "letterSpacing": "-1px"}),
                        html.Small(f"{fecha_texto}", 
                                  className="text-muted d-block text-center",
                                  style={"fontSize": "0.7rem", "opacity": "0.7"})
                    ], className="text-center")
                ], className="py-2")
            ], className="h-100 xm-card", style={
                "border": "none",
                "borderRadius": "16px",
                "background": "linear-gradient(135deg, #ffffff 0%, #fff1f0 100%)",
                "--card-color": "#FF6B6B"
            })
        ], width=12, lg=4, md=4, className="mb-3"),
        
        # Ficha Generación Total GWh
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-bolt fa-2x mb-2", style={"color": "#4285F4"}),
                        html.H6("Generación Total [GWh]", className="card-title text-center mb-2",
                               style={"fontWeight": "700", "color": "#2C3E50", "fontSize": "0.85rem"}),
                        html.H3(f"{generacion_total_gwh:,.2f}", className="text-center mb-1",
                               style={"fontWeight": "800", "color": "#4285F4", "fontSize": "2.5rem", "letterSpacing": "-1px"}),
                        html.Small(f"{fecha_texto}", 
                                  className="text-muted d-block text-center",
                                  style={"fontSize": "0.7rem", "opacity": "0.7"})
                    ], className="text-center")
                ], className="py-2")
            ], className="h-100 xm-card", style={
                "border": "none",
                "borderRadius": "16px",
                "background": "linear-gradient(135deg, #ffffff 0%, #f0f7ff 100%)",
                "--card-color": "#4285F4"
            })
        ], width=12, lg=4, md=4, className="mb-3")
    ], className="mb-4")

def crear_fichas_generacion_xm_fallback():
    # Eliminada función de fallback. Si no hay datos, mostrar mensaje de error.
    return html.Div("No se pudieron obtener datos reales de XM. Intente más tarde.", style={"color": "red"})

def create_technology_card(tech):
    """Crear tarjeta para cada tecnología de generación"""
    return dbc.Col([
        html.A([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(
                            className=tech["icon"],
                            style={
                                "fontSize": "5rem",
                                "color": tech["color"],
                                "marginBottom": "1.5rem"
                            }
                        ),
                        html.H4(tech["name"], 
                               className="mb-2",
                               style={"color": COLORS['text_primary'], "fontWeight": "600"}),
                        html.P(tech["description"],
                              className="text-muted small mb-0",
                              style={"fontSize": "0.9rem"})
                    ], className="text-center"),
                ], className="py-4")
            ], 
            className="h-100 shadow-sm tech-card",
            style={
                "cursor": "pointer",
                "transition": "all 0.3s ease",
                "border": f"2px solid {tech['color']}30"
            }
            )
        ], href=tech["path"], style={"textDecoration": "none"})
    ], lg=6, md=6, sm=12, className="mb-4")  # Cambiado de lg=4 a lg=6 para 2 columnas

layout = html.Div([
    # Sidebar desplegable
    crear_sidebar_universal(),
    
    # Header específico para generación
    crear_header(
        titulo_pagina="Generación Eléctrica",
        descripcion_pagina="Análisis por tecnologías de generación eléctrica en Colombia",
        icono_pagina="fas fa-bolt",
        color_tema=COLORS['primary']
    ),
    
    # Container principal
    dbc.Container([
        # Botón de regreso
        crear_boton_regresar(),
        
        # Título de la sección
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.I(className="fas fa-bolt", 
                          style={"fontSize": "4rem", "color": "#4285F4", "marginRight": "1rem"}),
                    html.H1("GENERACIÓN ELÉCTRICA", 
                           style={"color": COLORS['text_primary'], "fontWeight": "700", "display": "inline-block"})
                ], className="text-center mb-2")
            ])
        ]),
        
        dbc.Row([
            dbc.Col([
                html.P("Análisis integral de las diferentes tecnologías de generación eléctrica en Colombia",
                      className="text-center text-muted mb-4", 
                      style={"fontSize": "1.2rem"})
            ])
        ]),
        
        # Sección con imagen y fichas lado a lado
        dbc.Row([
            # Columna izquierda: Imagen
            dbc.Col([
                html.Div([
                    html.Img(
                        src="/assets/images/Recurso 1.png",
                        alt="Generación Eléctrica",
                        style={
                            "width": "100%",
                            "height": "100%",
                            "objectFit": "contain",
                            "minHeight": "600px"
                        },
                        className="mb-3"
                    )
                ], style={
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center",
                    "height": "100%"
                })
            ], lg=4, md=12, className="mb-4 d-flex align-items-stretch"),
            
            # Columna derecha: Fichas y botones
            dbc.Col([
                # Subtítulo para KPIs
                html.H5("Indicadores Clave del Sistema", 
                       className="text-center mb-3",
                       style={"color": COLORS['text_primary'], "fontWeight": "600"}),
                
                # Fichas de Reservas, Aportes y Generación - Se cargan dinámicamente
                dcc.Loading(
                    id="loading-fichas-hidricas",
                    type="default",
                    children=html.Div(id="fichas-hidricas-container", className="mb-3")
                ),
                
                # Subtítulo para tecnologías
                html.H5("Explorar por Tecnología", 
                       className="text-center mt-3 mb-3",
                       style={"color": COLORS['text_primary'], "fontWeight": "600"}),
                
                # Tarjetas de tecnologías
                dbc.Row([
                    create_technology_card(tech) for tech in GENERACION_TECHNOLOGIES
                ]),
            ], lg=8, md=12)
        ], className="mb-4"),
        
    ], fluid=True, className="py-4")
])

# Callback para cargar las fichas hídricas de forma asíncrona
@callback(
    Output("fichas-hidricas-container", "children"),
    Input("fichas-hidricas-container", "id")
)
def cargar_fichas_hidricas(_):
    """Cargar las fichas de reservas, aportes y generación de forma asíncrona"""
    try:
        return obtener_metricas_hidricas()
    except Exception as e:
        print(f"Error en callback de fichas hídricas: {e}")
        return html.Div("No se pudieron obtener datos reales de XM. Intente más tarde.", style={"color": "red"})
