# 🔌 Dashboard MME - Portal Energético Colombia

Dashboard interactivo multi-página para monitoreo del sector energético colombiano.
Integra datos en tiempo real del XM (Operador del Mercado) para visualizar generación,
demanda, transmisión, distribución y restricciones operativas.

---

## 📋 Tabla de Contenido

- [Características](#características)
- [Arquitectura del Sistema](#arquitectura-del-sistema)
- [Sistema Cache-Precalentamiento-Dashboard](#sistema-cache-precalentamiento-dashboard)
- [Instalación](#instalación)
- [Uso](#uso)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Documentación Técnica](#documentación-técnica)

---

## ✨ Características

### Módulos Principales

1. **Generación**
   - Indicadores clave: Reservas, Aportes, Generación total
   - Generación por fuentes (hidráulica, térmica, solar, eólica, biomasa)
   - Hidrología: niveles de embalses, caudales, aportes por río

2. **Demanda**
   - Demanda en tiempo real
   - Históricos y patrones de consumo
   - Pronósticos de demanda

3. **Transmisión**
   - Red de transmisión nacional
   - Congestiones y cuellos de botella
   - Estado de líneas y subestaciones

4. **Distribución**
   - Indicadores de calidad (DES, DEM)
   - Distribución geográfica por OR
   - Transformadores y redes

5. **Restricciones**
   - Restricciones operativas
   - Restricciones ambientales
   - Pérdidas técnicas y comerciales

---

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                      ARQUITECTURA GENERAL                        │
└─────────────────────────────────────────────────────────────────┘

┌───────────────┐      ┌──────────────────┐      ┌──────────────┐
│   XM API      │─────>│ Precalentamiento │─────>│    Cache     │
│  (pydataxm)   │      │   (cron 3x/día)  │      │ Persistente  │
└───────────────┘      └──────────────────┘      └──────────────┘
                                                         │
                                                         │
                                                         v
┌───────────────┐      ┌──────────────────┐      ┌──────────────┐
│   Dashboard   │<─────│  fetch_metric_   │<─────│ get_from_    │
│   (Dash UI)   │      │      data()      │      │   cache()    │
└───────────────┘      └──────────────────┘      └──────────────┘
```

### Componentes

1. **XM API (pydataxm):** Biblioteca Python para acceder a datos del XM
2. **Precalentamiento:** Script que consulta API y guarda en cache (cron)
3. **Cache Persistente:** Almacenamiento en disco (`/var/cache/portal_energetico_cache/`)
4. **Dashboard:** Interfaz Dash que lee del cache
5. **Nginx:** Proxy reverso para producción

---

## 🔄 Sistema Cache-Precalentamiento-Dashboard

### Diseño Fundamental

El sistema sigue el principio **"Precalentamiento hace TODO, Dashboard solo lee"**:

```python
# ✅ CORRECTO: Precalentamiento hace conversiones
# scripts/precalentar_cache_inteligente.py
data = api.request_data('Gene', 'Sistema', fecha_inicio, fecha_fin)
data_gwh = convertir_unidades(data, 'kWh_a_GWh')  # kWh → GWh
save_to_cache(cache_key, data_gwh)

# Dashboard solo lee
# pages/generacion.py
df = fetch_metric_data('Gene', 'Sistema', fecha, fecha)
gen_gwh = df['Value'].sum()  # Ya está en GWh
```

### Unidades de Métricas XM

**CRÍTICO:** Cada métrica viene en unidades DIFERENTES de la API:

| Métrica | Entidad | Unidad API | Conversión | Factor | Unidad Final |
|---------|---------|------------|------------|--------|--------------|
| `VoluUtilDiarEner` | Embalse | **Wh** | Wh → GWh | ÷1e9 | GWh |
| `CapaUtilDiarEner` | Embalse | **Wh** | Wh → GWh | ÷1e9 | GWh |
| `AporEner` | Sistema/Rio | **MWh** | MWh → GWh | ÷1e3 | GWh |
| `AporEnerMediHist` | Sistema/Rio | **MWh** | MWh → GWh | ÷1e3 | GWh |
| `Gene` | Sistema/Recurso | **kWh** | kWh → GWh | ÷1e6 | GWh |
| `DemaReal` | Sistema | **kWh** | kWh → GWh | ÷1e6 | GWh |

**Ver:** `CORRECCION_UNIDADES_CRITICA.md` para detalles completos.

### Flujo de Datos

#### 1. Precalentamiento (Automático 3x/día)

```bash
# Cron schedule: 06:30, 14:30, 20:30
python3 /home/admonctrlxm/server/scripts/precalentar_cache_inteligente.py --sin-timeout
```

**Proceso:**
1. Consultar XM API para métricas configuradas
2. Convertir unidades (Wh→GWh, MWh→GWh, kWh→GWh)
3. Validar datos (rangos, unidades, completitud)
4. Guardar en cache persistente con TTL

**Métricas precalentadas:**
- `VoluUtilDiarEner`, `CapaUtilDiarEner` (7 días)
- `AporEner`, `AporEnerMediHist` (30 días)
- `Gene/Sistema` (7 días)
- `Gene/Recurso` (3 días, batching por peso)

#### 2. Dashboard (Lectura)

```python
from datetime import datetime
from utils._xm import obtener_datos_con_fallback

# Buscar últimos datos disponibles (hasta 7 días atrás)
df_vol, fecha = obtener_datos_con_fallback(
    'VoluUtilDiarEner', 
    'Embalse', 
    datetime.now().date()
)

if df_vol is not None:
    vol_gwh = df_vol['Value'].sum()  # Ya en GWh
    print(f"Volumen: {vol_gwh:.2f} GWh (fecha: {fecha})")
else:
    print("No hay datos disponibles")
```

**Proceso:**
1. Dashboard solicita datos para fecha específica
2. `fetch_metric_data()` busca en cache
3. Si cache existe → retornar datos
4. Si NO existe → buscar hacia atrás (7 días)
5. Si nada → retornar `None` (dashboard muestra mensaje)

### Políticas de Cache

#### Cache Válido (✅ Usar siempre)
- Cache no expirado (dentro de TTL)
- Fechas coinciden exactamente
- Datos en unidades correctas

#### Cache Expirado (⚠️ Usar con precaución)
- Cache expirado pero < 30 días
- Fechas coinciden exactamente
- Logging de advertencia

#### Cache Alternativo (❌ NUNCA usar)
- ~~Cache de fechas diferentes~~
- ~~Cache de métricas mezcladas~~
- ~~Cache > 30 días~~

**Razón:** Causa datos corruptos/incorrectos en dashboard.

### Prevención de Cache Corrupto

**Problema eliminado:**
```python
# ❌ ANTES (INCORRECTO)
any_cache = find_any_cache_for_metric('fetch_metric_data', metric, entity)
return any_cache  # Retorna datos de CUALQUIER fecha

# ✅ AHORA (CORRECTO)
# Si no hay cache para fecha exacta → retornar None
# Dashboard hace búsqueda hacia atrás con obtener_datos_con_fallback()
```

**Ver:** `ANALISIS_SISTEMICO_CACHE.md` para análisis completo.

---

## 🚀 Instalación

### Requisitos

- Python 3.8+
- Ubuntu 20.04+ (producción)
- Nginx (proxy reverso)
- 4GB RAM mínimo
- 10GB espacio disco

### Dependencias Python

```bash
pip install -r requirements.txt
```

**Principales:**
- `dash` - Framework web
- `pandas` - Manipulación de datos
- `plotly` - Visualizaciones interactivas
- `pydataxm` - API cliente XM
- `gunicorn` - WSGI server

### Configuración

1. **Clonar repositorio:**
```bash
git clone https://github.com/MelissaCardona2003/Dashboard_Multipage_MME.git
cd Dashboard_Multipage_MME
```

2. **Instalar dependencias:**
```bash
pip install -r requirements.txt
```

3. **Configurar cache:**
```bash
sudo mkdir -p /var/cache/portal_energetico_cache
sudo mkdir -p /var/cache/portal_energetico_metadata
sudo chown -R $USER:$USER /var/cache/portal_energetico_*
```

4. **Configurar cron (precalentamiento):**
```bash
crontab -e
# Agregar:
30 6,14,20 * * * /usr/bin/python3 /home/admonctrlxm/server/scripts/precalentar_cache_inteligente.py --sin-timeout >> /var/log/dashboard_mme_cache.log 2>&1
```

5. **Configurar systemd service:**
```bash
sudo cp dashboard-mme.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable dashboard-mme
sudo systemctl start dashboard-mme
```

6. **Configurar Nginx:**
```bash
sudo cp nginx-dashboard.conf /etc/nginx/sites-available/dashboard-mme
sudo ln -s /etc/nginx/sites-available/dashboard-mme /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 💻 Uso

### Desarrollo

```bash
python app.py
# Dashboard en http://localhost:8050
```

### Producción

```bash
# Via systemd
sudo systemctl start dashboard-mme
sudo systemctl status dashboard-mme

# Via gunicorn manual
gunicorn -c gunicorn_config.py app:server
```

### Precalentamiento Manual

```bash
# Poblar cache completo
python3 scripts/precalentar_cache_inteligente.py --sin-timeout

# Ver logs
tail -f /var/log/dashboard_mme_cache.log
```

### Logs

```bash
# Dashboard logs
sudo journalctl -u dashboard-mme -f

# Cache logs
tail -f /var/log/dashboard_mme_cache.log

# Nginx logs
sudo tail -f /var/log/nginx/dashboard_access.log
sudo tail -f /var/log/nginx/dashboard_error.log
```

---

## 📁 Estructura del Proyecto

```
/home/admonctrlxm/server/
├── app.py                          # Aplicación principal Dash
├── gunicorn_config.py              # Configuración WSGI
├── requirements.txt                # Dependencias Python
├── dashboard-mme.service           # Systemd service
├── nginx-dashboard.conf            # Configuración Nginx
│
├── pages/                          # Páginas del dashboard
│   ├── generacion.py               # Página generación
│   ├── generacion_fuentes_unificado.py
│   ├── generacion_hidraulica_hidrologia.py
│   ├── demanda.py
│   ├── distribucion.py
│   ├── transmision.py
│   └── ...
│
├── componentes/                    # Componentes reutilizables
│   ├── navbar.py                   # Barra de navegación
│   ├── cards.py                    # Cards estadísticas
│   └── ...
│
├── assets/                         # CSS, JS, imágenes
│   ├── styles.css
│   ├── generacion-page.css
│   └── images/
│
├── utils/                          # Utilidades
│   ├── _xm.py                      # Wrapper API XM + cache
│   ├── cache_manager.py            # Gestión de cache
│   └── ...
│
├── scripts/                        # Scripts auxiliares
│   ├── precalentar_cache_inteligente.py  # Precalentamiento
│   └── ...
│
├── logs/                           # Logs aplicación
│   └── dashboard.pid
│
└── notebooks/                      # Jupyter notebooks (desarrollo)
    └── README.md
```

---

## 📚 Documentación Técnica

### Documentos Clave

1. **`CORRECCION_UNIDADES_CRITICA.md`**
   - Conversiones de unidades XM API
   - Investigación de unidades reales
   - Correcciones implementadas

2. **`ANALISIS_SISTEMICO_CACHE.md`**
   - Arquitectura completa del sistema cache
   - Problema de cache corrupto
   - Soluciones implementadas

3. **`ESTADO_FINAL_PROYECTO.md`**
   - Estado general del proyecto
   - Optimizaciones aplicadas
   - Roadmap futuro

4. **`OPTIMIZACION_CRITICA_HASH.md`**
   - Optimizaciones de performance
   - Sistema de hash de cache
   - Benchmarks

### APIs y Librerías

- **pydataxm:** https://github.com/BrandonJG/pydataxm
- **Dash:** https://dash.plotly.com/
- **Plotly:** https://plotly.com/python/

### Contacto

- **Repositorio:** https://github.com/MelissaCardona2003/Dashboard_Multipage_MME
- **Issues:** https://github.com/MelissaCardona2003/Dashboard_Multipage_MME/issues

---

*Última actualización: 2025-11-17*
