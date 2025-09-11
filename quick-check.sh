#!/bin/bash
# =============================================================================
# SCRIPT DE VERIFICACIÓN RÁPIDA - Dashboard MME
# =============================================================================

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

DOMAIN="vps-0c525a03.vps.ovh.ca"

echo -e "${GREEN}🚀 VERIFICACIÓN RÁPIDA - Dashboard MME${NC}"
echo "========================================"

# Estado de la aplicación
echo -e "\n${YELLOW}📊 Estado de la Aplicación:${NC}"
if pgrep -f "python.*app.py" > /dev/null; then
    PID=$(pgrep -f "python.*app.py")
    echo -e "${GREEN}✅ Aplicación corriendo (PID: $PID)${NC}"
else
    echo -e "${RED}❌ Aplicación NO está corriendo${NC}"
fi

# Estado de nginx
echo -e "\n${YELLOW}🌐 Estado de Nginx:${NC}"
if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✅ Nginx activo${NC}"
else
    echo -e "${RED}❌ Nginx inactivo${NC}"
fi

# Conectividad web
echo -e "\n${YELLOW}🔗 Conectividad Web:${NC}"
HTTP_STATUS=$(curl -o /dev/null -s -w "%{http_code}" https://$DOMAIN/)
if [ "$HTTP_STATUS" = "200" ]; then
    echo -e "${GREEN}✅ Web funcionando correctamente (HTTP $HTTP_STATUS)${NC}"
else
    echo -e "${RED}❌ Problema en web (HTTP $HTTP_STATUS)${NC}"
fi

# Test aplicación local
LOCAL_STATUS=$(curl -o /dev/null -s -w "%{http_code}" http://127.0.0.1:8056/)
if [ "$LOCAL_STATUS" = "200" ]; then
    echo -e "${GREEN}✅ Aplicación local respondiendo (HTTP $LOCAL_STATUS)${NC}"
else
    echo -e "${RED}❌ Aplicación local no responde (HTTP $LOCAL_STATUS)${NC}"
fi

# Uso de recursos
echo -e "\n${YELLOW}📈 Uso de Recursos:${NC}"
echo "Memoria:"
free -h | grep Mem | awk '{print "  Usada: "$3" / Total: "$2" ("$3/$2*100"% usado)"}'
echo "CPU Load:"
uptime | awk '{print "  "$10","$11","$12}'
echo "Disco:"
df -h / | tail -1 | awk '{print "  Usado: "$3" / Total: "$2" ("$5" usado)"}'

# Procesos Python
echo -e "\n${YELLOW}🔍 Procesos Python Activos:${NC}"
PYTHON_PROCS=$(ps aux | grep python | grep -v grep | wc -l)
echo "  Total procesos Python: $PYTHON_PROCS"
if [ $PYTHON_PROCS -gt 0 ]; then
    ps aux | grep python | grep -v grep | head -3 | awk '{print "  "$2" - "$11" "$12" "$13}'
fi

# SSL
echo -e "\n${YELLOW}🔐 Estado SSL:${NC}"
SSL_EXPIRY=$(echo | openssl s_client -servername $DOMAIN -connect $DOMAIN:443 2>/dev/null | openssl x509 -noout -dates 2>/dev/null | grep notAfter | cut -d= -f2)
if [ -n "$SSL_EXPIRY" ]; then
    echo "  Certificado expira: $SSL_EXPIRY"
else
    echo "  No se pudo verificar certificado SSL"
fi

echo -e "\n${GREEN}✅ Verificación completa terminada${NC}"
echo "========================================"

# Recomendaciones
echo -e "\n${YELLOW}💡 COMANDOS ÚTILES:${NC}"
echo "  ./manage-server.sh    # Menú de gestión completo"
echo "  ./deploy.sh          # Reiniciar aplicación"
echo "  tail -f logs/app.log # Ver logs en tiempo real"

# IP externa
if curl -s -I http://148.113.203.44:8056 | grep -q "200\|302"; then
    echo "  ✅ IP externa:8056 - FUNCIONA"
else
    echo "  ❌ IP externa:8056 - NO RESPONDE"
fi

# Dominio
if curl -s -I http://vps-0c525a03.vps.ovh.ca | grep -q "200\|302"; then
    echo "  ✅ Dominio OVH - FUNCIONA"
else
    echo "  ❌ Dominio OVH - NO RESPONDE"
fi

echo ""
echo "🎯 PRÓXIMOS PASOS RECOMENDADOS:"

if [ "$dashboard_status" != "active" ]; then
    echo "  1. Iniciar servicio dashboard: sudo systemctl start dashboard-mme"
fi

if [ "$nginx_status" != "active" ]; then
    echo "  2. Iniciar nginx: sudo systemctl start nginx"
fi

if [ $port_80 -eq 0 ]; then
    echo "  3. Configurar nginx en puerto 80: ./fix-nginx.sh"
fi

echo "  4. Ver diagnóstico completo: ./verify-status.sh"

echo ""
echo "====================================="
