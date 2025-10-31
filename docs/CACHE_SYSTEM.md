# Sistema de Caché - Portal Energético

## 🎯 Objetivo

Optimizar el rendimiento de la aplicación evitando consultas repetidas a la API de XM y reduciendo los tiempos de carga.

## ✨ Características Implementadas

### 1. **Cache Manager** (`utils/cache_manager.py`)

Sistema centralizado de caché con las siguientes capacidades:

- **Cache en memoria**: Para acceso ultra-rápido (microsegundos)
- **Cache en disco**: Para persistencia entre reinicios del servidor (`/tmp/portal_energetico_cache/`)
- **Expiración automática**: Los datos expiran según el tipo:
  - Métricas hídricas (reservas, aportes): 1 hora
  - Datos de generación XM: 1 hora  
  - Generación por plantas: 2 horas
  - Listado de recursos: 12 horas (cambia poco)
  - Precios: 30 minutos

### 2. **Función `fetch_metric_data()`** (`utils/_xm.py`)

Wrapper cacheado para consultas a la API de XM:

```python
from utils._xm import fetch_metric_data
from datetime import date, timedelta

# Esto se cachea automáticamente
df = fetch_metric_data(
    metric='Gene',
    entity='Sistema', 
    start_date=date.today() - timedelta(days=7),
    end_date=date.today()
)
```

**Beneficios:**
- Primera llamada: consulta API (puede tardar)
- Llamadas posteriores: retorna desde caché (instantáneo)
- Si la API falla: usa datos previamente cacheados

### 3. **Datos Hídricas con Cache** (`pages/generacion.py`)

La función `obtener_metricas_hidricas()` ahora:

1. Intenta obtener datos reales de la API (con caché)
2. Si hay datos cacheados, los usa aunque la API falle
3. Si no hay caché ni API, usa datos de fallback

### 4. **Datos XM con Cache** (`pages/generacion_fuentes_unificado.py`)

La función `crear_fichas_generacion_xm_fallback()` ahora:

1. Consulta `Gene/Recurso` con caché automático
2. Calcula porcentajes renovable/no renovable
3. Usa valores reales si están disponibles
4. Fallback a valores estáticos solo si no hay caché

## 🚀 Uso del Sistema de Caché

### Poblar Cache Inicial

Si la API de XM no está disponible, puedes poblar el caché con datos simulados:

```bash
cd /home/admonctrlxm/server
python3 scripts/poblar_cache.py
```

Esto creará datos simulados para:
- Reservas hídricas
- Aportes hídricos  
- Generación total
- Generación por recurso

### Limpiar Cache

Para limpiar todo el caché:

```python
from utils.cache_manager import clear_cache

# Limpiar todo
clear_cache()

# Limpiar solo un tipo específico
clear_cache(cache_type='metricas_hidricas')
```

Desde terminal:

```bash
# Limpiar archivos de caché en disco
rm -rf /tmp/portal_energetico_cache/*

# Reiniciar Gunicorn para limpiar caché en memoria
sudo systemctl restart gunicorn
```

### Ver Estadísticas del Cache

```python
from utils.cache_manager import get_cache_stats

stats = get_cache_stats()
print(f"Items en memoria: {stats['memory_items']}")
print(f"Items en disco: {stats['disk_items']}")
print(f"Tamaño total: {stats['total_size_mb']:.2f} MB")
```

### Limpiar Cache Expirado

```python
from utils.cache_manager import cleanup_old_cache

# Eliminar solo archivos expirados
cleaned = cleanup_old_cache()
print(f"Archivos limpiados: {cleaned}")
```

## 📊 Métricas de Rendimiento

### Sin Cache

- **Primera carga**: 10-30 segundos (esperando API)
- **Timeout**: 504 Gateway Timeout si API > 5s
- **Recargas**: Siempre consulta API (lento)

### Con Cache

- **Primera carga**: 10-30 segundos (poblando caché)
- **Recargas**: < 1 segundo (desde caché)
- **Sin API**: Funciona con datos cacheados
- **Beneficio**: **30x más rápido** en recargas

## 🔧 Configuración

### Tiempos de Expiración

Editar en `utils/cache_manager.py`:

```python
CACHE_EXPIRATION = {
    'metricas_hidricas': timedelta(hours=1),      # Cambiar aquí
    'generacion_xm': timedelta(hours=1),
    'generacion_plantas': timedelta(hours=2),
    'listado_recursos': timedelta(hours=12),
    'precios': timedelta(minutes=30),
    'default': timedelta(hours=1)
}
```

### Ubicación del Cache

Cambiar directorio en `utils/cache_manager.py`:

```python
CACHE_DIR = "/tmp/portal_energetico_cache"  # Cambiar aquí
```

## 🐛 Troubleshooting

### El cache no funciona

1. Verificar permisos del directorio:
```bash
sudo chmod 777 /tmp/portal_energetico_cache/
ls -la /tmp/portal_energetico_cache/
```

2. Ver logs de caché:
```bash
sudo journalctl -u gunicorn -f | grep -i cache
```

3. Verificar que existen archivos `.pkl`:
```bash
ls -lh /tmp/portal_energetico_cache/
```

### Los datos no se actualizan

El caché está funcionando! Los datos se actualizarán cuando expire el caché (según configuración).

Para forzar actualización:
```bash
# Limpiar caché
rm -rf /tmp/portal_energetico_cache/*

# Reiniciar aplicación
sudo systemctl restart gunicorn
```

### API de XM caída

Si la API de XM no responde:

1. Poblar cache con datos simulados:
```bash
python3 scripts/poblar_cache.py
```

2. Reiniciar Gunicorn:
```bash
sudo systemctl restart gunicorn
```

3. Los tableros mostrarán datos simulados en lugar de "fallback"

## 📝 Logs Útiles

Verificar uso de caché:
```bash
# Ver hits/misses
sudo journalctl -u gunicorn -f | grep "Cache HIT\|Cache MISS"

# Ver consultas a API
sudo journalctl -u gunicorn -f | grep "Consultando"

# Ver datos guardados en caché
sudo journalctl -u gunicorn -f | grep "Guardado en cache"
```

## ✅ Ventajas del Sistema

1. **Rendimiento**: 30x más rápido en recargas de página
2. **Resiliencia**: Funciona aunque la API esté caída
3. **Optimización**: Reduce carga en servidor XM
4. **Flexibilidad**: Configurable por tipo de dato
5. **Transparente**: No requiere cambios en código existente

## 🔄 Próximas Mejoras

- [ ] Cache distribuido (Redis) para múltiples workers
- [ ] Precargar cache automáticamente cada hora
- [ ] Dashboard de métricas de cache
- [ ] Compresión de archivos de cache
- [ ] Invalidación selectiva por fecha
