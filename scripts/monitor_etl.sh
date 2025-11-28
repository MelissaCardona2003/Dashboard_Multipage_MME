#!/bin/bash
# Monitor ETL Progress
# Monitorea el progreso del ETL y avisa cuando termine

LOG_FILE="/home/admonctrlxm/server/logs/etl_completar_2020.log"
CHECK_INTERVAL=30  # Verificar cada 30 segundos

echo "🔍 Monitoreando ETL..."
echo "📁 Log: $LOG_FILE"
echo "⏱️  Verificando cada ${CHECK_INTERVAL}s"
echo ""

# Función para obtener progreso
get_progress() {
    if [ ! -f "$LOG_FILE" ]; then
        echo "❌ Log file no encontrado"
        return 1
    fi
    
    # Contar métricas procesadas
    total_metricas=$(grep -c "📡.*Rango:" "$LOG_FILE" 2>/dev/null || echo "0")
    exitosas=$(grep -c "✅.*registros guardados en SQLite" "$LOG_FILE" 2>/dev/null || echo "0")
    errores=$(grep -c "ERROR:root:❌" "$LOG_FILE" 2>/dev/null || echo "0")
    
    echo "📊 Métricas procesadas: $exitosas/$total_metricas"
    echo "❌ Errores: $errores"
    
    # Última línea con progreso
    ultima_metrica=$(grep "📡" "$LOG_FILE" | tail -1)
    if [ ! -z "$ultima_metrica" ]; then
        echo "🔄 Última: $ultima_metrica"
    fi
}

# Loop principal
while true; do
    clear
    echo "════════════════════════════════════════════════════════════"
    echo "          🔍 MONITOR ETL - $(date '+%H:%M:%S')"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    
    # Verificar si el proceso sigue corriendo
    if ps aux | grep -q "[e]tl_xm_to_sqlite.py.*fecha-inicio"; then
        echo "✅ ETL en ejecución"
        echo ""
        get_progress
        echo ""
        echo "⏳ Esperando ${CHECK_INTERVAL}s para próxima verificación..."
        sleep $CHECK_INTERVAL
    else
        echo "🎉 ETL FINALIZADO"
        echo ""
        get_progress
        echo ""
        
        # Verificar si terminó exitosamente
        if grep -q "Fin:" "$LOG_FILE"; then
            echo "✅ ETL completado exitosamente"
            
            # Mostrar estadísticas finales
            echo ""
            echo "═══════════════════════════════════════════════════════════"
            echo "📊 RESUMEN FINAL"
            echo "═══════════════════════════════════════════════════════════"
            grep -A 10 "RESUMEN FINAL" "$LOG_FILE" 2>/dev/null || echo "(Resumen no disponible)"
        else
            echo "⚠️  ETL terminó inesperadamente"
            echo ""
            echo "Últimas líneas del log:"
            tail -20 "$LOG_FILE"
        fi
        
        break
    fi
done

echo ""
echo "🏁 Monitoreo finalizado"
