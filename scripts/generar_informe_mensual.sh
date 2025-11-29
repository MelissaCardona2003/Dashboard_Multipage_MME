#!/bin/bash
# Script para generar informe mensual de cambios en el sistema
# Uso: ./generar_informe_mensual.sh [mes] [año]
#      ./generar_informe_mensual.sh 11 2025
#      ./generar_informe_mensual.sh    # mes y año actual

cd /home/admonctrlxm/server

# Obtener mes y año (usar actual si no se especifica)
if [ -n "$1" ] && [ -n "$2" ]; then
    MES=$1
    ANIO=$2
else
    MES=$(date "+%m")
    ANIO=$(date "+%Y")
fi

# Convertir mes a nombre en español
case $MES in
    01) MES_NOMBRE="enero" ;;
    02) MES_NOMBRE="febrero" ;;
    03) MES_NOMBRE="marzo" ;;
    04) MES_NOMBRE="abril" ;;
    05) MES_NOMBRE="mayo" ;;
    06) MES_NOMBRE="junio" ;;
    07) MES_NOMBRE="julio" ;;
    08) MES_NOMBRE="agosto" ;;
    09) MES_NOMBRE="septiembre" ;;
    10) MES_NOMBRE="octubre" ;;
    11) MES_NOMBRE="noviembre" ;;
    12) MES_NOMBRE="diciembre" ;;
    *) MES_NOMBRE="mes desconocido" ;;
esac

NOMBRE_ARCHIVO="INFORME_${MES_NOMBRE^^}_${ANIO}.md"

echo "================================================================================"
echo "   📊 GENERANDO INFORME MENSUAL"
echo "================================================================================"
echo ""
echo "Período: $MES_NOMBRE $ANIO"
echo "Archivo: $NOMBRE_ARCHIVO"
echo ""

# Crear encabezado del informe
cat > "$NOMBRE_ARCHIVO" << ENDHEADER
# 📊 Informe Mensual - Sistema Dashboard Energético
## Período: $MES_NOMBRE $ANIO

---

## 📅 Cambios y Actualizaciones Registradas

ENDHEADER

# Extraer entradas del mes de legacy/README.md
echo "Extrayendo cambios de legacy/README.md..."

# Buscar todas las líneas con fechas del mes/año especificado
# Formato esperado: ### **📅 DD de NOMBRE_MES de YYYY - HH:MM**
# También formato antiguo: ### **Actualización: DD de NOMBRE_MES de YYYY**

grep -A 20 "### \*\*" legacy/README.md | \
awk -v mes="$MES_NOMBRE" -v anio="$ANIO" '
    /### \*\*/ {
        if ($0 ~ mes && $0 ~ anio) {
            capture = 1
            print ""
        }
    }
    capture {
        print
        if (/^---$/ || /^###/ && !/### \*\*/) {
            capture = 0
        }
    }
' >> "$NOMBRE_ARCHIVO"

# Agregar sección de commits del mes
echo "" >> "$NOMBRE_ARCHIVO"
echo "---" >> "$NOMBRE_ARCHIVO"
echo "" >> "$NOMBRE_ARCHIVO"
echo "## 🔧 Commits del Período" >> "$NOMBRE_ARCHIVO"
echo "" >> "$NOMBRE_ARCHIVO"

# Obtener commits del mes (formato: YYYY-MM)
PERIODO="${ANIO}-${MES}"
git log --since="${PERIODO}-01" --until="${PERIODO}-31" --pretty=format:"- **%ad** - %s (commit: \`%h\`)" --date=short >> "$NOMBRE_ARCHIVO"

# Agregar estadísticas finales del mes
echo "" >> "$NOMBRE_ARCHIVO"
echo "" >> "$NOMBRE_ARCHIVO"
echo "---" >> "$NOMBRE_ARCHIVO"
echo "" >> "$NOMBRE_ARCHIVO"
echo "## 📈 Estado Final del Sistema" >> "$NOMBRE_ARCHIVO"
echo "" >> "$NOMBRE_ARCHIVO"

# Leer estado actual del sistema
if [ -f "logs/documentacion_state.json" ]; then
    echo "Estadísticas al cierre del período:" >> "$NOMBRE_ARCHIVO"
    echo "" >> "$NOMBRE_ARCHIVO"
    echo "\`\`\`json" >> "$NOMBRE_ARCHIVO"
    cat logs/documentacion_state.json >> "$NOMBRE_ARCHIVO"
    echo "\`\`\`" >> "$NOMBRE_ARCHIVO"
fi

echo "" >> "$NOMBRE_ARCHIVO"
echo "---" >> "$NOMBRE_ARCHIVO"
echo "" >> "$NOMBRE_ARCHIVO"
echo "*Informe generado automáticamente el $(date "+%d de %B de %Y a las %H:%M")*" >> "$NOMBRE_ARCHIVO"

# Mostrar resumen
echo ""
echo "================================================================================"
echo "   ✅ INFORME GENERADO EXITOSAMENTE"
echo "================================================================================"
echo ""
echo "Archivo creado: $NOMBRE_ARCHIVO"
echo ""
echo "Contenido:"
wc -l "$NOMBRE_ARCHIVO"
echo ""
echo "Para ver el informe:"
echo "  cat $NOMBRE_ARCHIVO"
echo ""
echo "Para editarlo:"
echo "  nano $NOMBRE_ARCHIVO"
echo ""
