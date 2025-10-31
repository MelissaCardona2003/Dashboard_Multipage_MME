#!/bin/bash

# Script de gestión del Dashboard MME

case "$1" in
    start)
        echo "🚀 Iniciando Dashboard MME..."
        sudo systemctl start dashboard-mme
        sudo systemctl start nginx
        sleep 3
        echo ""
        echo "✅ Dashboard iniciado"
        echo "📍 Acceso local: http://localhost"
        echo "📍 Acceso red: http://172.17.0.46"
        ;;
    
    stop)
        echo "🛑 Deteniendo Dashboard MME..."
        sudo systemctl stop dashboard-mme
        echo "✅ Dashboard detenido"
        ;;
    
    restart)
        echo "🔄 Reiniciando Dashboard MME..."
        sudo systemctl restart dashboard-mme
        sudo systemctl reload nginx
        sleep 3
        echo "✅ Dashboard reiniciado"
        ;;
    
    status)
        echo "📊 Estado del Dashboard MME"
        echo "================================"
        echo ""
        echo "Servicio Dashboard:"
        sudo systemctl status dashboard-mme --no-pager -l | head -15
        echo ""
        echo "Servicio Nginx:"
        sudo systemctl status nginx --no-pager | head -10
        echo ""
        echo "Puertos activos:"
        sudo ss -tlnp | grep -E '(:80|:8050)'
        ;;
    
    logs)
        echo "📋 Logs del Dashboard (Ctrl+C para salir)"
        echo "=========================================="
        sudo journalctl -u dashboard-mme -f
        ;;
    
    logs-app)
        echo "📋 Logs de la aplicación (Ctrl+C para salir)"
        echo "============================================="
        tail -f /home/admonctrlxm/server/logs/dashboard.log
        ;;
    
    logs-error)
        echo "⚠️  Logs de errores (Ctrl+C para salir)"
        echo "========================================"
        tail -f /home/admonctrlxm/server/logs/dashboard-error.log
        ;;
    
    test)
        echo "🧪 Probando el Dashboard..."
        echo ""
        
        # Test local
        if curl -s -o /dev/null -w "%{http_code}" http://localhost | grep -q "200"; then
            echo "✅ http://localhost - Funcionando"
        else
            echo "❌ http://localhost - Fallo"
        fi
        
        # Test IP privada
        if curl -s -o /dev/null -w "%{http_code}" http://172.17.0.46 | grep -q "200"; then
            echo "✅ http://172.17.0.46 - Funcionando"
        else
            echo "❌ http://172.17.0.46 - Fallo"
        fi
        
        # Test puerto directo
        if curl -s -o /dev/null -w "%{http_code}" http://localhost:8050 | grep -q "200"; then
            echo "✅ http://localhost:8050 (Gunicorn) - Funcionando"
        else
            echo "❌ http://localhost:8050 - Fallo"
        fi
        
        echo ""
        echo "Estado de servicios:"
        systemctl is-active dashboard-mme >/dev/null 2>&1 && echo "✅ Dashboard: Activo" || echo "❌ Dashboard: Inactivo"
        systemctl is-active nginx >/dev/null 2>&1 && echo "✅ Nginx: Activo" || echo "❌ Nginx: Inactivo"
        ;;
    
    update)
        echo "🔄 Actualizando Dashboard desde GitHub..."
        cd /home/admonctrlxm/server
        git pull
        echo ""
        echo "📦 Actualizando dependencias..."
        pip install --break-system-packages -r requirements.txt --upgrade
        echo ""
        echo "🔄 Reiniciando servicio..."
        sudo systemctl restart dashboard-mme
        echo "✅ Dashboard actualizado"
        ;;
    
    *)
        echo "🌟 Dashboard MME - Sistema de Gestión"
        echo "======================================"
        echo ""
        echo "Uso: $0 {start|stop|restart|status|logs|logs-app|logs-error|test|update}"
        echo ""
        echo "Comandos disponibles:"
        echo "  start       - Iniciar el dashboard"
        echo "  stop        - Detener el dashboard"
        echo "  restart     - Reiniciar el dashboard"
        echo "  status      - Ver estado de servicios"
        echo "  logs        - Ver logs del servicio (tiempo real)"
        echo "  logs-app    - Ver logs de la aplicación"
        echo "  logs-error  - Ver logs de errores"
        echo "  test        - Probar accesibilidad"
        echo "  update      - Actualizar desde GitHub"
        echo ""
        exit 1
        ;;
esac
