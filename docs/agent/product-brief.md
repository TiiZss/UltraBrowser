# UltraBrowser — borrador de producto

Fecha: 2026-10-28. El modo por defecto está cerrado.

## Para quién

Una persona en Windows que quiere abrir un icono y navegar como en un navegador normal, con menos rastro local y con un modo Tor cuando lo pida. No hay usuarios medidos ni métrica de retención.

## Qué es hoy

Carcasa PyQt6 sobre Qt WebEngine (Chromium). Hay atrás, adelante, recargar, pestañas, barra de direcciones, búsqueda en DuckDuckGo, pantalla completa, forzado HTTPS, perfil sin historial en disco, bloqueo de cámara y micrófono, lista fija de dominios, un script que falsea WebGL, rotación de User-Agent cada 30 minutos e interruptor Tor. Desde la 0.6.0 también hay búsqueda en la página, zoom por pestaña, descargas de la sesión, reabrir pestaña en memoria y marcadores en el directorio de runtime. Con Tor encendido la rotación del User-Agent se pausa.

No hay ajustes en una ventana, ni extensiones, ni contraseñas, ni historial de navegación en disco.

## Qué no se puede prometer a la vez

- Ultrarrápido y Tor encendido. El circuito Tor añade saltos. El modo rápido es Chromium directo.
- Lo más anónimo posible y, a la vez, contraseñas, sincronización, historial y extensiones. Eso es un perfil persistente identificable.
- La rotación de User-Agent no acerca al anonimato. Un navegador anónimo se parece al resto de usuarios del mismo modo. Cambiar el agente cada 30 minutos hace el cliente más raro. Con Tor encendido el temporizador ya se detiene. El agente que había en ese momento sigue siendo el de la sesión diaria.
- El script de WebGL fijo (`Intel Inc.` / `Intel Iris`) también destaca si casi nadie más lo envía.
- La seguridad de un navegador estándar es el motor al día. Empaquetar un Qt WebEngine congelado sin canal de actualización envejece el Chromium de dentro.

## Fuera de alcance

Fork de Firefox, reescritura en Rust, tienda de extensiones, cuentas, sincronización y telemetría.

## Si se construye, el primer corte

Sobre esta carcasa, en este orden:

1. Hecho en 0.6.0: descargas visibles, buscar en la página, zoom y reabrir la pestaña cerrada solo en memoria.
2. Hecho en 0.6.0: marcadores en un fichero local, separados del perfil de navegación.
3. Hecho a medias en 0.6.0: con Tor no rota el User-Agent. Sigue pendiente no arrastrar la sesión del modo diario.
4. Instalador de Windows con icono, cuando esas piezas existan.
5. Forma de actualizar el motor. Sin eso, el adjetivo «seguro» caduca en la primera CVE de Chromium.

## Decisión

El doble clic abre el modo diario, rápido y sin Tor. Tor se enciende solo con el interruptor.

Eso ya es el arranque actual. `tor_toggle` nace desmarcado y `launch_tor` no se llama al crear la ventana.

El corte de usabilidad de sesión está en `docs/plans/usabilidad-sesion.md`. Los marcadores locales están en `docs/plans/marcadores.md`. La rotación de User-Agent se pausa con Tor (`docs/plans/tor-sin-rotacion-ua.md`). Siguen pendientes aislar la sesión diaria al entrar en Tor, el instalador y la actualización del motor.
