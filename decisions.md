# Registro de decisiones

## 2026-10-27 (Europe/Madrid) — Reglas de trabajo del agente

Auditoría de las instrucciones nuevas frente a este repositorio. Hechos comprobados en esa fecha. Lo que no está en esta lista no se da por hecho.

### Hechos

- El proyecto ya existe: https://github.com/TiiZss/UltraBrowser. Visibilidad pública. Rama por defecto `main`. Licencia MIT, copyright 2026 TiiZss.
- No hay GitHub Actions (cero workflows) ni remoto de Gitea configurado. El único remoto de trabajo es `origin` hacia GitHub.
- Es un navegador de escritorio en Python 3.12 y PyQt6, un solo proceso, sin frontend web. El entorno se gestiona con `uv`. La codificación de trabajo ya es UTF-8.
- El mapa del agente en Cursor es `AGENTS.md`. No hace falta un segundo manual con el mismo contenido.
- `gitea.tiizss.internal` no resuelve desde este entorno. `gitea.tiizss.com` resuelve, responde HTTP 301 y HTTPS con un certificado cuyo nombre no coincide con el host. No hay credencial de Gitea disponible aquí.
- `D:\Scripts\Z-externos\ECC` y `D:\Scripts\Z-externos\Anthropic-Cybersecurity-Skills` no existen en esta máquina.
- MCP conectados aquí: Context7, Telegram, Outlook, Gmail, Google Calendar, cursor-cloud y cursor-subscriptions. No están GitHub MCP, Playwright, Filesystem MCP, markitdown ni Sentry. GitHub se usa con `gh` y git. Los ficheros se leen con las herramientas del entorno.
- El paquete del índice de código (Graft, ahora Trail-code) no está instalado. El árbol Python es pequeño.
- `docs.md` describe módulos en la raíz que hoy viven en `ultrabrowser/`. Esa deriva queda anotada y no se reescribe en esta decisión.

### Se adoptan

1. `AGENTS.md` es el mapa. `CLAUDE.md` solo remite a él, para quien abra el repo en Claude Code.
2. Python con `uv`. Sin `pip` para instalar dependencias del proyecto.
3. UTF-8 en código, configuración y documentación.
4. La licencia sigue siendo MIT. Cambiarla es una decisión legal aparte.
5. Una rama por funcionalidad. En este entorno el nombre es `cursor/<descripcion>-1332`.
6. Antes de un cambio amplio, el respaldo es un commit en esa rama. No se duplica el árbol en otra carpeta.
7. El código que ya funciona se toca solo si el cambio pedido lo exige. El comportamiento actual se conserva.
8. Una funcionalidad nueva y grande se contrasta antes con proyectos públicos similares. Un arreglo de un fallo ya localizado no abre esa búsqueda.
9. Un plan de un cambio no trivial se escribe en un fichero del repo (`decisions.md` o `docs/`), no se deja solo en el chat.
10. Raíz mínima. Metadatos de agente: `AGENTS.md`, `CLAUDE.md`, este archivo. `MEMORY.md` y `LEARNINGS.md` se crean cuando haya un hecho estable o una lección repetida que registrar. No se crean vacíos.
11. Texto de cara al lector (párrafos del README) se revisa para quitar muletillas de redacción automática, sin añadir datos. Changelog técnico, comentarios, logs y `SECURITY_AUDIT.md` se dejan literales.
12. Context7 se usa cuando haga falta documentación actual de una librería. La GUI de PyQt se comprueba en el escritorio del entorno, no con Playwright.
13. Cada cambio de seguridad relevante se revisa en el diff. La auditoría completa del árbol no se relanza en cada edición.
14. README y changelog se actualizan cuando cambia el comportamiento visible. Tag y release van con un corte de versión, no con cada rama.
15. Si una instrucción no se puede comprobar, se dice y se para. No se rellena el hueco.

### No se adoptan

- Crear de nuevo el repo en GitHub, ni pasarlo a privado. Ya es público y el README enlaza badges de ese repo público.
- Publicar primero en Gitea y después en GitHub. Faltan nombre canónico (`.internal` y `.com` aparecen los dos), TLS válido y credencial. Hasta eso, el remoto es GitHub.
- Fusionar a `main` y borrar ramas al terminar cada tarea. Sin CI, "en verde" no significa nada. Un merge se hace cuando se pida para ese cambio concreto.
- Exigir panel de problemas, kanban, architecture, troubleshooting, fichero graft, tag y release después de cada PR.
- Instalar Graft/Trail-code, Caveman, Napkin, Diagram Design o el humanizador como dependencia permanente. Caveman además choca con respuestas en español claro y completo. Napkin duplica este registro. Diagramas solo si se piden. Graft se reconsidera si el código crece bastante.
- Importar skills desde `D:\Scripts\...`. Esas carpetas no están aquí.
- Tratar como obligatorios Playwright, Sentry, markitdown, Filesystem MCP o un MCP de GitHub que no está conectado.
- Aplicar skills de diseño web (Impeccable, Frontend Design, UI UX Pro Max, Theme Factory, reglas visuales de Vercel). No hay interfaz web.
- Copia de seguridad en paralelo al historial de git.
- Reescribir módulos estables para "mejorar la rueda" sin un pedido explícito.

### Choques dentro del propio encargo

- "No reinventar" y "preservar el código que funciona" chocan con adoptar cinco herramientas de agente y rehacer el flujo de publicación.
- "Raíz con los mínimos ficheros" choca con MEMORY, LEARNINGS, decisions, CLAUDE, kanban, architecture, troubleshooting y graft a la vez.
- "El menor consumo de tokens" choca con Caveman como voz de las respuestas, con auditar todo el código en cada cambio y con generar esa documentación en cada PR.
- "Nada de sobreingeniería" choca con tag, release y merge automático por cada funcionalidad.
- "No te inventes nada" choca con humanizar todo texto si eso altera cifras, rutas o advertencias de seguridad.
- "Cuestiónalo todo" choca con incorporar el bloque entero sin criba.
- Dos URLs de Gitea distintas. Una no resuelve.

### Pendiente de una decisión explícita

- URL única de Gitea, certificado a nombre de ese host y credencial. Sin eso no hay segundo remoto.
- Si el repo público debe seguir público.
- Si se quiere un CI mínimo (sintaxis y arranque) para que "en verde" sea comprobable. Eso sería una funcionalidad aparte, en su rama.
