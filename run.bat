@echo off
setlocal
cd /d "%~dp0"
REM Script para ejecutar UltraBrowser en Windows
REM Intenta usar uv primero (gestiona venv+deps automáticamente),
REM si no, cae a Python puro con venv manual.

set "UV_CMD=uv"
set "PIP_DEPS="pyqt6>=6.10.2" "pyqt6-webengine>=6.10.0" "stem>=1.8.2""

set "DIAG_RUNNER="
set "DIAG_ARGS="

where uv >nul 2>nul
if not errorlevel 1 goto :RUN_UV

REM uv no encontrado: intentar instalarlo
echo [ADVERTENCIA] uv no encontrado en el PATH. Intentando instalar uv...
powershell -NoProfile -ExecutionPolicy Bypass -Command "iwr -useb https://astral.sh/uv/install.ps1 | iex"
set "PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%"

where uv >nul 2>nul
if not errorlevel 1 goto :RUN_UV

if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV_CMD=%USERPROFILE%\.local\bin\uv.exe"
if exist "%USERPROFILE%\.cargo\bin\uv.exe" set "UV_CMD=%USERPROFILE%\.cargo\bin\uv.exe"

"%UV_CMD%" --version >nul 2>nul
if not errorlevel 1 goto :RUN_UV

goto :CHECK_PYTHON

:RUN_UV
echo [INFO] uv detectado. Sincronizando entorno y dependencias...
set "DIAG_RUNNER=%UV_CMD%"
set "DIAG_ARGS=run python"
REM 'uv sync' crea el .venv si no existe y lee las deps de pyproject.toml
"%UV_CMD%" sync
if errorlevel 1 (
    echo [ADVERTENCIA] uv sync fallo. Intentando instalar dependencias directamente...
    "%UV_CMD%" venv
    "%UV_CMD%" pip install %PIP_DEPS%
    if errorlevel 1 goto :ERROR_DEPS
)
echo [INFO] Ejecutando UltraBrowser...
"%UV_CMD%" run python -m ultrabrowser.main
if errorlevel 1 goto :ERROR
goto :END

:CHECK_PYTHON
echo [ADVERTENCIA] uv no disponible. Usando Python con entorno virtual manual...

where python >nul 2>nul
if errorlevel 1 goto :NO_PYTHON

REM Detectar y limpiar venv incompatible (de Linux/WSL)
if exist ".venv\" if not exist ".venv\Scripts\activate.bat" (
    if exist ".venv\bin\activate" (
        echo [ADVERTENCIA] Se detecto un entorno virtual de Linux/WSL en .venv.
    ) else (
        echo [ADVERTENCIA] El entorno virtual .venv no es valido en este sistema.
    )
    echo [INFO] Rehaciendo el entorno virtual para Windows...
    ren ".venv" ".venv.wsl.bak"
)

REM Crear venv si no existe
if not exist ".venv\" (
    echo [INFO] Creando entorno virtual (.venv)...
    python -m venv ".venv"
    if errorlevel 1 goto :ERROR_VENV
)

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] No se pudo encontrar el script de activacion del entorno virtual.
    goto :ERROR_PAUSE
)

echo [INFO] Activando entorno virtual...
call ".venv\Scripts\activate.bat"
set "DIAG_RUNNER=python"
set "DIAG_ARGS="

echo [INFO] Actualizando pip...
python -m pip install --upgrade pip --quiet

echo [INFO] Instalando dependencias...
python -m pip install %PIP_DEPS% --quiet
if errorlevel 1 goto :ERROR_DEPS

echo [INFO] Ejecutando UltraBrowser...
python -m ultrabrowser.main
if errorlevel 1 goto :ERROR
goto :END

:NO_PYTHON
echo [ADVERTENCIA] Python no encontrado. Intentando instalar con winget...
where winget >nul 2>nul
if errorlevel 1 goto :NO_PYTHON_FINAL
winget install -e --id Python.Python.3.12
where python >nul 2>nul
if not errorlevel 1 goto :CHECK_PYTHON

:NO_PYTHON_FINAL
echo [ERROR] Python no encontrado. Por favor instala Python 3.12+ desde:
echo         https://www.python.org/downloads/
echo         O instala uv desde: https://docs.astral.sh/uv/
goto :ERROR_PAUSE

:ERROR_VENV
echo [ERROR] Fallo al crear el entorno virtual.
goto :ERROR_PAUSE

:ERROR_DEPS
echo [ERROR] Fallo al instalar dependencias.
echo         Prueba manualmente: python -m pip install %PIP_DEPS%
goto :ERROR_PAUSE

:ERROR
call :OPEN_DIAGNOSTICS
echo [ERROR] Error al ejecutar la aplicacion.
echo         Revisa los logs o ejecuta con: python -m ultrabrowser.main

:ERROR_PAUSE
pause
exit /b 1

:OPEN_DIAGNOSTICS
if not defined DIAG_RUNNER goto :EOF

set "OPEN_DIAGNOSTICS="
for /f "usebackq delims=" %%I in (`%DIAG_RUNNER% %DIAG_ARGS% -m ultrabrowser.diagnostics --print-open-on-failure 2^>nul`) do set "OPEN_DIAGNOSTICS=%%I"
if /I not "%OPEN_DIAGNOSTICS%"=="1" goto :EOF

set "DIAG_DIR="
for /f "usebackq delims=" %%I in (`%DIAG_RUNNER% %DIAG_ARGS% -m ultrabrowser.diagnostics --print-log-dir 2^>nul`) do set "DIAG_DIR=%%I"
if not defined DIAG_DIR goto :EOF
if not exist "%DIAG_DIR%" goto :EOF

echo [INFO] Abriendo carpeta de diagnostico: %DIAG_DIR%
start "" explorer "%DIAG_DIR%"
goto :EOF

:END
exit /b 0
