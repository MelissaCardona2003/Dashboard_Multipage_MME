# 📊 EXPLICACIÓN: CÁLCULO DE DATOS EN DISTRIBUCIÓN DE DEMANDA

## Fecha: 24 de Noviembre 2025

---

## 🎯 RESUMEN EJECUTIVO

El dashboard de **Distribución de Demanda** muestra 3 tipos de cálculos:

1. **Gráfica Principal** → Demanda total del sistema (suma de todos los agentes)
2. **Gráfica por Agente** → Demanda de un agente específico seleccionado
3. **Modal Horario** → Desglose hora por hora del día seleccionado

---

## 1️⃣ GRÁFICA PRINCIPAL - DEMANDA TOTAL DEL SISTEMA

### 📍 Ubicación en código
**Archivo**: `pages/distribucion_demanda_unificado.py`  
**Funciones**: `obtener_demanda_comercial()` + `obtener_demanda_real()` + `crear_grafica_lineas_demanda()`

### 🔄 Flujo de datos

```
┌─────────────────────────────────────────────────────────────────┐
│ PASO 1: Obtener datos de fuente (SQLite o API XM)              │
└─────────────────────────────────────────────────────────────────┘
                            ↓
        función: obtener_datos_inteligente()
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ • SI fecha >= 2020 → Consulta SQLite (tabla metrics)           │
│ • SI fecha < 2020  → Consulta API XM                            │
│                                                                  │
│ SQL Query ejemplo:                                              │
│   SELECT fecha, recurso, valor_gwh                              │
│   FROM metrics                                                  │
│   WHERE metrica = 'DemaCome'                                    │
│     AND entidad = 'Agente'                                      │
│     AND fecha BETWEEN '2025-11-16' AND '2025-11-21'             │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 2: Procesar datos horarios                                │
└─────────────────────────────────────────────────────────────────┘
                            ↓
        función: procesar_datos_horarios(df, 'DemaCome')
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ CASO A: Datos de API XM (con columnas horarias)                │
│                                                                  │
│   Columnas: Values_Hour01, Values_Hour02, ..., Values_Hour24   │
│                                                                  │
│   Cálculo:                                                      │
│   1. Sumar 24 horas → Total_kWh                                 │
│      Total_kWh = Hour01 + Hour02 + ... + Hour24                 │
│                                                                  │
│   2. Convertir kWh → GWh                                        │
│      Demanda_GWh = Total_kWh / 1,000,000                        │
│                                                                  │
│   Ejemplo:                                                      │
│   - Hour01 = 50,000 kWh                                         │
│   - Hour02 = 48,000 kWh                                         │
│   - ...                                                         │
│   - Hour24 = 52,000 kWh                                         │
│   → Total_kWh = 1,200,000 kWh                                   │
│   → Demanda_GWh = 1.2 GWh                                       │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│ CASO B: Datos de SQLite (ya agregados)                         │
│                                                                  │
│   Columna: Value (ya en GWh)                                    │
│                                                                  │
│   Cálculo:                                                      │
│   Demanda_GWh = Value  (sin conversión)                         │
│                                                                  │
│   NOTA: SQLite guarda datos pre-agregados por el ETL           │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 3: Crear DataFrame resultado                              │
└─────────────────────────────────────────────────────────────────┘
                            ↓
    DataFrame con columnas:
    - Fecha: datetime
    - Codigo_Agente: str (ej: "CASC", "CDNC")
    - Demanda_GWh: float
    - Tipo: str ('DemaCome' o 'DemaReal')
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 4: Agregar por fecha (SUMA DE TODOS LOS AGENTES)          │
└─────────────────────────────────────────────────────────────────┘
                            ↓
    función: crear_grafica_lineas_demanda()
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Código en crear_grafica_lineas_demanda():                      │
│                                                                  │
│   df_come_agg = df_demanda_come.groupby('Fecha', as_index=False)['Demanda_GWh'].sum()
│   df_real_agg = df_demanda_real.groupby('Fecha', as_index=False)['Demanda_GWh'].sum()
│                                                                  │
│ Ejemplo:                                                        │
│                                                                  │
│ Antes de agrupar (múltiples agentes):                          │
│ ┌────────────┬──────────────┬─────────────┐                    │
│ │   Fecha    │ Codigo_Agente│ Demanda_GWh │                    │
│ ├────────────┼──────────────┼─────────────┤                    │
│ │ 2025-11-21 │    CASC      │    1.5      │                    │
│ │ 2025-11-21 │    CDNC      │    0.3      │                    │
│ │ 2025-11-21 │    AAGG      │    0.0002   │                    │
│ │ 2025-11-21 │    ...       │    ...      │  (92 agentes)     │
│ │ 2025-11-21 │    EPSA      │    2.1      │                    │
│ └────────────┴──────────────┴─────────────┘                    │
│                                                                  │
│ Después de agrupar (suma total):                               │
│ ┌────────────┬─────────────┐                                   │
│ │   Fecha    │ Demanda_GWh │                                   │
│ ├────────────┼─────────────┤                                   │
│ │ 2025-11-21 │   44.05     │  ← Suma de 92 agentes            │
│ │ 2025-11-20 │   42.30     │                                   │
│ │ 2025-11-19 │   43.15     │                                   │
│ └────────────┴─────────────┘                                   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ RESULTADO: Gráfica muestra evolución diaria del SISTEMA        │
│                                                                  │
│   📈 Línea azul: Demanda Comercial agregada                    │
│   📈 Línea verde punteada: Demanda Real agregada               │
│                                                                  │
│   Cada punto = SUMA de todos los 92 agentes para ese día       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2️⃣ GRÁFICA POR AGENTE ESPECÍFICO

### 📍 Ubicación en código
**Callback**: `actualizar_datos_distribucion()`  
**Líneas**: ~587-650

### 🔄 Flujo de datos

```
┌─────────────────────────────────────────────────────────────────┐
│ Usuario selecciona agente en dropdown                           │
└─────────────────────────────────────────────────────────────────┘
                            ↓
    ej: selector-agente-distribucion = 'CASC'
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 1: Determinar códigos de agentes a consultar              │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Código en actualizar_datos_distribucion():                     │
│                                                                  │
│   codigos_agentes = None  # Por defecto: todos                 │
│   agente_nombre = "Todos los Agentes"                          │
│                                                                  │
│   if codigo_agente and codigo_agente != 'TODOS':               │
│       codigos_agentes = [codigo_agente]  # ej: ['CASC']        │
│       agente_nombre = "Codensa S.A. ESP"  # nombre real        │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 2: Obtener datos con FILTRO de agente                     │
└─────────────────────────────────────────────────────────────────┘
                            ↓
    obtener_demanda_comercial(fecha_inicio, fecha_fin, ['CASC'])
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Dentro de obtener_demanda_comercial():                         │
│                                                                  │
│   1. Obtener TODOS los datos:                                  │
│      df = obtener_datos_inteligente('DemaCome', 'Agente', ...)│
│                                                                  │
│   2. SI codigos_agentes NO es None:                            │
│      → Aplicar filtro:                                          │
│                                                                  │
│      df = df[df['Values_code'].isin(['CASC'])].copy()          │
│                                                                  │
│   Ejemplo de filtrado:                                         │
│                                                                  │
│   ANTES del filtro (todos los agentes):                        │
│   ┌────────────┬──────────────┬─────────────┐                  │
│   │   Fecha    │ Values_code  │ Demanda_GWh │                  │
│   ├────────────┼──────────────┼─────────────┤                  │
│   │ 2025-11-21 │    CASC      │    1.5      │ ← mantener      │
│   │ 2025-11-21 │    CDNC      │    0.3      │ ← eliminar      │
│   │ 2025-11-21 │    AAGG      │    0.0002   │ ← eliminar      │
│   │ 2025-11-21 │    EPSA      │    2.1      │ ← eliminar      │
│   └────────────┴──────────────┴─────────────┘                  │
│                                                                  │
│   DESPUÉS del filtro (solo CASC):                              │
│   ┌────────────┬──────────────┬─────────────┐                  │
│   │   Fecha    │ Values_code  │ Demanda_GWh │                  │
│   ├────────────┼──────────────┼─────────────┤                  │
│   │ 2025-11-21 │    CASC      │    1.5      │                  │
│   │ 2025-11-20 │    CASC      │    1.4      │                  │
│   │ 2025-11-19 │    CASC      │    1.6      │                  │
│   └────────────┴──────────────┴─────────────┘                  │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 3: Procesar datos horarios (igual que antes)              │
└─────────────────────────────────────────────────────────────────┘
                            ↓
    procesar_datos_horarios(df_filtrado, 'DemaCome')
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 4: Agregar por fecha (solo ese agente)                    │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Código en crear_grafica_lineas_demanda():                      │
│                                                                  │
│   df_come_agg = df_demanda_come.groupby('Fecha')['Demanda_GWh'].sum()
│                                                                  │
│   Como solo hay 1 agente (CASC), el SUM es el valor del agente │
│                                                                  │
│   ┌────────────┬─────────────┐                                 │
│   │   Fecha    │ Demanda_GWh │                                 │
│   ├────────────┼─────────────┤                                 │
│   │ 2025-11-21 │    1.5      │  ← Solo CASC                   │
│   │ 2025-11-20 │    1.4      │                                 │
│   │ 2025-11-19 │    1.6      │                                 │
│   └────────────┴─────────────┘                                 │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ RESULTADO: Gráfica muestra evolución del AGENTE seleccionado   │
│                                                                  │
│   📈 Título: "Evolución Temporal - Codensa S.A. ESP"           │
│   📈 Datos: Solo ese agente, sin suma de otros                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3️⃣ MODAL HORARIO - DESGLOSE HORA POR HORA

### 📍 Ubicación en código
**Callback**: `mostrar_detalle_horario()`  
**Líneas**: ~681-820

### 🔄 Flujo de datos

```
┌─────────────────────────────────────────────────────────────────┐
│ Usuario hace click en un punto de la gráfica                    │
└─────────────────────────────────────────────────────────────────┘
                            ↓
    clickData = { 'points': [{ 'x': '2025-11-21', ... }] }
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 1: Extraer fecha seleccionada                             │
└─────────────────────────────────────────────────────────────────┘
                            ↓
    fecha_str = '2025-11-21'
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 2: Obtener datos horarios AGREGADOS de SQLite             │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Código:                                                         │
│                                                                  │
│   df_horas_come = db_manager.get_hourly_data_aggregated(       │
│       'DemaCome', 'Agente', '2025-11-21'                        │
│   )                                                             │
│                                                                  │
│   df_horas_real = db_manager.get_hourly_data_aggregated(       │
│       'DemaReal', 'Agente', '2025-11-21'                        │
│   )                                                             │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Función get_hourly_data_aggregated():                          │
│                                                                  │
│   SQL Query:                                                    │
│   SELECT hora, SUM(valor_mwh) as valor_mwh                     │
│   FROM metrics_hourly                                           │
│   WHERE metrica = 'DemaCome'                                    │
│     AND entidad = 'Agente'                                      │
│     AND fecha = '2025-11-21'                                    │
│   GROUP BY hora                                                 │
│   ORDER BY hora                                                 │
│                                                                  │
│   Resultado DemaCome:                                           │
│   ┌──────┬────────────┐                                        │
│   │ hora │ valor_mwh  │                                        │
│   ├──────┼────────────┤                                        │
│   │  1   │ 1315.18    │  ← Suma de 92 agentes en hora 1       │
│   │  2   │ 1211.12    │  ← Suma de 92 agentes en hora 2       │
│   │  3   │ 1183.24    │                                        │
│   │ ...  │  ...       │                                        │
│   │  24  │ 2024.45    │  ← Suma de 92 agentes en hora 24      │
│   └──────┴────────────┘                                        │
│                                                                  │
│   Total día: 44,051.36 MWh = 44.05 GWh                         │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 3: Crear DataFrame con 24 horas                           │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Código:                                                         │
│                                                                  │
│   # DataFrame base con horas 1-24                               │
│   df_horas = pd.DataFrame({'hora': range(1, 25)})              │
│                                                                  │
│   # Merge con DemaCome                                          │
│   df_horas = df_horas.merge(                                    │
│       df_horas_come[['hora', 'valor_mwh']],                     │
│       on='hora',                                                │
│       how='left'                                                │
│   ).rename(columns={'valor_mwh': 'DemaCome_MWh'})              │
│                                                                  │
│   # Merge con DemaReal                                          │
│   df_horas = df_horas.merge(                                    │
│       df_horas_real[['hora', 'valor_mwh']],                     │
│       on='hora',                                                │
│       how='left'                                                │
│   ).rename(columns={'valor_mwh': 'DemaReal_MWh'})              │
│                                                                  │
│   # Convertir MWh → GWh                                         │
│   df_horas['DemaCome_GWh'] = df_horas['DemaCome_MWh'] / 1000   │
│   df_horas['DemaReal_GWh'] = df_horas['DemaReal_MWh'] / 1000   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 4: Calcular DIFERENCIA EN PORCENTAJE                      │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Fórmula:                                                        │
│                                                                  │
│   Diferencia_% = ((Real - Comercial) / Comercial) × 100        │
│                                                                  │
│ Ejemplo para Hora 1:                                           │
│   DemaCome = 1315.18 MWh = 1.315 GWh                           │
│   DemaReal = 1315.18 MWh = 1.315 GWh                           │
│                                                                  │
│   Diferencia_% = ((1.315 - 1.315) / 1.315) × 100 = 0.00%      │
│                                                                  │
│ Ejemplo para Hora 12 (si hubiera diferencia):                 │
│   DemaCome = 1800.00 MWh = 1.800 GWh                           │
│   DemaReal = 1890.00 MWh = 1.890 GWh                           │
│                                                                  │
│   Diferencia_% = ((1.890 - 1.800) / 1.800) × 100 = +5.00%     │
│                                                                  │
│ Casos especiales:                                              │
│   • Si Comercial = 0 y Real > 0 → Diferencia = 100%           │
│   • Si ambos = 0 → Diferencia = 0%                             │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 5: Calcular PARTICIPACIÓN HORARIA                         │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Fórmula:                                                        │
│                                                                  │
│   Participacion_% = (Demanda_hora / SUM(24_horas)) × 100       │
│                                                                  │
│ Ejemplo:                                                        │
│   Hora 1: 1315.18 MWh                                          │
│   Total día: 44,051.36 MWh                                     │
│                                                                  │
│   Participacion_% = (1315.18 / 44051.36) × 100 = 2.99%        │
│                                                                  │
│   Hora 18 (pico): 2200.00 MWh                                  │
│   Participacion_% = (2200.00 / 44051.36) × 100 = 4.99%        │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 6: Formatear tabla                                        │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Resultado en modal:                                            │
│                                                                  │
│ ┌─────────┬─────────────┬─────────────┬──────────────┬─────────┐│
│ │  Hora   │Demanda Come │Demanda Real │ Diferencia   │Particip.││
│ │         │    (GWh)    │    (GWh)    │     (%)      │   (%)   ││
│ ├─────────┼─────────────┼─────────────┼──────────────┼─────────┤│
│ │ Hora 01 │   1.3152    │   1.3152    │    +0.00%    │  2.99%  ││
│ │ Hora 02 │   1.2111    │   1.2111    │    +0.00%    │  2.75%  ││
│ │ Hora 03 │   1.1832    │   1.1832    │    +0.00%    │  2.69%  ││
│ │   ...   │     ...     │     ...     │      ...     │   ...   ││
│ │ Hora 24 │   2.0244    │   2.0244    │    +0.00%    │  4.60%  ││
│ ├─────────┼─────────────┼─────────────┼──────────────┼─────────┤│
│ │  TOTAL  │  44.0514    │  44.0514    │    +0.00%    │ 100.00% ││
│ └─────────┴─────────────┴─────────────┴──────────────┴─────────┘│
│                                                                  │
│ • Verde: Diferencia positiva (Real > Comercial)                │
│ • Rojo: Diferencia negativa (Real < Comercial)                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔑 DIFERENCIAS CLAVE ENTRE CÁLCULOS

| Aspecto | Gráfica Principal | Gráfica por Agente | Modal Horario |
|---------|-------------------|-------------------|---------------|
| **Fuente de datos** | SQLite `metrics` o API XM | SQLite `metrics` o API XM | SQLite `metrics_hourly` |
| **Granularidad temporal** | Diaria (1 punto por día) | Diaria (1 punto por día) | Horaria (24 puntos por día) |
| **Agregación espacial** | SUMA de ~50 agentes | 1 agente específico | SUMA de ~50 agentes |
| **Cálculo principal** | `SUM(Demanda_GWh) GROUP BY Fecha` | `Demanda_GWh WHERE agente=X` | `SUM(valor_mwh) GROUP BY hora` |
| **Unidades** | GWh (Giga Watt hora) | GWh | GWh (convertido de MWh) |
| **Conversión** | kWh ÷ 1,000,000 → GWh | kWh ÷ 1,000,000 → GWh | MWh ÷ 1,000 → GWh |
| **Filtro aplicado** | Ninguno (todos) | `df[df['Values_Code']==codigo]` | Ninguno (todos) |
| **Triggered por** | Botón "Actualizar" | Dropdown + Botón | Click en gráfica |

### ⚠️ CORRECCIÓN IMPLEMENTADA (24 Nov 2025)

**Problema detectado**: Al seleccionar un agente específico, la gráfica mostraba los mismos datos que la gráfica general.

**Causa raíz**: La función `obtener_datos_inteligente()` en `utils/_xm.py` no estaba creando la columna `Values_Code` cuando obtenía datos de SQLite, por lo que el filtro `df[df['Values_Code'].isin(codigos_agentes)]` no funcionaba.

**Solución aplicada**: Agregado mapeo explícito de columna `recurso` → `Values_Code` en línea ~530 de `utils/_xm.py`:

```python
# Crear columna Values_Code con el código (para filtrado por agente/recurso)
if 'recurso' in df.columns:
    df['Values_Code'] = df['recurso']
    df['Values_code'] = df['recurso']  # Alias lowercase
```

**Validación**: 
- Sistema completo: 44.04 GWh (100%)
- Solo CASC: 2.53 GWh (5.75%) ✅
- Solo CDNC: 0.62 GWh (1.40%) ✅

---

## 📐 FÓRMULAS UTILIZADAS

### 1. Conversión de unidades

```python
# API XM entrega datos en kWh (kilo Watt hora)
# Dashboard muestra en GWh (Giga Watt hora)

# Para datos diarios:
Demanda_GWh = (SUM(Hour01...Hour24)) / 1,000,000

# Ejemplo:
# Hour01 = 50,000 kWh
# Hour02 = 48,000 kWh
# ...
# Hour24 = 52,000 kWh
# Total = 1,200,000 kWh
# Demanda_GWh = 1,200,000 / 1,000,000 = 1.2 GWh
```

### 2. Agregación por fecha (gráfica principal)

```python
# Pandas groupby
df_come_agg = df_demanda_come.groupby('Fecha', as_index=False)['Demanda_GWh'].sum()

# Equivalente SQL:
SELECT fecha, SUM(Demanda_GWh) as Demanda_Total
FROM df_demanda_come
GROUP BY fecha
ORDER BY fecha

# Ejemplo:
# Antes: 92 filas (1 por agente) para fecha 2025-11-21
# Después: 1 fila con la suma de los 92 agentes
```

### 3. Filtrado por agente

```python
# Python
df = df[df['Values_code'].isin(['CASC'])].copy()

# Equivalente SQL:
SELECT *
FROM df
WHERE Values_code IN ('CASC')

# Reduce el dataset de 92 agentes a solo 1
```

### 4. Diferencia en porcentaje (modal)

```python
# Fórmula
Diferencia_% = ((DemaReal - DemaCome) / DemaCome) * 100

# Casos:
# Real > Comercial → Positivo (+5.00%) → Verde
# Real < Comercial → Negativo (-3.50%) → Rojo
# Real = Comercial → Cero (0.00%) → Neutro
```

### 5. Participación horaria (modal)

```python
# Fórmula
Participacion_% = (Demanda_hora / SUM(Demanda_24_horas)) * 100

# Ejemplo:
# Hora 1: 1315.18 MWh
# Total: 44051.36 MWh
# Participacion = (1315.18 / 44051.36) * 100 = 2.99%

# Validación: SUM(Participacion_24_horas) = 100.00%
```

---

## 🗄️ ESTRUCTURA DE DATOS EN SQLite

### Tabla `metrics` (datos agregados diarios)

```sql
CREATE TABLE metrics (
    id INTEGER PRIMARY KEY,
    fecha TEXT,           -- 'YYYY-MM-DD'
    metrica TEXT,         -- 'DemaCome', 'DemaReal'
    entidad TEXT,         -- 'Agente', 'Sistema'
    recurso TEXT,         -- Código del agente (ej: 'CASC')
    valor_gwh REAL,       -- Valor ya agregado en GWh
    unidad TEXT,          -- 'GWh'
    fecha_actualizacion TIMESTAMP
);

-- Ejemplo de registros:
┌────────────┬──────────┬─────────┬────────┬───────────┐
│   fecha    │ metrica  │ entidad │recurso │valor_gwh  │
├────────────┼──────────┼─────────┼────────┼───────────┤
│2025-11-21  │DemaCome  │ Agente  │ CASC   │  1.5      │
│2025-11-21  │DemaCome  │ Agente  │ CDNC   │  0.3      │
│2025-11-21  │DemaCome  │ Agente  │ AAGG   │  0.0002   │
│    ...     │   ...    │  ...    │  ...   │   ...     │
└────────────┴──────────┴─────────┴────────┴───────────┘
```

### Tabla `metrics_hourly` (datos horarios por agente)

```sql
CREATE TABLE metrics_hourly (
    id INTEGER PRIMARY KEY,
    fecha TEXT,           -- 'YYYY-MM-DD'
    metrica TEXT,         -- 'DemaCome', 'DemaReal'
    entidad TEXT,         -- 'Agente'
    recurso TEXT,         -- Código del agente
    hora INTEGER,         -- 1 a 24
    valor_mwh REAL,       -- Valor en MWh (NO GWh)
    unidad TEXT,          -- 'MWh'
    fecha_actualizacion TIMESTAMP,
    UNIQUE(fecha, metrica, entidad, recurso, hora)
);

-- Ejemplo de registros:
┌────────────┬──────────┬─────────┬────────┬──────┬───────────┐
│   fecha    │ metrica  │ entidad │recurso │ hora │ valor_mwh │
├────────────┼──────────┼─────────┼────────┼──────┼───────────┤
│2025-11-21  │DemaCome  │ Agente  │ CASC   │  1   │  50.12    │
│2025-11-21  │DemaCome  │ Agente  │ CASC   │  2   │  48.30    │
│2025-11-21  │DemaCome  │ Agente  │ CASC   │  3   │  47.85    │
│    ...     │   ...    │  ...    │  ...   │ ...  │   ...     │
│2025-11-21  │DemaCome  │ Agente  │ CASC   │ 24   │  55.90    │
│2025-11-21  │DemaCome  │ Agente  │ CDNC   │  1   │  10.22    │
│    ...     │   ...    │  ...    │  ...   │ ...  │   ...     │
└────────────┴──────────┴─────────┴────────┴──────┴───────────┘

-- Total registros por día:
-- 92 agentes × 24 horas × 2 métricas = 4,416 registros/día
```

---

## 🎯 RESUMEN DE FLUJOS

### Flujo 1: Cargar gráfica principal (todos los agentes)
```
Usuario abre /distribucion
    ↓
Callback inicial carga datos últimos 7 días
    ↓
obtener_demanda_comercial(fecha_inicio, fecha_fin, codigos_agentes=None)
    ↓
obtener_datos_inteligente('DemaCome', 'Agente', ...) → SQLite
    ↓
procesar_datos_horarios(df, 'DemaCome') → Suma 24 horas
    ↓
crear_grafica_lineas_demanda() → groupby('Fecha').sum()
    ↓
Gráfica muestra SUMA de 92 agentes por día
```

### Flujo 2: Filtrar por agente específico
```
Usuario selecciona "CASC" en dropdown
    ↓
Usuario presiona "Actualizar Datos"
    ↓
Callback actualizar_datos_distribucion(codigo_agente='CASC')
    ↓
obtener_demanda_comercial(..., codigos_agentes=['CASC'])
    ↓
df = df[df['Values_code'].isin(['CASC'])] → Filtro
    ↓
procesar_datos_horarios(df_filtrado, 'DemaCome')
    ↓
crear_grafica_lineas_demanda() → Solo datos de CASC
    ↓
Gráfica muestra evolución de CASC únicamente
```

### Flujo 3: Ver detalle horario de un día
```
Usuario hace click en punto de gráfica (ej: 2025-11-21)
    ↓
Callback mostrar_detalle_horario(clickData)
    ↓
Extraer fecha: '2025-11-21'
    ↓
db_manager.get_hourly_data_aggregated('DemaCome', 'Agente', fecha)
    ↓
SQL: SELECT hora, SUM(valor_mwh) GROUP BY hora
    ↓
Merge DemaCome + DemaReal por hora
    ↓
Calcular Diferencia_% y Participacion_%
    ↓
Modal muestra tabla con 24 horas + TOTAL
```

---

## 📝 NOTAS IMPORTANTES

1. **Datos en SQLite están pre-agregados**: La tabla `metrics` ya tiene el valor diario total en GWh, no necesita sumar columnas horarias.

2. **Datos de API XM vienen con columnas horarias**: Requieren sumar `Values_Hour01` a `Values_Hour24` y convertir kWh → GWh.

3. **Modal usa tabla separada**: `metrics_hourly` almacena datos desagregados por hora en MWh (no GWh).

4. **Diferencia entre MWh y GWh**:
   - `metrics_hourly`: MWh (Mega Watt hora)
   - `metrics`: GWh (Giga Watt hora)
   - Conversión: 1 GWh = 1,000 MWh

5. **Participación horaria siempre suma 100%**: Es un porcentaje del total diario, no un valor absoluto.

---

**FIN DE LA EXPLICACIÓN**
