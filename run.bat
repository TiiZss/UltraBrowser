@echo off
REM Script para ejecutar UltraBrowser en Windows
REM Intenta usar uv primero para gestionar el entorno y las dependencias

where uv >nul 2>nul
if %errorlevel% equ 0 (
    echo [INFO] uv detectado. Ejecutando con 'uv run'...
    uv run -m ultrabrowser.main
    if errorlevel 1 (
        echo [ERROR] Fallo al ejecutar con uv.
        pause
        exit /b 1
    )
) else (
    echo [ADVERTENCIA] uv no encontrado en el PATH.
    echo [INFO] Iniciando modo de auto-preparacion...

    where python >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ERROR] Python no encontrado. Por favor instala Python 3.12+ o uv.
        echo https://www.python.org/downloads/
        pause
        exit /b 1
    )
    
    if not exist .venv (
        echo [INFO] Creando entorno virtual (.venv)...
        python -m venv .venv
        if errorlevel 1 (
            echo [ERROR] Fallo al crear el entorno virtual.
            pause
            exit /b 1
        )
    )

    if exist .venv\Scripts\activate.bat (
        echo [INFO] Activando entorno virtual...
        call .venv\Scripts\activate.bat
        
        echo [INFO] Verificando e instalando dependencias...
        pip install pyqt6 pyqt6-webengine stem
        if errorlevel 1 (
            echo [ERROR] Fallo al instalar las dependencias.
            pause
            exit /b 1
        )

        echo [INFO] Ejecutando UltraBrowser...
        python -m ultrabrowser.main
    ) else (
        echo [ERROR] No se pudo encontrar el script de activacion del entorno virtual.
        pause
        exit /b 1
    )
)

if errorlevel 1 (
    echo [ERROR] La aplicacion cerro con errores.
    pause
    exit /b 1
)

echo [INFO] Aplicacion finalizada.
pause
