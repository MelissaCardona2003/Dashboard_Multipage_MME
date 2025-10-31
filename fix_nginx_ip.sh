#!/bin/bash
# Script para arreglar nginx y permitir acceso por IP

echo "======================================================================"
echo "Arreglando configuración de Nginx para acceso por IP"
echo "======================================================================"

# Hacer backup
sudo cp /etc/nginx/sites-available/portalenergetico /etc/nginx/sites-available/portalenergetico.backup

# Actualizar ambos bloques server para incluir la IP
sudo sed -i 's/server_name portalenergetico.minenergia.gov.co www.portalenergetico.minenergia.gov.co;/server_name portalenergetico.minenergia.gov.co www.portalenergetico.minenergia.gov.co 172.17.0.46 localhost;/g' /etc/nginx/sites-available/portalenergetico

# Verificar configuración
echo ""
echo "Verificando configuración de Nginx..."
sudo nginx -t

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Configuración válida. Recargando Nginx..."
    sudo systemctl reload nginx
    echo ""
    echo "✅ Nginx recargado exitosamente"
    echo ""
    echo "Ahora puedes acceder a:"
    echo "  - http://172.17.0.46"
    echo "  - http://localhost"
    echo "  - http://portalenergetico.minenergia.gov.co (cuando DNS esté actualizado)"
else
    echo ""
    echo "❌ Error en la configuración. Restaurando backup..."
    sudo cp /etc/nginx/sites-available/portalenergetico.backup /etc/nginx/sites-available/portalenergetico
fi
