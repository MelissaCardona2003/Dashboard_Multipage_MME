#!/bin/bash
# =============================================================================
# SCRIPT DE ACTUALIZACIÓN AUTOMÁTICA SEGURA - Dashboard MME
# =============================================================================
# Descripción: Actualiza el dashboard desde GitHub de forma segura
# Autor: Dashboard MME Team
# Fecha: Septiembre 2025
# =============================================================================

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Variables de configuración
REPO_DIR="/home/ubuntu/Dashboard_Multipage_MME"
BACKUP_DIR="/home/ubuntu/backups/dashboard"
LOG_FILE="$REPO_DIR/logs/update.log"
GITHUB_REPO="https://github.com/MelissaCardona2003/Dashboard_Multipage_MME.git"
BRANCH="main"

# Función para logging
log_message() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

# Función para crear backup
create_backup() {
    echo -e "${YELLOW}📦 Creando backup de seguridad...${NC}"
    
    # Crear directorio de backup si no existe
    mkdir -p "$BACKUP_DIR"
    
    # Crear backup con timestamp
    local backup_name="dashboard_backup_$(date +%Y%m%d_%H%M%S)"
    local backup_path="$BACKUP_DIR/$backup_name"
    
    # Copiar archivos importantes (excluir env y logs)
    rsync -av --exclude='dashboard_env/' --exclude='logs/' --exclude='.git/' \
          "$REPO_DIR/" "$backup_path/" > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Backup creado en: $backup_path${NC}"
        log_message "INFO" "Backup creado exitosamente en $backup_path"
        echo "$backup_path" > "$BACKUP_DIR/latest_backup.txt"
        return 0
    else
        echo -e "${RED}❌ Error al crear backup${NC}"
        log_message "ERROR" "Fallo al crear backup"
        return 1
    fi
}

# Función para verificar estado del repositorio
check_repo_status() {
    echo -e "${CYAN}🔍 Verificando estado del repositorio...${NC}"
    
    cd "$REPO_DIR" || exit 1
    
    # Verificar si hay cambios locales no guardados
    if ! git diff --quiet || ! git diff --staged --quiet; then
        echo -e "${YELLOW}⚠️ Hay cambios locales no guardados:${NC}"
        git status --porcelain
        return 1
    fi
    
    # Obtener información de commits
    local current_commit=$(git rev-parse HEAD)
    git fetch origin "$BRANCH" > /dev/null 2>&1
    local remote_commit=$(git rev-parse "origin/$BRANCH")
    
    echo "Commit actual: ${current_commit:0:8}"
    echo "Commit remoto: ${remote_commit:0:8}"
    
    if [ "$current_commit" = "$remote_commit" ]; then
        echo -e "${GREEN}✅ El repositorio ya está actualizado${NC}"
        return 2
    else
        echo -e "${YELLOW}📥 Hay actualizaciones disponibles${NC}"
        return 0
    fi
}

# Función para mostrar cambios
show_changes() {
    echo -e "${CYAN}📋 Cambios que se aplicarán:${NC}"
    
    cd "$REPO_DIR" || exit 1
    
    # Mostrar commits nuevos
    echo -e "\n${YELLOW}🔄 Nuevos commits:${NC}"
    git log --oneline HEAD..origin/"$BRANCH" | head -10
    
    # Mostrar archivos que cambiarán
    echo -e "\n${YELLOW}📁 Archivos modificados:${NC}"
    git diff --name-status HEAD..origin/"$BRANCH"
    
    # Verificar si hay cambios en archivos críticos
    local critical_files="app.py requirements.txt"
    local critical_changes=false
    
    for file in $critical_files; do
        if git diff --name-only HEAD..origin/"$BRANCH" | grep -q "^$file$"; then
            echo -e "${RED}⚠️ Archivo crítico modificado: $file${NC}"
            critical_changes=true
        fi
    done
    
    if [ "$critical_changes" = true ]; then
        echo -e "\n${RED}🚨 ATENCIÓN: Hay cambios en archivos críticos${NC}"
        return 1
    fi
    
    return 0
}

# Función para verificar dependencias
check_dependencies() {
    echo -e "${CYAN}🔍 Verificando dependencias...${NC}"
    
    cd "$REPO_DIR" || exit 1
    
    # Verificar si requirements.txt cambió
    if git diff --name-only HEAD..origin/"$BRANCH" | grep -q "requirements.txt"; then
        echo -e "${YELLOW}📦 requirements.txt ha cambiado. Será necesario actualizar dependencias.${NC}"
        return 1
    fi
    
    return 0
}

# Función para actualizar dependencias
update_dependencies() {
    echo -e "${YELLOW}📦 Actualizando dependencias...${NC}"
    
    cd "$REPO_DIR" || exit 1
    source dashboard_env/bin/activate
    
    pip install -r requirements.txt --quiet
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Dependencias actualizadas${NC}"
        log_message "INFO" "Dependencias actualizadas exitosamente"
        return 0
    else
        echo -e "${RED}❌ Error al actualizar dependencias${NC}"
        log_message "ERROR" "Fallo al actualizar dependencias"
        return 1
    fi
}

# Función para aplicar actualización
apply_update() {
    echo -e "${YELLOW}🔄 Aplicando actualización...${NC}"
    
    cd "$REPO_DIR" || exit 1
    
    # Hacer merge de los cambios
    git merge "origin/$BRANCH" --no-edit
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Actualización aplicada exitosamente${NC}"
        log_message "INFO" "Actualización Git aplicada exitosamente"
        return 0
    else
        echo -e "${RED}❌ Error al aplicar actualización${NC}"
        log_message "ERROR" "Fallo al aplicar actualización Git"
        return 1
    fi
}

# Función para reiniciar aplicación
restart_application() {
    echo -e "${YELLOW}🔄 Reiniciando aplicación...${NC}"
    
    # Detener aplicación actual
    pkill -f "python.*app.py" 2>/dev/null || true
    sleep 3
    
    # Iniciar aplicación
    cd "$REPO_DIR" || exit 1
    source dashboard_env/bin/activate
    nohup python app.py > logs/app.log 2>&1 &
    
    # Verificar que inició correctamente
    sleep 5
    if pgrep -f "python.*app.py" > /dev/null; then
        echo -e "${GREEN}✅ Aplicación reiniciada exitosamente${NC}"
        log_message "INFO" "Aplicación reiniciada exitosamente"
        
        # Verificar conectividad
        if curl -s http://127.0.0.1:8056/ > /dev/null; then
            echo -e "${GREEN}✅ Aplicación respondiendo correctamente${NC}"
            return 0
        else
            echo -e "${RED}❌ Aplicación no responde${NC}"
            log_message "ERROR" "Aplicación no responde después del reinicio"
            return 1
        fi
    else
        echo -e "${RED}❌ Error al reiniciar aplicación${NC}"
        log_message "ERROR" "Fallo al reiniciar aplicación"
        return 1
    fi
}

# Función para rollback
rollback() {
    echo -e "${RED}🔙 Iniciando rollback...${NC}"
    
    # Obtener último backup
    local latest_backup=$(cat "$BACKUP_DIR/latest_backup.txt" 2>/dev/null)
    
    if [ -z "$latest_backup" ] || [ ! -d "$latest_backup" ]; then
        echo -e "${RED}❌ No se encontró backup para rollback${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}📦 Restaurando desde: $latest_backup${NC}"
    
    # Detener aplicación
    pkill -f "python.*app.py" 2>/dev/null || true
    
    # Restaurar archivos (preservar env y logs)
    rsync -av --exclude='dashboard_env/' --exclude='logs/' \
          "$latest_backup/" "$REPO_DIR/" > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Rollback completado${NC}"
        log_message "INFO" "Rollback ejecutado exitosamente"
        
        # Reiniciar aplicación
        restart_application
        return $?
    else
        echo -e "${RED}❌ Error en rollback${NC}"
        log_message "ERROR" "Fallo en rollback"
        return 1
    fi
}

# Función para limpieza de backups antiguos
cleanup_old_backups() {
    echo -e "${CYAN}🧹 Limpiando backups antiguos...${NC}"
    
    # Mantener solo los últimos 5 backups
    find "$BACKUP_DIR" -name "dashboard_backup_*" -type d | sort -r | tail -n +6 | xargs rm -rf 2>/dev/null
    
    echo -e "${GREEN}✅ Limpieza de backups completada${NC}"
}

# Función principal de actualización
main_update() {
    echo -e "${BLUE}🚀 INICIANDO ACTUALIZACIÓN AUTOMÁTICA${NC}"
    echo -e "${BLUE}=====================================${NC}"
    log_message "INFO" "Iniciando proceso de actualización automática"
    
    # Verificar que estamos en el directorio correcto
    if [ ! -d "$REPO_DIR/.git" ]; then
        echo -e "${RED}❌ No se encontró repositorio Git en $REPO_DIR${NC}"
        exit 1
    fi
    
    # Crear directorio de logs si no existe
    mkdir -p "$REPO_DIR/logs"
    
    # Paso 1: Crear backup
    if ! create_backup; then
        echo -e "${RED}❌ No se pudo crear backup. Abortando actualización.${NC}"
        exit 1
    fi
    
    # Paso 2: Verificar estado del repositorio
    check_repo_status
    local repo_status=$?
    
    if [ $repo_status -eq 1 ]; then
        echo -e "${RED}❌ Hay cambios locales no guardados. Abortando actualización.${NC}"
        echo -e "${YELLOW}💡 Ejecuta 'git status' para ver los cambios${NC}"
        exit 1
    elif [ $repo_status -eq 2 ]; then
        echo -e "${GREEN}🎉 No hay actualizaciones disponibles${NC}"
        cleanup_old_backups
        exit 0
    fi
    
    # Paso 3: Mostrar cambios
    show_changes
    local critical_changes=$?
    
    # Paso 4: Verificar dependencias
    check_dependencies
    local deps_changed=$?
    
    # Paso 5: Confirmación del usuario
    echo -e "\n${YELLOW}❓ ¿Deseas continuar con la actualización?${NC}"
    if [ $critical_changes -eq 1 ]; then
        echo -e "${RED}⚠️ ADVERTENCIA: Hay cambios en archivos críticos${NC}"
    fi
    
    read -p "Continuar? [y/N]: " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}❌ Actualización cancelada por el usuario${NC}"
        exit 0
    fi
    
    # Paso 6: Aplicar actualización
    if ! apply_update; then
        echo -e "${RED}❌ Error en la actualización. Iniciando rollback...${NC}"
        rollback
        exit 1
    fi
    
    # Paso 7: Actualizar dependencias si es necesario
    if [ $deps_changed -eq 1 ]; then
        if ! update_dependencies; then
            echo -e "${RED}❌ Error al actualizar dependencias. Iniciando rollback...${NC}"
            rollback
            exit 1
        fi
    fi
    
    # Paso 8: Reiniciar aplicación
    if ! restart_application; then
        echo -e "${RED}❌ Error al reiniciar aplicación. Iniciando rollback...${NC}"
        rollback
        exit 1
    fi
    
    # Paso 9: Verificación final
    echo -e "\n${GREEN}🎉 ACTUALIZACIÓN COMPLETADA EXITOSAMENTE${NC}"
    echo -e "${GREEN}=====================================${NC}"
    echo -e "${GREEN}✅ Dashboard actualizado desde GitHub${NC}"
    echo -e "${GREEN}✅ Aplicación funcionando correctamente${NC}"
    echo -e "${GREEN}🌐 Disponible en: https://vps-0c525a03.vps.ovh.ca/${NC}"
    
    log_message "INFO" "Actualización completada exitosamente"
    
    # Limpiar backups antiguos
    cleanup_old_backups
    
    echo -e "\n${CYAN}📋 Para ver los logs: tail -f $LOG_FILE${NC}"
}

# Función para mostrar ayuda
show_help() {
    echo -e "${BLUE}📖 SCRIPT DE ACTUALIZACIÓN AUTOMÁTICA - Dashboard MME${NC}"
    echo ""
    echo "Uso: $0 [opción]"
    echo ""
    echo "Opciones:"
    echo "  update, -u        Ejecutar actualización automática"
    echo "  check, -c         Solo verificar si hay actualizaciones"
    echo "  rollback, -r      Rollback a la última versión"
    echo "  status, -s        Ver estado del repositorio"
    echo "  help, -h          Mostrar esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  $0 update         # Actualizar dashboard"
    echo "  $0 check          # Solo verificar actualizaciones"
    echo "  $0 rollback       # Rollback si algo salió mal"
}

# Función para solo verificar actualizaciones
check_only() {
    echo -e "${CYAN}🔍 VERIFICANDO ACTUALIZACIONES${NC}"
    echo -e "${CYAN}==============================${NC}"
    
    cd "$REPO_DIR" || exit 1
    
    check_repo_status
    local status=$?
    
    if [ $status -eq 2 ]; then
        echo -e "${GREEN}✅ Tu dashboard está actualizado${NC}"
    elif [ $status -eq 0 ]; then
        show_changes
        echo -e "\n${YELLOW}💡 Ejecuta '$0 update' para actualizar${NC}"
    else
        echo -e "${RED}❌ Hay problemas con el repositorio local${NC}"
    fi
}

# Función para mostrar estado
show_status() {
    echo -e "${CYAN}📊 ESTADO DEL REPOSITORIO${NC}"
    echo -e "${CYAN}=========================${NC}"
    
    cd "$REPO_DIR" || exit 1
    
    echo "Rama actual: $(git branch --show-current)"
    echo "Último commit: $(git log --oneline -1)"
    echo ""
    
    git status
}

# Procesamiento de argumentos
case "${1:-update}" in
    "update"|"-u")
        main_update
        ;;
    "check"|"-c")
        check_only
        ;;
    "rollback"|"-r")
        rollback
        ;;
    "status"|"-s")
        show_status
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo -e "${RED}❌ Opción inválida: $1${NC}"
        show_help
        exit 1
        ;;
esac
