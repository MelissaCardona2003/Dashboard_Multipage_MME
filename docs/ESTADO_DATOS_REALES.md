# Estado de Datos del Portal Energético

## 🚨 ESTADO ACTUAL DE LA API DE XM

**API de XM: ❌ NO DISPONIBLE**
- Servidor: `servapibi.xm.com.co`
- Error: Connection timeout
- Estado: La API de XM no está respondiendo desde hace varias horas

## 📊 Métricas de XM que DEBERÍAN Usarse (cuando funcione)

### 1. Fichas de Hidrología (`/generacion`)

| Ficha | Métrica XM | Entidad | Descripción | Estado Actual |
|-------|------------|---------|-------------|---------------|
| **Reservas Hídricas** | `VolEmbalDiar` | `Sistema` | Volumen de embalses en GWh y % | ❌ Usando fallback |
| **Aportes Hídricos** | `AporEner` | `Sistema` | Aportes de energía en GWh y % | ❌ Usando fallback |
| **Generación SIN** | `Gene` | `Sistema` | Generación total del SIN en GWh | ❌ Usando fallback |

**Código actual:**
```python
# pages/generacion.py líneas 43-53
df_reservas = fetch_metric_data('VolEmbalDiar', 'Sistema', fecha_inicio, fecha_fin)
df_aportes = fetch_metric_data('AporEner', 'Sistema', fecha_inicio, fecha_fin)
df_generacion = fetch_metric_data('Gene', 'Sistema', fecha_inicio, fecha_fin)
```

### 2. Fichas de Generación XM (`/generacion/fuentes`)

| Ficha | Cálculo | Métrica XM Base | Estado Actual |
|-------|---------|-----------------|---------------|
| **Generación Renovable %** | % de HIDRAULICA + EOLICA + SOLAR + BIOMASA | `Gene/Recurso` | ❌ Usando fallback |
| **Generación No Renovable %** | % de TERMICA GAS + TERMICA CARBON + otras | `Gene/Recurso` | ❌ Usando fallback |
| **Generación Total** | Suma total en GWh | `Gene/Recurso` | ❌ Usando fallback |

**Código actual:**
```python
# pages/generacion_fuentes_unificado.py líneas 51-76
df_gene_recurso = fetch_metric_data('Gene', 'Recurso', fecha_inicio, fecha_fin)

# Clasificar como renovable o no renovable
renovables = ['HIDRAULICA', 'EOLICA', 'SOLAR', 'BIOMASA']
df_gene_recurso['Es_Renovable'] = df_gene_recurso['Tipo'].apply(
    lambda x: any(r in str(x) for r in renovables)
)

gen_renovable = df_gene_recurso[df_gene_recurso['Es_Renovable'] == True]['Values_gwh'].sum()
gen_no_renovable = df_gene_recurso[df_gene_recurso['Es_Renovable'] == False]['Values_gwh'].sum()
```

## 🎭 DATOS ACTUALES: Reales vs Fallback

### Datos de Fallback (Estáticos - NO REALES)

**Archivo:** `pages/generacion.py`

```python
# Líneas 128-218 - DATOS INVENTADOS
reserva_gwh = 14000      # ❌ INVENTADO
reserva_pct = 83.29      # ❌ INVENTADO
aporte_gwh = 220.62      # ❌ INVENTADO
aporte_pct = 89.51       # ❌ INVENTADO
gen_gwh = 198.45         # ❌ INVENTADO
```

**Archivo:** `pages/generacion_fuentes_unificado.py`

```python
# Líneas 78-80 - DATOS INVENTADOS
pct_renovable = 70.31      # ❌ INVENTADO
pct_no_renovable = 29.69   # ❌ INVENTADO
gen_total = 26864.17       # ❌ INVENTADO
```

### ¿De Dónde Vienen Estos Números?

Los valores de fallback fueron **copiados de la página de XM**:
- https://sinergox.xm.com.co/Paginas/Home.aspx

**Pero son estáticos** - fueron tomados en un momento específico y NO se actualizan.

## ✅ SOLUCIÓN: Qué Hacer Cuando la API Funcione

### Opción 1: Esperar a que XM arregle su API
```bash
# Verificar estado
curl -I https://servapibi.xm.com.co/Lists --max-time 5
```

### Opción 2: Usar datos del día anterior (de respaldo)
XM publica datos oficiales en:
- https://www.xm.com.co/consumo/demanda-de-energia-sin

### Opción 3: Scraping directo de la página de XM
```python
# Hacer scraping de https://sinergox.xm.com.co/
# Extraer valores directamente del HTML
```

## 🔍 Verificar Estado de la API

Ejecutar este script para verificar:

```bash
python3 << 'EOF'
from pydataxm.pydataxm import ReadDB
from datetime import date, timedelta

try:
    api = ReadDB()
    print("✅ API conectada")
    
    # Probar consulta simple
    data = api.request_data(
        'Gene', 
        'Sistema', 
        date.today() - timedelta(days=7),
        date.today() - timedelta(days=1)
    )
    
    if data is not None:
        print(f"✅ Datos obtenidos: {len(data)} filas")
        print(f"Columnas: {data.columns.tolist()}")
    else:
        print("⚠️ API conectada pero sin datos")
        
except Exception as e:
    print(f"❌ API no disponible: {e}")
EOF
```

## 📝 Resumen

| Componente | Fuente de Datos | Estado | Acción Requerida |
|------------|----------------|--------|------------------|
| Reservas Hídricas | XM API: `VolEmbalDiar/Sistema` | ❌ Fallback | Esperar API |
| Aportes Hídricos | XM API: `AporEner/Sistema` | ❌ Fallback | Esperar API |
| Generación SIN | XM API: `Gene/Sistema` | ❌ Fallback | Esperar API |
| Gen. Renovable % | XM API: `Gene/Recurso` (calculado) | ❌ Fallback | Esperar API |
| Gen. No Renovable % | XM API: `Gene/Recurso` (calculado) | ❌ Fallback | Esperar API |
| Gen. Total | XM API: `Gene/Recurso` (suma) | ❌ Fallback | Esperar API |

## ⚠️ CONCLUSIÓN

**TODOS LOS DATOS ACTUALES SON DE FALLBACK (INVENTADOS)**

La aplicación está mostrando valores estáticos porque:
1. ❌ La API de XM no responde
2. ❌ No hay caché previo con datos reales
3. ✅ El sistema usa fallback para evitar errores 500

**Cuando la API de XM vuelva a funcionar:**
- ✅ Los datos se actualizarán automáticamente
- ✅ Se guardarán en caché
- ✅ Las fichas mostrarán valores reales
