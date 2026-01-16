"""
Ejemplo de sistema de logging profesional
Este archivo muestra cómo implementar la mejora #1
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


def setup_logging(
    debug_mode: bool = False,
    log_file: Optional[Path] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Configura el sistema de logging para UltraBrowser
    
    Args:
        debug_mode: Si es True, muestra logs DEBUG. Si es False, solo INFO y superiores
        log_file: Ruta opcional para guardar logs en archivo
        max_bytes: Tamaño máximo del archivo de log antes de rotar
        backup_count: Número de archivos de backup a mantener
        
    Returns:
        Logger configurado
    """
    # Determinar nivel de log
    level = logging.DEBUG if debug_mode else logging.INFO
    
    # Crear logger principal
    logger = logging.getLogger('ultrabrowser')
    logger.setLevel(level)
    
    # Evitar duplicación de handlers
    if logger.handlers:
        return logger
    
    # Formato de los logs
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler para archivo (si se especifica)
    if log_file:
        # Crear directorio si no existe
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Usar RotatingFileHandler para evitar archivos muy grandes
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# Logger global (se inicializa en main.py)
logger: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    """
    Obtiene el logger global
    
    Returns:
        Logger configurado
        
    Raises:
        RuntimeError: Si el logger no ha sido inicializado
    """
    if logger is None:
        raise RuntimeError("Logger no inicializado. Llama a setup_logging() primero.")
    return logger


# Ejemplo de uso:
"""
# En main.py:
from logging_example import setup_logging, get_logger

logger = setup_logging(debug_mode=True, log_file=Path("logs/app.log"))

# En otros módulos:
from logging_example import get_logger

logger = get_logger()
logger.debug("Mensaje de debug")
logger.info("Información general")
logger.warning("Advertencia")
logger.error("Error ocurrido")
"""
