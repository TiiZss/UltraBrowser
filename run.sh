#!/usr/bin/env bash
# Script para ejecutar UltraBrowser en Linux/macOS
# Gestiona el entorno virtual y dependencias automáticamente

set -euo pipefail
cd "$(dirname "$0")"

UV_CMD="uv"

# Buscar uv en el PATH, intentar instalarlo si no está
if ! command -v uv &>/dev/null; then
    echo "[ADVERTENCIA] uv no encontrado en el PATH. Intentando instalar uv..."
    if command -v curl &>/dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh || true
    elif command -v wget &>/dev/null; then
        wget -qO- https://astral.sh/uv/install.sh | sh || true
    else
        echo "[ADVERTENCIA] No se encontro curl ni wget para instalar uv."
    fi
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

# ── Rama principal: uv disponible ─────────────────────────────────────────────
if command -v uv &>/dev/null; then
    echo "[INFO] uv detectado. Sincronizando entorno y dependencias..."

    # 'uv sync' crea el .venv si no existe y lee las deps de pyproject.toml
    if ! uv sync; then
        echo "[ADVERTENCIA] uv sync fallo. Intentando crear venv manualmente..."
        uv venv || true
        uv pip install pyqt6 pyqt6-webengine stem
    fi

    echo "[INFO] Ejecutando UltraBrowser..."
    uv run python -m ultrabrowser.main

# ── Fallback: Python puro con venv manual ─────────────────────────────────────
else
    echo "[ADVERTENCIA] uv no disponible. Usando Python con venv manual..."

    # Detectar comando de Python disponible
    if command -v python3 &>/dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &>/dev/null; then
        PYTHON_CMD="python"
    else
        echo "[ADVERTENCIA] Python no encontrado. Intentando instalar..."
        if command -v apt-get &>/dev/null; then
            sudo apt-get update -q
            sudo apt-get install -y python3 python3-venv python3-pip
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y python3 python3-venv python3-pip
        elif command -v pacman &>/dev/null; then
            sudo pacman -Syu --noconfirm python python-virtualenv python-pip
        elif command -v brew &>/dev/null; then
            brew install python
        else
            echo "[ERROR] No se encontro un gestor de paquetes para instalar Python."
            echo "        Instala Python 3.12+ desde: https://www.python.org/downloads/"
            echo "        O uv desde: https://docs.astral.sh/uv/"
            read -rp "Presiona Enter para salir"
            exit 1
        fi

        if command -v python3 &>/dev/null; then
            PYTHON_CMD="python3"
        elif command -v python &>/dev/null; then
            PYTHON_CMD="python"
        else
            echo "[ERROR] Python no encontrado tras instalación."
            read -rp "Presiona Enter para salir"
            exit 1
        fi
    fi

    # Detectar y limpiar venv incompatible (de Windows)
    if [ -d ".venv" ] && [ ! -f ".venv/bin/activate" ]; then
        if [ -f ".venv/Scripts/activate.bat" ]; then
            echo "[ADVERTENCIA] Se detecto un entorno virtual de Windows en .venv."
        else
            echo "[ADVERTENCIA] El entorno virtual .venv no es valido en este sistema."
        fi
        echo "[INFO] Rehaciendo el entorno virtual para Linux/macOS..."
        mv .venv .venv.windows.bak 2>/dev/null || true
    fi

    # Crear venv si no existe
    if [ ! -d ".venv" ]; then
        echo "[INFO] Creando entorno virtual (.venv)..."
        $PYTHON_CMD -m venv .venv
    fi

    if [ ! -f ".venv/bin/activate" ]; then
        echo "[ERROR] No se pudo encontrar el script de activacion del entorno virtual."
        read -rp "Presiona Enter para salir"
        exit 1
    fi

    echo "[INFO] Activando entorno virtual..."
    # shellcheck disable=SC1091
    source .venv/bin/activate

    echo "[INFO] Actualizando pip..."
    pip install --upgrade pip --quiet

    echo "[INFO] Instalando dependencias..."
    pip install pyqt6 pyqt6-webengine stem --quiet
    if [ $? -ne 0 ]; then
        echo "[ERROR] Fallo al instalar dependencias."
        echo "        Prueba manualmente: pip install pyqt6 pyqt6-webengine stem"
        read -rp "Presiona Enter para salir"
        exit 1
    fi

    echo "[INFO] Ejecutando UltraBrowser..."
    python -m ultrabrowser.main
fi

exit 0
