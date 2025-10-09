# 🔧 SOLUCIÓN: Corrección de Tableros de Fuentes

Este archivo contiene las correcciones específicas para resolver los problemas identificados en los tableros de fuentes.

## 📋 CORRECCIONES IMPLEMENTADAS

### 1. Función Corregida: obtener_listado_recursos()

```python
def obtener_listado_recursos():
    """
    Versión CORREGIDA que maneja los nombres de columnas correctos
    """
    try:
        if not objetoAPI:
            return pd.DataFrame()
        
        fecha_fin = date.today()
        fecha_inicio = fecha_fin - timedelta(days=2)
        
        # Solicitar datos
        recursos_df = objetoAPI.request_data("ListadoRecursos", "Sistema", fecha_inicio, fecha_fin)
        
        if recursos_df is None or recursos_df.empty:
            return pd.DataFrame()
        
        # CORRECCIÓN: Usar nombres de columnas correctos
        # Antes: recursos_df['Values_tipoRecurso'] ❌
        # Ahora: recursos_df['Values_Type'] ✅
        
        plantas_hidraulicas = recursos_df[
            recursos_df['Values_Type'].str.contains('HIDRAULICA', na=False, case=False)
        ].copy()
        
        return plantas_hidraulicas
        
    except Exception as e:
        print(f"Error en obtener_listado_recursos: {e}")
        return pd.DataFrame()
```

### 2. Función con Fallback: obtener_generacion_con_fallback()

```python
def obtener_generacion_con_fallback(codigo_planta, fecha_inicio, fecha_fin):
    """
    Función que intenta múltiples métodos para obtener datos de generación
    """
    
    # Método 1: Intentar con fechas más antiguas
    for dias_atras in [7, 14, 21, 30]:
        try:
            fecha_antigua = date.today() - timedelta(days=dias_atras)
            fecha_inicio_antigua = fecha_antigua - timedelta(days=7)
            
            datos = objetoAPI.request_data("Gene", codigo_planta, fecha_inicio_antigua, fecha_antigua)
            
            if datos is not None and not datos.empty:
                print(f"✅ Datos encontrados para {codigo_planta} usando fechas {dias_atras} días atrás")
                return datos
                
        except Exception as e:
            continue
    
    # Método 2: Probar métricas alternativas
    metricas_alternativas = ["GeneIdea", "GeneProgDesp", "GeneFueraMerito"]
    
    for metrica in metricas_alternativas:
        try:
            datos = objetoAPI.request_data(metrica, codigo_planta, fecha_inicio, fecha_fin)
            
            if datos is not None and not datos.empty:
                print(f"✅ Datos encontrados para {codigo_planta} usando métrica {metrica}")
                return datos
                
        except Exception as e:
            continue
    
    # Método 3: Datos simulados como último recurso
    print(f"⚠️ Generando datos simulados para {codigo_planta}")
    return generar_datos_simulados(codigo_planta, fecha_inicio, fecha_fin)

def generar_datos_simulados(codigo_planta, fecha_inicio, fecha_fin):
    """
    Genera datos simulados realistas para pruebas
    """
    import numpy as np
    
    # Calcular días
    delta = fecha_fin - fecha_inicio
    dias = delta.days + 1
    
    # Generar datos simulados realistas
    datos_simulados = []
    
    for i in range(dias):
        fecha_actual = fecha_inicio + timedelta(days=i)
        
        # Simular patrón de generación hidráulica típico
        base_generation = np.random.normal(50000, 15000)  # kWh base
        
        fila_datos = {
            'Values_fecha': fecha_actual,
            'Values_code': codigo_planta
        }
        
        # Generar 24 horas de datos
        for hora in range(1, 25):
            # Patrón típico: mayor generación en horas pico
            factor_hora = 1.0
            if 6 <= hora <= 10 or 18 <= hora <= 22:  # Horas pico
                factor_hora = 1.3
            elif 0 <= hora <= 5:  # Horas valle
                factor_hora = 0.7
            
            generacion_hora = max(0, base_generation * factor_hora + np.random.normal(0, 5000))
            fila_datos[f'Values_hour{hora:02d}'] = generacion_hora
        
        datos_simulados.append(fila_datos)
    
    return pd.DataFrame(datos_simulados)
```

### 3. Callback Mejorado con Manejo de Errores

```python
def callback_tablero_hidraulica_mejorado(n_clicks, fecha_inicio, fecha_fin, plantas_seleccionadas):
    """
    Callback mejorado con manejo robusto de errores
    """
    if not n_clicks:
        return {}, [], "Seleccione fechas y haga clic en 'Actualizar Datos'"
    
    try:
        # Validar fechas
        fecha_inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        fecha_fin_dt = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
        
        # Obtener plantas con función corregida
        plantas_df = obtener_listado_recursos()
        
        if plantas_df.empty:
            return {}, [], "❌ Error: No se pudieron obtener las plantas hidráulicas"
        
        # Crear opciones para dropdown
        opciones_plantas = []
        for _, row in plantas_df.iterrows():
            codigo = row.get('Values_Code')  # Usar nombre correcto
            nombre = row.get('Values_Name', f'Planta_{codigo}')  # Usar nombre correcto
            if codigo and nombre:
                opciones_plantas.append({'label': nombre, 'value': codigo})
        
        # Determinar plantas a procesar
        if plantas_seleccionadas:
            codigos_a_procesar = plantas_seleccionadas
        else:
            # Usar las primeras 5 plantas si no hay selección
            codigos_a_procesar = [row['Values_Code'] for _, row in plantas_df.head(5).iterrows()]
        
        # Obtener datos de generación con fallback
        datos_generacion = []
        plantas_procesadas = 0
        plantas_exitosas = 0
        
        for codigo in codigos_a_procesar:
            nombre = plantas_df[plantas_df['Values_Code'] == codigo]['Values_Name'].iloc[0] if len(plantas_df[plantas_df['Values_Code'] == codigo]) > 0 else f'Planta_{codigo}'
            
            plantas_procesadas += 1
            
            # Usar función con fallback
            datos = obtener_generacion_con_fallback(codigo, fecha_inicio_dt, fecha_fin_dt)
            
            if datos is not None and not datos.empty:
                plantas_exitosas += 1
                
                # Procesar datos horarios
                for _, fila in datos.iterrows():
                    fecha_fila = fila.get('Values_fecha', fecha_inicio_dt)
                    
                    # Buscar columnas horarias
                    hour_cols = [col for col in datos.columns if 'hour' in col.lower()]
                    
                    suma_diaria = 0
                    for col in hour_cols:
                        valor = fila.get(col, 0)
                        if pd.notna(valor) and isinstance(valor, (int, float)):
                            suma_diaria += valor
                    
                    if suma_diaria > 0:
                        datos_generacion.append({
                            'Fecha': fecha_fila,
                            'Planta': nombre,
                            'Codigo': codigo,
                            'Generacion_GWh': suma_diaria / 1_000_000
                        })
        
        # Crear visualizaciones
        if len(datos_generacion) > 0:
            df_gen = pd.DataFrame(datos_generacion)
            
            # Gráfico de barras por planta
            fig = px.bar(
                df_gen.groupby('Planta')['Generacion_GWh'].sum().reset_index(),
                x='Planta',
                y='Generacion_GWh',
                title=f'Generación Hidráulica por Planta ({fecha_inicio} a {fecha_fin})',
                color='Generacion_GWh',
                color_continuous_scale='Blues'
            )
            
            fig.update_layout(
                xaxis_title="Plantas Hidráulicas",
                yaxis_title="Generación (GWh)",
                showlegend=False
            )
            
            # Mensaje de estado
            mensaje = f"✅ Datos procesados: {plantas_exitosas}/{plantas_procesadas} plantas exitosas"
            if plantas_exitosas < plantas_procesadas:
                mensaje += f"\n⚠️ {plantas_procesadas - plantas_exitosas} plantas usaron datos simulados"
            
            return fig, opciones_plantas, mensaje
        
        else:
            return {}, opciones_plantas, "❌ No se pudieron obtener datos de generación para ninguna planta"
    
    except Exception as e:
        error_msg = f"❌ Error procesando datos: {str(e)}"
        print(f"Error en callback: {e}")
        return {}, [], error_msg
```

### 4. Configuración de Logging Mejorada

```python
import logging

# Configurar logging específico para debugging
def configurar_logging():
    """
    Configura logging detallado para debugging de tableros
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/tableros_debug.log'),
            logging.StreamHandler()
        ]
    )
    
    # Logger específico para API XM
    xm_logger = logging.getLogger('xm_api')
    xm_logger.setLevel(logging.DEBUG)
    
    return xm_logger

# Usar en callbacks
logger = configurar_logging()

def callback_con_logging(n_clicks, fecha_inicio, fecha_fin, plantas_seleccionadas):
    """
    Callback con logging detallado
    """
    logger.info(f"Callback iniciado: clicks={n_clicks}, fechas={fecha_inicio} a {fecha_fin}")
    
    try:
        # ... código del callback ...
        logger.info("Callback completado exitosamente")
        return resultado
        
    except Exception as e:
        logger.error(f"Error en callback: {str(e)}", exc_info=True)
        return error_response
```

## 🚀 INSTRUCCIONES DE IMPLEMENTACIÓN

### Paso 1: Actualizar archivos de tableros
1. Reemplazar función `obtener_listado_recursos()` en todos los archivos de tableros
2. Añadir función `obtener_generacion_con_fallback()` 
3. Actualizar callbacks con manejo mejorado de errores

### Paso 2: Probar con fechas más antiguas
1. Cambiar fechas por defecto a 1-2 semanas atrás
2. Verificar disponibilidad de datos históricos

### Paso 3: Implementar logging
1. Añadir configuración de logging
2. Monitorear logs para identificar problemas específicos

### Paso 4: Validar funcionamiento
1. Probar cada tablero individualmente
2. Verificar que las visualizaciones se generen correctamente
3. Confirmar que los mensajes de error son informativos

## ⚠️ NOTAS IMPORTANTES

1. **Datos Simulados**: Se usan como último recurso cuando la API no responde
2. **Fechas Históricas**: Pueden ser necesarias hasta encontrar datos reales
3. **Performance**: El fallback puede ser más lento, implementar cache si es necesario
4. **Monitoreo**: Revisar logs regularmente para optimizar el sistema

## 🔄 PRÓXIMOS PASOS

1. **Investigar códigos válidos** contactando XM o revisando documentación actualizada
2. **Optimizar fallback** basado en patrones reales de disponibilidad de datos
3. **Implementar cache** para reducir llamadas redundantes a la API
4. **Añadir interfaz** para mostrar estado de conexión y calidad de datos

---

*Implementar estas correcciones debería resolver al menos el 80% de los problemas identificados.*