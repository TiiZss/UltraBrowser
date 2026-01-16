# Script PowerShell para ejecutar UltraBrowser en Windows

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Get-Command "uv" -ErrorAction SilentlyContinue) {
    Write-Host "[INFO] uv detectado. Ejecutando con 'uv run'..." -ForegroundColor Cyan
    uv run -m ultrabrowser.main
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Fallo al ejecutar con uv." -ForegroundColor Red
        Read-Host "Presiona Enter para salir"
        exit 1
    }
}
else {
    Write-Host "[ADVERTENCIA] uv no encontrado. Iniciando modo de auto-preparacion..." -ForegroundColor Yellow

    if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
        Write-Host "[ERROR] Python no encontrado. Por favor instala Python 3.12+ o uv." -ForegroundColor Red
        Write-Host "https://www.python.org/downloads/" -ForegroundColor White
        Read-Host "Presiona Enter para salir"
        exit 1
    }

    if (-not (Test-Path ".\.venv")) {
        Write-Host "[INFO] Creando entorno virtual (.venv)..." -ForegroundColor Cyan
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] Fallo al crear el entorno virtual." -ForegroundColor Red
            Read-Host "Presiona Enter para salir"
            exit 1
        }
    }
    
    if (Test-Path ".\.venv\Scripts\Activate.ps1") {
        Write-Host "[INFO] Activando entorno virtual..." -ForegroundColor Cyan
        & .\.venv\Scripts\Activate.ps1
        
        Write-Host "[INFO] Verificando e instalando dependencias..." -ForegroundColor Cyan
        pip install pyqt6 pyqt6-webengine stem
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] Fallo al instalar las dependencias." -ForegroundColor Red
            Read-Host "Presiona Enter para salir"
            exit 1
        }
        
        Write-Host "[INFO] Ejecutando UltraBrowser..." -ForegroundColor Green
        python -m ultrabrowser.main
    }
    else {
        Write-Host "[ERROR] No se pudo encontrar el script de activacion del entorno virtual." -ForegroundColor Red
        Read-Host "Presiona Enter para salir"
        exit 1
    }
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error al ejecutar la aplicacion" -ForegroundColor Red
    Read-Host "Presiona Enter para salir"
    exit 1
}

Read-Host "Presiona Enter para salir"
