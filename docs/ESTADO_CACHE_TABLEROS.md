# Estado de Cache y Datos Históricos por Tablero

## ✅ Tableros CON datos históricos

Estos tableros usan `fetch_metric_data()` que tiene el sistema de cache con datos históricos:

| Tablero | Página | Datos Cacheados |
|---------|--------|-----------------|
| **Generación** | `/generacion` | ✅ Reservas, Aportes, Generación SIN |
| **Generación por Fuentes** | `/generacion/fuentes` | ✅ Generación por Recurso (Renovable/No Renovable) |

### Métricas con cache histórico:
- `VolEmbalDiar/Sistema` - Reservas Hídricas
- `AporEner/Sistema` - Aportes Hídricos
- `Gene/Sistema` - Generación SIN
- `Gene/Recurso` - Generación por Recurso (para calcular % renovable)

---

## ⚠️ Tableros SIN datos históricos (usan API directa)

Estos tableros usan `get_objetoAPI()` o `ReadDB()` directamente, **sin cache**:

| Tablero | Página | Estado cuando API cae |
|---------|--------|----------------------|
| **Hidrología** | `/generacion/hidraulica/hidrologia` | ❌ Sin datos |
| **Métricas** | `/metricas` | ❌ Datos de ejemplo |
| **Generación Fuentes (gráficos)** | `/generacion/fuentes` | ❌ Sin gráficos |
| **Otros tableros** | Todos los demás | ❌ Sin datos |

### Cantidad de usos de API directa:
- `generacion_hidraulica_hidrologia.py`: **18 llamadas** a `get_objetoAPI()`
- `generacion_fuentes_unificado.py`: **3 llamadas** a `get_objetoAPI()`
- `metricas.py`: **2 llamadas** (1 a `get_objetoAPI()`, 1 a `ReadDB()`)
- `generacion.py`: **1 llamada** a `ReadDB()` (para gráfico adicional)

---

## 🔧 Solución: Extender Cache a Todos los Tableros

Para que TODOS los tableros usen datos históricos, necesitamos:

### Opción 1: Migrar a `fetch_metric_data()` (Recomendado)

Cambiar todas las llamadas de:
```python
objetoAPI = get_objetoAPI()
df = objetoAPI.request_data(metric, entity, start, end)
```

Por:
```python
df = fetch_metric_data(metric, entity, start, end)
```

**Ventajas:**
- ✅ Cache automático con datos históricos
- ✅ Fallback en cascada (API → Cache → Histórico → Fallback)
- ✅ Código más simple
- ✅ Menor carga en la API

**Archivos a modificar:**
1. `generacion_hidraulica_hidrologia.py` - 18 funciones
2. `generacion_fuentes_unificado.py` - 3 callbacks
3. `metricas.py` - 2 funciones
4. `generacion.py` - 1 callback adicional

### Opción 2: Crear funciones de cache específicas

Crear wrappers para cada tipo de dato:
```python
@cached_function(cache_type='hidrologia')
def fetch_hidrologia_data(metric, entity, start, end):
    # Implementar con fallback histórico
    pass
```

**Ventajas:**
- ✅ Configuración específica por tipo de dato
- ✅ Cache más granular
- ⚠️ Más código a mantener

---

## 📊 Impacto Actual

### Cuando API XM está CAÍDA:

| Sección | Fichas | Gráficos | Tablas |
|---------|--------|----------|--------|
| `/generacion` | ✅ Con históricos | ❌ Sin datos | N/A |
| `/generacion/fuentes` | ✅ Con históricos | ❌ Sin datos | ❌ Sin datos |
| `/generacion/hidraulica/hidrologia` | ❌ Sin datos | ❌ Sin datos | ❌ Sin datos |
| `/metricas` | N/A | ❌ Datos ejemplo | ❌ Datos ejemplo |

### Cuando API XM está FUNCIONANDO:

| Sección | Fichas | Gráficos | Tablas |
|---------|--------|----------|--------|
| Todo | ✅ Datos reales | ✅ Datos reales | ✅ Datos reales |

---

## 🎯 Recomendación

**Migrar todos los tableros a usar `fetch_metric_data()`**

Esto garantizará que:
1. ✅ Todos los tableros tengan datos históricos como fallback
2. ✅ Cache uniforme en toda la aplicación
3. ✅ Mejor experiencia de usuario durante caídas de API
4. ✅ Reducción de carga en servidores de XM

---

## 🔍 Verificar Estado Actual

```bash
# Ver qué datos están cacheados
ls -lh /tmp/portal_energetico_cache/

# Ver tableros usando cache histórico
grep -r "fetch_metric_data" pages/*.py

# Ver tableros usando API directa (sin cache)
grep -r "get_objetoAPI()\|ReadDB()" pages/*.py
```

---

## ⏭️ Siguiente Paso

¿Quieres que **migremos todos los tableros** para usar el sistema de cache con datos históricos?

Esto haría que TODA la aplicación tenga datos (históricos) incluso cuando la API de XM esté caída.
