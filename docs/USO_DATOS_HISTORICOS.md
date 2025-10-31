# Sistema de Datos Históricos - Portal Energético

## 🎯 Problema Resuelto

Cuando la API de XM no está disponible, la aplicación ahora usa **datos históricos del cache** en lugar de valores inventados de fallback.

## ✨ Cómo Funciona

### 1. **Cache Inteligente con Datos Históricos**

El sistema de cache ahora tiene dos modos:

- **Modo Normal**: Usa solo datos que no han expirado
- **Modo Histórico**: Cuando la API falla, usa datos expirados como respaldo

```python
# Permite usar datos expirados si la API no está disponible
data = get_from_cache(cache_key, allow_expired=True)
```

### 2. **Estrategia de Fallback en Cascada**

```
┌─────────────────────────────────────┐
│  1. Intentar API de XM              │
│     └─> Si falla...                 │
│                                     │
│  2. Buscar en cache (no expirado)   │
│     └─> Si no hay...                │
│                                     │
│  3. Buscar datos históricos         │
│     └─> Si no hay...                │
│                                     │
│  4. Usar fallback estático          │
└─────────────────────────────────────┘
```

### 3. **Actualización Automática**

Script para actualizar el cache cuando la API esté disponible:

```bash
# Ejecutar manualmente
python3 /home/admonctrlxm/server/scripts/actualizar_cache_xm.py

# Ver estadísticas
python3 << EOF
from utils.cache_manager import get_cache_stats
stats = get_cache_stats()
print(f"Items en memoria: {stats['memory_items']}")
print(f"Items en disco: {stats['disk_items']}")
print(f"Tamaño: {stats['total_size_mb']:.2f} MB")
EOF
```

## 📊 Ventajas

| Aspecto | Antes | Ahora |
|---------|-------|-------|
| API caída | Datos inventados | **Datos históricos reales** |
| Fecha de datos | Hoy (falso) | **Fecha real del último dato** |
| Confiabilidad | ⚠️ Engañoso | ✅ Transparente |
| Tiempo de carga | Normal | Normal (usa cache) |

## 🔧 Configuración de Cron (Opcional)

Para actualizar datos automáticamente cada hora cuando la API funcione:

```bash
# Editar crontab
crontab -e

# Agregar línea:
0 * * * * /usr/bin/python3 /home/admonctrlxm/server/scripts/actualizar_cache_xm.py >> /var/log/portal_cache_update.log 2>&1
```

Esto intentará actualizar el cache cada hora. Si la API está caída, fallará silenciosamente y los datos históricos seguirán disponibles.

## 📝 Logs Útiles

Ver si está usando datos históricos:

```bash
# Logs en tiempo real
sudo journalctl -u gunicorn -f | grep "históricos"

# Últimos 50 logs
sudo journalctl -u gunicorn -n 50 | grep -E "históricos|Cache HIT|EXPIRED"
```

Mensajes esperados:

- `✅ Cache HIT (memoria)` - Datos frescos en memoria
- `✅ Cache HIT (disco)` - Datos frescos en disco
- `⚠️ Cache EXPIRED pero usando datos históricos` - **Usando datos antiguos por fallo de API**
- `📊 Usando datos históricos para Gene/Recurso` - **Confirmación de datos históricos**

## 🧪 Pruebas

### Test 1: Verificar datos históricos disponibles

```bash
ls -lh /tmp/portal_energetico_cache/
```

Deberías ver archivos `.pkl` con datos guardados.

### Test 2: Forzar uso de datos históricos

```bash
# Eliminar conexión temporal (simular API caída)
# Los datos históricos se usarán automáticamente
curl http://127.0.0.1:8050/generacion

# Ver logs
sudo journalctl -u gunicorn -n 20 | grep históricos
```

### Test 3: Actualizar cache manualmente

```bash
python3 /home/admonctrlxm/server/scripts/actualizar_cache_xm.py
```

Si API XM está caída, verás:
```
❌ API de XM no disponible
ℹ️  La aplicación usará datos históricos del cache
```

Si API XM funciona, verás:
```
✅ Conexión exitosa a API de XM
✅ Hidrología: OK
✅ Generación: OK
```

## 🎯 Resultado Final

### Antes:
```
Reservas Hídricas: 83.29%      ← INVENTADO
Aportes Hídricos: 89.51%       ← INVENTADO  
Generación SIN: 198.45 GWh     ← INVENTADO
```

### Ahora (con datos históricos):
```
Reservas Hídricas: 83.29%      ← DATO REAL del 27 oct
Aportes Hídricos: 220.62 GWh   ← DATO REAL del 27 oct
Generación SIN: 198.45 GWh     ← DATO REAL del 27 oct
```

**Con indicador visual de que son datos históricos:**
```
SIN • 27 de octubre  ← Muestra la fecha real
```

## ⚙️ Archivos Modificados

1. `utils/cache_manager.py` - Agregado parámetro `allow_expired`
2. `utils/_xm.py` - Lógica para usar datos históricos en `fetch_metric_data()`
3. `scripts/actualizar_cache_xm.py` - Script para actualizar cache

## ✅ Estado Actual

- ✅ Sistema de cache con datos históricos implementado
- ✅ Fallback inteligente en cascada
- ✅ Script de actualización automática
- ✅ Logs informativos
- ⏳ Pendiente: Configurar cron para actualización automática (opcional)
