# Decisiones

## 2026-10-27 — Publicación

- Forja interna: `https://gitea.tiizss.internal/tiizss/UltraBrowser`. El nombre resuelve a `192.168.1.2`. La API responde y el usuario `tiizss` existe. Una consulta sin autenticación al repo devuelve 404. En Gitea eso también ocurre con un repo privado, así que no consta que `UltraBrowser` esté creado. No hay token de Gitea en el entorno. No se ha creado el remoto ni el repo.
- Forja pública: `origin` ya apunta a `https://github.com/TiiZss/UltraBrowser.git`.
- Orden cuando haya CI: rama de la funcionalidad, push a Gitea, CI en verde, push a GitHub, merge a `main`, borrar la rama de la funcionalidad. Tag y release solo si cambia la versión.
- La regla de no hacer commit ni push salvo pedido explícito queda derogada en este repo. Sigue vigente la condición de CI en verde. Mientras no exista un workflow, no se publica.
- La licencia sigue siendo MIT. Cambiarla es una decisión legal aparte.
- `pyproject.toml` declara el nombre `navigator` y `package = false`. No se publica a PyPI.

## 2026-10-27 — Skills

- Hay 261 skills en `D:\Scripts\Z-externos\ECC\skills` y 818 en `D:\Scripts\Z-externos\Anthropic-Cybersecurity-Skills\skills`.
- No se copian al repo. Se usan desde esa ruta, y solo las de `docs/agent/skills.md`.
- Playwright, Sentry y las guías de diseño web quedan fuera: la interfaz es Qt y el producto no envía telemetría.

## 2026-10-28 — Producto

- El objetivo declarado es un navegador rápido, seguro, lo más anónimo posible y con la usabilidad de uno estándar.
- Esas cuatro metas no caben en un solo modo. La velocidad la da Chromium sin Tor. El anonimato fuerte lo da el circuito Tor. La usabilidad estándar (descargas, buscar en la página, zoom, marcadores) se añade en la carcasa actual.
- Se descarta reescribir en Rust y descartar un fork de Firefox.
- El icono abre el modo diario: rápido y sin Tor. Tor queda como interruptor. El código ya arranca así: el botón nace en OFF y `TorManager` no lanza el proceso hasta que se pulsa.

## 2026-10-28 — Versión 0.6.0

- No hay workflows de CI. El verde de esta versión es `python -m py_compile` de los módulos de `ultrabrowser/`, no un pipeline.
- La 0.6.0 junta búsqueda, zoom, descargas, reabrir pestaña, marcadores y la pausa de la rotación de User-Agent con Tor.
- Las ramas `feat/usabilidad-sesion`, `feat/marcadores` y `feat/tor-sin-rotacion-ua` se funden en `main`. El tag es `v0.6.0`.
