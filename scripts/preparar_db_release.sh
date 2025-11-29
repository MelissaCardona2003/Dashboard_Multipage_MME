#!/bin/bash
# Script para preparar la base de datos para GitHub Release

cd /home/admonctrlxm/server

echo "================================================================================"
echo "   📦 PREPARAR BASE DE DATOS PARA GITHUB RELEASE"
echo "================================================================================"
echo ""

# Verificar si ya existe el archivo comprimido
if [ -f "portal_energetico.db.tar.gz" ]; then
    echo "✅ Archivo comprimido ya existe: portal_energetico.db.tar.gz"
    ls -lh portal_energetico.db.tar.gz
else
    echo "📦 Comprimiendo base de datos..."
    tar -czf portal_energetico.db.tar.gz portal_energetico.db
    echo "✅ Compresión completada"
    ls -lh portal_energetico.db.tar.gz
fi

echo ""
echo "================================================================================"
echo "   📋 INSTRUCCIONES PARA SUBIR A GITHUB"
echo "================================================================================"
echo ""
echo "1. Descarga el archivo a tu computador local:"
echo "   scp admonctrlxm@Srvwebprdctrlxm:/home/admonctrlxm/server/portal_energetico.db.tar.gz ./"
echo ""
echo "2. Ve a GitHub: https://github.com/MelissaCardona2003/Dashboard_Multipage_MME"
echo ""
echo "3. Click en 'Releases' (lado derecho)"
echo ""
echo "4. Click en 'Create a new release'"
echo ""
echo "5. Configurar:"
echo "   - Tag: v1.0-db-$(date +%Y%m%d)"
echo "   - Title: Base de Datos Portal Energético - $(date '+%d %B %Y')"
echo "   - Description: Base de datos SQLite con 1.3M+ registros (5 años históricos)"
echo ""
echo "6. Arrastra el archivo portal_energetico.db.tar.gz al área de 'Attach binaries'"
echo ""
echo "7. Click en 'Publish release'"
echo ""
echo "================================================================================"
echo "   📥 PARA USAR EN LOCAL"
echo "================================================================================"
echo ""
echo "Después de descargar desde GitHub Releases:"
echo "  tar -xzf portal_energetico.db.tar.gz"
echo ""
echo "Tamaño original: $(du -h portal_energetico.db 2>/dev/null | cut -f1)"
echo "Tamaño comprimido: $(du -h portal_energetico.db.tar.gz 2>/dev/null | cut -f1)"
echo ""
