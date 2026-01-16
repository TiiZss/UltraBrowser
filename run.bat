@echo off
cd /d "%~dp0"
REM Script para ejecutar UltraBrowser en Windows
REM Intenta usar uv primero para gestionar el entorno y las dependencias

where uv >nul 2>nul
if %errorlevel% equ 0 goto :RUN_UV
goto :CHECK_PYTHON

:RUN_UV
echo [INFO] uv detectado. Ejecutando con 'uv run'...
uv run -m ultrabrowser.main
if errorlevel 1 goto :ERROR
goto :END

:CHECK_PYTHON
echo [ADVERTENCIA] uv no encontrado en el PATH.
echo [INFO] Iniciando modo de auto-preparacion...

where python >nul 2>nul
if %errorlevel% neq 0 goto :NO_PYTHON

if not exist .venv (
    echo [INFO] Creando entorno virtual (.venv)...
    python -m venv .venv
    if errorlevel 1 goto :ERROR_VENV
)

if exist .venv\Scripts\activate.bat (
    echo [INFO] Activando entorno virtual...
    call .venv\Scripts\activate.bat
    
    echo [INFO] Verificando e instalando dependencias...
    pip install pyqt6 pyqt6-webengine stem
    if errorlevel 1 goto :ERROR_DEPS

    echo [INFO] Ejecutando UltraBrowser...
    python -m ultrabrowser.main
    if errorlevel 1 goto :ERROR
    goto :END
) else (
    echo [ERROR] No se pudo encontrar el script de activacion del entorno virtual.
    goto :ERROR_PAUSE
)

:NO_PYTHON
echo [ERROR] Python no encontrado. Por favor instala Python 3.12+ o uv.
echo https://www.python.org/downloads/
goto :ERROR_PAUSE

:ERROR_VENV
echo [ERROR] Fallo al crear el entorno virtual.
goto :ERROR_PAUSE

:ERROR_DEPS
echo [ERROR] Fallo al instalar las dependencias.
goto :ERROR_PAUSE

:ERROR
echo [ERROR] La aplicacion cerro con errores.
:ERROR_PAUSE
pause
exit /b 1

:END
echo [INFO] Aplicacion finalizada.
pause
