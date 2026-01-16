#!/bin/bash
# Script para ejecutar UltraBrowser en Linux/macOS
# Se intenta usar uv primero

if command -v uv &> /dev/null; then
    echo "[INFO] uv detectado. Ejecutando con 'uv run'..."
    uv run -m ultrabrowser.main
    if [ $? -ne 0 ]; then
        echo "[ERROR] Fallo al ejecutar con uv."
        read -p "Presiona Enter para salir"
        exit 1
    fi
else
    echo "[ADVERTENCIA] uv no encontrado. Iniciando modo de auto-preparacion..."
    
    # Check for python3 or python
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo "[ERROR] Python no encontrado. Por favor instala Python 3.12+ o uv."
        read -p "Presiona Enter para salir"
        exit 1
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
        
        echo "[INFO] Verificando e instalando dependencias..."
        pip install pyqt6 pyqt6-webengine stem
        if [ $? -ne 0 ]; then
            echo "[ERROR] Fallo al instalar las dependencias."
            read -p "Presiona Enter para salir"
            exit 1
        fi
        
        echo "[INFO] Ejecutando UltraBrowser..."
        python -m ultrabrowser.main
    else
        echo "[ERROR] No se pudo encontrar el script de activacion del entorno virtual."
        read -p "Presiona Enter para salir"
        exit 1
    fi
fi

if [ $? -ne 0 ]; then
    echo "Error al ejecutar la aplicacion"
    read -p "Presiona Enter para salir"
    exit 1
fi

read -p "Presiona Enter para salir"
