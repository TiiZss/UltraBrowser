"""
UltraBrowser: Navegador Privado, Seguro y Ligero con Integración Tor
Punto de entrada principal de la aplicación
"""

import faulthandler
import os
import signal
import sys
import traceback
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from .diagnostics import get_diagnostics_paths
from .logging_config import setup_logging, set_logger
from .config import BrowserConfig, set_config
from .exceptions import ConfigFileNotFoundError, ConfigFileInvalidError


_FAULT_LOG_HANDLE = None


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _prepare_qt_environment(chromium_log_path: Path) -> None:
    flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
    flag_parts = [part for part in flags.split() if part]

    if not any(part.startswith("--proxy-bypass-list=") for part in flag_parts):
        flag_parts.append("--proxy-bypass-list=localhost,127.0.0.1,<local>")

    if "--enable-logging" not in flag_parts:
        flag_parts.append("--enable-logging")
    if not any(part.startswith("--log-level=") for part in flag_parts):
        flag_parts.append("--log-level=0")

    os.environ.setdefault("CHROME_LOG_FILE", str(chromium_log_path))

    if sys.platform.startswith("win"):
        if "ULTRABROWSER_USE_SOFTWARE_OPENGL" not in os.environ:
            os.environ["ULTRABROWSER_USE_SOFTWARE_OPENGL"] = "1"

        if os.environ.get("ULTRABROWSER_USE_SOFTWARE_OPENGL") == "1":
            os.environ.setdefault("QT_OPENGL", "software")
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL, True)

        if not any(part.startswith("--disable-features=") for part in flag_parts):
            flag_parts.append("--disable-features=RendererCodeIntegrity")

    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = " ".join(flag_parts)


def _enable_fault_diagnostics(fault_log_path: Path) -> Path:
    global _FAULT_LOG_HANDLE
    try:
        _FAULT_LOG_HANDLE = open(fault_log_path, "a", encoding="utf-8")
        _FAULT_LOG_HANDLE.write("\n=== UltraBrowser fault diagnostics session start ===\n")
        _FAULT_LOG_HANDLE.flush()
        faulthandler.enable(file=_FAULT_LOG_HANDLE, all_threads=True)

        if hasattr(signal, "SIGBREAK"):
            faulthandler.register(signal.SIGBREAK, file=_FAULT_LOG_HANDLE, all_threads=True)
    except Exception:
        pass
    return fault_log_path


def main():
    """Función principal de la aplicación"""
    # Forzar UTF-8 en stdout/stderr para evitar UnicodeEncodeError en Windows
    # (cp1252 no soporta muchos caracteres Unicode usados en logs)
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass  # Si falla la reconfiguración, continuamos igualmente

    try:
        return _main_inner()
    except Exception as e:
        # Captura de último recurso para errores catastróficos no controlados
        try:
            print(f"[FATAL] Error catastrofico al iniciar UltraBrowser: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
        except Exception:
            pass
        return 1


def _main_inner():
    """Lógica principal separada para facilitar la captura de errores catastróficos."""
    # Intentar cargar configuración desde archivo
    config_path = _project_root() / "config" / "config.json"
    try:
        config = BrowserConfig.from_file(config_path)
        print(f"[OK] Configuracion cargada desde {config_path}")
    except (ConfigFileNotFoundError, ConfigFileInvalidError) as e:
        print(f"[WARN] Usando configuracion por defecto: {e}")
        config = BrowserConfig()

    diagnostics_paths = get_diagnostics_paths(config, _project_root())
    fault_log_path = _enable_fault_diagnostics(diagnostics_paths["fault_log"])
    _prepare_qt_environment(diagnostics_paths["chromium_log"])

    # Configurar logging
    logger = setup_logging(
        debug_mode=config.debug_mode,
        log_file=config.log_file if config.log_file else None
    )
    set_logger(logger)

    logger.info("=" * 60)
    logger.info("Iniciando UltraBrowser by TiiZss")
    logger.info("=" * 60)
    logger.info(f"Logs de diagnostico persistente: {diagnostics_paths['log_dir']}")
    logger.info(f"Faulthandler activo en: {fault_log_path}")
    logger.info(f"Chromium log activo en: {diagnostics_paths['chromium_log']}")

    if sys.platform.startswith("win") and os.environ.get("QT_OPENGL") == "software":
        logger.info("Qt configurado para renderizado por software en Windows")

    # Establecer configuración global
    set_config(config)

    def _handle_uncaught_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        try:
            with open(diagnostics_paths["uncaught_log"], "a", encoding="utf-8") as exception_log:
                exception_log.write("\n=== Excepcion no controlada ===\n")
                traceback.print_exception(exc_type, exc_value, exc_traceback, file=exception_log)
        except OSError:
            pass

        logger.critical(
            "Excepción no controlada durante la ejecución",
            exc_info=(exc_type, exc_value, exc_traceback)
        )

    sys.excepthook = _handle_uncaught_exception

    from .browser_engine import BrowserWindow

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
