#!/bin/bash
# =============================================================================
# SCRIPT DE INSTALACIÓN DE ALIAS - Dashboard MME
# =============================================================================

echo "🚀 Configurando alias útiles para gestión del servidor..."

# Crear archivo de alias
cat >> ~/.bashrc << 'EOF'

# =============================================================================
# ALIAS PARA DASHBOARD MME - Agregados automáticamente
# =============================================================================

# Gestión rápida del dashboard
alias dashboard-status='sudo systemctl status dashboard-mme'
alias dashboard-start='sudo systemctl start dashboard-mme'
alias dashboard-stop='sudo systemctl stop dashboard-mme'
alias dashboard-restart='sudo systemctl restart dashboard-mme'
alias dashboard-logs='sudo journalctl -u dashboard-mme -f'

# Verificaciones rápidas
alias check-web='curl -I https://vps-0c525a03.vps.ovh.ca/'
alias check-app='curl -I http://localhost:8056/'
alias check-ssl='sudo certbot certificates'

# Navegación rápida
alias go-dashboard='cd /home/ubuntu/Dashboard_Multipage_MME'
alias go-logs='cd /home/ubuntu/Dashboard_Multipage_MME/logs'

# Scripts personalizados
alias manage='cd /home/ubuntu/Dashboard_Multipage_MME && ./manage-server.sh'
alias quick-check='cd /home/ubuntu/Dashboard_Multipage_MME && ./quick-check.sh'
alias show-commands='cd /home/ubuntu/Dashboard_Multipage_MME && ./commands-reference.sh'

# Monitoreo del sistema
alias recursos='htop'
alias espacio='df -h'
alias memoria='free -h'
alias procesos-dashboard='ps aux | grep -E "(gunicorn|python)" | grep -v grep'

# Actualización rápida
alias update-dashboard='cd /home/ubuntu/Dashboard_Multipage_MME && git pull origin main && sudo systemctl restart dashboard-mme'

# =============================================================================
EOF

echo "✅ Alias configurados exitosamente!"
echo ""
echo "🔄 Para activar los alias ahora mismo, ejecuta:"
echo "   source ~/.bashrc"
echo ""
echo "📋 NUEVOS COMANDOS DISPONIBLES:"
echo "   dashboard-status     # Ver estado del dashboard"
echo "   dashboard-restart    # Reiniciar dashboard"
echo "   dashboard-logs       # Ver logs en tiempo real"
echo "   check-web           # Verificar web"
echo "   manage              # Abrir menú de gestión"
echo "   quick-check         # Verificación rápida"
echo "   update-dashboard    # Actualizar desde Git"
echo "   procesos-dashboard  # Ver procesos activos"
echo ""
echo "💡 Ejecuta 'show-commands' para ver todos los comandos disponibles"
