# Archivos Legacy (Obsoletos)

**Fecha de migración:** 2025-11-20

## Arquitectura Deprecada: CACHE-PRECALENTAMIENTO-DASHBOARD

Esta carpeta contiene archivos de la arquitectura antigua que fue reemplazada por **ETL-SQLITE-DASHBOARD**.

### ❌ Sistema Antiguo (Deprecado)
- **Cache en RAM/Disco:** Archivos `.pkl` en `/var/cache/portal_energetico_cache/`
- **Precalentamiento manual:** Scripts que generaban cache antes de cargar páginas
- **Problemas:** 
  - Sincronización compleja
  - Errores frecuentes en cron
  - Datos inconsistentes entre cache y dashboard
  - Alto consumo de memoria

### ✅ Sistema Actual (Desde 19 Nov 2025)
- **SQLite:** Base de datos persistente `portal_energetico.db`
- **ETL automatizado:** `etl/etl_xm_to_sqlite.py` ejecuta 3×/día
- **Dashboard directo:** Lee directamente de SQLite (sin cache intermedio)
- **Beneficios:**
  - Datos consistentes
  - Sin errores de sincronización
  - Performance superior
  - Mantenimiento mínimo

## Contenido de Legacy

### `legacy/scripts/` (10 archivos)
1. `precalentar_cache_inteligente.py` - Script principal de precalentamiento (reemplazado por ETL)
2. `precalentar_cache_v2.py` - Versión 2 del precalentador
3. `poblar_cache_sin_timeout.py` - Poblador de cache sin timeouts
4. `actualizar_cache_automatico.sh` - Shell wrapper para actualización
5. `cron_actualizar_cache.sh` - Cron para actualizar cache raw
6. `cron_precalentar_paginas.sh` - Cron para precalentar páginas
7. `instalar_cron.sh` - Instalador de cron antiguo
8. `instalar_cron_completo.sh` - Instalador completo
9. `validar_cache_rapido.py` - Validador de cache
10. `verificar_cache.py` - Verificador de integridad

### `legacy/utils/` (2 archivos)
1. `cache_manager.py` - Gestor de cache en disco (reemplazado por `db_manager.py`)
2. `cache_validator.py` - Validador de cache

## ⚠️ NO USAR ESTOS ARCHIVOS

Estos archivos se mantienen solo como referencia histórica. 
**NO** deben ser utilizados en producción.

Si necesitas restaurar algo, consulta:
- `ARQUITECTURA_ETL_SQLITE.md` - Documentación del sistema actual
- `MIGRACION_CACHE_SQLITE.md` - Proceso de migración completo

## Eliminación Futura

Estos archivos pueden ser eliminados completamente después de:
- ✅ 1 semana sin problemas en producción (cumplido)
- ✅ Verificación de que no hay dependencias (cumplido)
- ✅ Backup del repositorio en GitHub (pendiente)

**Fecha sugerida de eliminación:** 2025-12-01
