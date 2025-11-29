# 📦 Base de Datos Portal Energético - Release

**Fecha:** 29 de noviembre de 2025  
**Versión:** v1.0-db-20251129

---

## 📊 Contenido

Este archivo contiene la base de datos SQLite completa del Portal Energético Colombia con datos históricos del sector energético.

### Estadísticas:
- **Registros:** 1,366,002
- **Tamaño original:** 5.0 GB
- **Tamaño comprimido:** 855 MB
- **Período:** 2020 - 2025 (5 años)
- **Duplicados:** 0
- **Última actualización:** 29 de noviembre de 2025

### Métricas incluidas:
- ✅ Generación eléctrica (hidráulica, térmica, solar, eólica)
- ✅ Aportes hídricos y niveles de embalses
- ✅ Demanda comercial del Sistema Interconectado Nacional (SIN)
- ✅ Precios de bolsa y escasez
- ✅ Listado de recursos y plantas

---

## 📥 Descargar e Instalar

### 1. Descargar desde GitHub Releases

```bash
# Desde tu computador local, descarga el archivo
# Ve a: https://github.com/MelissaCardona2003/Dashboard_Multipage_MME/releases
# O usa wget/curl:

wget https://github.com/MelissaCardona2003/Dashboard_Multipage_MME/releases/download/v1.0-db-20251129/portal_energetico.db.tar.gz
```

### 2. Descomprimir

```bash
# Descomprimir el archivo
tar -xzf portal_energetico.db.tar.gz

# Verificar tamaño
ls -lh portal_energetico.db
# Debe mostrar: 5.0G
```

### 3. Colocar en tu proyecto

```bash
# Mover al directorio del proyecto
mv portal_energetico.db /ruta/a/tu/Dashboard_Multipage_MME/

# O crear enlace simbólico
ln -s $(pwd)/portal_energetico.db /ruta/a/tu/Dashboard_Multipage_MME/portal_energetico.db
```

---

## 🔧 Uso con el Dashboard

Una vez descargada e instalada la base de datos:

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Verificar que portal_energetico.db está en la raíz del proyecto
ls -lh portal_energetico.db

# 3. Ejecutar el dashboard
python app.py
```

El dashboard automáticamente detectará y usará la base de datos.

---

## 🔍 Inspeccionar la Base de Datos

### Usando SQLite CLI:

```bash
# Abrir base de datos
sqlite3 portal_energetico.db

# Ver tablas
.tables

# Ver estructura de la tabla metrics
.schema metrics

# Contar registros
SELECT COUNT(*) FROM metrics;

# Ver últimas 10 entradas
SELECT * FROM metrics ORDER BY fecha DESC LIMIT 10;

# Salir
.quit
```

### Usando Python:

```python
import sqlite3
import pandas as pd

# Conectar
conn = sqlite3.connect('portal_energetico.db')

# Ver primeros registros
df = pd.read_sql_query("SELECT * FROM metrics LIMIT 10", conn)
print(df)

# Estadísticas
total = pd.read_sql_query("SELECT COUNT(*) as total FROM metrics", conn)
print(f"Total registros: {total['total'][0]:,}")

conn.close()
```

---

## 🔄 Actualizar la Base de Datos

Si necesitas datos más recientes:

### Opción 1: Actualización Incremental (Recomendado)

```bash
# Ejecutar script de actualización incremental
python scripts/actualizar_incremental.py
```

Este script:
- Trae solo datos nuevos desde la última fecha
- Toma 30-60 segundos
- Actualiza automáticamente

### Opción 2: ETL Completo (5 años)

```bash
# Recarga completa (toma 2-3 horas)
python etl/etl_xm_to_sqlite.py
```

---

## 📝 Estructura de la Base de Datos

### Tabla: `metrics`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | INTEGER | Primary key auto-incremental |
| `fecha` | DATE | Fecha del dato (YYYY-MM-DD) |
| `metrica` | VARCHAR | Tipo de métrica (Gene, DemaCome, etc.) |
| `entidad` | VARCHAR | Entidad (Sistema, Embalse, Recurso) |
| `recurso` | VARCHAR | Nombre específico del recurso |
| `valor_gwh` | REAL | Valor en GWh (ya convertido) |
| `unidad` | VARCHAR | Unidad de medida ('GWh') |
| `fecha_actualizacion` | TIMESTAMP | Fecha de inserción en BD |

### Índices Optimizados:

- `idx_metrics_metrica_entidad_fecha` - Consultas principales
- `idx_metrics_fecha` - Filtros temporales

---

## ⚠️ Notas Importantes

### Conversiones Aplicadas:

Todos los valores en la base de datos ya están convertidos a GWh:

- **VoluUtilDiarEner:** kWh → GWh (÷ 1,000,000)
- **CapaUtilDiarEner:** kWh → GWh (÷ 1,000,000)
- **AporEner:** Wh → GWh (÷ 1,000,000,000)
- **Gene:** Σ(Hour01-24 kWh) → GWh (÷ 1,000,000)
- **DemaCome:** Σ(Hour01-24 kWh) → GWh (÷ 1,000,000)

**No es necesario convertir nuevamente** al consultar la base de datos.

### Compatibilidad:

- ✅ Python 3.8+
- ✅ SQLite 3.31+
- ✅ Pandas 1.3+
- ✅ Linux, macOS, Windows

---

## 🆘 Solución de Problemas

### Error: "database is locked"

```bash
# Cerrar todas las conexiones abiertas
pkill -f portal_energetico.db

# O reiniciar el dashboard
sudo systemctl restart dashboard-mme
```

### Base de datos corrupta:

```bash
# Verificar integridad
sqlite3 portal_energetico.db "PRAGMA integrity_check;"

# Si hay errores, re-descargar desde GitHub Releases
```

### Falta espacio en disco:

```bash
# Verificar espacio disponible
df -h

# Liberar espacio (eliminar logs antiguos)
find . -name "*.log" -mtime +60 -delete
```

---

## 📞 Soporte

Para problemas o preguntas:
- **Issues:** https://github.com/MelissaCardona2003/Dashboard_Multipage_MME/issues
- **Email:** [Tu email]
- **Documentación:** Ver README.md del proyecto

---

## 📜 Licencia

Ver archivo LICENSE en el repositorio principal.

---

**Generado automáticamente el 29 de noviembre de 2025**
