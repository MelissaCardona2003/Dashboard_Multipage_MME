#!/bin/bash
# Script para monitorear logs de formateo de datos de embalses

echo "=========================================="
echo "  MONITOR DE LOGS - FORMATEO DE EMBALSES"
echo "=========================================="
echo ""
echo "Presiona Ctrl+C para detener"
echo ""

# Seguir los logs del dashboard filtrando solo las líneas de debugging
sudo journalctl -u dashboard-mme.service -f --since "1 minute ago" | grep -E "\[RAW\]|\[FLOAT\]|\[FORMATTED\]|\[STORE_VERIFICATION\]|\[BUILD_TABLE\]|\[TABLE_DISPLAY\]|\[TABLE_DATA\]|\[get_embalses_data_for_table\]|\[INIT_TABLES\]|Error convirtiendo"
