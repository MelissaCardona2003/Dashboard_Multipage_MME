import pandas as pd
from datetime import date, timedelta
from typing import Iterable, List, Tuple, Optional
import time

def chunk_date_ranges(start: date, end: date, chunk_days: int = 30) -> List[Tuple[date, date]]:
	"""Divide un rango [start, end] en sub-rangos de hasta chunk_days días (incluidos).
	Retorna lista de tuplas (ini, fin) contiguas y no superpuestas.
	"""
	if start > end:
		return []
	ranges = []
	cur = start
	while cur <= end:
		seg_end = min(cur + timedelta(days=chunk_days - 1), end)
		ranges.append((cur, seg_end))
		cur = seg_end + timedelta(days=1)
	return ranges

def fetch_gene_recurso_chunked(objetoAPI, start: date, end: date, filtros: Iterable[str], batch_size: int = 50, chunk_days: int = 180, retries: int = 2, backoff_sec: float = 0.8) -> pd.DataFrame:
	"""Consulta Gene con Entity='Recurso' para una lista de filtros (SIC) en lotes y por chunks de fechas.
	Devuelve DataFrame con columnas: ['Codigo','Fecha','Generacion_GWh'] agregadas por día.
	OPTIMIZADO: Usa cache manager para evitar consultas repetidas a API.
	MEJORA DE PERFORMANCE: chunk_days aumentado de 90 a 180 días para reducir overhead.
	"""
	from utils._xm import fetch_metric_data
	from utils.cache_manager import get_cache_key, get_from_cache, save_to_cache
	import logging
	logger = logging.getLogger(__name__)
	
	filtros = [str(x).strip() for x in filtros if x and isinstance(x, (str, int))]
	if not filtros:
		return pd.DataFrame(columns=['Codigo','Fecha','Generacion_GWh'])

	# OPTIMIZACIÓN: Cachear resultado completo de consulta
	filtros_hash = hash(tuple(sorted(filtros)))
	cache_key = get_cache_key('gene_recurso_chunked', filtros_hash, start, end)
	cached_data = get_from_cache(cache_key, allow_expired=False)
	if cached_data is not None:
		logger.info(f"✅ Cache válido para Gene/Recurso ({len(filtros)} códigos, {start} a {end})")
		return cached_data

	# MEJORA: chunk_days por defecto 180 (era 90) - menos llamadas API
	registros = []
	for ini, fin in chunk_date_ranges(start, end, chunk_days=chunk_days):
		# Batches por códigos SIC
		for i in range(0, len(filtros), batch_size):
			lote = filtros[i:i+batch_size]
			# Usar la API directamente con códigos específicos
			df = objetoAPI.request_data("Gene", "Recurso", ini, fin, lote)
			if df is None or df.empty:
				continue
			horas_cols = [c for c in df.columns if str(c).startswith('Values_Hour')]
			if not horas_cols:
				continue
			# Identificar columna de código en respuesta Gene (puede variar)
			code_col = None
			for cand in ('Values_code', 'Values_Code', 'Values_resourceCode', 'Values_ResourceCode'):
				if cand in df.columns:
					code_col = cand
					break
			for _, row in df.iterrows():
				try:
					kwh = sum(float(row.get(c)) for c in horas_cols if pd.notna(row.get(c)))
				except Exception:
					kwh = 0.0
				registros.append({
					'Codigo': str(row.get(code_col, '') if code_col else '').strip(),
					'Fecha': row.get('Date'),
					'Generacion_GWh': kwh/1_000_000.0
				})

	if not registros:
		return pd.DataFrame(columns=['Codigo','Fecha','Generacion_GWh'])
	
	df_out = pd.DataFrame(registros)
	# Asegurar tipos/orden básico
	if 'Fecha' in df_out.columns:
		try:
			df_out['Fecha'] = pd.to_datetime(df_out['Fecha']).dt.date
		except Exception:
			pass
	
	# Cachear resultado por 6 horas (datos de generación actualizados diariamente)
	save_to_cache(cache_key, df_out, cache_type='gene_recurso')
	logger.info(f"✅ Cacheado Gene/Recurso: {len(df_out)} registros ({len(filtros)} códigos)")
	
	return df_out

