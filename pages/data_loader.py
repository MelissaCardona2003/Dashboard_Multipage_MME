"""
Módulo para cargar y procesar datos para Dash
"""
import pandas as pd
from io import BytesIO
from .config import DATA_FILES

def cargar_datos():
    """Cargar todos los datasets necesarios"""
    try:
        datasets = {}
        for key, filename in DATA_FILES.items():
            datasets[key] = pd.read_csv(filename)
        
        return (
            datasets["granjas_actualizadas"],
            datasets["granjas_original"], 
            datasets["comunidades"],
            datasets["estadisticas"],
            datasets["resumen_detallado"]
        )
    except Exception as e:
        print(f"Error cargando datos: {e}")
        return None, None, None, None, None

def to_excel(df):
    """Convertir DataFrame a Excel"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Datos')
    processed_data = output.getvalue()
    return processed_data

def crear_tabla_principal(granjas_actualizadas, estadisticas):
    """Crear tabla principal con todos los datos"""
    tabla_principal = []
    
    for _, granja in granjas_actualizadas.iterrows():
        item = granja['Item']
        ces_ids = granja['CEs Relacionadas']
        stats_granja = estadisticas[estadisticas['Item'] == item].iloc[0]
        
        tabla_principal.append({
            'Granja': f"Granja {item}",
            'Ubicación': f"{granja['Municipio']}, {granja['Departamento']}",
            'Potencia_kW': granja['Potencia  KW'],
            'IDs_10_CEs_Mas_Cercanas': ces_ids,
            'Distancia_Promedio_km': round(stats_granja['Distancia_Media'], 2),
            'Distancia_Minima_km': round(stats_granja['Distancia_Min'], 2),
            'Beneficiarios': granja['Beneficiarios']
        })
    
    return pd.DataFrame(tabla_principal)

def filtrar_coordenadas_validas(df, lat_col='Latitud', lon_col='Longitud'):
    """Filtrar coordenadas válidas para Colombia"""
    return df[
        (df[lat_col].notna()) & 
        (df[lon_col].notna()) &
        (df[lat_col] >= -5) & 
        (df[lat_col] <= 15) &
        (df[lon_col] >= -85) & 
        (df[lon_col] <= -65)
    ]

def preparar_datos_comunidades(comunidades_df, sample_size=100):
    """Preparar datos de comunidades para visualización"""
    # Filtrar coordenadas válidas
    comunidades_validas = comunidades_df[
        (comunidades_df['y'].notna()) & 
        (comunidades_df['x'].notna()) &
        (comunidades_df['y'] >= -5) & 
        (comunidades_df['y'] <= 15) &
        (comunidades_df['x'] >= -85) & 
        (comunidades_df['x'] <= -65)
    ]
    
    # Tomar una muestra para mejor rendimiento
    if len(comunidades_validas) > sample_size:
        return comunidades_validas.sample(n=sample_size, random_state=42)
    
    return comunidades_validas
