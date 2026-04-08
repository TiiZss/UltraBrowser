# Script PowerShell para ejecutar UltraBrowser en Windows
# Gestiona el entorno virtual y dependencias automáticamente

$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

$uvCmd = "uv"
$pythonDependencies = @(
    "pyqt6>=6.10.2",
    "pyqt6-webengine>=6.10.0",
    "stem>=1.8.2"
)
$pythonDependenciesHint = $pythonDependencies -join " "

function Open-DiagnosticsFolder {
    param(
        [string]$PythonRunner,
        [string[]]$RunnerArgs = @()
    )

    try {
        $shouldOpen = & $PythonRunner @RunnerArgs -m ultrabrowser.diagnostics --print-open-on-failure 2>$null
        if ($LASTEXITCODE -ne 0 -or $shouldOpen.Trim() -ne "1") {
            return
        }

        $diagnosticsDir = & $PythonRunner @RunnerArgs -m ultrabrowser.diagnostics --print-log-dir 2>$null
        if ($LASTEXITCODE -ne 0) {
            return
        }

        $diagnosticsDir = $diagnosticsDir.Trim()
        if ($diagnosticsDir -and (Test-Path $diagnosticsDir)) {
            Write-Host "[INFO] Abriendo carpeta de diagnostico: $diagnosticsDir" -ForegroundColor Yellow
            Start-Process explorer.exe $diagnosticsDir
        }
    }
    catch {
        Write-Host "[ADVERTENCIA] No se pudo abrir la carpeta de diagnostico." -ForegroundColor Yellow
    }
}

# Buscar uv en el PATH
if (-not (Get-Command "uv" -ErrorAction SilentlyContinue)) {
    Write-Host "[ADVERTENCIA] uv no encontrado en el PATH. Intentando instalar uv..." -ForegroundColor Yellow
    try {
        Invoke-WebRequest -UseBasicParsing https://astral.sh/uv/install.ps1 | Invoke-Expression
    }
    catch {
        Write-Host "[ADVERTENCIA] Fallo al instalar uv con el instalador oficial." -ForegroundColor Yellow
    }

    $env:PATH = "$HOME\.local\bin;$HOME\.cargo\bin;$env:PATH"

    if (-not (Get-Command "uv" -ErrorAction SilentlyContinue)) {
        if (Test-Path "$HOME\.local\bin\uv.exe")    { $uvCmd = "$HOME\.local\bin\uv.exe" }
        elseif (Test-Path "$HOME\.cargo\bin\uv.exe") { $uvCmd = "$HOME\.cargo\bin\uv.exe" }
    }
}

# ── Rama principal: uv disponible ─────────────────────────────────────────────
if (Get-Command $uvCmd -ErrorAction SilentlyContinue) {
    Write-Host "[INFO] uv detectado. Sincronizando entorno y dependencias..." -ForegroundColor Cyan

    & $uvCmd sync
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ADVERTENCIA] uv sync fallo. Intentando crear venv manualmente..." -ForegroundColor Yellow
        & $uvCmd venv
        & $uvCmd pip install @pythonDependencies
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] Fallo al instalar dependencias con uv." -ForegroundColor Red
            Read-Host "Presiona Enter para salir"
            exit 1
        }
    }

    Write-Host "[INFO] Ejecutando UltraBrowser..." -ForegroundColor Green
    & $uvCmd run python -m ultrabrowser.main
    if ($LASTEXITCODE -ne 0) {
        Open-DiagnosticsFolder -PythonRunner $uvCmd -RunnerArgs @("run", "python")
        Write-Host "[ERROR] Fallo al ejecutar UltraBrowser." -ForegroundColor Red
        Read-Host "Presiona Enter para salir"
        exit 1
    }
}
# ── Fallback: Python puro con venv manual ─────────────────────────────────────
else {
    Write-Host "[ADVERTENCIA] uv no disponible. Usando Python con venv manual..." -ForegroundColor Yellow

    if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
        Write-Host "[ADVERTENCIA] Python no encontrado. Intentando instalar con winget..." -ForegroundColor Yellow
        if (Get-Command "winget" -ErrorAction SilentlyContinue) {
            winget install -e --id Python.Python.3.12
        }
        if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
            Write-Host "[ERROR] Python no encontrado. Instala Python 3.12+ desde:" -ForegroundColor Red
            Write-Host "        https://www.python.org/downloads/" -ForegroundColor White
            Write-Host "        O uv desde: https://docs.astral.sh/uv/" -ForegroundColor White
            Read-Host "Presiona Enter para salir"
            exit 1
        }
    }

    if (Test-Path ".\.venv") {
        if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
            if (Test-Path ".\.venv\bin\activate") {
                Write-Host "[ADVERTENCIA] Se detecto un entorno virtual de Linux/WSL en .venv." -ForegroundColor Yellow
            } else {
                Write-Host "[ADVERTENCIA] El entorno virtual .venv no es valido en este sistema." -ForegroundColor Yellow
            }
            Write-Host "[INFO] Rehaciendo el entorno virtual para Windows..." -ForegroundColor Cyan
            Rename-Item -Path ".\.venv" -NewName ".venv.wsl.bak" -Force
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

    if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
        Write-Host "[ERROR] No se encontro el script de activacion del entorno virtual." -ForegroundColor Red
        Read-Host "Presiona Enter para salir"
        exit 1
    }

    Write-Host "[INFO] Activando entorno virtual..." -ForegroundColor Cyan
    & .\.venv\Scripts\Activate.ps1

    Write-Host "[INFO] Actualizando pip..." -ForegroundColor Cyan
    python -m pip install --upgrade pip --quiet

    Write-Host "[INFO] Instalando dependencias..." -ForegroundColor Cyan
    python -m pip install @pythonDependencies --quiet
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Fallo al instalar dependencias." -ForegroundColor Red
        Write-Host "        Prueba manualmente: python -m pip install $pythonDependenciesHint" -ForegroundColor White
        Read-Host "Presiona Enter para salir"
        exit 1
    }

    Write-Host "[INFO] Ejecutando UltraBrowser..." -ForegroundColor Green
    python -m ultrabrowser.main
    if ($LASTEXITCODE -ne 0) {
        Open-DiagnosticsFolder -PythonRunner "python"
        Write-Host "[ERROR] Error al ejecutar UltraBrowser." -ForegroundColor Red
        Read-Host "Presiona Enter para salir"
        exit 1
    }
}

exit 0
