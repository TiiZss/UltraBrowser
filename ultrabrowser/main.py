"""
UltraBrowser: Navegador Privado, Seguro y Ligero con Integración Tor
Punto de entrada principal de la aplicación
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from .browser_engine import BrowserWindow
from .logging_config import setup_logging, set_logger
from .config import BrowserConfig, get_config, set_config, load_user_agents
from .exceptions import ConfigFileNotFoundError, ConfigFileInvalidError

def main():
    """Función principal de la aplicación"""
    # Intentar cargar configuración desde archivo
    config_path = Path("config/config.json")
    try:
        config = BrowserConfig.from_file(config_path)
        print(f"✓ Configuración cargada desde {config_path}")
    except (ConfigFileNotFoundError, ConfigFileInvalidError) as e:
        print(f"⚠ Usando configuración por defecto: {e}")
        config = BrowserConfig()
    
    # Configurar logging
    logger = setup_logging(
        debug_mode=config.debug_mode,
        log_file=config.log_file if config.log_file else None
    )
    set_logger(logger)
    
    logger.info("=" * 60)
    logger.info("Iniciando UltraBrowser")
    logger.info("=" * 60)
    
    # Establecer configuración global
    set_config(config)
    
    # Crear aplicación Qt
    app = QApplication(sys.argv)
    app.setApplicationName("UltraBrowser")
    app.setOrganizationName("Navigator")
    
    try:
        # Crear y mostrar ventana principal
        window = BrowserWindow()
        window.show()
        
        logger.info("Ventana principal mostrada")
        
        # Ejecutar aplicación
        exit_code = app.exec()
        logger.info(f"Aplicación finalizada con código: {exit_code}")
        return exit_code
        
    except Exception as e:
        logger.critical(f"Error crítico al iniciar la aplicación: {e}", exc_info=True)
        return 1
    finally:
        logger.info("=" * 60)
        logger.info("UltraBrowser finalizado")
        logger.info("=" * 60)

if __name__ == "__main__":
    sys.exit(main())
