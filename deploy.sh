#!/bin/bash

echo "🚀 Desplegando Dashboard MME..."

# Detener procesos existentes
sudo pkill -f "python.*app.py" 2>/dev/null || true
sleep 2

# Iniciar aplicación
cd /home/ubuntu/Dashboard_Multipage_MME
source dashboard_env/bin/activate

echo "📱 Iniciando aplicación Dash en puerto 8056..."
nohup python app.py > logs/app.log 2>&1 &

sleep 5

# Verificar que la aplicación esté corriendo
if curl -s http://127.0.0.1:8056/ > /dev/null; then
    echo "✅ Aplicación funcionando en puerto 8056"
    echo "🌐 Disponible en:"
    echo "   - https://vps-0c525a03.vps.ovh.ca/ (HTTPS seguro)"
    echo "   - http://148.113.203.44:8056/ (directo)"
else
    echo "❌ Error: Aplicación no responde en puerto 8056"
    exit 1
fi

echo "🎉 Despliegue completado!"
