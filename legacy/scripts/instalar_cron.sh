#!/bin/bash
#
# Instalador automático del cron job para actualización de cache
#

set -e

echo "=========================================="
echo "📅 INSTALACIÓN AUTOMÁTICA DE CRON JOB"
echo "=========================================="
echo ""

# Detectar directorio del proyecto
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "📂 Directorio del proyecto: $PROJECT_DIR"
echo ""

# Dar permisos de ejecución
echo "🔧 Configurando permisos..."
chmod +x "$SCRIPT_DIR/cron_actualizar_cache.sh"
chmod +x "$SCRIPT_DIR/actualizar_cache_automatico.py"
echo "✅ Permisos configurados"
echo ""

# Crear directorio de logs si no existe
mkdir -p "$PROJECT_DIR/logs"
echo "✅ Directorio de logs creado"
echo ""

# Verificar si ya existe el cron job
if crontab -l 2>/dev/null | grep -q "cron_actualizar_cache.sh"; then
    echo "⚠️  El cron job ya existe. ¿Desea reinstalarlo? (s/n)"
    read -r respuesta
    if [ "$respuesta" != "s" ] && [ "$respuesta" != "S" ]; then
        echo "❌ Instalación cancelada"
        exit 0
    fi
    
    # Eliminar cron job existente
    echo "🗑️  Eliminando cron job existente..."
    crontab -l 2>/dev/null | grep -v "cron_actualizar_cache.sh" | crontab -
fi

# Crear nuevo cron job
echo "📅 Instalando cron job..."

# Obtener crontab actual (o crear vacío si no existe)
(crontab -l 2>/dev/null || echo "") | {
    cat
    echo ""
    echo "# Actualización automática de cache - Portal Energético MME"
    echo "# Ejecuta a las 6am, 12pm y 8pm todos los días"
    echo "0 6 * * * $SCRIPT_DIR/cron_actualizar_cache.sh"
    echo "0 12 * * * $SCRIPT_DIR/cron_actualizar_cache.sh"
    echo "0 20 * * * $SCRIPT_DIR/cron_actualizar_cache.sh"
} | crontab -

echo "✅ Cron job instalado correctamente"
echo ""

# Mostrar crontab actual
echo "📋 Cron jobs actuales:"
echo "----------------------------------------"
crontab -l | grep -A 3 "Portal Energético" || crontab -l | tail -3
echo "----------------------------------------"
echo ""

# Ejecutar primera actualización
echo "🚀 ¿Desea ejecutar la primera actualización ahora? (s/n)"
read -r ejecutar

if [ "$ejecutar" = "s" ] || [ "$ejecutar" = "S" ]; then
    echo ""
    echo "🔄 Ejecutando actualización inicial..."
    echo "=========================================="
    cd "$PROJECT_DIR"
    python3 "$SCRIPT_DIR/actualizar_cache_automatico.py"
    echo "=========================================="
    echo ""
fi

echo "✅ INSTALACIÓN COMPLETADA"
echo ""
echo "📊 Próximas ejecuciones:"
echo "  - Mañana a las 06:00 AM"
echo "  - Mañana a las 12:00 PM"
echo "  - Hoy/Mañana a las 08:00 PM"
echo ""
echo "📝 Monitorear logs:"
echo "  tail -f $PROJECT_DIR/logs/cache_automatico.log"
echo ""
echo "🔧 Desinstalar:"
echo "  crontab -e  (eliminar las 3 líneas del cache)"
echo ""
