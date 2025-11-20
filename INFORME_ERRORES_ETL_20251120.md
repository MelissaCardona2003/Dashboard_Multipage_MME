# INFORME DE ERRORES CRÍTICOS EN ETL
**Fecha:** 2025-11-20 13:15
**Responsable:** Auditoría de datos SQLite vs API XM

---

## 🎯 RESUMEN EJECUTIVO

El análisis reveló que **SQLite contenía datos INVENTADOS** que NO existen en la API de XM. El ETL tiene múltiples errores que impiden la correcta actualización de datos.

---

## ❌ ERRORES IDENTIFICADOS

### 1. **DATOS INVENTADOS (CRÍTICO)**
**Métrica:** `Gene/Sistema` (Generación Sistema)

**Problema:**
- SQLite mostraba: `2025-11-19: 250.50 GWh`
- API XM real: Última fecha `2025-11-17` (NO existe 2025-11-19)

**Impacto:**
- ❌ Dashboard mostraba datos falsos a usuarios
- ❌ Métricas de generación incorrectas
- ❌ Decisiones basadas en información inexistente

**Causa raíz:**
- ETL insertó registros con fechas futuras
- Constraint UNIQUE no detectó duplicados por diferencia en campo `recurso`:
  - Algunos registros: `recurso = '_SISTEMA_'`
  - Otros registros: `recurso = 'Sistema'`

**Solución aplicada:**
```sql
-- Eliminados 1,825 registros duplicados
DELETE FROM metrics WHERE id NOT IN (...)
-- Eliminado 1 registro de fecha inventada (2025-11-19)
DELETE FROM metrics WHERE fecha = '2025-11-19' AND metrica = 'Gene'
```

---

### 2. **ERROR EN MAPEO DE EMBALSES (ALTO)**
**Métrica:** `VoluUtilDiarEner/Embalse`, `CapaUtilDiarEner/Embalse`

**Problema:**
```
ERROR:root:❌ Error poblando VoluUtilDiarEner/Embalse: 
The truth value of a DataFrame is ambiguous. Use a.empty, a.bool(), a.item(), a.any() or a.all().
```

**Ubicación:** `/home/admonctrlxm/server/etl/etl_xm_to_sqlite.py`, líneas 310-340

**Causa:**
```python
# FIX MAPEO EMBALSES: API devuelve nombres completos, necesitamos códigos
if entity == 'Embalse' and recurso is not None:
    catalogos_nombres = db_manager.get_catalogo('ListadoEmbalses')
    if catalogos_nombres:  # ❌ Error: DataFrame no se puede evaluar como bool
        ...
```

**Impacto:**
- ❌ VoluUtilDiarEner/Embalse: NO se actualiza desde 2025-11-18
- ❌ CapaUtilDiarEner/Embalse: NO se actualiza desde 2025-11-18
- ⚠️ API XM tiene datos de 2025-11-19, pero SQLite NO los guarda
- ❌ Métricas de "Reservas Hídricas" desactualizadas

**Estado actual:**
- API XM: `2025-11-19` (120 registros)
- SQLite: `2025-11-18` (96 registros)
- **Diferencia:** 1 día de retraso

---

### 3. **ERROR EN MÉTRICAS SIN COLUMN 'Value' (MEDIO)**
**Métricas afectadas:**
- `ListadoEmbalses/Sistema`
- `ListadoRios/Sistema`
- `DemaCome/Agente`
- `DemaReal/Agente`
- `ListadoRecursos/Sistema`
- `ListadoAgentes/Sistema`

**Problema:**
```
ERROR:root:❌ ListadoEmbalses/Sistema: Falta columna 'Value'
ERROR:root:❌ DemaCome/Agente: Falta columna 'Value'
```

**Causa:**
```python
# Línea 287 en etl/etl_xm_to_sqlite.py
if 'Value' not in df.columns:
    logging.error(f"❌ {metric}/{entity}: Falta columna 'Value'")
    return 0  # ❌ Sale sin procesar
```

**Impacto:**
- ❌ Catálogos NO se actualizan (ListadoEmbalses, ListadoRios, etc.)
- ❌ Demanda por Agente NO se guarda
- ⚠️ Datos históricos de distribución incompletos

**Estado:**
- 6 de 18 métricas fallan completamente
- 33% de tasa de error en ETL

---

### 4. **VALIDACIÓN INCORRECTA DE DemaCome (MEDIO)**
**Métrica:** `DemaCome/Sistema`

**Problema:**
```python
# Línea 304: Validación rechaza datos válidos
if metric == 'DemaCome' and entity == 'Sistema' and valor_gwh < 100:
    logging.warning(f"⚠️ Valor {valor_gwh:.2f} GWh muy bajo, RECHAZADO")
    continue  # ❌ Saltar este registro
```

**Logs:**
```
WARNING:root:⚠️ DemaCome/Sistema (2025-11-16): Valor 42.43 GWh muy bajo, RECHAZADO
WARNING:root:⚠️ DemaCome/Sistema (2025-11-17): Valor 43.12 GWh muy bajo, RECHAZADO
```

**Impacto:**
- ❌ Datos reales de demanda rechazados incorrectamente
- ⚠️ API XM tiene datos hasta `2025-11-17`
- ❌ SQLite solo tiene hasta `2025-11-15`
- **Pérdida:** 2 días de datos de demanda

**Nota:** Valores de 42-43 GWh pueden ser correctos para días parciales o datos horarios no agregados correctamente.

---

## 📊 ESTADÍSTICAS GENERALES DEL ETL

**Ejecución:** 2025-11-20 13:02:06 - 13:13:51 (11.8 min)

```
Total métricas procesadas: 18
  ✅ Exitosas: 10 (55%)
  ❌ Fallidas: 8 (45%)

Total registros insertados: 526,988
Base de datos: 583,486 registros totales (346.83 MB)
Rango: 2020-11-18 a 2025-11-19
```

---

## 🔧 CORRECCIONES APLICADAS

### ✅ 1. Limpieza de datos incorrectos
```python
# Eliminados 1,825 registros duplicados
# Eliminado 1 registro de fecha inventada (2025-11-19)
```

### ✅ 2. Verificación API vs SQLite
```python
# Confirmado que API XM tiene fechas más recientes
VoluUtilDiarEner/Embalse: API=2025-11-19, SQLite=2025-11-18 ❌
Gene/Sistema: API=2025-11-17, SQLite=2025-11-17 ✅
DemaCome/Sistema: API=2025-11-17, SQLite=2025-11-15 ❌
```

---

## 🚨 ACCIONES REQUERIDAS

### URGENTE (Hoy)
1. ✅ **Limpiar datos inventados** (COMPLETADO)
2. ⚠️ **Corregir error de DataFrame en mapeo embalses**
3. ⚠️ **Ajustar validación de DemaCome** (threshold muy alto)

### PRIORITARIO (Esta semana)
4. **Implementar manejo de métricas sin columna 'Value'**
   - Catálogos tienen estructura diferente
   - Crear función separada: `poblar_catalogo_temporal()`
5. **Unificar campo `recurso` en constraints**
   - Normalizar: `'Sistema'` → `'_SISTEMA_'` siempre
   - Evitar duplicados futuros

### MEJORAS (Mes)
6. **Agregar validación post-ETL**
   - Comparar fechas máximas API vs SQLite
   - Alertar si diferencia > 1 día
7. **Logging estructurado**
   - Guardar resumen en JSON
   - Dashboard de monitoreo ETL

---

## 📈 DATOS CORRECTOS DESPUÉS DE LIMPIEZA

```
Gene/Sistema:
  ✅ 2025-11-17: 212.00 GWh (última fecha REAL de API XM)
  ✅ 2025-11-16: 204.99 GWh
  ✅ 2025-11-15: 226.85 GWh

AporEner/Sistema:
  ✅ 2025-11-19: Actualizado correctamente

Gene/Recurso:
  ✅ 459,150 registros (2020-2025) actualizados
```

---

## 💡 RECOMENDACIONES

1. **Monitoreo continuo:**
   - Ejecutar comparación API vs SQLite después de cada ETL
   - Alertar diferencias > 1 día

2. **Testing:**
   - Crear suite de tests unitarios para ETL
   - Validar estructura de datos antes de insertar

3. **Rollback automático:**
   - Si ETL falla > 30%, revertir cambios
   - Mantener backup antes de cada ejecución

4. **Documentación:**
   - Especificar estructura esperada por métrica
   - Mapear diferencias entre API y SQLite

---

## 🎓 LECCIONES APRENDIDAS

1. **NUNCA asumir que datos en BD son correctos**
   - Siempre validar contra fuente original (API)
   
2. **Constraints UNIQUE deben ser precisos**
   - `'Sistema'` ≠ `'_SISTEMA_'` en SQLite
   - Normalizar datos antes de insertar

3. **Validaciones deben ser flexibles**
   - Threshold de 100 GWh muy alto para DemaCome
   - Considerar contexto temporal (días parciales)

4. **Errores silenciosos son peligrosos**
   - DataFrame ambiguity no detuvo el ETL
   - Métricas fallaron sin alertas críticas

---

**FIN DEL INFORME**
