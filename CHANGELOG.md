# Changelog

All notable changes to this project will be documented in this file.

## [0.5.0] - 2026-04-08

### Added
- **Diagnóstico persistente** (`ultrabrowser/diagnostics.py`): Nuevo módulo central para resolver directorios y archivos de diagnóstico en runtime. Soporta configuración desde `config/config.json` y expone utilidades CLI para que los scripts de arranque consulten la ruta efectiva de logs.
- **Logs de crash y Chromium**: La aplicación ahora registra `python-fault.log`, `uncaught-exceptions.log` y `qtwebengine-chromium.log` fuera del repositorio por defecto. Esto deja trazas útiles incluso cuando el cierre viene de QtWebEngine o del runtime nativo de Windows.
- **Acceso a diagnóstico desde la UI**: Nueva acción `📂 Diagnóstico` en la barra principal, menú `Herramientas` y atajo global `Ctrl+Alt+D` para abrir la carpeta de logs persistentes sin salir del navegador.
- **Configuración de diagnóstico**: Nuevas claves `diagnostics_dir`, `chromium_log_file`, `fault_log_file`, `uncaught_exceptions_file` y `open_diagnostics_on_failure` en `config/config.json` y en el ejemplo de configuración.

### Changed
- **Secuencia de arranque de QtWebEngine**: `main.py` ahora prepara el entorno de Qt y Chromium antes de cargar `BrowserWindow`, evitando que flags críticas lleguen demasiado tarde al motor embebido.
- **Estabilidad de renderizado en Windows**: UltraBrowser usa OpenGL por software por defecto en Windows (`ULTRABROWSER_USE_SOFTWARE_OPENGL=1`) para reducir cierres nativos asociados a drivers gráficos o inicialización de WebEngine.
- **Scripts de arranque de Windows**: `run.bat` y `run.ps1` ahora instalan dependencias usando los mismos mínimos declarados en `pyproject.toml` en lugar de versiones flotantes.
- **Tor runtime fuera del repositorio**: El estado mutable de Tor pasa a `%LOCALAPPDATA%/UltraBrowser/tor_data` en Windows y `~/.ultrabrowser/tor_data` en Linux/macOS. Esto evita contaminar el árbol git con locks y cachés generados por ejecución.
- **Documentación de configuración**: README y ejemplos actualizados para reflejar las rutas de diagnóstico, la apertura automática de logs en Windows y las nuevas acciones disponibles en la interfaz.

### Fixed
- **Detección de Tor no disponible**: `TorManager` ahora contempla también `SocketError` de `stem` cuando valida el puerto de control, reduciendo falsos errores y mejorando el diagnóstico real.
- **Locks obsoletos de Tor**: Se eliminan locks residuales antes de iniciar el proceso Tor portable, evitando fallos intermitentes tras cierres anteriores o sesiones abortadas.
- **Reproducibilidad del entorno en Windows**: Las rutas de diagnóstico y la apertura automática de la carpeta de logs se resuelven contra la configuración efectiva del proyecto, en lugar de usar rutas duplicadas o hardcodeadas.

## [0.4.0] - 2026-03-25

### Added
- **Ad Blocker** (`ad_blocker.py`): New `QWebEngineUrlRequestInterceptor` that blocks requests to 100+ known ad networks and trackers (Google Ads, Doubleclick, Taboola, Criteo, Hotjar, Facebook Pixel, etc.) at the network level, before they leave the browser. Pages maintain full functionality — only third-party ad resources are blocked. Toggle available in the toolbar with live counter in the status bar.
- **Anti-Fingerprinting JS** (`ANTI_FINGERPRINT_JS`): Script injected via `QWebEngineScript` on every page at `DocumentCreation` time. Masks WebGL vendor/renderer, standardizes `navigator.deviceMemory`, `navigator.hardwareConcurrency`, `screen.colorDepth/pixelDepth`, and disables the Battery API.
- **`TorConnectWorker` (QThread)**: Tor connection now runs in a background thread. The UI remains fully responsive during the 5–30 second connection process. A spinner screen is shown while connecting.
- **`create_private_profile()`**: Dedicated factory function that creates a true off-the-record `QWebEngineProfile("")` (empty name = no disk persistence). Previously `defaultProfile()` was used, which may share state between instances.
- **`closeEvent` override in `BrowserWindow`**: Orderly shutdown that destroys all `QWebEnginePage` objects before the `QWebEngineProfile` is released, eliminating the Chromium warning *"Release of profile requested but WebEnginePage still not deleted."*
- **User-Agent rotation timer**: `QTimer` now actually rotates the User-Agent on the shared profile every N minutes (configurable). Previously the interval was configured but never executed automatically.
- **`block_ads` config option**: New boolean field in `config.json` and `BrowserConfig` (default: `true`).

### Changed
- **True off-the-record profile**: All tabs now share a single `QWebEngineProfile("")` created at `BrowserWindow` level and passed into each `BrowserEngine`. Nothing is ever written to disk (no cookies, no cache, no history).
- **`TorManager.get_exit_ip()`** (renamed from `get_current_ip()`): Previous implementation incorrectly sent a raw HTTP request directly to the SOCKS5 port without implementing the SOCKS5 protocol. New implementation uses `requests` with `socks5h://` proxy when available, or returns `None` safely.
- **`load_user_agents()`**: Removed confusing recursive call used as fallback. Default list is now defined explicitly inside the function.
- **`BrowserConfig.from_file()`**: Now filters unknown JSON keys for forward compatibility with older config files.
- **`log_file` default**: Changed from `"logs/ultrabrowser.log"` to `null`. Logging to disk must be explicitly enabled in `config.json`. Writing navigation data to disk by default was a privacy concern.
- **`run.bat` / `run.ps1` / `run.sh`**: Fixed `uv pip install` failing with *"No virtual environment found"*. Scripts now use `uv sync` (reads `pyproject.toml`, creates `.venv` automatically) instead of `uv pip install`.
- **`run.*` scripts**: Terminal/console window now closes automatically on clean exit. The pause prompt only appears on error, so the user can read the message.
- **`pyproject.toml`**: Added `[tool.uv] package = false` to suppress *"Skipping installation of entry points"* warning. Added `link-mode = "copy"` to suppress hardlink warning on cross-filesystem setups. Removed unused `[project.scripts]` entry.

### Fixed
- **Duplicate camera denial bug**: `handle_permission_request()` was calling `setFeaturePermission(PermissionDeniedByUser)` twice for camera (duplicate code block at lines 153–155). Now has a single call per branch.
- **UI freeze during Tor connection**: `toggle_tor()` previously called `time.sleep()` and `QApplication.processEvents()` in the main thread, freezing the interface. Fixed by moving connection to `TorConnectWorker(QThread)`.
- **`bare except:` in `TorManager.__del__`**: Changed to `except Exception: pass` with explanatory comment.
- **Linux/macOS Tor binary permissions**: The bundled Tor binary now has executable permissions set automatically (`chmod +x`) before launch.

---

## [0.3.1] - 2026-02-28

### Added
- Added release date and downloads badges to README.

### Fixed
- Fixed internal project version consistency in `pyproject.toml`.

## [0.3.0] - 2026-02-06

### Added
- Auto-install support for uv and Python in run scripts (where possible).
- License file (MIT).

### Changed
- Run scripts now use uv consistently for dependency install and execution.
- Safer handling of cross-platform venvs between Windows and WSL/Linux.

## [0.2.0] - 2026-01-16

### Added
- **Portable Tor Integration**: Tor is now bundled directly with the application, removing the need for external installation.
- **Multi-platform Bundling**: Support for dropping platform-specific Tor binaries in `bin/windows`, `bin/linux`, and `bin/macos`.
- **Automatic Process Management**: The application automatically launches and manages the Tor background process.
- **Improved UX**: New visual loading screens for Tor connection ("Connecting...", "Success", "Error").
- **Visual Feedback**: Tor button now changes color (Orange for connecting, Green for active).

### Changed
- Refactored `TorManager` to support automatic binary detection.
- Updated `config.json` to be environment-agnostic.
- Removed invalid `setProxy` calls preventing application crash.

### Fixed
- Fixed `WinError 10061` connection refused by auto-launching Tor.
- Fixed Windows compatibility issue with `stem` library (timeout argument).
- Fixed application crash when toggling Tor due to QWebEngineProfile error.

## [0.1.0] - 2026-01-15
### Initial Release
- Basic browsing functionality.
- Tabbed interface.
- Camera/Microphone software toggles.
- Basic Tor toggle (requires external Tor).
