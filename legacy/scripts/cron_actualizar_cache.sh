#!/bin/bash
#
# Script para configurar actualización automática del cache
# Ejecuta el script de Python en horarios estratégicos
#

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON_SCRIPT="$SCRIPT_DIR/actualizar_cache_automatico.py"
LOG_FILE="$PROJECT_DIR/logs/cron_cache.log"

echo "========================================" >> "$LOG_FILE"
echo "$(date '+%Y-%m-%d %H:%M:%S') - Ejecutando actualización automática de cache" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# Ejecutar script de Python
cd "$PROJECT_DIR"
/usr/bin/python3 "$PYTHON_SCRIPT" >> "$LOG_FILE" 2>&1

exit_code=$?

echo "Exit code: $exit_code" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

exit $exit_code
