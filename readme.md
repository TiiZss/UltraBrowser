
# UltraBrowser

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/TiiZss/UltraBrowser)](https://github.com/TiiZss/UltraBrowser/blob/main/LICENSE)
[![Release](https://img.shields.io/github/v/release/TiiZss/UltraBrowser)](https://github.com/TiiZss/UltraBrowser/releases)
![Release Date](https://img.shields.io/github/release-date/TiiZss/UltraBrowser)
![Downloads](https://img.shields.io/github/downloads/TiiZss/UltraBrowser/total)
![Version](https://img.shields.io/badge/version-v0.4.0-brightgreen)
![UV](https://img.shields.io/badge/uv-fast-purple)
![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?style=flat&logo=buy-me-a-coffee&logoColor=black)

**UltraBrowser** es un navegador web de escritorio ultra-ligero y seguro, diseñado para proporcionar anonimato y control total sobre la privacidad del hardware.

## Descripción

UltraBrowser está construido con **Python 3.12+** y **PyQt6**, enfocado en la privacidad extrema. Integra la red Tor de forma nativa (**Portable**, sin instalaciones extra), bloquea anuncios y rastreadores a nivel de red, aplica protecciones anti-fingerprinting y ofrece controles de hardware granulares para bloquear físicamente (vía software) el acceso a la cámara y el micrófono.

## Características Principales

### 🔒 Privacidad y Seguridad
- **Modo Tor Nativo**: Interruptor global para enrutar todo el tráfico a través de la red Tor. La conexión se establece en segundo plano sin bloquear la interfaz.
- **Bloqueador de Anuncios y Rastreadores**: Bloqueo a nivel de red de más de 100 dominios publicitarios y de rastreo conocidos (Google Ads, Doubleclick, Taboola, Facebook Pixel, Hotjar, Criteo...). Las páginas mantienen su funcionalidad completa.
- **Perfil Off-the-record Real**: Sin historial, sin caché en disco, sin cookies persistentes. Nada se escribe en disco durante la sesión.
- **Anti-Fingerprinting**:
  - Rotación automática de User-Agent cada 30 minutos (configurable).
  - Script inyectado en cada página que enmascara WebGL, deshabilita la Battery API y estandariza parámetros de hardware.
  - Bloqueo de WebRTC para prevenir fugas de IP local.
- **Gestión de Hardware**: Toggles para habilitar/deshabilitar cámara y micrófono. Bloqueo estricto por defecto.
- **Forzado HTTPS**: Redirección automática de HTTP a HTTPS con protección anti-loop.

### 🚀 Stack Tecnológico
- **Core**: Python 3.12+
- **GUI**: PyQt6
- **Engine**: PyQt6-WebEngine (Chromium-based)
- **Tor Control**: stem
- **Gestor de entorno**: uv

## Funcionalidades

- **Navegación por Pestañas**: Soporte completo para múltiples pestañas con atajos (`Ctrl+T`, `Ctrl+W`).
- **Privacidad Global**: Los interruptores de privacidad (Tor, AdBlock, cámara, micrófono) controlan todas las pestañas simultáneamente.
- **Limpieza Rápida**: Botón para borrar caché, cookies y datos de sesión de todas las pestañas de una sola vez (`Ctrl+Shift+Del`).
- **Nueva Identidad Tor**: Solicita un nuevo circuito Tor (nueva IP) sin necesidad de desconectar.
- **Búsqueda Integrada**: Las búsquedas desde la barra de direcciones van a DuckDuckGo automáticamente.

## Instalación y Ejecución

No se requieren instalaciones extra. **Tor ya viene incluido** en el proyecto (Portable). Solo necesitas [Python 3.12+](https://www.python.org/) o [uv](https://docs.astral.sh/uv/).

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
chmod +x run.sh
./run.sh
```

Los scripts de ejecución se encargan automáticamente de crear el entorno virtual e instalar las dependencias. La ventana de terminal se cierra sola al salir del navegador.

## Configuración

Edita `config/config.json` para personalizar el comportamiento:

```json
{
  "block_ads": true,
  "force_https": true,
  "rotate_user_agent": true,
  "user_agent_rotation_interval": 30,
  "default_homepage": "https://www.duckduckgo.com",
  "debug_mode": false,
  "log_file": null
}
```

> **Nota de privacidad**: `log_file` es `null` por defecto. Activarlo escribe datos de navegación en disco — úsalo solo para depuración.

## Estructura del Proyecto

```
UltraBrowser/
├── ultrabrowser/
│   ├── main.py            # Punto de entrada
│   ├── browser_engine.py  # Motor del navegador y ventana principal
│   ├── tor_logic.py       # Gestión de Tor (SOCKS5, control, identidad)
│   ├── ad_blocker.py      # Bloqueador de anuncios y rastreadores
│   ├── config.py          # Sistema de configuración
│   ├── exceptions.py      # Excepciones personalizadas
│   └── logging_config.py  # Sistema de logging
├── config/
│   ├── config.json        # Configuración principal
│   └── user_agents.json   # Lista de User-Agents para rotación
├── bin/
│   ├── windows/Tor/       # Binario Tor portátil para Windows
│   ├── linux/Tor/         # Binario Tor portátil para Linux
│   └── macos/Tor/         # Binario Tor portátil para macOS
├── run.bat                # Lanzador Windows (cmd)
├── run.ps1                # Lanzador Windows (PowerShell)
├── run.sh                 # Lanzador Linux/macOS
└── SECURITY_AUDIT.md      # Auditoría de seguridad detallada
```

## Atajos de Teclado

| Atajo | Acción |
|---|---|
| `Ctrl+T` | Nueva pestaña |
| `Ctrl+W` | Cerrar pestaña activa |
| `Ctrl+L` | Foco en la barra de direcciones |
| `Ctrl+Shift+Del` | Limpiar todos los datos |
| `F5` | Recargar página |
| `Alt+←` | Atrás |
| `Alt+→` | Adelante |

---
Desarrollado con ❤️ por [TiiZss](https://github.com/TiiZss).
