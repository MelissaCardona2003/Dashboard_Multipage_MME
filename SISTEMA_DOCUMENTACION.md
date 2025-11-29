# 📚 Sistema de Actualización Automática de Documentación

**Fecha de implementación:** 29 de noviembre de 2025  
**Última mejora:** 29 de noviembre de 2025 - Sistema de fechas para informes mensuales

---

## 📋 Objetivo

Mantener automáticamente actualizados los dos únicos archivos de documentación del proyecto:

1. **`README.md`** - Arquitectura y funcionamiento actual del sistema
2. **`legacy/README.md`** - Trazabilidad histórica del proyecto

**Principio:** No crear más archivos `.md` para documentar cambios. Todo se mantiene en estos 2 archivos.

**Nuevo:** Todas las actualizaciones incluyen fecha y hora para facilitar la generación de informes mensuales.

---

## 🏗️ Componentes del Sistema

### 1. **Script Principal: `scripts/actualizar_documentacion.py`**

**Función:** Actualiza automáticamente ambos README cuando detecta cambios importantes.

**Qué actualiza:**

**En `README.md`:**
- Estadísticas actuales (registros, duplicados, tamaño BD)
- Configuración de workers/threads
- Estado del servicio
- Fecha de última actualización

**En `legacy/README.md`:**
- Agrega nueva entrada con cambios detectados
- Mantiene historial cronológico
- Actualiza métricas del sistema

**Cambios importantes que detecta:**
- Modificación de workers/threads en `gunicorn_config.py`
- Crecimiento significativo de base de datos (>100 MB)
- Eliminación de duplicados
- Cambios en configuración del sistema

**Uso:**
```bash
python3 scripts/actualizar_documentacion.py
```

---

### 2. **Git Hook: `.git/hooks/post-commit`**

**Función:** Se ejecuta automáticamente después de cada commit.

**Cuándo actualiza la documentación:**
- Solo si el commit modificó archivos importantes:
  - `pages/` - Código del dashboard
  - `utils/` - Utilidades
  - `etl/` - Scripts ETL
  - `scripts/` - Scripts de automatización
  - `gunicorn_config.py` - Configuración del servidor
  - `app.py` - Aplicación principal
  - `requirements.txt` - Dependencias

**Comportamiento:**
1. Detecta cambios en archivos importantes
2. Ejecuta `actualizar_documentacion.py`
3. Si hay cambios en README, los agrega al commit automáticamente

**Instalación:**
```bash
chmod +x .git/hooks/post-commit
```

---

### 3. **Tarea Cron: Actualización Diaria**

**Función:** Ejecuta el script diariamente a las 23:00 para actualizar documentación aunque no haya commits.

**Configuración:**
```bash
0 23 * * * cd /home/admonctrlxm/server && /usr/bin/python3 scripts/actualizar_documentacion.py >> logs/documentacion.log 2>&1
```

**Por qué es útil:**
- Actualiza estadísticas aunque no haya commits
- Captura cambios del sistema (crecimiento de BD, limpieza de duplicados, etc.)
- Mantiene README siempre actualizado

**Ver logs:**
```bash
tail -f logs/documentacion.log
```

---

### 4. **Generador de Informes Mensuales: `scripts/generar_informe_mensual.sh`**

**Función:** Genera un informe mensual completo con todos los cambios del período.

**Características:**
- Extrae todas las actualizaciones del mes de `legacy/README.md`
- Lista todos los commits del período
- Incluye estadísticas finales del sistema
- Genera archivo listo para presentar: `INFORME_MES_AÑO.md`

**Uso:**
```bash
# Informe del mes actual
./scripts/generar_informe_mensual.sh

# Informe de un mes específico (ejemplo: noviembre 2025)
./scripts/generar_informe_mensual.sh 11 2025

# Informe de diciembre 2025
./scripts/generar_informe_mensual.sh 12 2025
```

**Ejemplo de salida:**
```
INFORME_NOVIEMBRE_2025.md
- 📅 Cambios y actualizaciones (todas las entradas con fechas del mes)
- 🔧 Commits del período (todos los commits de git)
- 📈 Estado final del sistema (métricas al cierre)
```

**Beneficio:** Ahorra tiempo al construir informes mensuales - toda la información ya está organizada y lista.

---

### 5. **Script Manual: `scripts/actualizar_docs.sh`**

**Función:** Actualizar documentación manualmente con nota personalizada.

**Uso:**
```bash
# Actualización simple
./scripts/actualizar_docs.sh

# Con nota personalizada para legacy/README.md
./scripts/actualizar_docs.sh "Implementada optimización de cache en páginas"
```

**Formato de notas:** Ahora incluye automáticamente fecha y hora:
```
### **📅 29 de November de 2025 - 15:24**

**Nota:** Implementada optimización de cache en páginas

**Fecha para informe:** 29/11/2025
```

**Casos de uso:**
- Después de cambios importantes sin commit
- Para agregar notas específicas al historial
- Forzar actualización de estadísticas

---

## 🔄 Flujo de Trabajo

### Escenario 1: Commit Normal
```
1. Desarrollador: git commit -m "Optimizar consultas SQL"
2. Git Hook: Detecta cambio en utils/
3. Script: Actualiza README.md y legacy/README.md
4. Git Hook: Agrega cambios en README al commit
5. Resultado: Documentación siempre sincronizada
```

### Escenario 2: Actualización Automática Diaria
```
1. Cron: 23:00 ejecuta actualizar_documentacion.py
2. Script: Lee estadísticas del sistema
3. Script: Actualiza README.md con datos actuales
4. Script: Si hay cambios importantes, actualiza legacy/README.md
5. Log: Guarda resultado en logs/documentacion.log
```

### Escenario 3: Actualización Manual con Nota
```
1. Administrador: ./scripts/actualizar_docs.sh "Fase 3 completada"
2. Script: Actualiza ambos README
3. Script: Agrega nota personalizada a legacy/README.md
4. Resultado: Cambios listos para commit
```

---

## 📊 Archivo de Estado

**Ubicación:** `logs/documentacion_state.json`

**Contenido:**
```json
{
  "fecha": "29 de noviembre de 2025",
  "fecha_iso": "2025-11-29T15:10:00",
  "db_size_mb": 5066.32,
  "total_records": 1366002,
  "duplicate_records": 0,
  "data_age_days": 6,
  "workers": 6,
  "threads": 3,
  "connections": 18,
  "service_active": true
}
```

**Función:**
- Almacena estado anterior del sistema
- Permite detectar cambios (workers, threads, BD, duplicados)
- Se actualiza en cada ejecución del script

---

## ✅ Beneficios del Sistema

### 1. **Un Solo Lugar para Documentación**
- ❌ Antes: Múltiples archivos `.md` (FASE1_*.txt, FASE2_*.txt, etc.)
- ✅ Ahora: Solo `README.md` y `legacy/README.md`

### 2. **Siempre Actualizado**
- Automático en cada commit importante
- Actualización diaria vía cron
- Opción de actualización manual

### 3. **Trazabilidad Completa**
- `legacy/README.md` mantiene historial cronológico
- Cada cambio importante queda documentado
- Fácil de seguir evolución del proyecto

### 4. **Menos Trabajo Manual**
- No necesitas crear archivos `.md` nuevos
- No necesitas actualizar estadísticas manualmente
- Sistema se mantiene solo

### 5. **Información Siempre Actual**
- README muestra estado real del sistema
- Estadísticas actualizadas diariamente
- Historial ordenado cronológicamente

---

## 🔧 Mantenimiento

### Ver Estado Actual
```bash
cat logs/documentacion_state.json | python3 -m json.tool
```

### Ver Últimas Actualizaciones
```bash
tail -50 logs/documentacion.log
```

### Forzar Actualización
```bash
python3 scripts/actualizar_documentacion.py
```

### Verificar Cron
```bash
crontab -l | grep documentacion
```

### Verificar Git Hook
```bash
ls -lh .git/hooks/post-commit
cat .git/hooks/post-commit
```

---

## 📝 Guía de Uso

### Para Desarrolladores

**Después de hacer cambios importantes:**
```bash
# 1. Hacer commit normal
git add .
git commit -m "Optimización de consultas"

# 2. El hook de Git actualiza automáticamente la documentación
# 3. Si quieres agregar nota específica:
./scripts/actualizar_docs.sh "Reducción de 50% en tiempos de respuesta"

# 4. Commit de documentación (si actualizaste manualmente)
git add README.md legacy/README.md
git commit -m "docs: actualización automática"
```

### Para Administradores

**Revisión periódica:**
```bash
# Ver estado del sistema
curl http://localhost:8050/health | python3 -m json.tool

# Actualizar documentación
./scripts/actualizar_docs.sh

# Ver historial
cat legacy/README.md | grep "### \*\*Actualización"
```

---

## ⚠️ Notas Importantes

1. **No crear más archivos `.md`:** Todo debe ir a `README.md` o `legacy/README.md`

2. **El hook de Git requiere Git:** Si trabajas sin Git, usa el script manual o el cron

3. **Logs en `logs/documentacion.log`:** Revisar si hay problemas de actualización

4. **Estado en `logs/documentacion_state.json`:** No eliminar, necesario para detectar cambios

5. **Actualización diaria a las 23:00:** Cambiar horario en crontab si necesario

---

## 🔄 Migración de Documentación Existente

Si tienes archivos `.md` antiguos en `logs/`:

```bash
# 1. Revisar contenido importante
ls -lh logs/*.md logs/*.txt

# 2. Extraer información relevante y agregarla manualmente a legacy/README.md
./scripts/actualizar_docs.sh "Migración de documentación antigua completada"

# 3. Eliminar archivos antiguos
rm logs/FASE*.txt logs/*OPTIMIZACION*.txt

# 4. Mantener solo README.md y legacy/README.md
```

---

## 📚 Referencias

- **README.md** - Documentación principal del proyecto
- **legacy/README.md** - Historial y trazabilidad
- **ARQUITECTURA_ETL_SQLITE.md** - Arquitectura técnica detallada

---

**Última actualización:** 29 de noviembre de 2025  
**Versión:** 1.0  
**Estado:** ✅ Sistema implementado y operativo
