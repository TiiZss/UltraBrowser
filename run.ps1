# Script PowerShell para ejecutar UltraBrowser en Windows

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$uvCmd = "uv"

if (-not (Get-Command "uv" -ErrorAction SilentlyContinue)) {
    Write-Host "[ADVERTENCIA] uv no encontrado en el PATH. Intentando instalar uv..." -ForegroundColor Yellow
    try {
        Invoke-WebRequest -UseBasicParsing https://astral.sh/uv/install.ps1 | Invoke-Expression
    }
    catch {
        Write-Host "[ERROR] Fallo al instalar uv con el instalador oficial." -ForegroundColor Red
    }

    $env:PATH = "$HOME\.local\bin;$HOME\.cargo\bin;$env:PATH"

    if (-not (Get-Command "uv" -ErrorAction SilentlyContinue)) {
        if (Test-Path "$HOME\.local\bin\uv.exe") {
            $uvCmd = "$HOME\.local\bin\uv.exe"
        }
        elseif (Test-Path "$HOME\.cargo\bin\uv.exe") {
            $uvCmd = "$HOME\.cargo\bin\uv.exe"
        }
    }
}

if (Get-Command $uvCmd -ErrorAction SilentlyContinue) {
    Write-Host "[INFO] uv detectado. Ejecutando con 'uv run'..." -ForegroundColor Cyan
    Write-Host "[INFO] Verificando e instalando dependencias con uv..." -ForegroundColor Cyan
    & $uvCmd pip install pyqt6 pyqt6-webengine stem
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Fallo al instalar dependencias con uv." -ForegroundColor Red
        Read-Host "Presiona Enter para salir"
        exit 1
    }
    & $uvCmd run -m ultrabrowser.main
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Fallo al ejecutar con uv." -ForegroundColor Red
        Read-Host "Presiona Enter para salir"
        exit 1
    }
}
else {
    Write-Host "[ADVERTENCIA] uv no encontrado en el PATH. Iniciando modo de auto-preparacion..." -ForegroundColor Yellow

    if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
        Write-Host "[ADVERTENCIA] Python no encontrado. Intentando instalar..." -ForegroundColor Yellow
        if (Get-Command "winget" -ErrorAction SilentlyContinue) {
            winget install -e --id Python.Python.3.12
        }
        else {
            Write-Host "[ERROR] winget no encontrado para instalar Python." -ForegroundColor Red
        }

        if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
            Write-Host "[ERROR] Python no encontrado. Por favor instala Python 3.12+ o uv." -ForegroundColor Red
            Write-Host "https://www.python.org/downloads/" -ForegroundColor White
            Read-Host "Presiona Enter para salir"
            exit 1
        }
    }

    if (Test-Path ".\.venv") {
        if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
            if (Test-Path ".\.venv\bin\activate") {
                Write-Host "[ADVERTENCIA] Se detecto un entorno virtual de Linux/WSL en .venv." -ForegroundColor Yellow
            }
            else {
                Write-Host "[ADVERTENCIA] El entorno virtual .venv no es valido en este sistema." -ForegroundColor Yellow
            }
            Write-Host "[INFO] Rehaciendo el entorno virtual para Windows..." -ForegroundColor Cyan
            Rename-Item -Path ".\.venv" -NewName ".venv.wsl.bak"
        }
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
        
        Write-Host "[INFO] Instalando uv dentro del entorno virtual..." -ForegroundColor Cyan
        python -m pip install --upgrade uv
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] Fallo al instalar uv en el entorno virtual." -ForegroundColor Red
            Read-Host "Presiona Enter para salir"
            exit 1
        }

        Write-Host "[INFO] Verificando e instalando dependencias con uv..." -ForegroundColor Cyan
        $uvCmd = "uv"
        & $uvCmd pip install pyqt6 pyqt6-webengine stem
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] Fallo al instalar dependencias con uv." -ForegroundColor Red
            Read-Host "Presiona Enter para salir"
            exit 1
        }
        
        Write-Host "[INFO] Ejecutando UltraBrowser..." -ForegroundColor Green
        & $uvCmd run -m ultrabrowser.main
    }
    else {
        Write-Host "[ERROR] No se pudo encontrar el script de activacion del entorno virtual." -ForegroundColor Red
        Read-Host "Presiona Enter para salir"
        exit 1
    }
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Error al ejecutar la aplicacion." -ForegroundColor Red
    Read-Host "Presiona Enter para salir"
    exit 1
}

Read-Host "Presiona Enter para salir"
