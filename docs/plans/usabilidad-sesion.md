# Usabilidad de sesión

Fecha: 2026-10-28.

## Aceptación

En el modo diario, sin cambiar Tor, el perfil off-the-record ni el bloqueo de cámara y micrófono:

- Ctrl+F abre una barra de búsqueda en la página activa, con siguiente, anterior y Escape para cerrar.
- Ctrl++ / Ctrl+- / Ctrl+0 cambian el zoom solo de la pestaña activa. No se guarda.
- Una descarga pide ruta con el diálogo del sistema y aparece en un panel de esta sesión, con el estado.
- Ctrl+Shift+T reabre la última pestaña cerrada. Como máximo 10, solo en memoria. Cerrar la última pestaña sigue sin hacer nada.
- Limpiar todo vacía también esa pila.

## Fuera

Marcadores, instalador, canal de actualización, rotación de User-Agent, historial en disco y reescritura del motor.

## Dónde

`BrowserWindow` en `ultrabrowser/browser_engine.py`. La descarga cuelga de `downloadRequested` del perfil que ya crea `create_private_profile`.
