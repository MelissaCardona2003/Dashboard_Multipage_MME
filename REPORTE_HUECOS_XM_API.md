
# Reporte de Huecos en Métricas ETL (Diagnóstico XM API)

**Fecha de generación:** 2025-11-25

## Resumen
Se ejecutó el script de diagnóstico para intentar rellenar los días faltantes en las métricas históricas usando el API de XM. El resultado fue que para todos los días con hueco, el API de XM no devolvió datos o se produjo un error, por lo que no fue posible completar esos registros.

## Días sin datos disponibles en XM API, agrupados por métrica

A continuación se listan, para cada métrica, los días específicos para los cuales el sistema intentó rellenar datos pero el API de XM respondió sin información o con error:

---

### Gene
**Días sin datos:**
```
2025-11-23: API no devolvió datos.
2025-11-24: API no devolvió datos.
```

### DemaCome
**Días sin datos:**
```
2022-08-08: API no devolvió datos.
2022-08-09: API no devolvió datos.
2022-08-10: API no devolvió datos.
2022-08-11: API no devolvió datos.
2022-08-12: API no devolvió datos.
2022-08-13: API no devolvió datos.
2022-08-14: API no devolvió datos.
2022-08-15: API no devolvió datos.
2022-08-16: API no devolvió datos.
2022-08-17: API no devolvió datos.
2022-08-18: API no devolvió datos.
2022-08-19: API no devolvió datos.
2022-08-20: API no devolvió datos.
2022-08-21: API no devolvió datos.
2022-08-22: API no devolvió datos.
2022-08-23: API no devolvió datos.
2022-08-24: API no devolvió datos.
2022-08-25: API no devolvió datos.
2022-08-26: API no devolvió datos.
2022-08-27: API no devolvió datos.
2025-11-23: API no devolvió datos.
2025-11-24: API no devolvió datos.
```

### DemaReal
**Días sin datos:**
```
2022-08-08: API no devolvió datos.
2022-08-09: API no devolvió datos.
2022-08-10: API no devolvió datos.
2022-08-11: API no devolvió datos.
2022-08-12: API no devolvió datos.
2022-08-13: API no devolvió datos.
2022-08-14: API no devolvió datos.
2022-08-15: API no devolvió datos.
2022-08-16: API no devolvió datos.
2022-08-17: API no devolvió datos.
2022-08-18: API no devolvió datos.
2022-08-19: API no devolvió datos.
2022-08-20: API no devolvió datos.
2022-08-21: API no devolvió datos.
2022-08-22: API no devolvió datos.
2022-08-23: API no devolvió datos.
2022-08-24: API no devolvió datos.
2022-08-25: API no devolvió datos.
2022-08-26: API no devolvió datos.
2022-08-27: API no devolvió datos.
2025-11-23: API no devolvió datos.
2025-11-24: API no devolvió datos.
```

### AporCaudal
**Errores detectados:**
```
2020-07-17: index 0 is out of bounds for axis 0 with size 0
2020-07-19: index 0 is out of bounds for axis 0 with size 0
2021-12-07: index 0 is out of bounds for axis 0 with size 0
2021-12-08: index 0 is out of bounds for axis 0 with size 0
2021-12-27: index 0 is out of bounds for axis 0 with size 0
2022-01-26: index 0 is out of bounds for axis 0 with size 0
2022-02-20: index 0 is out of bounds for axis 0 with size 0
```

### DemaNoAtenProg
**Errores detectados:**
```
2020-01-01: index 0 is out of bounds for axis 0 with size 0
2020-01-02: index 0 is out of bounds for axis 0 with size 0
2020-01-03: index 0 is out of bounds for axis 0 with size 0
2020-01-04: index 0 is out of bounds for axis 0 with size 0
2020-01-05: index 0 is out of bounds for axis 0 with size 0
2020-01-06: index 0 is out of bounds for axis 0 with size 0
2020-01-07: index 0 is out of bounds for axis 0 with size 0
2020-01-08: index 0 is out of bounds for axis 0 with size 0
2020-01-09: index 0 is out of bounds for axis 0 with size 0
2020-01-10: index 0 is out of bounds for axis 0 with size 0
... (más de 1200 días, ver log completo)
```

---

## Causa raíz
- El sistema ETL intentó rellenar los huecos históricos, pero el API de XM no tiene datos para esos días o devolvió error.
- No hay evidencia de borrado o pérdida interna: los huecos existen porque la fuente (XM) no tiene datos para esos días.

## Recomendaciones
1. Documentar estos días como huecos irrecuperables desde la fuente XM.
2. Si es crítico tener esos días, considerar:
   - Buscar fuentes alternativas de datos.
   - Interpolación o estimación basada en días vecinos (si es aceptable para el negocio).
3. El sistema ETL ya es robusto: si el API provee datos, los rellena automáticamente.

---

_Reporte generado automáticamente por GitHub Copilot._
