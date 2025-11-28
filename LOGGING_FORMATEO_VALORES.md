# 🔍 SISTEMA DE LOGGING PARA DETECCIÓN DE VALORES CORRUPTOS

## Objetivo
Detectar si hay valores repetidos, corruptos o inconsistencias debido a múltiples capas de formateo en las tablas de embalses.

## Puntos de Logging Agregados

### 1. **Inicialización de Tablas Jerárquicas** (`initialize_hierarchical_tables`)
**Ubicación**: Líneas ~2623-2670

**Logs agregados**:
- 🔍 `[INIT_TABLES]`: Muestra cuántas regiones y embalses se están procesando
- 🔍 `[RAW]`: Valores RAW antes de cualquier formateo (tipo de dato incluido)
- 🔍 `[FLOAT]`: Valores después de conversión a float (previo a formateo)
- 🔍 `[FORMATTED]`: Valores después de formateo con decimales consistentes
- 🔍 `[STORE_VERIFICATION]`: Verifica que ambos stores (participación y capacidad) tienen EXACTAMENTE los mismos valores

**Mejora implementada**:
```python
# ANTES: Formateo directo con posible inconsistencia
'participacion': f"{embalse_row['Participación (%)']}%"
'capacidad': f"{volumen_embalse:.1f}%"

# AHORA: Conversión a float primero, luego formateo consistente
participacion_float = float(embalse_row['Participación (%)'])
volumen_float = float(volumen_embalse)
participacion_formatted = f"{participacion_float:.2f}%"
volumen_formatted = f"{volumen_float:.1f}%"
```

### 2. **Construcción de Vista de Tabla** (`build_hierarchical_table_view`)
**Ubicación**: Líneas ~2740-2755

**Logs agregados**:
- 🔍 `[BUILD_TABLE]`: Muestra región, tipo de vista y número de embalses
- 🔍 `[TABLE_DISPLAY]`: Valores que se mostrarán finalmente en la tabla

### 3. **Obtención de Datos para Tabla** (`get_embalses_data_for_table`)
**Ubicación**: Líneas ~3895-3915

**Logs agregados**:
- 🔍 `[get_embalses_data_for_table]`: Región y número de registros obtenidos
- 🔍 `[TABLE_DATA]`: Valor RAW de Volumen Útil con tipo de dato
- 🔍 `[TABLE_DATA]`: Valor formateado final

## Cómo Monitorear los Logs

### Opción 1: Monitoreo en Tiempo Real (Recomendado)
```bash
cd /home/admonctrlxm/server
./monitor_formateo_logs.sh
```

### Opción 2: Ver Logs Completos
```bash
sudo journalctl -u dashboard-mme.service -f
```

### Opción 3: Buscar Logs Específicos de Valle
```bash
sudo journalctl -u dashboard-mme.service --since "5 minutes ago" | grep -i "valle\|altoanchicaya\|calima\|salvajina"
```

## Qué Buscar en los Logs

### ✅ VALORES CORRECTOS (Ejemplo esperado):
```
🔍 [RAW] SALVAJINA: Volumen=32.6 (tipo=float), Participación=66.88 (tipo=float)
🔍 [FLOAT] SALVAJINA: Volumen=32.60%, Participación=66.88%
🔍 [FORMATTED] SALVAJINA: Volumen=32.6%, Participación=66.88%
🔍 [STORE_VERIFICATION] SALVAJINA - PARTICIPACION_STORE: vol=32.6%, part=66.88%
🔍 [STORE_VERIFICATION] SALVAJINA - CAPACIDAD_STORE: vol=32.6%, part=66.88%
🔍 [TABLE_DISPLAY] SALVAJINA (participacion): Display=66.88%, Part=66.88%, Vol=32.6%
🔍 [TABLE_DISPLAY] SALVAJINA (capacidad): Display=32.6%, Part=66.88%, Vol=32.6%
```

### ❌ VALORES CORRUPTOS (Ejemplos de problemas):
```
# Problema 1: Tipo de dato incorrecto
🔍 [RAW] SALVAJINA: Volumen=32.6% (tipo=str), Participación=66.88 (tipo=float)
                                   ^^^^ Ya viene formateado!

# Problema 2: Doble formateo
🔍 [FORMATTED] SALVAJINA: Volumen=32.6%%, Participación=66.88%%
                                      ^^^ Doble símbolo de porcentaje

# Problema 3: Valores diferentes entre stores
🔍 [STORE_VERIFICATION] SALVAJINA - PARTICIPACION_STORE: vol=27.7%, part=66.88%
🔍 [STORE_VERIFICATION] SALVAJINA - CAPACIDAD_STORE: vol=32.6%, part=66.88%
                                                         ^^^^^ DIFERENTES!

# Problema 4: Valores diferentes entre vistas
🔍 [TABLE_DISPLAY] SALVAJINA (participacion): Display=66.88%, Part=66.88%, Vol=27.7%
🔍 [TABLE_DISPLAY] SALVAJINA (capacidad): Display=32.6%, Part=66.88%, Vol=32.6%
                                                  ^^^^^ DIFERENTES!

# Problema 5: Error de conversión
❌ Error convirtiendo valores a float para SALVAJINA: could not convert string to float: '32.6%'
```

## Próximos Pasos

1. **Esperar a que termine el ETL** (actualmente 43.2%)
2. **Acceder al dashboard** y expandir la región Valle
3. **Ejecutar el monitor de logs** mientras observas el dashboard
4. **Buscar inconsistencias** comparando:
   - Valores mostrados en el dashboard
   - Valores en los logs `[FORMATTED]`
   - Valores en los logs `[STORE_VERIFICATION]`
   - Valores en los logs `[TABLE_DISPLAY]`

5. **Si se detectan inconsistencias**:
   - Documentar exactamente qué valores difieren y en qué punto
   - Revisar si hay doble formateo (agregar % a un string que ya tiene %)
   - Verificar si hay conversiones de tipo incorrectas
   - Comprobar si hay llamadas a diferentes fuentes de datos

## Estado del Sistema

- ✅ Dashboard reiniciado con nuevos logs
- ✅ Script de monitoreo creado
- ✅ Formateo unificado implementado (conversión a float antes de formatear)
- ⏳ ETL en ejecución (esperando a que termine)
- 🔍 Logs activos y listos para inspección

## Archivos Modificados

- `/home/admonctrlxm/server/pages/generacion_hidraulica_hidrologia.py` (5 cambios)
- `/home/admonctrlxm/server/monitor_formateo_logs.sh` (nuevo)

---
**Fecha**: 2025-11-25 14:40
**PID Dashboard**: 1119890
**Estado**: Activo y listo para monitoreo
