#!/bin/bash
# Script manual para actualizar documentación del proyecto
# Uso: ./actualizar_docs.sh [mensaje]

cd /home/admonctrlxm/server

echo "================================================================================"
echo "   📚 ACTUALIZACIÓN MANUAL DE DOCUMENTACIÓN"
echo "================================================================================"

# Ejecutar actualización
python3 scripts/actualizar_documentacion.py

# Si se proporcionó un mensaje, agregarlo al legacy/README.md
if [ -n "$1" ]; then
    FECHA=$(date "+%d de %B de %Y - %H:%M")
    FECHA_CORTA=$(date "+%d/%m/%Y")
    ENTRADA="

### **📅 $FECHA**

**Nota:** $1

**Fecha para informe:** $FECHA_CORTA

---
"
    
    # Insertar en legacy/README.md después de "## 📊 ESTADO ACTUAL DEL SISTEMA"
    if grep -q "## 📊 ESTADO ACTUAL DEL SISTEMA" legacy/README.md; then
        # Crear archivo temporal con la entrada
        echo "$ENTRADA" > /tmp/entrada_legacy.txt
        
        # Insertar después de la primera aparición de "###" tras "## 📊 ESTADO ACTUAL"
        awk '/## 📊 ESTADO ACTUAL DEL SISTEMA/{found=1} found && /^###/{if(!inserted){system("cat /tmp/entrada_legacy.txt"); inserted=1}} 1' legacy/README.md > /tmp/legacy_nuevo.md
        
        mv /tmp/legacy_nuevo.md legacy/README.md
        rm /tmp/entrada_legacy.txt
        
        echo ""
        echo "✅ Nota agregada a legacy/README.md: $1"
    fi
fi

echo ""
echo "================================================================================"
echo "   ✅ DOCUMENTACIÓN ACTUALIZADA"
echo "================================================================================"
echo ""
echo "Archivos actualizados:"
echo "  - README.md (arquitectura actual)"
echo "  - legacy/README.md (trazabilidad histórica)"
echo ""
echo "Para ver cambios: git diff README.md legacy/README.md"
echo ""
