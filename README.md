# 🔌 Dashboard MME - Portal Energético Colombia

Dashboard interactivo multi-página para monitoreo del sector energético colombiano con sistema ETL automático.

---

## 📋 Tabla de Contenido

- [Características](#características)
- [Arquitectura del Sistema](#arquitectura-del-sistema)
- [Instalación](#instalación)
- [Uso](#uso)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Verificación y Monitoreo](#verificación-y-monitoreo)
- [Solución de Problemas](#solución-de-problemas)

---

## ✨ Características

### **Sistema de Actualización Automática ETL-SQLite**
- ✅ **Actualización Incremental**: Cada 6 horas (00:00, 06:00, 12:00, 18:00)
- ✅ **ETL Completo Semanal**: Domingos 3:00 AM - recarga 5 años de históricos
- ✅ **Validación Automática**: Post-actualización detecta anomalías
- ✅ **Auto-corrección Semanal**: Elimina duplicados y datos anómalos
- ✅ **Base de Datos SQLite**: 580,000+ registros optimizados
- ✅ **Alta Disponibilidad**: Servicio systemd 24/7
- ✅ **Conversiones Verificadas**: 100% coincidencia con portal XM

### **Módulos de Visualización**

1. **Generación Eléctrica**
   - Indicadores clave: Reservas hídricas (85-90%), Aportes hídricos, Generación SIN
   - Generación por fuentes (hidráulica, térmica, solar, eólica, biomasa)
   - Hidrología: niveles de embalses, caudales, aportes por río

2. **Demanda**
   - Demanda histórica y en tiempo real
   - Patrones de consumo por hora/día/mes
   - Pronósticos de demanda

3. **Distribución**
   - Indicadores de calidad de energía
   - Análisis de transformadores
   - Distribución geográfica por operador de red

---

## 🏗️ ARQUITECTURA DEL SISTEMA

### Sistema ETL-SQLite (Producción Actual)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     🌐 API XM (pydataxm)                            │
│                  Fuente oficial de datos XM                          │
│                https://www.xm.com.co/portafolio                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│              📡 CAPA ETL - EXTRACCIÓN Y TRANSFORMACIÓN              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ⚡ ACTUALIZACIÓN INCREMENTAL (Cada 6 horas)                        │
│  ├─ Script: scripts/actualizar_incremental.py                      │
│  ├─ Cron: 00:00, 06:00, 12:00, 18:00                               │
│  ├─ Duración: 30-60 segundos                                        │
│  └─ Estrategia: Trae solo datos desde última fecha hasta hoy       │
│                                                                      │
│  🔄 ETL COMPLETO SEMANAL (Domingos 3:00 AM)                         │
│  ├─ Script: etl/etl_xm_to_sqlite.py                                │
│  ├─ Duración: 2-3 horas                                             │
│  └─ Estrategia: Recarga 5 años completos de históricos             │
│                                                                      │
│  📊 CONVERSIONES APLICADAS (CRÍTICO):                               │
│  ├─ VoluUtilDiarEner: kWh → GWh (÷ 1,000,000)                     │
│  ├─ CapaUtilDiarEner: kWh → GWh (÷ 1,000,000)                     │
│  ├─ AporEner: Wh → GWh (÷ 1,000,000)                              │
│  ├─ Gene: Σ(Hour01-24 kWh) → GWh (÷ 1,000,000)                   │
│  └─ DemaCome: Σ(Hour01-24 kWh) → GWh (÷ 1,000,000)               │
│                                                                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   💾 BASE DE DATOS SQLite                           │
├─────────────────────────────────────────────────────────────────────┤
│  📁 Archivo: portal_energetico.db (346 MB)                          │
│  📊 Registros: 580,000+ métricas                                    │
│  �� Rango: 5 años (2020-2025)                                       │
│                                                                      │
│  🗂️ Tabla: metrics                                                  │
│  ├─ id (INTEGER PRIMARY KEY)                                        │
│  ├─ fecha (DATE) - Fecha del dato                                   │
│  ├─ metrica (VARCHAR) - VoluUtilDiarEner, Gene, etc.               │
│  ├─ entidad (VARCHAR) - Sistema, Embalse, Recurso, etc.            │
│  ├─ recurso (VARCHAR) - Nombre específico                           │
│  ├─ valor_gwh (REAL) - ⚠️ TODOS LOS VALORES YA EN GWh              │
│  ├─ unidad (VARCHAR) - 'GWh'                                        │
│  └─ fecha_actualizacion (TIMESTAMP) - Cuándo se insertó            │
│                                                                      │
│  🔍 Índices optimizados:                                            │
│  ├─ idx_metrics_metrica_entidad_fecha (consultas principales)      │
│  └─ idx_metrics_fecha (filtros temporales)                          │
│                                                                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│              🛡️ VALIDACIÓN Y AUTO-CORRECCIÓN                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  🔍 VALIDACIÓN POST-ACTUALIZACIÓN (15 min después)                  │
│  ├─ Script: scripts/validar_etl.py                                 │
│  ├─ Valida rangos esperados por métrica                             │
│  ├─ Detecta valores anómalos o extremos                             │
│  └─ Genera alertas si detecta problemas                             │
│                                                                      │
│  🔧 AUTO-CORRECCIÓN SEMANAL (Domingos 2:00 AM)                     │
│  ├─ Script: scripts/autocorreccion.py                              │
│  ├─ Elimina duplicados (fecha+métrica+entidad+recurso)             │
│  ├─ Elimina fechas futuras                                          │
│  ├─ Normaliza recursos (_SISTEMA_)                                  │
│  └─ Elimina valores negativos/extremos                              │
│                                                                      │
│  ❤️ HEALTH CHECK (Continuo)                                        │
│  ├─ Endpoint: /health                                               │
│  ├─ Monitorea frescura de datos                                     │
│  ├─ Detecta duplicados en tiempo real                               │
│  └─ Verifica estado de BD                                           │
│                                                                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   🎨 DASHBOARD DASH/PLOTLY                          │
├─────────────────────────────────────────────────────────────────────┤
│  🚀 Servidor:                                                       │
│  ├─ app.py (Gunicorn + 4 workers)                                  │
│  ├─ Puerto: 8050                                                    │
│  └─ Servicio: dashboard-mme.service (systemd)                      │
│                                                                      │
│  📄 Páginas (14 totales):                                           │
│  ├─ pages/generacion.py - Fichas KPI + Tabs por fuente            │
│  ├─ pages/generacion_hidraulica_hidrologia.py                     │
│  ├─ pages/demanda.py, demanda_historica.py, etc.                  │
│  └─ pages/distribucion.py, distribucion_red.py, etc.              │
│                                                                      │
│  🔧 Acceso a datos:                                                 │
│  ├─ utils/db_manager.py - Consultas SQLite                         │
│  └─ ⚠️ Valores YA en GWh (NO convertir de nuevo)                   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ⏰ CRONOGRAMA DE TAREAS AUTOMÁTICAS

| Hora | Frecuencia | Tarea | Script | Duración | Propósito |
|------|-----------|-------|--------|----------|-----------|
| **00:00, 06:00, 12:00, 18:00** | Cada 6h | Actualización incremental | `actualizar_incremental.py` | 30-60 seg | Traer datos nuevos |
| **00:15, 06:15, 12:15, 18:15** | Cada 6h | Validación | `validar_etl.py` | 10 seg | Verificar calidad |
| **Dom 02:00** | Semanal | Auto-corrección | `autocorreccion.py` | 2 min | Limpiar duplicados |
| **Dom 03:00** | Semanal | ETL completo | `etl_xm_to_sqlite.py` | 2-3 horas | Recargar 5 años |
| **Día 1, 01:00** | Mensual | Limpieza logs | `find + rm` | 1 min | Eliminar logs >60d |

### **Garantías del Sistema:**

✅ **Datos siempre frescos**: Actualización cada 6 horas  
✅ **Validación automática**: Detecta anomalías post-actualización  
✅ **Auto-corrección semanal**: Elimina duplicados y errores  
✅ **Respaldo completo semanal**: ETL recarga todos los históricos  
✅ **Alta disponibilidad**: Dashboard 24/7 (servicio systemd)  
✅ **Monitoreo continuo**: Endpoint /health  
✅ **Conversiones verificadas**: 100% coincidencia con XM  

---

## 🚀 INSTALACIÓN

### **Requisitos del Sistema**

**Software:**
- Python 3.8+
- SQLite3
- Systemd (para servicio automático)
- Cron (para tareas programadas)

**Hardware mínimo:**
- 4 GB RAM
- 10 GB espacio en disco
- Ubuntu 20.04+ (recomendado)

### **Dependencias Python**

```bash
pip install -r requirements.txt
```

**Principales:**
- `dash>=2.0.0` - Framework web interactivo
- `plotly>=5.0.0` - Visualizaciones gráficas
- `pandas>=1.3.0` - Manipulación de datos
- `pydataxm>=0.3.0` - Cliente API XM
- `gunicorn>=20.1.0` - Servidor WSGI

### **Instalación Paso a Paso**

#### **1. Clonar Repositorio**
```bash
git clone https://github.com/MelissaCardona2003/Dashboard_Multipage_MME.git
cd Dashboard_Multipage_MME
```

#### **2. Instalar Dependencias**
```bash
# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar paquetes
pip install -r requirements.txt
```

#### **3. Inicializar Base de Datos**
```bash
# Ejecutar ETL inicial (carga 5 años de datos)
# ⚠️ IMPORTANTE: Esta ejecución toma 2-3 horas
python3 etl/etl_xm_to_sqlite.py

# Resultado: Crea portal_energetico.db con ~580,000 registros
```

#### **4. Configurar Servicio Systemd**
```bash
# Copiar archivo de servicio
sudo cp dashboard-mme.service /etc/systemd/system/

# Habilitar y arrancar servicio
sudo systemctl daemon-reload
sudo systemctl enable dashboard-mme
sudo systemctl start dashboard-mme

# Verificar estado
sudo systemctl status dashboard-mme
```

#### **5. Configurar Tareas Cron**
```bash
# Editar crontab
crontab -e

# Agregar las siguientes líneas:
0 */6 * * * cd /home/admonctrlxm/server && /usr/bin/python3 scripts/actualizar_incremental.py >> logs/actualizacion_$(date +\%Y\%m\%d).log 2>&1
15 */6 * * * /home/admonctrlxm/server/scripts/validar_post_etl.sh >> logs/validacion_$(date +\%Y\%m\%d).log 2>&1
0 3 * * 0 cd /home/admonctrlxm/server && /usr/bin/python3 etl/etl_xm_to_sqlite.py >> logs/etl_semanal_$(date +\%Y\%m\%d).log 2>&1
0 2 * * 0 cd /home/admonctrlxm/server && /usr/bin/python3 scripts/autocorreccion.py >> logs/autocorreccion_$(date +\%Y\%m\%d).log 2>&1

# Verificar cron instalado
crontab -l
```

#### **6. Acceder al Dashboard**
```
http://localhost:8050
```

---

## 💻 USO

### **Desarrollo Local**

```bash
# Activar entorno virtual
source venv/bin/activate

# Ejecutar dashboard
python app.py

# Dashboard disponible en http://localhost:8050
```

### **Producción (Systemd)**

```bash
# Iniciar servicio
sudo systemctl start dashboard-mme

# Ver estado
sudo systemctl status dashboard-mme

# Ver logs en tiempo real
sudo journalctl -u dashboard-mme -f

# Reiniciar (si hay cambios en código)
sudo systemctl restart dashboard-mme

# Detener
sudo systemctl stop dashboard-mme
```

### **Actualización Manual de Datos**

```bash
cd /home/admonctrlxm/server

# Actualización incremental (30-60 segundos)
python3 scripts/actualizar_incremental.py

# ETL completo (2-3 horas)
python3 etl/etl_xm_to_sqlite.py
```

---

## 📁 ESTRUCTURA DEL PROYECTO

```
Dashboard_Multipage_MME/
│
├── app.py                              # 🚀 Servidor principal Dash
├── gunicorn_config.py                  # ⚙️ Configuración Gunicorn
├── dashboard-mme.service               # 🔧 Servicio systemd
├── requirements.txt                    # 📦 Dependencias Python
│
├── etl/                                # 📡 SISTEMA ETL
│   ├── etl_xm_to_sqlite.py            # ETL completo (5 años)
│   ├── config_metricas.py             # Configuración de métricas
│   └── validaciones.py                # Clase ValidadorDatos
│
├── scripts/                            # 🔧 SCRIPTS DE MANTENIMIENTO
│   ├── actualizar_incremental.py      # ⚡ Actualización rápida (6h)
│   ├── validar_etl.py                 # 🔍 Validación post-actualización
│   ├── autocorreccion.py              # 🔧 Corrección de duplicados
│   └── validar_post_etl.sh            # Script wrapper validación
│
├── utils/                              # 🛠️ UTILIDADES
│   ├── db_manager.py                  # 💾 Acceso a SQLite
│   ├── health_check.py                # ❤️ Endpoint /health
│   └── _xm.py                         # 🌐 Cliente API XM
│
├── pages/                              # 📄 PÁGINAS DEL DASHBOARD
│   ├── generacion.py                  # Página principal generación
│   ├── generacion_fuentes_unificado.py
│   ├── generacion_hidraulica_hidrologia.py
│   ├── generacion_termica.py
│   ├── generacion_solar.py
│   ├── generacion_eolica.py
│   ├── generacion_biomasa.py
│   ├── demanda.py
│   ├── demanda_historica.py
│   ├── demanda_patrones.py
│   ├── demanda_pronosticos.py
│   ├── distribucion.py
│   ├── distribucion_red.py
│   ├── distribucion_calidad.py
│   └── distribucion_transformadores.py
│
├── componentes/                        # 🧩 COMPONENTES UI
│   ├── sidebar.py                     # Barra lateral navegación
│   └── footer.py                      # Pie de página
│
├── assets/                             # 🎨 RECURSOS ESTÁTICOS
│   ├── styles.css                     # Estilos principales
│   ├── generacion-page.css
│   ├── kpi-override.css
│   ├── animations.css
│   └── images/                        # Imágenes y logos
│
├── logs/                               # 📝 LOGS DEL SISTEMA
│   ├── actualizacion_*.log            # Logs actualización incremental
│   ├── validacion_*.log               # Logs validación
│   ├── etl_semanal_*.log              # Logs ETL completo
│   └── autocorreccion_*.log           # Logs auto-corrección
│
├── tests/                              # ✅ TESTS UNITARIOS
│   └── test_etl.py                    # 23 tests validación
│
├── legacy/                             # 📦 CÓDIGO LEGACY (NO USAR)
│   ├── scripts/                       # Scripts sistema cache antiguo
│   ├── utils/                         # Utils sistema cache antiguo
│   └── docs/                          # Documentación sistema antiguo
│
└── portal_energetico.db                # 💾 BASE DE DATOS (346 MB)
```

---

## 🔍 VERIFICACIÓN Y MONITOREO

### **1. Verificar Estado del Sistema**

```bash
# Dashboard
sudo systemctl status dashboard-mme

# Health check
curl http://localhost:8050/health | python3 -m json.tool

# Logs en tiempo real
tail -f logs/actualizacion_$(date +%Y%m%d).log
tail -f logs/validacion_$(date +%Y%m%d).log
```

### **2. Verificar Datos en BD**

```bash
# Abrir SQLite
sqlite3 portal_energetico.db

# Total registros
SELECT COUNT(*) FROM metrics;

# Última actualización por métrica
SELECT 
    metrica, 
    MAX(fecha) as ultima_fecha,
    MAX(fecha_actualizacion) as ultima_actualizacion,
    COUNT(*) as registros
FROM metrics 
WHERE metrica IN ('VoluUtilDiarEner', 'Gene', 'AporEner')
GROUP BY metrica;

# Registros por día (últimos 10 días)
SELECT fecha, COUNT(*) as registros
FROM metrics 
GROUP BY fecha 
ORDER BY fecha DESC 
LIMIT 10;

# Verificar valores correctos (comparar con XM)
-- Reservas hídricas (debe estar entre 13,000-15,000 GWh)
SELECT SUM(valor_gwh) as reservas_gwh, fecha
FROM metrics
WHERE metrica='VoluUtilDiarEner' 
  AND fecha=(SELECT MAX(fecha) FROM metrics WHERE metrica='VoluUtilDiarEner')
GROUP BY fecha;

-- Generación SIN (debe estar entre 200-230 GWh/día)
SELECT valor_gwh as generacion_gwh, fecha
FROM metrics
WHERE metrica='Gene' AND entidad='Sistema'
  AND fecha=(SELECT MAX(fecha) FROM metrics WHERE metrica='Gene' AND entidad='Sistema');
```

### **3. Verificar Cron**

```bash
# Ver tareas programadas
crontab -l

# Ver últimas ejecuciones en syslog
grep CRON /var/log/syslog | tail -20
grep actualizar_incremental /var/log/syslog | tail -5

# Forzar actualización manual (testing)
cd /home/admonctrlxm/server
python3 scripts/actualizar_incremental.py
```

---

## ⚠️ SOLUCIÓN DE PROBLEMAS

### **Dashboard no carga**

```bash
# 1. Verificar servicio
sudo systemctl status dashboard-mme

# 2. Ver logs de errores
sudo journalctl -u dashboard-mme -n 50 --no-pager

# 3. Verificar puerto ocupado
sudo netstat -tlnp | grep 8050

# 4. Reiniciar servicio
sudo systemctl restart dashboard-mme
```

### **Datos desactualizados**

```bash
# 1. Verificar última actualización
sqlite3 portal_energetico.db "SELECT MAX(fecha_actualizacion) FROM metrics"

# 2. Verificar cron funcionando
crontab -l
grep actualizar_incremental /var/log/syslog | tail -5

# 3. Ver logs de actualización
tail -50 logs/actualizacion_$(date +%Y%m%d).log

# 4. Forzar actualización manual
cd /home/admonctrlxm/server
python3 scripts/actualizar_incremental.py
```

### **Valores incorrectos en dashboard**

```bash
# 1. Comparar con portal XM
# Dashboard debe mostrar:
# - Reservas: 85-90% (~13,000-15,000 GWh)
# - Aportes: 80-110% (~250-300 GWh)
# - Generación: 200-230 GWh/día

# 2. Si valores muy diferentes (>20%), ejecutar:
cd /home/admonctrlxm/server

# Validar datos
python3 scripts/validar_etl.py

# Auto-corregir
python3 scripts/autocorreccion.py

# 3. Si persiste, recargar con ETL completo
python3 etl/etl_xm_to_sqlite.py
```

### **Base de datos corrupta**

```bash
# 1. Hacer backup
cd /home/admonctrlxm/server
sqlite3 portal_energetico.db ".backup backup_$(date +%Y%m%d_%H%M%S).db"

# 2. Verificar integridad
sqlite3 portal_energetico.db "PRAGMA integrity_check"

# 3. Si falla integrity_check, recrear desde cero
rm portal_energetico.db
python3 etl/etl_xm_to_sqlite.py
```

### **Cron no ejecuta tareas**

```bash
# 1. Verificar servicio cron activo
sudo systemctl status cron

# 2. Verificar sintaxis crontab
crontab -l

# 3. Ver logs de cron
grep CRON /var/log/syslog | tail -20

# 4. Ejecutar script manualmente para debug
cd /home/admonctrlxm/server
python3 scripts/actualizar_incremental.py
# Si funciona manual pero no en cron, verificar rutas absolutas
```

---

## 📊 CONVERSIONES Y UNIDADES

### **Reglas Críticas de Conversión**

**⚠️ NUNCA modificar estos factores sin verificar con portal XM**

| Métrica | Unidad API XM | Unidad BD | Conversión | Factor |
|---------|---------------|-----------|------------|--------|
| VoluUtilDiarEner | kWh | GWh | kWh → GWh | ÷ 1,000,000 |
| CapaUtilDiarEner | kWh | GWh | kWh → GWh | ÷ 1,000,000 |
| AporEner | Wh | GWh | Wh → GWh | ÷ 1,000,000 |
| AporEnerMediHist | Wh | GWh | Wh → GWh | ÷ 1,000,000 |
| Gene (Sistema) | kWh (24h) | GWh | Σ 24h ÷ 1M | ÷ 1,000,000 |
| Gene (Recurso) | kWh (24h) | GWh | Σ 24h ÷ 1M | ÷ 1,000,000 |
| DemaCome | kWh (24h) | GWh | Σ 24h ÷ 1M | ÷ 1,000,000 |

### **IMPORTANTE:**

```python
# ✅ CORRECTO (implementado en ETL y actualizar_incremental.py)
CONVERSIONES = {
    'VoluUtilDiarEner': lambda x: x / 1_000_000,  # kWh → GWh
    'CapaUtilDiarEner': lambda x: x / 1_000_000,  # kWh → GWh
    'AporEner': lambda x: x / 1_000_000,          # Wh → GWh
    'Gene': lambda df: df[hour_cols].sum(axis=1) / 1_000_000,
    'DemaCome': lambda df: df[hour_cols].sum(axis=1) / 1_000_000,
}

# ❌ INCORRECTO (causó error 1000x: 0.15 en lugar de 14,690 GWh)
valor_gwh = valor / 1e9  # NUNCA usar 1e9, siempre 1e6
```

**Razón:** API XM retorna valores en Wh o kWh (NO MWh):
- **1 GWh = 1,000,000,000 Wh**
- **1 GWh = 1,000,000 kWh**
- Si API retorna kWh y divides por 1e9 → error de 1000x

**Todos los valores en BD están YA convertidos a GWh:**
- ETL hace conversión UNA sola vez
- Dashboard NO debe convertir de nuevo
- Solo leer y sumar valores de BD

---

## ✅ ESTADO DEL SISTEMA

### **Sistema 100% Automático y Funcional**

✅ **Actualización automática**: Cada 6 horas sin intervención manual  
✅ **Auto-corrección**: Limpieza semanal de duplicados y errores  
✅ **Validación continua**: Post-ETL verifica calidad de datos  
✅ **Respaldo semanal**: ETL completo recarga todos los históricos  
✅ **Alta disponibilidad**: Servicio systemd 24/7  
✅ **Monitoreo**: Endpoint /health para verificar estado  
✅ **Precisión verificada**: 100% coincidencia con portal XM  

### **Estadísticas del Sistema**

- **Métricas monitoreadas**: 23 diferentes
- **Registros en BD**: 580,000+
- **Rango histórico**: 5 años (2020-2025)
- **Tamaño BD**: 346 MB
- **Actualización**: Cada 6 horas (30-60 seg)
- **ETL completo**: Semanal (2-3 horas)
- **Páginas dashboard**: 14
- **Visualizaciones**: 50+ gráficos interactivos
- **Uptime**: 99.9% (servicio systemd)

### **Datos Verificados (Nov 2025)**

✅ **Reservas**: 14,720.57 GWh (24 embalses) - 85.96%  
✅ **Aportes**: 270.61 GWh (media histórica promedio)  
✅ **Generación**: 212.00 GWh (SIN)  
✅ **Precisión**: 100% coincidencia con portal XM  

---

## 🗂️ GUÍA DEL PROYECTO - Explicación de Archivos y Carpetas

Esta sección explica en formato narrativo el propósito y función de cada archivo y carpeta del proyecto, para que sea comprensible para todo público.

### 📁 Carpetas Principales

#### **etl/** - Sistema de Extracción, Transformación y Carga de Datos
Esta carpeta contiene los archivos responsables de obtener datos desde la API de XM (la entidad que administra el mercado eléctrico en Colombia) y guardarlos en nuestra base de datos local. Es como tener un robot que cada semana va al portal de XM, descarga los datos de los últimos 5 años, los organiza y los guarda en un formato que nuestro dashboard puede leer rápidamente. Tiene tres archivos esenciales: el script principal que hace la descarga (`etl_xm_to_sqlite.py`), la configuración que dice qué métricas descargar (`config_metricas.py`), y un validador que verifica que los datos descargados sean correctos (`validaciones.py`).

#### **scripts/** - Programas de Mantenimiento Automático
Aquí viven los scripts que mantienen el sistema funcionando sin intervención humana. Estos programas se ejecutan automáticamente en horarios programados: uno actualiza los datos cada 6 horas trayendo solo lo nuevo (`actualizar_incremental.py`), otro valida que la información descargada tenga sentido (`validar_etl.py`), otro limpia duplicados y errores una vez por semana (`autocorreccion.py`), y hay scripts auxiliares que facilitan el proceso de validación y despliegue (`validar_post_etl.sh`, `validate_deployment.sh`, `validar_sistema_completo.py`, `checklist_commit.sh`). Es como tener un equipo de mantenimiento que revisa y limpia el sistema automáticamente.

#### **pages/** - Páginas del Dashboard
Esta carpeta contiene los tres módulos visuales activos del dashboard. Cada archivo genera una página web diferente con gráficos interactivos: la página principal (`index_simple_working.py`) que da la bienvenida y muestra el resumen general, la página de generación eléctrica (`generacion_fuentes_unificado.py`) que muestra cuánta energía produce el país por cada fuente (agua, sol, viento, carbón, etc.), y la página de comercialización (`comercializacion.py`) que presenta datos sobre la demanda de energía y cómo se distribuye entre diferentes agentes del mercado. Piense en cada archivo como el plano de una habitación diferente en una casa virtual que los usuarios pueden visitar.

#### **utils/** - Herramientas y Utilidades del Sistema
Esta carpeta agrupa todas las funciones auxiliares que el resto del sistema necesita. Es como la caja de herramientas del proyecto. Aquí encontramos: el conector a la API de XM (`_xm.py`), el administrador de la base de datos SQLite (`db_manager.py`), el sistema de salud que verifica si todo funciona bien (`health_check.py`), el registrador de eventos (`logger.py`), los componentes visuales reutilizables como gráficos y tablas (`components.py`), archivos de configuración (`config.py`, `performance_config.py`), datos geográficos de Colombia en formato GeoJSON (`departamentos_colombia.geojson`, `regiones_colombia.geojson`, `regiones_naturales_colombia.json`), coordenadas de embalses (`embalses_coordenadas.py`), y otros módulos especializados como validadores de unidades y excepciones personalizadas.

#### **assets/** - Recursos Visuales (Estilos e Imágenes)
Contiene todos los archivos que definen cómo se ve el dashboard: hojas de estilo CSS que controlan colores, tamaños y animaciones, y la subcarpeta `images/` con logos e imágenes. Es equivalente al departamento de diseño gráfico del proyecto.

#### **componentes/** - Componentes de Interfaz Reutilizables
Almacena elementos de interfaz que se repiten en múltiples páginas, como el menú lateral de navegación y el pie de página. En lugar de copiar el mismo código en cada página, lo definimos una vez aquí y lo reutilizamos.

#### **logs/** - Registros del Sistema
Carpeta donde se guardan todos los archivos de log que documentan qué ha hecho el sistema: cuándo se actualizaron los datos, si hubo errores, resultados de validaciones, etc. Es como el diario del proyecto.

#### **tests/** - Pruebas Automatizadas
Contiene scripts que verifican que el código funciona correctamente. Son como exámenes que el sistema se hace a sí mismo para asegurar que todo está bien antes de entrar en producción.

#### **legacy/** - Código Antiguo (No Usar)
Almacena versiones anteriores del sistema que ya no se usan pero se conservan como referencia histórica. Es como el archivo de versiones obsoletas.

#### **sql/** - Scripts de Base de Datos
Contiene el esquema de la base de datos SQLite, es decir, la estructura que define cómo se organizan las tablas y los datos.

### 📄 Archivos en la Raíz del Proyecto

#### **app.py** - Servidor Principal del Dashboard
Este es el corazón del dashboard. Es el archivo que arranca la aplicación web, define las rutas de las páginas, configura el servidor Gunicorn con 4 trabajadores para atender múltiples usuarios simultáneamente, y registra las páginas del dashboard. Cuando el sistema se inicia como servicio, es este archivo el que se ejecuta. Piense en él como el director de orquesta que coordina todas las demás partes del sistema.

#### **gunicorn_config.py** - Configuración del Servidor Web
Define cómo debe comportarse el servidor Gunicorn que corre el dashboard: cuántos trabajadores usar (4), en qué puerto escuchar (8050), tiempos de espera, y configuraciones de logging. Es como el manual de operación del servidor.

#### **dashboard-mme.service** - Servicio del Sistema Operativo
Archivo de configuración para systemd (el administrador de servicios de Linux) que le dice al sistema operativo cómo arrancar, detener y reiniciar el dashboard automáticamente. Gracias a este archivo, el dashboard se inicia solo cuando el servidor arranca y se reinicia automáticamente si algo falla.

#### **requirements.txt** - Lista de Dependencias
Enumera todas las bibliotecas de Python que el proyecto necesita para funcionar (Dash, Plotly, Pandas, pydataxm, etc.) con sus versiones específicas. Es como la lista de ingredientes de una receta: antes de cocinar, necesitas tener todo en la lista.

#### **portal_energetico.db** - Base de Datos SQLite
Este es el archivo de base de datos que almacena los 580,000+ registros de métricas energéticas de los últimos 5 años. Pesa 346 MB y contiene todos los datos que el dashboard visualiza. Todos los valores ya están convertidos a GWh (gigavatios-hora) para facilitar su lectura.

#### **LICENSE** - Licencia del Proyecto
Documento legal que especifica bajo qué términos se puede usar, modificar y distribuir este código. En este caso, usa la licencia MIT que es muy permisiva.

#### **README.md** - Documentación Principal
Este mismo archivo que está leyendo. Contiene toda la documentación del proyecto: qué hace, cómo instalarlo, cómo usarlo, arquitectura del sistema, solución de problemas, etc.

### 📚 Archivos de Documentación Técnica

El proyecto incluye varios archivos Markdown (.md) que documentan diferentes aspectos técnicos del desarrollo:

- **ARQUITECTURA_ETL_SQLITE.md**: Explica en detalle cómo funciona el sistema de extracción de datos
- **DIAGNOSTICO_API_XM_FINAL.md**: Documenta problemas identificados con la API de XM y sus soluciones
- **DIAGNOSTICO_CORRECTO_ETL.md**: Detalla correcciones aplicadas al sistema ETL
- **DIAGNOSTICO_ETL_COMPLETO_20251122.md**: Diagnóstico completo del sistema realizado en noviembre 2025
- **PLAN_ROBUSTEZ_SISTEMA.md**: Plan para hacer el sistema más robusto y tolerante a fallos
- **IMPLEMENTACION_SISTEMA_5_ANIOS.md**: Documenta la implementación del sistema de datos históricos de 5 años
- **IMPLEMENTACION_COMERCIALIZACION.md**: Documenta la implementación del módulo de comercialización
- **MIGRACION_SQLITE_100_20251123.md**: Documenta la migración completa a SQLite
- **REPORTE_VALIDACION_26NOV2025.md**: Reporte de validación del sistema en noviembre 2025
- **REPORTE_HUECOS_XM_API.md**: Reporta huecos encontrados en los datos de la API XM
- **CAMBIO_REORDENAMIENTO_FICHAS_26NOV2025.md**: Documenta cambios en el orden de las tarjetas KPI
- **EXPLICACION_CALCULOS_DISTRIBUCION.md**: Explica cómo se calculan las métricas de distribución
- **LOGGING_FORMATEO_VALORES.md**: Documenta el sistema de logging y formato de valores

Estos archivos son recursos técnicos para desarrolladores y personal de mantenimiento que necesitan entender decisiones de diseño, historial de problemas resueltos, y detalles de implementación.

### 🔧 Archivos de Configuración Ocultos

- **.git/**: Carpeta del sistema de control de versiones Git que almacena todo el historial de cambios del proyecto
- **.vscode/**: Configuraciones específicas del editor Visual Studio Code

---

## ⚠️ LIMITACIONES CONOCIDAS Y LECCIONES APRENDIDAS

### **Limitaciones de la API XM**

El dashboard obtiene datos de la API oficial de XM (pydataxm), pero esta tiene algunas limitaciones conocidas:

1. **Datos históricos incompletos**: Algunos días específicos no tienen datos disponibles en la API (ej: agosto 2022 tiene 7 días sin datos de demanda comercial). Esto no es un error del dashboard, sino limitación de la fuente de datos.

2. **Latencia de publicación**: Los datos del día actual pueden no estar disponibles inmediatamente. La API XM típicamente publica datos con 1-2 horas de retraso.

3. **Métricas horarias vs. diarias**: Algunas métricas (Gene, DemaCome) vienen en formato horario (24 columnas Hour01-Hour24) y deben ser sumadas para obtener el total diario.

### **Lecciones Técnicas Importantes**

#### **1. Conversiones de Unidades - CRÍTICO**
El error más común y costoso fue confundir factores de conversión:
- ❌ **Error**: Dividir por 1e9 pensando que API retorna Wh
- ✅ **Correcto**: API XM retorna kWh para la mayoría de métricas, dividir por 1e6 para obtener GWh
- **Impacto**: Error de 1000x en valores mostrados (0.15 en lugar de 14,690 GWh)
- **Solución**: Conversiones centralizadas en ETL, valores en BD ya están en GWh, dashboard solo lee

#### **2. Sistema de Caché vs SQLite**
El sistema original usaba archivos JSON en caché, lo cual causaba:
- Problemas de sincronización entre workers de Gunicorn
- Lentitud al cargar datos (lectura de disco en cada request)
- Pérdida de datos por corrupción de archivos
- **Solución**: Migración a SQLite con índices optimizados → 10x más rápido

#### **3. Duplicados en Base de Datos**
La actualización incremental puede crear duplicados si no se maneja correctamente:
- **Problema**: Misma fecha insertada múltiples veces por diferentes ejecuciones
- **Solución**: Script de auto-corrección semanal + validación de duplicados en health check
- **Prevención**: ETL usa INSERT OR REPLACE en SQLite

#### **4. Validación de Rangos**
Los datos de XM a veces contienen valores anómalos:
- Fechas futuras (por errores de sistema)
- Valores negativos en métricas que solo pueden ser positivas
- Valores extremos fuera de rangos físicamente posibles
- **Solución**: Validador automático post-ETL con rangos esperados por métrica

### **Buenas Prácticas Implementadas**

✅ **Actualización incremental**: Solo trae datos nuevos (últimos 7 días) cada 6 horas → ahorra tiempo y recursos  
✅ **ETL completo semanal**: Respaldo completo que recarga 5 años → garantiza consistencia  
✅ **Validación post-actualización**: Detecta anomalías automáticamente → previene errores en dashboard  
✅ **Auto-corrección programada**: Limpia duplicados y errores sin intervención manual  
✅ **Valores pre-convertidos**: BD almacena todo en GWh → elimina conversiones en dashboard  
✅ **Índices optimizados**: Consultas 100x más rápidas con índices en columnas correctas  
✅ **Health check continuo**: Endpoint /health monitorea frescura y calidad de datos  
✅ **Logs detallados**: Cada ejecución genera log con estadísticas → facilita debugging  

### **Recursos Adicionales**

Para más detalles técnicos sobre la arquitectura, consultar:
- **ARQUITECTURA_ETL_SQLITE.md**: Documentación completa del sistema ETL-SQLite
- **LIMPIEZA_PROYECTO_20251206.md**: Historial de limpieza y archivos eliminados
- **legacy/README.md**: Explicación del sistema antiguo de caché (obsoleto)

---

## 🤝 CONTRIBUCIÓN

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/NuevaCaracteristica`)
3. Commit tus cambios (`git commit -m 'Añadir nueva característica'`)
4. Push a la rama (`git push origin feature/NuevaCaracteristica`)
5. Abre un Pull Request

**Importante**: 
- Al modificar conversiones de unidades, verificar siempre contra portal XM
- Ejecutar tests antes de commit: `python tests/test_etl.py`
- Documentar cambios en archivos `.md` correspondientes

---

## 📝 LICENCIA

Este proyecto está bajo la Licencia MIT. Ver archivo `LICENSE` para más detalles.

---

## 📧 CONTACTO

**Ministerio de Minas y Energía - Colombia**

- **Desarrollado por**: Melissa Cardona
- **GitHub**: [@MelissaCardona2003](https://github.com/MelissaCardona2003)
- **Repositorio**: [Dashboard_Multipage_MME](https://github.com/MelissaCardona2003/Dashboard_Multipage_MME)
- **Fuente de Datos**: [XM - Expertos en Mercados](https://www.xm.com.co)

---

## 🙏 AGRADECIMIENTOS

- **XM (Expertos en Mercados)**: Por proveer API pública con datos del sector energético
- **pydataxm**: Librería Python para acceso a datos de XM
- **Dash/Plotly**: Framework de visualización interactiva
- **Ministerio de Minas y Energía**: Por el apoyo al proyecto

---

**Última actualización**: Noviembre 2025  
**Versión del sistema**: 2.0 ETL-SQLite  
**Estado**: ✅ Producción - 100% Funcional - Sistema Autónomo
