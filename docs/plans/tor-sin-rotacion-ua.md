# Pausar la rotación de User-Agent con Tor

Fecha: 2026-10-28.

## Aceptación

- Al pulsar Tor, el temporizador deja de cambiar el User-Agent.
- Si la conexión falla o el usuario apaga Tor, el temporizador vuelve a correr con el mismo intervalo.
- Con `rotate_user_agent` en false no hay temporizador y no cambia nada.
- El User-Agent que ya estaba puesto no se sustituye por otro.

## Fuera

No se unifica el agente con el de Tor Browser ni se aísla la sesión del modo diario.
