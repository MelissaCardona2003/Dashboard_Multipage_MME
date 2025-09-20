#!/bin/bash
# =============================================================================
# SCRIPT DE COMANDOS ESENCIALES - Dashboard MME
# =============================================================================

# Variables
SERVICE="dashboard-mme"
DOMAIN="vps-0c525a03.vps.ovh.ca"

echo "📋 COMANDOS ESENCIALES PARA GESTIÓN DEL SERVIDOR"
echo "=============================================="
echo ""

echo "🔧 GESTIÓN DEL SERVICIO:"
echo "  sudo systemctl status $SERVICE      # Ver estado"
echo "  sudo systemctl start $SERVICE       # Iniciar"
echo "  sudo systemctl stop $SERVICE        # Detener"
echo "  sudo systemctl restart $SERVICE     # Reiniciar"
echo "  sudo systemctl enable $SERVICE      # Auto-inicio"
echo ""

echo "📝 LOGS Y MONITOREO:"
echo "  sudo journalctl -u $SERVICE -f      # Ver logs en tiempo real"
echo "  sudo journalctl -u $SERVICE -n 50   # Ver últimos 50 logs"
echo "  ps aux | grep gunicorn               # Ver procesos"
echo "  htop                                 # Monitor de recursos"
echo ""

echo "🌐 VERIFICACIÓN WEB:"
echo "  curl -I https://$DOMAIN/             # Test HTTP"
echo "  curl -I http://localhost:8056/       # Test app directa"
echo "  sudo nginx -t                        # Test configuración nginx"
echo "  sudo systemctl reload nginx         # Recargar nginx"
echo ""

echo "🔐 SSL Y CERTIFICADOS:"
echo "  sudo certbot certificates           # Ver certificados"
echo "  sudo certbot renew                  # Renovar certificados"
echo "  sudo certbot renew --dry-run        # Test renovación"
echo ""

echo "📊 SISTEMA:"
echo "  df -h                                # Espacio en disco"
echo "  free -h                              # Memoria RAM"
echo "  uptime                               # Tiempo funcionando"
echo "  top                                  # Procesos en tiempo real"
echo ""

echo "🔄 ACTUALIZACIÓN:"
echo "  cd /home/ubuntu/Dashboard_Multipage_MME"
echo "  git pull origin main                 # Actualizar código"
echo "  sudo systemctl restart $SERVICE     # Reiniciar después de actualizar"
echo ""

echo "🚨 EMERGENCIA:"
echo "  sudo systemctl restart nginx        # Reiniciar nginx"
echo "  sudo systemctl restart $SERVICE     # Reiniciar dashboard"
echo "  sudo reboot                          # Reiniciar servidor completo"
echo ""

echo "💡 SCRIPTS PERSONALIZADOS:"
echo "  ./manage-server.sh                   # Script de gestión completo"
echo "  ./quick-check.sh                     # Verificación rápida"
echo ""

echo "=============================================="
