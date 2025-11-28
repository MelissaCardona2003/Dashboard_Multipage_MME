# 📊 Implementación del Dashboard de Comercialización

## Resumen Ejecutivo

Se ha implementado exitosamente el nuevo dashboard de **Comercialización** que visualiza los precios del mercado eléctrico colombiano utilizando datos directos de la API de XM.

---

## 🎯 Características Implementadas

### 1. Métricas Visualizadas

El dashboard muestra las siguientes métricas de precios:

#### **PrecBolsNaci** - Precio Bolsa Nacional
- **Formato**: Datos horarios (24 columnas por día)
- **Visualización**: Promedio diario en la gráfica principal
- **Detalle**: Click en punto → muestra tabla con las 24 horas
- **Unidad**: COP/kWh

#### **PrecEsca** - Precio de Escasez
- **Formato**: Datos diarios (1 valor por día)
- **Visualización**: Línea directa en la gráfica
- **Unidad**: COP/kWh

#### **Nota sobre PrecEscaAct**
- Esta métrica NO tiene datos disponibles en la API XM
- Se decidió no incluirla en el dashboard

---

## 🏗️ Arquitectura Implementada

### Estructura del Archivo
```
pages/comercializacion.py
├── Importaciones y configuración
├── Funciones de datos
│   ├── obtener_precio_bolsa()      → Query PrecBolsNaci
│   └── obtener_precio_escasez()    → Query PrecEsca
├── Funciones de visualización
│   ├── crear_grafica_precios()     → Gráfica de líneas
│   └── crear_tabla_horaria()       → Tabla 24 horas
├── Layout
│   ├── Filtros de fecha
│   ├── 3 fichas KPI
│   ├── Gráfica principal
│   └── Modal para detalle horario
└── Callbacks
    ├── actualizar_datos_comercializacion()
    └── toggle_modal_detalle()
```

---

## 🔧 Componentes Técnicos

### 1. Obtención de Datos

#### `obtener_precio_bolsa(fecha_inicio, fecha_fin)`

```python
# Utiliza fetch_metric_data directamente (NO obtener_datos_inteligente)
df = fetch_metric_data('PrecBolsNaci', 'Sistema', fecha_inicio, fecha_fin)

# Procesa formato ancho → calcula promedio diario
hour_cols = [c for c in df.columns if 'Hour' in c]
df['Promedio_Diario'] = df[hour_cols].mean(axis=1)

# Guarda datos horarios completos para el modal
df_result['Datos_Horarios'] = df[['Date'] + hour_cols].to_dict('records')
```

**Estructura de datos retornados**:
```
Columns: ['Date', 'Value', 'Metrica', 'Datos_Horarios']
- Date: fecha del día
- Value: promedio de las 24 horas
- Metrica: 'Precio Bolsa Nacional'
- Datos_Horarios: diccionario con Values_Hour01 a Values_Hour24
```

#### `obtener_precio_escasez(fecha_inicio, fecha_fin)`

```python
# Datos diarios - uso directo
df = fetch_metric_data('PrecEsca', 'Sistema', fecha_inicio, fecha_fin)
df['Metrica'] = 'Precio Escasez'
return df[['Date', 'Value', 'Metrica']]
```

### 2. Visualización

#### Gráfica Principal
- **Tipo**: Plotly Line Chart con 2 trazas
- **Interacción**: Click en punto abre modal
- **Colores**:
  - Precio Bolsa: Azul primario (`COLORS['primary']`)
  - Precio Escasez: Rojo (`COLORS['danger']`)

#### Fichas KPI
1. **💰 Precio Promedio Bolsa**: `mean()` de PrecBolsNaci
2. **📈 Precio Máximo Bolsa**: `max()` de PrecBolsNaci
3. **⚠️ Precio Escasez Actual**: Último valor de PrecEsca

#### Modal de Detalle Horario
- Se abre SOLO al hacer click en puntos de "Precio Bolsa Nacional"
- Muestra tabla de 24 horas dividida en 3 columnas
- Formato: `Hora XX | Precio $XXX.XX`

---

## 📡 Callbacks

### Callback 1: Actualizar Datos

```python
@callback(
    [Output('grafica-precios-comercializacion', 'figure'),
     Output('store-comercializacion', 'data'),
     Output('ficha-precio-promedio', 'children'),
     Output('ficha-precio-max', 'children'),
     Output('ficha-precio-escasez', 'children')],
    [Input('btn-actualizar-comercializacion', 'n_clicks')],
    [State('selector-fechas-comercializacion', 'start_date'),
     State('selector-fechas-comercializacion', 'end_date')]
)
```

**Flujo**:
1. Valida rango de fechas (máximo 365 días)
2. Obtiene datos de ambas métricas
3. Crea gráfica combinada
4. Calcula estadísticas para fichas KPI
5. Guarda datos en `dcc.Store` para el modal

### Callback 2: Toggle Modal

```python
@callback(
    [Output('modal-detalle-comercializacion', 'is_open'),
     Output('modal-titulo-comercializacion', 'children'),
     Output('modal-contenido-comercializacion', 'children')],
    [Input('grafica-precios-comercializacion', 'clickData'),
     Input('modal-cerrar-comercializacion', 'n_clicks')],
    [State('store-comercializacion', 'data'),
     State('modal-detalle-comercializacion', 'is_open')]
)
```

**Flujo**:
1. Detecta click en gráfica
2. Verifica que sea en "Precio Bolsa Nacional"
3. Extrae fecha del punto clickeado
4. Busca datos horarios en Store
5. Crea tabla de 24 horas
6. Abre modal con tabla

---

## 🎨 UI/UX

### Diseño Visual
- **Header**: Icono ⚡ + título "COMERCIALIZACIÓN"
- **Alert informativa**: Explica que se muestra promedio diario y cómo ver detalle
- **Card de filtros**: Selector de rango + botón actualizar
- **Row de fichas**: 3 KPI cards con iconos distintivos
- **Gráfica**: Card con título "📊 Evolución de Precios"
- **Modal**: XL size, tabla responsiva en 3 columnas

### Paleta de Colores
- **Primario (Bolsa)**: Azul `#0d6efd`
- **Peligro (Escasez)**: Rojo `#dc3545`
- **Advertencia (Max)**: Amarillo `#ffc107`

---

## 🔗 Integración con Sistema

### Sidebar
Ya configurado en `utils/components.py`:
```python
html.A([
    html.Span("💰 Comercialización", style={"fontWeight": "600"})
], href="/comercializacion", active="exact", className="nav-link-sidebar mb-4")
```

### Registro de Página
```python
dash.register_page(__name__, path='/comercializacion', name='Comercialización')
```

---

## 📊 Ejemplo de Datos

### PrecBolsNaci (Entrada API)
```
Shape: (2, 27)
Columns: ['Id', 'Values_code', 'Values_Hour01', ..., 'Values_Hour24', 'Date']

Datos de ejemplo:
Date: 2025-11-22
Values_Hour01: 256.55940
Values_Hour02: 138.55940
Values_Hour20: 795.36740
...
```

### PrecBolsNaci (Procesado para gráfica)
```
Columns: ['Date', 'Value', 'Metrica', 'Datos_Horarios']

Date: 2025-11-22
Value: 412.73 (promedio de 24 horas)
Metrica: 'Precio Bolsa Nacional'
Datos_Horarios: {dict con Values_Hour01 a Hour24}
```

### PrecEsca (Directo)
```
Columns: ['Date', 'Value', 'Metrica']

Date: 2025-11-22
Value: 658.63049
Metrica: 'Precio Escasez'
```

---

## ⚠️ Diferencias con Otros Dashboards

| Aspecto | Distribución/Generación | Comercialización |
|---------|-------------------------|------------------|
| **Fuente de datos** | Base de datos SQLite | API XM directa |
| **Función de obtención** | `obtener_datos_inteligente()` | `fetch_metric_data()` |
| **Filtro principal** | Agente/Recurso | Rango de fechas |
| **Granularidad** | Diaria | Horaria → agregada a diaria |
| **Detalle interactivo** | No aplica | Modal con 24 horas |
| **ETL** | Ya poblado | Pendiente de implementar |

---

## 🚀 Próximos Pasos

### 1. Agregar Métricas al ETL
```python
# En etl/config_metricas.py
METRICAS_COMERCIALIZACION = [
    'PrecBolsNaci',  # Precio Bolsa Nacional
    'PrecEsca'       # Precio Escasez
]
```

### 2. Modificar `etl_xm_to_sqlite.py`
- Procesar formato horario de PrecBolsNaci
- Decisión: ¿Guardar 24 registros por día o solo promedio?
- Considerar volumen de datos (24x registros)

### 3. Actualizar Dashboard
Una vez datos en BD:
```python
# Cambiar de:
df = fetch_metric_data('PrecBolsNaci', ...)

# A:
df = obtener_datos_db('PrecBolsNaci', ...)
```

### 4. Agregar Más Funcionalidades
- **Comparación de períodos**: Año actual vs año anterior
- **Alertas de precios**: Notificar cuando precio > umbral
- **Estadísticas avanzadas**: Percentiles, desviación estándar
- **Exportar datos**: Botón para descargar CSV/Excel

---

## 🧪 Testing

### Casos de Prueba Sugeridos

1. **Rango de fechas normal (30 días)**
   - ✅ Debe mostrar gráfica con 2 líneas
   - ✅ Fichas KPI deben tener valores

2. **Rango muy amplio (>365 días)**
   - ✅ Debe mostrar mensaje de error

3. **Click en Precio Bolsa Nacional**
   - ✅ Modal se abre con tabla de 24 horas

4. **Click en Precio Escasez**
   - ✅ Modal NO se abre (solo diario)

5. **Fechas sin datos**
   - ✅ Gráfica muestra mensaje "No hay datos"

---

## 📝 Notas Técnicas

### Performance
- **Cache**: `fetch_metric_data` usa sistema de cache existente
  - Datos históricos (>7 días): cache 7 días
  - Datos recientes (<7 días): cache 24 horas
- **Carga inicial**: ~2-3 segundos para 30 días
- **Actualización**: Similar a carga inicial

### Limitaciones Conocidas
1. **PrecEscaAct no disponible**: No hay datos en API XM
2. **Máximo 365 días**: Restricción por performance
3. **Solo entidad Sistema**: Métricas no existen por Agente

### Compatibilidad
- **Dash**: 2.x
- **Plotly**: Compatible con versión actual
- **Bootstrap**: Usa `dash-bootstrap-components`

---

## 📚 Referencias

### Archivos Relacionados
- `pages/comercializacion.py` - Dashboard principal
- `utils/_xm.py` - Funciones de API XM
- `utils/components.py` - Componentes UI
- `utils/config.py` - Configuración de colores

### Métricas XM
- **Documentación**: [Portal API XM](https://www.xm.com.co/consumo/oferta-demanda-y-generacion/datos-historicos)
- **Nombres correctos**:
  - `PrecBolsNaci` (no PreciBolsNaci)
  - `PrecEsca` (activo)
  - `PrecEscaAct` (sin datos)

---

## ✅ Checklist de Implementación

- [x] Crear archivo `pages/comercializacion.py`
- [x] Implementar funciones de obtención de datos
- [x] Crear visualización de gráfica de líneas
- [x] Implementar fichas KPI
- [x] Configurar modal de detalle horario
- [x] Crear callbacks de actualización
- [x] Crear callback de modal interactivo
- [x] Verificar integración en sidebar
- [x] Documentar implementación
- [ ] Agregar métricas al ETL (futuro)
- [ ] Testing exhaustivo con usuarios
- [ ] Optimizaciones de performance

---

**Fecha de implementación**: 26 de noviembre de 2025  
**Versión**: 1.0  
**Estado**: ✅ Implementado y funcional
