#!/bin/bash
#
# Script de actualización automática del cache del Dashboard MME
# Ejecuta el precalentamiento inteligente SIN timeout para evitar caídas por API lenta
#
# Horarios de ejecución configurados en crontab:
# - 06:30 AM (datos nocturnos)
# - 12:30 PM (actualización mediodía)
# - 20:30 PM (datos del día completo)
#

# Directorio del proyecto
PROYECTO_DIR="/home/admonctrlxm/server"
SCRIPT_PYTHON="$PROYECTO_DIR/scripts/precalentar_cache_inteligente.py"
LOG_FILE="/var/log/dashboard_mme_cache.log"

# Timestamp para logs
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

echo "======================================" >> "$LOG_FILE"
echo "[$TIMESTAMP] Inicio actualización cache automática" >> "$LOG_FILE"

# Cambiar al directorio del proyecto
cd "$PROYECTO_DIR" || {
    echo "[$TIMESTAMP] ERROR: No se pudo acceder al directorio $PROYECTO_DIR" >> "$LOG_FILE"
    exit 1
}

# Ejecutar precalentamiento SIN timeout (--sin-timeout)
# Esto permite que la API tome el tiempo que necesite sin caer
echo "[$TIMESTAMP] Ejecutando: python3 $SCRIPT_PYTHON --sin-timeout" >> "$LOG_FILE"
python3 "$SCRIPT_PYTHON" --sin-timeout >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "[$TIMESTAMP] ✅ Actualización completada exitosamente" >> "$LOG_FILE"
else
    echo "[$TIMESTAMP] ❌ ERROR: Actualización falló con código $EXIT_CODE" >> "$LOG_FILE"
fi

echo "[$TIMESTAMP] Fin actualización cache automática" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

exit $EXIT_CODE
