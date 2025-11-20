#!/bin/bash
#
# Instalador COMPLETO de cron jobs para cache
# 
# FASE 1: Actualizar datos crudos de API XM (6am, 12pm, 8pm)
# FASE 2: Precalentar páginas 30 min después (6:30am, 12:30pm, 8:30pm)
#

echo "=========================================="
echo "🔧 INSTALACIÓN DE CRON JOBS DE CACHE"
echo "=========================================="
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Dar permisos de ejecución
echo "📝 Dando permisos de ejecución..."
chmod +x "$SCRIPT_DIR/cron_actualizar_cache.sh"
chmod +x "$SCRIPT_DIR/actualizar_cache_automatico.py"
chmod +x "$SCRIPT_DIR/cron_precalentar_paginas.sh"
chmod +x "$SCRIPT_DIR/precalentar_cache_paginas.py"

# Verificar si ya existen los cron jobs
if crontab -l 2>/dev/null | grep -q "cron_actualizar_cache.sh"; then
    echo "⚠️  Cron jobs YA EXISTEN. Actualizando..."
    
    # Remover líneas antiguas
    crontab -l 2>/dev/null | grep -v "cron_actualizar_cache.sh" | grep -v "cron_precalentar_paginas.sh" | grep -v "Portal Energético MME" > /tmp/crontab_temp
    
    # Agregar nuevas líneas
    cat >> /tmp/crontab_temp << 'EOF'

# Actualización automática de cache - Portal Energético MME
# FASE 1: Actualizar datos crudos (API XM)
0 6 * * * /home/admonctrlxm/server/scripts/cron_actualizar_cache.sh
0 12 * * * /home/admonctrlxm/server/scripts/cron_actualizar_cache.sh
0 20 * * * /home/admonctrlxm/server/scripts/cron_actualizar_cache.sh

# FASE 2: Precalentar páginas (30 min después)
30 6 * * * /home/admonctrlxm/server/scripts/cron_precalentar_paginas.sh
30 12 * * * /home/admonctrlxm/server/scripts/cron_precalentar_paginas.sh
30 20 * * * /home/admonctrlxm/server/scripts/cron_precalentar_paginas.sh
EOF
    
    crontab /tmp/crontab_temp
    rm /tmp/crontab_temp
    
    echo "✅ Cron jobs ACTUALIZADOS"
else
    echo "📅 Instalando nuevos cron jobs..."
    
    # Crear archivo temporal con crontab actual + nuevas líneas
    (crontab -l 2>/dev/null; cat << 'EOF'

# Actualización automática de cache - Portal Energético MME
# FASE 1: Actualizar datos crudos (API XM)
0 6 * * * /home/admonctrlxm/server/scripts/cron_actualizar_cache.sh
0 12 * * * /home/admonctrlxm/server/scripts/cron_actualizar_cache.sh
0 20 * * * /home/admonctrlxm/server/scripts/cron_actualizar_cache.sh

# FASE 2: Precalentar páginas (30 min después)
30 6 * * * /home/admonctrlxm/server/scripts/cron_precalentar_paginas.sh
30 12 * * * /home/admonctrlxm/server/scripts/cron_precalentar_paginas.sh
30 20 * * * /home/admonctrlxm/server/scripts/cron_precalentar_paginas.sh
EOF
    ) | crontab -
    
    echo "✅ Cron jobs INSTALADOS"
fi

echo ""
echo "=========================================="
echo "📋 VERIFICACIÓN"
echo "=========================================="
echo ""
echo "Cron jobs instalados:"
crontab -l | grep -A 10 "Portal Energético MME"

echo ""
echo "=========================================="
echo "✅ INSTALACIÓN COMPLETADA"
echo "=========================================="
echo ""
echo "📅 Horarios configurados:"
echo ""
echo "  FASE 1 - Actualizar datos crudos:"
echo "    • 06:00 AM - Después de actualización XM"
echo "    • 12:00 PM - Verificación mediodía"
echo "    • 20:00 PM - Actualización nocturna"
echo ""
echo "  FASE 2 - Precalentar páginas (30 min después):"
echo "    • 06:30 AM"
echo "    • 12:30 PM"
echo "    • 20:30 PM"
echo ""
echo "🎯 BENEFICIO: Las páginas cargarán INSTANTÁNEAMENTE"
echo "   porque los datos ya estarán procesados."
echo ""
echo "📊 Monitorear ejecuciones:"
echo "   tail -f $PROJECT_DIR/logs/cron_precalentamiento.log"
echo ""
echo "🧪 Probar manualmente:"
echo "   cd $PROJECT_DIR"
echo "   python3 scripts/precalentar_cache_paginas.py"
echo ""
