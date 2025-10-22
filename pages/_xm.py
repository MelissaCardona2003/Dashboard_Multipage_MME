"""Helper ligero para inicializar la conexión a pydataxm de forma perezosa (lazy).

Los módulos de la carpeta `pages` deben llamar a `get_objetoAPI()` cuando necesiten
usar la API en vez de inicializar al importar el módulo. Esto evita que imports largos
bloqueen el arranque del servidor Dash.
"""
from typing import Optional
import logging

try:
    from pydataxm.pydataxm import ReadDB
    _PYDATAXM_AVAILABLE = True
except Exception:
    ReadDB = None  # type: ignore
    _PYDATAXM_AVAILABLE = False

_objetoAPI = None

def get_objetoAPI():
    """Retorna una instancia única de ReadDB si está disponible, o None.

    Inicializa la instancia la primera vez que se llama. Si la importación falla,
    retorna None silenciosamente y registra un warning.
    """
    global _objetoAPI
    if _objetoAPI is not None:
        return _objetoAPI

    logger = logging.getLogger('xm_helper')
    if not _PYDATAXM_AVAILABLE:
        logger.warning('pydataxm no disponible (get_objetoAPI)')
        _objetoAPI = None
        return None

    try:
        _objetoAPI = ReadDB()
        logger.info('pydataxm ReadDB inicializada (lazy)')
    except Exception as e:
        logger.exception('Error inicializando ReadDB: %s', e)
        _objetoAPI = None
    return _objetoAPI
