# 🚀 Sistema de Actualización Automática - Dashboard MME

Este documento explica cómo funciona el sistema de actualización automática del Dashboard MME desde GitHub.

## 📋 Scripts Disponibles

### 1. `auto-update.sh` - Script Principal de Actualización

**Funciones principales:**
- ✅ Verificación segura de actualizaciones desde GitHub
- 📦 Creación automática de backups antes de actualizar
- 🔄 Actualización inteligente con rollback automático en caso de error
- 📝 Logging detallado de todas las operaciones
- 🔍 Verificación de cambios críticos antes de aplicar

**Comandos disponibles:**
```bash
./auto-update.sh update     # Actualizar dashboard completo
./auto-update.sh check      # Solo verificar si hay actualizaciones
./auto-update.sh rollback   # Rollback a la versión anterior
./auto-update.sh status     # Ver estado del repositorio
./auto-update.sh help       # Mostrar ayuda
```

### 2. `setup-auto-update.sh` - Configurador de Actualizaciones Automáticas

**Opciones de configuración:**
- ⏰ Cada hora
- ⏰ Cada 4 horas  
- ⏰ Cada 12 horas
- ⏰ Diariamente (2:00 AM)
- 👁️ Solo verificación (sin actualizar)
- ❌ Desactivar actualizaciones automáticas

**Para configurar:**
```bash
./setup-auto-update.sh
```

## 🔧 Cómo Funciona

### Proceso de Actualización Segura

1. **Verificación inicial**: Comprueba el estado del repositorio local
2. **Backup automático**: Crea copia de seguridad de los archivos actuales
3. **Análisis de cambios**: Muestra qué archivos y commits van a aplicarse
4. **Verificación de dependencias**: Detecta si `requirements.txt` cambió
5. **Confirmación**: Pide confirmación si hay cambios críticos
6. **Aplicación segura**: Aplica los cambios con Git merge
7. **Actualización de dependencias**: Si es necesario, actualiza pip packages
8. **Reinicio de aplicación**: Reinicia el dashboard automáticamente
9. **Verificación final**: Confirma que todo funciona correctamente
10. **Rollback automático**: Si algo falla, restaura la versión anterior

### Sistema de Backups

- 📦 Backup automático antes de cada actualización
- 📅 Conserva los últimos 5 backups
- 🗂️ Ubicación: `/home/ubuntu/backups/dashboard/`
- 🔄 Rollback rápido con `./auto-update.sh rollback`

### Logging

- 📝 **Logs detallados**: `/home/ubuntu/Dashboard_Multipage_MME/logs/update.log`
- 📝 **Logs de cron**: `/home/ubuntu/Dashboard_Multipage_MME/logs/cron_update.log`
- 📊 **Timestamp de todas las operaciones**
- 🚨 **Registro de errores y recuperaciones**

## 🛡️ Características de Seguridad

### Protección contra Conflictos
- ❌ No actualiza si hay cambios locales no guardados
- 🔍 Detecta conflictos antes de aplicar cambios
- 📋 Muestra preview de todos los cambios

### Detección de Cambios Críticos
- ⚠️ Alerta especial para cambios en `app.py`
- ⚠️ Alerta especial para cambios en `requirements.txt`
- 🔔 Solicita confirmación explícita para cambios importantes

### Rollback Automático
- 🔄 Rollback automático si falla la actualización
- 🔄 Rollback automático si falla el reinicio de la aplicación
- 🔄 Rollback manual disponible en cualquier momento

## 📊 Monitoreo y Logs

### Ver Logs en Tiempo Real
```bash
# Logs de actualización
tail -f /home/ubuntu/Dashboard_Multipage_MME/logs/update.log

# Logs de cron (actualizaciones automáticas)
tail -f /home/ubuntu/Dashboard_Multipage_MME/logs/cron_update.log

# Logs de la aplicación
tail -f /home/ubuntu/Dashboard_Multipage_MME/logs/app.log
```

### Verificar Estado
```bash
# Estado del repositorio
./auto-update.sh status

# Verificar actualizaciones disponibles
./auto-update.sh check

# Ver configuración de cron
crontab -l | grep auto-update
```

## 🔧 Integración con manage-server.sh

El script de gestión principal incluye opciones para:
- **Opción 8**: Actualización automática segura
- **Opción 9**: Configurar actualizaciones automáticas con cron

## 🚨 Troubleshooting

### Problema: "Hay cambios locales no guardados"
```bash
cd /home/ubuntu/Dashboard_Multipage_MME
git status                    # Ver qué cambió
git add .                     # Agregar cambios
git commit -m "Local changes" # Hacer commit
./auto-update.sh update       # Intentar actualización nuevamente
```

### Problema: Falla la actualización
```bash
./auto-update.sh rollback     # Rollback automático
./manage-server.sh            # Usar menú de gestión
```

### Problema: Aplicación no inicia después de actualización
- El rollback se ejecuta automáticamente
- Si no funciona: `./deploy.sh` para reinicio manual

## 🔔 Notificaciones (Opcional)

### Configurar Webhook
Durante la configuración con `setup-auto-update.sh`, puedes configurar:
- 📱 Slack webhook
- 📱 Discord webhook  
- 📱 Microsoft Teams webhook
- 📱 Cualquier webhook compatible

### Formato de Notificaciones
- ✅ Actualizaciones exitosas
- ❌ Errores en actualizaciones
- 📊 Información de cambios aplicados

## 📈 Mejores Prácticas

### Para el Equipo de Desarrollo
1. **Commits descriptivos**: Usar mensajes claros en commits
2. **Testing local**: Probar cambios antes de push
3. **Requirements.txt**: Actualizar dependencias cuando sea necesario
4. **Comunicación**: Avisar al equipo sobre cambios críticos

### Para el Administrador del VPS
1. **Monitoreo regular**: Revisar logs periódicamente
2. **Backups manuales**: Crear backups antes de cambios importantes
3. **Testing de rollback**: Probar rollback ocasionalmente
4. **Configuración de notificaciones**: Configurar webhooks para alertas

## 🎯 Ventajas del Sistema

- 🔄 **Actualizaciones automáticas** desde GitHub
- 🛡️ **Rollback automático** en caso de errores
- 📦 **Backups automáticos** antes de cada actualización  
- 🔍 **Verificación inteligente** de cambios críticos
- 📝 **Logging completo** de todas las operaciones
- ⚡ **Zero-downtime** para actualizaciones menores
- 👥 **Colaboración segura** con múltiples desarrolladores
- 🚨 **Notificaciones** opcionales de estado

---

**¡Tu dashboard se mantiene siempre actualizado de forma segura y automática!** 🚀
