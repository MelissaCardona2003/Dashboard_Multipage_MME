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

def fetch_gene_recurso_chunked(objetoAPI, start: date, end: date, filtros: Iterable[str], batch_size: int = 50, chunk_days: int = 30, retries: int = 2, backoff_sec: float = 0.8) -> pd.DataFrame:
	"""Consulta Gene con Entity='Recurso' para una lista de filtros (SIC) en lotes y por chunks de fechas.
	Devuelve DataFrame con columnas: ['Codigo','Fecha','Generacion_GWh'] agregadas por día.
	"""
	filtros = [str(x).strip() for x in filtros if x and isinstance(x, (str, int))]
	if objetoAPI is None or not filtros:
		return pd.DataFrame(columns=['Codigo','Fecha','Generacion_GWh'])

	registros = []
	for ini, fin in chunk_date_ranges(start, end, chunk_days=chunk_days):
		# Batches por códigos SIC
		for i in range(0, len(filtros), batch_size):
			lote = filtros[i:i+batch_size]
			attempt = 0
			df = None
			while attempt <= retries:
				try:
					df = objetoAPI.request_data("Gene", "Recurso", ini, fin, lote)
					break
				except Exception:
					if attempt >= retries:
						df = None
						break
					time.sleep(backoff_sec * (2 ** attempt))
					attempt += 1
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
	return df_out

