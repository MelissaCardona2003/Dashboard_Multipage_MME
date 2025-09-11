#!/bin/bash
# =============================================================================
# CONFIGURADOR DE ACTUALIZACIONES AUTOMÁTICAS - Dashboard MME
# =============================================================================

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

APP_DIR="/home/ubuntu/Dashboard_Multipage_MME"
CRON_LOG="/home/ubuntu/Dashboard_Multipage_MME/logs/cron_update.log"

echo -e "${BLUE}⚙️ CONFIGURADOR DE ACTUALIZACIONES AUTOMÁTICAS${NC}"
echo -e "${BLUE}=============================================${NC}"

echo ""
echo "Este script te ayudará a configurar actualizaciones automáticas"
echo "para tu dashboard desde GitHub."
echo ""

# Función para mostrar opciones de frecuencia
show_frequency_options() {
    echo "Opciones de frecuencia:"
    echo "  1) Cada hora"
    echo "  2) Cada 4 horas"
    echo "  3) Cada 12 horas"
    echo "  4) Diariamente (a las 2:00 AM)"
    echo "  5) Solo verificar (sin actualizar automáticamente)"
    echo "  6) Desactivar actualizaciones automáticas"
    echo "  0) Cancelar"
}

# Función para configurar cron
setup_cron() {
    local frequency=$1
    local cron_command=""
    
    case $frequency in
        1)
            cron_command="0 * * * * cd $APP_DIR && ./auto-update.sh update >> $CRON_LOG 2>&1"
            echo "Configurando: Actualización cada hora"
            ;;
        2)
            cron_command="0 */4 * * * cd $APP_DIR && ./auto-update.sh update >> $CRON_LOG 2>&1"
            echo "Configurando: Actualización cada 4 horas"
            ;;
        3)
            cron_command="0 */12 * * * cd $APP_DIR && ./auto-update.sh update >> $CRON_LOG 2>&1"
            echo "Configurando: Actualización cada 12 horas"
            ;;
        4)
            cron_command="0 2 * * * cd $APP_DIR && ./auto-update.sh update >> $CRON_LOG 2>&1"
            echo "Configurando: Actualización diaria a las 2:00 AM"
            ;;
        5)
            cron_command="0 */2 * * * cd $APP_DIR && ./auto-update.sh check >> $CRON_LOG 2>&1"
            echo "Configurando: Solo verificación cada 2 horas"
            ;;
    esac
    
    # Remover entradas anteriores del auto-update
    (crontab -l 2>/dev/null | grep -v "auto-update.sh") | crontab -
    
    # Agregar nueva entrada si no es desactivar
    if [ $frequency -ne 6 ]; then
        (crontab -l 2>/dev/null; echo "$cron_command") | crontab -
        echo -e "${GREEN}✅ Cron configurado exitosamente${NC}"
        
        # Crear script de notificación
        create_notification_script $frequency
    else
        echo -e "${GREEN}✅ Actualizaciones automáticas desactivadas${NC}"
    fi
}

# Función para crear script de notificación
create_notification_script() {
    local freq=$1
    
    cat > "$APP_DIR/notify-update.sh" << 'EOF'
#!/bin/bash
# Script de notificación de actualizaciones

LOGFILE="/home/ubuntu/Dashboard_Multipage_MME/logs/update.log"
WEBHOOK_URL=""  # Opcional: URL de webhook para notificaciones

# Función para enviar notificación
send_notification() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo "[$timestamp] $message" >> "$LOGFILE"
    
    # Si tienes webhook configurado, descomenta y configura:
    # curl -X POST -H 'Content-type: application/json' \
    #      --data '{"text":"'"$message"'"}' \
    #      "$WEBHOOK_URL"
}

# Verificar último resultado de actualización
if tail -n 1 "$LOGFILE" | grep -q "ERROR"; then
    send_notification "❌ Error en actualización automática del Dashboard MME"
elif tail -n 1 "$LOGFILE" | grep -q "Actualización completada exitosamente"; then
    send_notification "✅ Dashboard MME actualizado exitosamente desde GitHub"
fi
EOF
    
    chmod +x "$APP_DIR/notify-update.sh"
}

# Función para mostrar estado actual
show_current_status() {
    echo -e "${YELLOW}📊 Estado Actual de Cron:${NC}"
    
    local cron_entries=$(crontab -l 2>/dev/null | grep "auto-update.sh" | wc -l)
    
    if [ $cron_entries -eq 0 ]; then
        echo "❌ No hay actualizaciones automáticas configuradas"
    else
        echo "✅ Actualizaciones automáticas activas:"
        crontab -l 2>/dev/null | grep "auto-update.sh"
    fi
    echo ""
}

# Función para crear configuración de webhook (opcional)
setup_webhook() {
    echo -e "${YELLOW}🔔 Configuración de Notificaciones (Opcional)${NC}"
    echo ""
    echo "¿Deseas configurar notificaciones webhook? (Slack, Discord, etc.)"
    read -p "Configurar webhook? [y/N]: " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Ingresa la URL del webhook:"
        read webhook_url
        
        if [ -n "$webhook_url" ]; then
            sed -i "s|WEBHOOK_URL=\"\"|WEBHOOK_URL=\"$webhook_url\"|" "$APP_DIR/notify-update.sh"
            echo -e "${GREEN}✅ Webhook configurado${NC}"
        fi
    fi
}

# Función principal
main() {
    # Verificar directorio
    if [ ! -f "$APP_DIR/auto-update.sh" ]; then
        echo -e "${RED}❌ No se encontró auto-update.sh en $APP_DIR${NC}"
        exit 1
    fi
    
    # Crear directorio de logs
    mkdir -p "$APP_DIR/logs"
    
    # Mostrar estado actual
    show_current_status
    
    # Mostrar opciones
    show_frequency_options
    
    echo ""
    read -p "Selecciona una opción [1-6]: " -n 1 -r
    echo ""
    
    case $REPLY in
        [1-6])
            setup_cron $REPLY
            
            if [ $REPLY -ne 6 ] && [ $REPLY -ne 0 ]; then
                setup_webhook
                
                echo ""
                echo -e "${GREEN}🎉 Configuración completada${NC}"
                echo ""
                echo "📋 Comandos útiles:"
                echo "  crontab -l                    # Ver tareas programadas"
                echo "  tail -f $CRON_LOG            # Ver logs de actualizaciones automáticas"
                echo "  ./auto-update.sh check        # Verificar actualizaciones manualmente"
                echo "  ./auto-update.sh update       # Actualizar manualmente"
                echo ""
                echo "📁 Logs en:"
                echo "  $APP_DIR/logs/update.log      # Logs detallados"
                echo "  $CRON_LOG                     # Logs de cron"
            fi
            ;;
        0)
            echo "Operación cancelada"
            ;;
        *)
            echo "Opción inválida"
            ;;
    esac
}

# Ejecutar función principal
main
