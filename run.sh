#!/usr/bin/env bash
# Script para ejecutar UltraBrowser en Linux/macOS
# Se intenta usar uv primero

UV_CMD="uv"

if ! command -v uv &> /dev/null; then
    echo "[ADVERTENCIA] uv no encontrado en el PATH. Intentando instalar uv..."
    if command -v curl &> /dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif command -v wget &> /dev/null; then
        wget -qO- https://astral.sh/uv/install.sh | sh
    else
        echo "[ERROR] No se encontro curl ni wget para instalar uv."
    fi
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

if command -v uv &> /dev/null; then
    echo "[INFO] uv detectado. Ejecutando con 'uv run'..."
    echo "[INFO] Verificando e instalando dependencias con uv..."
    $UV_CMD pip install pyqt6 pyqt6-webengine stem
    if [ $? -ne 0 ]; then
        echo "[ERROR] Fallo al instalar dependencias con uv."
        read -p "Presiona Enter para salir"
        exit 1
    fi
    $UV_CMD run -m ultrabrowser.main
    if [ $? -ne 0 ]; then
        echo "[ERROR] Fallo al ejecutar con uv."
        read -p "Presiona Enter para salir"
        exit 1
    fi
else
    echo "[ADVERTENCIA] uv no encontrado en el PATH. Iniciando modo de auto-preparacion..."

    # Check for python3 or python
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo "[ADVERTENCIA] Python no encontrado. Intentando instalar..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y python3 python3-venv python3-pip
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y python3 python3-venv python3-pip
        elif command -v yum &> /dev/null; then
            sudo yum install -y python3 python3-venv python3-pip
        elif command -v pacman &> /dev/null; then
            sudo pacman -Syu --noconfirm python python-virtualenv python-pip
        elif command -v apk &> /dev/null; then
            sudo apk add --no-cache python3 py3-virtualenv py3-pip
        else
            echo "[ERROR] No se encontro un gestor de paquetes compatible para instalar Python."
        fi

        if command -v python3 &> /dev/null; then
            PYTHON_CMD="python3"
        elif command -v python &> /dev/null; then
            PYTHON_CMD="python"
        else
            echo "[ERROR] Python no encontrado. Por favor instala Python 3.12+ o uv."
            echo "https://www.python.org/downloads/"
            read -p "Presiona Enter para salir"
            exit 1
        fi
    fi

    if [ -d ".venv" ] && [ ! -f .venv/bin/activate ]; then
        if [ -f .venv/Scripts/activate.bat ]; then
            echo "[ADVERTENCIA] Se detecto un entorno virtual de Windows en .venv."
        else
            echo "[ADVERTENCIA] El entorno virtual .venv no es valido en este sistema."
        fi
        echo "[INFO] Rehaciendo el entorno virtual para WSL..."
        mv .venv .venv.windows.bak 2>/dev/null
    fi

    if [ ! -d ".venv" ]; then
        echo "[INFO] Creando entorno virtual (.venv)..."
        $PYTHON_CMD -m venv .venv
        if [ $? -ne 0 ]; then
            echo "[ERROR] Fallo al crear el entorno virtual."
            read -p "Presiona Enter para salir"
            exit 1
        fi
    fi

    if [ -f .venv/bin/activate ]; then
        echo "[INFO] Activando entorno virtual..."
        source .venv/bin/activate

        echo "[INFO] Instalando uv dentro del entorno virtual..."
        $PYTHON_CMD -m pip install --upgrade uv
        if [ $? -ne 0 ]; then
            echo "[ERROR] Fallo al instalar uv en el entorno virtual."
            read -p "Presiona Enter para salir"
            exit 1
        fi

        echo "[INFO] Verificando e instalando dependencias con uv..."
        uv pip install pyqt6 pyqt6-webengine stem
        if [ $? -ne 0 ]; then
            echo "[ERROR] Fallo al instalar dependencias con uv."
            read -p "Presiona Enter para salir"
            exit 1
        fi

        echo "[INFO] Ejecutando UltraBrowser..."
        uv run -m ultrabrowser.main
    else
        echo "[ERROR] No se pudo encontrar el script de activacion del entorno virtual."
        read -p "Presiona Enter para salir"
        exit 1
    fi
fi

if [ $? -ne 0 ]; then
    echo "[ERROR] Error al ejecutar la aplicacion."
    read -p "Presiona Enter para salir"
    exit 1
fi

read -p "Presiona Enter para salir"
