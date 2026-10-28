# UltraBrowser — borrador de producto

Fecha: 2026-10-28. El modo por defecto está cerrado.

## Para quién

Una persona en Windows que quiere abrir un icono y navegar como en un navegador normal, con menos rastro local y con un modo Tor cuando lo pida. No hay usuarios medidos ni métrica de retención.

## Qué es hoy

Carcasa PyQt6 sobre Qt WebEngine (Chromium), unas 2.000 líneas. Hay atrás, adelante, recargar, pestañas, barra de direcciones, búsqueda en DuckDuckGo, pantalla completa, forzado HTTPS, perfil sin escritura de historial en disco, bloqueo de cámara y micrófono, lista fija de dominios en `ad_blocker.py`, un script que falsea WebGL y otras APIs, rotación de User-Agent cada 30 minutos, e interruptor Tor con nueva identidad.

No hay ajustes en una ventana, ni extensiones, ni contraseñas, ni historial de navegación en disco. Buscar, zoom, descargas de la sesión y reabrir pestaña cerrada están en la rama de usabilidad. Los marcadores van a un fichero de runtime, no al perfil web.

## Qué no se puede prometer a la vez

- Ultrarrápido y Tor encendido. El circuito Tor añade saltos. El modo rápido es Chromium directo.
- Lo más anónimo posible y, a la vez, contraseñas, sincronización, historial y extensiones. Eso es un perfil persistente identificable.
- La rotación de User-Agent no acerca al anonimato. Un navegador anónimo se parece al resto de usuarios del mismo modo. Cambiar el agente cada 30 minutos hace el cliente más raro. En modo Tor hay que pararla.
- El script de WebGL fijo (`Intel Inc.` / `Intel Iris`) también destaca si casi nadie más lo envía.
- La seguridad de un navegador estándar es el motor al día. Empaquetar un Qt WebEngine congelado sin canal de actualización envejece el Chromium de dentro.

## Fuera de alcance

Fork de Firefox, reescritura en Rust, tienda de extensiones, cuentas, sincronización y telemetría.

## Si se construye, el primer corte

Sobre esta carcasa, en este orden:

1. Descargas visibles, buscar en la página, zoom y reabrir la pestaña cerrada solo en memoria.
2. Marcadores en un fichero local, separados del perfil de navegación.
3. En modo Tor: sin rotación de User-Agent y sin arrastrar la sesión del modo diario.
4. Instalador de Windows con icono, cuando esas piezas existan.
5. Forma de actualizar el motor. Sin eso, el adjetivo «seguro» caduca en la primera CVE de Chromium.

## Decisión

El doble clic abre el modo diario, rápido y sin Tor. Tor se enciende solo con el interruptor.

Eso ya es el arranque actual. `tor_toggle` nace desmarcado y `launch_tor` no se llama al crear la ventana.

El corte de usabilidad de sesión está en `docs/plans/usabilidad-sesion.md`. Los marcadores locales están en `docs/plans/marcadores.md`. Siguen pendientes el modo Tor sin rotación de User-Agent, el instalador y la actualización del motor.
