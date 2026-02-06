
# UltraBrowser

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/TiiZss/UltraBrowser)](https://github.com/TiiZss/UltraBrowser/blob/main/LICENSE)
[![Release](https://img.shields.io/github/v/release/TiiZss/UltraBrowser)](https://github.com/TiiZss/UltraBrowser/releases)
![Version](https://img.shields.io/badge/version-v0.3.0-brightgreen)
![UV](https://img.shields.io/badge/uv-fast-purple)
![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?style=flat&logo=buy-me-a-coffee&logoColor=black)

**UltraBrowser** es un navegador web de escritorio ultra-ligero y seguro, diseñado para proporcionar anonimato y control total sobre la privacidad del hardware.

## Descripción

UltraBrowser está construido con **Python 3.12+** y **PyQt6**, enfocado en la privacidad extrema. Integra la red Tor de forma nativa (**Portable**, sin instalaciones extra) y ofrece controles de hardware granulares para bloquear físicamente (vía software) el acceso a la cámara y el micrófono.

## Características Principales

### 🔒 Privacidad y Seguridad
*   **Modo Tor Nativo**: Interruptor global para enrutar todo el tráfico a través de la red Tor.
*   **Gestión de Hardware**: Toggles para habilitar/deshabilitar cámara y micrófono. Bloqueo estricto por defecto.
*   **Navegación "Off-the-record"**: Sin historial, caché en RAM, sin cookies persistentes.
*   **Anti-Fingerprinting**: Rotación de User-Agents y bloqueo de WebRTC.

### 🚀 Stack Tecnológico
*   **Core**: Python 3.12+
*   **GUI**: PyQt6
*   **Engine**: PyQt6-WebEngine (Chromium-based)
*   **Tor Control**: stem

## Funcionalidades
*   **Navegación por Pestañas**: Soporte completo para múltiples pestañas con atajos (Ctrl+T, Ctrl+W).
*   **Privacidad Global**: Los interruptores de privacidad controlan todas las pestañas simultáneamente.


## Instalación y Ejecución

Es necesario tener instalado [Python 3.12+](https://www.python.org/). **Tor ya viene incluido** en el proyecto (Portable).

### Windows
```cmd
run.bat
```
o
```powershell
.\run.ps1
```

### Linux / macOS
```bash
./run.sh
```

Los scripts de ejecución se encargarán automáticamente de crear el entorno virtual e instalar las dependencias si no existen.

## Estructura del Proyecto

*   `ultrabrowser/`: Código fuente del paquete.
*   `bin/`: Binarios portables de Tor (Windows/Linux/Mac).
*   `docs/`: Documentación y auditorías de seguridad.
*   `run.*`: Scripts de lanzamiento automático.

---
Desarrollado con ❤️ por [TiiZss](https://github.com/TiiZss).
