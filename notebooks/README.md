# Notebooks de réplica de tableros

Este directorio contiene réplicas en Jupyter Notebook de la lógica de los tableros en `pages/` para validación línea por línea con datos reales de XM.

## Archivos
- metricas_repl.ipynb: réplica de la página `pages/metricas.py`. Incluye:
  - Inicialización de `pydataxm.ReadDB` y carga del catálogo de métricas.
  - Generación de opciones (métricas y entidades) a partir del catálogo.
  - Selección de parámetros, consulta con `request_data`, vista previa y exportación a CSV.
  - Ficha automática de la métrica (nombre, descripción, unidad, uso MME, valores críticos, categoría).
  - Gráfico de serie temporal con detección flexible de columnas (`Date/Value` o `Values_Date/Values_Value`).

## Cómo usar
1. Abre el notebook `metricas_repl.ipynb`.
2. Ejecuta las celdas en orden. Si alguna métrica/entidad no coincide, la celda "Ajuste automático" corrige la entidad y acota fechas al `MaxDays` del catálogo.
3. Repite cambiando `selected_metric`, `selected_entity`, `start_dt`, `end_dt` en la celda de parámetros.
4. Para exportar, ejecuta la celda "Exportar datos a CSV"; guarda un archivo `metricas_<métrica>_<entidad>_<timestamp>.csv` en este directorio.

## Requisitos
- Python 3.10+ con los paquetes instalados: `pydataxm`, `pandas`, `plotly`, `dash` (ya resueltos en el entorno del proyecto).
- Conectividad a internet para consultar a los servicios de XM.

## Notas
- Las columnas devueltas por XM pueden variar según métrica y entidad. El notebook detecta automáticamente los nombres de fecha/valor cuando es posible.
- Si no aparecen datos, reduce el rango de fechas o cambia de entidad según lo listado en el catálogo.
