@echo off
setlocal
cd /d "%~dp0"
REM Script para ejecutar UltraBrowser en Windows
REM Intenta usar uv primero para gestionar el entorno y las dependencias

set "UV_CMD=uv"

where uv >nul 2>nul
if not errorlevel 1 goto :RUN_UV

echo [ADVERTENCIA] uv no encontrado en el PATH. Intentando instalar uv...
powershell -NoProfile -ExecutionPolicy Bypass -Command "iwr -useb https://astral.sh/uv/install.ps1 | iex"
set "PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%"

where uv >nul 2>nul
if not errorlevel 1 goto :RUN_UV

if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV_CMD=%USERPROFILE%\.local\bin\uv.exe"
if exist "%USERPROFILE%\.cargo\bin\uv.exe" set "UV_CMD=%USERPROFILE%\.cargo\bin\uv.exe"

where "%UV_CMD%" >nul 2>nul
if not errorlevel 1 goto :RUN_UV

goto :CHECK_PYTHON

:RUN_UV
echo [INFO] uv detectado. Ejecutando con 'uv run'...
echo [INFO] Verificando e instalando dependencias con uv...
"%UV_CMD%" pip install pyqt6 pyqt6-webengine stem
if errorlevel 1 goto :ERROR_DEPS
"%UV_CMD%" run -m ultrabrowser.main
if errorlevel 1 goto :ERROR
goto :END

:CHECK_PYTHON
echo [ADVERTENCIA] uv no encontrado en el PATH.
echo [INFO] Iniciando modo de auto-preparacion...

where python >nul 2>nul
if errorlevel 1 goto :NO_PYTHON

if exist ".venv\" if not exist ".venv\Scripts\activate.bat" (
    if exist ".venv\bin\activate" (
        echo [ADVERTENCIA] Se detecto un entorno virtual de Linux/WSL en .venv.
    ) else (
        echo [ADVERTENCIA] El entorno virtual .venv no es valido en este sistema.
    )
    echo [INFO] Rehaciendo el entorno virtual para Windows...
    ren ".venv" ".venv.wsl.bak"
)

if not exist ".venv\" (
    echo [INFO] Creando entorno virtual (.venv)...
    python -m venv ".venv"
    if errorlevel 1 goto :ERROR_VENV
)

if exist ".venv\Scripts\activate.bat" (
    echo [INFO] Activando entorno virtual...
    call ".venv\Scripts\activate.bat"
    
    echo [INFO] Instalando uv dentro del entorno virtual...
    python -m pip install --upgrade uv
    if errorlevel 1 goto :ERROR_UV

    echo [INFO] Verificando e instalando dependencias con uv...
    uv pip install pyqt6 pyqt6-webengine stem
    if errorlevel 1 goto :ERROR_DEPS

    echo [INFO] Ejecutando UltraBrowser...
    uv run -m ultrabrowser.main
    if errorlevel 1 goto :ERROR
    goto :END
) else (
    echo [ERROR] No se pudo encontrar el script de activacion del entorno virtual.
    goto :ERROR_PAUSE
)

:NO_PYTHON
echo [ADVERTENCIA] Python no encontrado. Intentando instalar...
where winget >nul 2>nul
if errorlevel 1 goto :NO_PYTHON_FINAL
winget install -e --id Python.Python.3.12
where python >nul 2>nul
if not errorlevel 1 goto :CHECK_PYTHON

:NO_PYTHON_FINAL
echo [ERROR] Python no encontrado. Por favor instala Python 3.12+ o uv.
echo https://www.python.org/downloads/
goto :ERROR_PAUSE

:ERROR_VENV
echo [ERROR] Fallo al crear el entorno virtual.
goto :ERROR_PAUSE

:ERROR_UV
echo [ERROR] Fallo al instalar uv en el entorno virtual.
goto :ERROR_PAUSE

:ERROR_DEPS
echo [ERROR] Fallo al instalar dependencias con uv.
goto :ERROR_PAUSE

:ERROR
echo [ERROR] Error al ejecutar la aplicacion.
:ERROR_PAUSE
pause
exit /b 1

:END
echo [INFO] Aplicacion finalizada.
pause
