#!/bin/bash
#
# Script para precalentar cache de PÁGINAS (datos procesados)
# Se ejecuta 30 minutos DESPUÉS de actualizar datos crudos
# para que los datos ya estén disponibles cuando se procesen
#

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON_SCRIPT="$SCRIPT_DIR/precalentar_cache_v2.py"
LOG_FILE="$PROJECT_DIR/logs/cron_precalentamiento.log"

echo "========================================" >> "$LOG_FILE"
echo "$(date '+%Y-%m-%d %H:%M:%S') - Precalentando cache de páginas" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# Ejecutar script de Python
cd "$PROJECT_DIR"
/usr/bin/python3 "$PYTHON_SCRIPT" >> "$LOG_FILE" 2>&1

exit_code=$?

echo "Exit code: $exit_code" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

exit $exit_code
