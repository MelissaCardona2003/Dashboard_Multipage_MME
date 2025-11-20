# 📚 Guía de Mantenimiento - Dashboard MME

## 🔄 Sistema de Actualización Automática

### Arquitectura Optimizada

El sistema ahora utiliza **actualización incremental** para mayor eficiencia:

- **Actualización Incremental** (cada 6 horas): Solo actualiza datos nuevos desde la última fecha en BD
- **ETL Completo** (semanal): Mantiene integridad histórica completa

### Horarios de Ejecución Automática

```
🔄 Actualización Incremental:
   - 00:00 (medianoche)
   - 06:00 (mañana)
   - 12:00 (mediodía)
   - 18:00 (tarde)

📊 ETL Completo:
   - Domingos 03:00 AM

🔧 Auto-corrección:
   - Domingos 02:00 AM (antes del ETL)

✅ Validación:
   - 15 minutos después de cada actualización incremental
```

## 🛠️ Comandos Manuales

### Actualización Rápida (Recomendado)
```bash
cd /home/admonctrlxm/server
python3 scripts/actualizar_incremental.py
```
⏱️ Duración: ~30 segundos  
📊 Actualiza: Solo datos nuevos desde última fecha

### ETL Completo (Si es necesario)
```bash
cd /home/admonctrlxm/server
python3 etl/etl_xm_to_sqlite.py
```
⏱️ Duración: ~2-3 horas  
📊 Actualiza: 5 años de datos históricos

### Auto-corrección
```bash
cd /home/admonctrlxm/server

# Modo dry-run (ver qué se corregirá)
python3 scripts/autocorreccion.py --dry-run

# Modo real (aplicar correcciones)
python3 scripts/autocorreccion.py
```

### Validación
```bash
cd /home/admonctrlxm/server
python3 scripts/validar_etl.py
```

### Health Check
```bash
# Vía script
python3 -c "from utils.health_check import verificar_salud_sistema; import json; print(json.dumps(verificar_salud_sistema(), indent=2))"

# Vía API
curl http://localhost:8050/health | python3 -m json.tool
```

## 📋 Verificación de Estado

### Estado de Datos
```bash
python3 << 'EOF'
import sqlite3
from datetime import datetime

conn = sqlite3.connect('portal_energetico.db')
cursor = conn.cursor()

metricas = [
    ('Gene', 'Sistema', 'Generación'),
    ('DemaCome', 'Sistema', 'Demanda'),
    ('AporEner', 'Sistema', 'Aportes'),
    ('VoluUtilDiarEner', 'Embalse', 'Volumen'),
]

for metrica, entidad, nombre in metricas:
    cursor.execute("SELECT MAX(fecha) FROM metrics WHERE metrica=? AND entidad=?", (metrica, entidad))
    print(f"{nombre}: {cursor.fetchone()[0]}")
conn.close()
EOF
```

### Estado del Dashboard
```bash
sudo systemctl status dashboard-mme
```

### Logs Recientes
```bash
# Actualización incremental
tail -50 logs/actualizacion_$(date +%Y%m%d).log

# ETL completo
tail -50 logs/etl_semanal_$(date +%Y%m%d).log

# Dashboard
sudo journalctl -u dashboard-mme -n 50
```

## 🔧 Reiniciar Servicios

### Dashboard
```bash
sudo systemctl restart dashboard-mme
```

### Verificar Crontab
```bash
crontab -l
```

### Modificar Crontab
```bash
crontab -e
```

## 📊 Métricas Monitoreadas

| Métrica | Entidad | Uso |
|---------|---------|-----|
| `VoluUtilDiarEner` | Embalse | Volumen útil de embalses (reservas) |
| `CapaUtilDiarEner` | Embalse | Capacidad útil de embalses |
| `AporEner` | Sistema | Aportes hídricos |
| `AporEnerMediHist` | Sistema | Media histórica de aportes |
| `Gene` | Sistema | Generación total SIN |
| `DemaCome` | Sistema | Demanda comercial |

## ⚠️ Troubleshooting

### Dashboard no carga
```bash
# Ver logs
sudo journalctl -u dashboard-mme -n 100

# Reiniciar
sudo systemctl restart dashboard-mme
```

### Datos desactualizados
```bash
# Ejecutar actualización manual
python3 scripts/actualizar_incremental.py

# Ver última fecha en BD
sqlite3 portal_energetico.db "SELECT metrica, entidad, MAX(fecha) FROM metrics GROUP BY metrica, entidad"
```

### Cron no se ejecuta
```bash
# Verificar crontab
crontab -l

# Ver logs del sistema
grep CRON /var/log/syslog | tail -20

# Verificar permisos
ls -la scripts/*.py
```

### Errores de API XM
```bash
# Probar conexión
python3 -c "from utils._xm import get_objetoAPI; api = get_objetoAPI(); print('✅ API OK')"

# Ver logs de actualización
tail -100 logs/actualizacion_*.log | grep -i error
```

## 📁 Estructura de Archivos Importante

```
/home/admonctrlxm/server/
├── etl/
│   ├── etl_xm_to_sqlite.py       # ETL completo (5 años)
│   └── validaciones.py            # Validaciones de datos
├── scripts/
│   ├── actualizar_incremental.py  # 🆕 Actualización rápida
│   ├── validar_etl.py            # Validación post-ETL
│   ├── autocorreccion.py         # Corrección automática
│   └── validar_post_etl.sh       # Orquestador de validación
├── utils/
│   ├── health_check.py           # Health check del sistema
│   ├── db_manager.py             # Gestor de BD
│   └── _xm.py                    # Cliente API XM
├── logs/                          # Logs de ejecución
├── portal_energetico.db          # Base de datos SQLite
└── crontab_optimizado.txt        # Configuración de cron
```

## 🎯 Mejores Prácticas

1. **Usar actualización incremental** para updates diarios
2. **Dejar el ETL completo** solo para mantenimiento semanal
3. **Monitorear logs** regularmente
4. **Verificar health check** después de actualizaciones
5. **Hacer backup** de la BD antes de cambios mayores

## 📞 Contacto y Soporte

- Repositorio: https://github.com/MelissaCardona2003/Dashboard_Multipage_MME
- API XM: https://www.xm.com.co/
- Dashboard: http://localhost:8050/

---

**Última actualización**: 2025-11-20  
**Versión**: 2.0 (Optimizada con actualización incremental)
