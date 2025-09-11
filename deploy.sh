#!/bin/bash

echo "🚀 Desplegando Dashboard MME..."

# Detener procesos existentes
sudo systemctl stop dashboard-mme 2>/dev/null || true
sudo pkill -f "python.*app.py" 2>/dev/null || true
sleep 2

# Crear directorio de logs si no existe
mkdir -p /home/ubuntu/Dashboard_Multipage_MME/logs

# Iniciar aplicación manualmente con nohup
echo "📱 Iniciando aplicación en modo background..."
cd /home/ubuntu/Dashboard_Multipage_MME
source dashboard_env/bin/activate
nohup python app.py > logs/app.log 2>&1 &

sleep 5

# Verificar que la aplicación esté corriendo
if curl -s http://127.0.0.1:8056/ > /dev/null; then
    echo "✅ Aplicación funcionando en puerto 8056"
    echo "🌐 Disponible en: https://vps-0c525a03.vps.ovh.ca/"
    echo "🎉 Despliegue completado exitosamente!"
else
    echo "❌ Error: Aplicación no responde en puerto 8056"
    echo "📝 Ver logs: tail -f logs/app.log"
    exit 1
fi
