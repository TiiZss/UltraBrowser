# Skills que sí entran en UltraBrowser

Se leen en su carpeta de origen. No se venden al repo.

Origen ECC: `D:\Scripts\Z-externos\ECC\skills`. Origen ciberseguridad: `D:\Scripts\Z-externos\Anthropic-Cybersecurity-Skills\skills`.

## Usar cuando el cambio lo pida

| Skill | Cuándo |
|---|---|
| `python-patterns` | Código Python nuevo. El código que ya funciona no se reescribe para acercarlo a la guía. |
| `error-handling` | Un módulo nuevo que necesite excepciones o reintentos. Tor ya tiene las suyas en `ultrabrowser/exceptions.py`. |
| `click-path-audit` | Un fallo en el que un interruptor (Tor, anuncios, cámara, micrófono, limpiar datos) deja la ventana en un estado distinto del que promete el botón. |
| `security-review` | Cambios en la barra de direcciones, HTTPS, permisos de cámara o micrófono, ficheros de diagnóstico o el arranque de Tor. |
| `product-lens` | Antes de aceptar una funcionalidad nueva cuyo motivo no está claro. |
| `architecture-decision-records` | Cuando haya que elegir entre dos diseños y dejar el motivo en `docs/agent/`. |
| `windows-desktop-e2e` | Cuando se pida una prueba de la ventana Qt en Windows. Hoy no hay suite de pruebas y no se crea solo por tener la skill. |
| `implementing-secret-scanning-with-gitleaks` | Antes del primer push a Gitea o GitHub, en local. |
| `implementing-semgrep-for-custom-sast-rules` | Cuando exista CI. Reglas locales, sin servicio externo. |
| `generating-and-analyzing-sboms` | En una release, para inventariar dependencias. No en cada arreglo. |

`git-workflow` no fija el flujo de este repo. Manda la sección «Flujo de este repo» de `AGENTS.md`: Gitea primero, GitHub después, merge a `main` solo con CI en verde.

## Revisadas y fuera

Estas carpetas existen y no aplican a este navegador de escritorio:

- Guías web y de motion (`frontend-patterns`, `frontend-design-direction`, `make-interfaces-feel-better`, `design-system`, `seo`, `e2e-testing`, `browser-qa`). La interfaz es PyQt6.
- `verification-loop`. Exige build de npm, Pyright, Ruff y un 80 % de cobertura. El repo no tiene nada de eso. Activarla obligaría a montar un toolchain que el propio `AGENTS.md` dice que no existe.
- `tdd-workflow` y `python-testing`, hasta que se pida una suite de pruebas.
- `performing-privacy-impact-assessment`. Es un programa GDPR/NIST para tratamientos de datos. Aquí no hay cuentas ni servidor.
- `analyzing-browser-forensics-with-hindsight` y `extracting-browser-history-artifacts`. Reconstruyen perfiles de Chrome, Edge, Brave u Opera en una investigación. No comprueban el perfil en memoria de UltraBrowser.
- `performing-sca-dependency-scanning-with-snyk`. Sube el inventario a un servicio de terceros.
- `performing-directory-traversal-testing`, `testing-for-open-redirect-vulnerabilities`, `testing-for-xss-vulnerabilities`, `performing-content-security-policy-bypass`. Son procedimientos de pentest contra aplicaciones web. Este repo no sirve páginas.
- `performing-threat-modeling-with-owasp-threat-dragon`. Informe formal de GRC. El mapa de amenazas, si hace falta, cabe en `docs/agent/decisions.md`.
- `detecting-dependency-confusion`. El paquete no se publica (`package = false`). Vuelve a mirarse si algún día se sube a PyPI. El nombre `navigator` en `pyproject.toml` es genérico; no se cambia sin pedirlo.
- El resto de los dos catálogos: otras plataformas, nube, sanidad, finanzas, malware, Active Directory o contenedores.
