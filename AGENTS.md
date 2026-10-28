# AGENTS.md

## Cursor Cloud specific instructions

### Overview

UltraBrowser is a privacy-focused desktop web browser built with Python 3.12+ and PyQt6. It is a single-process GUI application (no backend/database/docker). See `readme.md` for feature details.

### Running the application

```bash
DISPLAY=:1 uv run python -m ultrabrowser.main
```

The app requires a display server (X11). On Cloud VMs, use the existing display (`:1`) or start Xvfb (`Xvfb :99 -screen 0 1920x1080x24 -ac &` then `DISPLAY=:99`).

### Key caveats

- **No automated tests or lint tooling**: The project has no `pytest`, `ruff`, `flake8`, `mypy`, or similar configured. Use `python -m py_compile <file>` for basic syntax checking.
- **No build step**: The app runs directly via `uv run -m ultrabrowser.main`.
- **System Qt6 libraries required**: PyQt6-WebEngine needs `libegl1`, `libxkbcommon-x11-0`, `libxcb-cursor0`, `libxcb-icccm4`, `libxcb-image0`, `libxcb-keysyms1`, `libxcb-render-util0`, `libxcb-xinerama0`. These are installed once during environment setup.
- **Tor is optional**: The Tor toggle feature requires a Tor binary (bundled in `bin/linux/Tor/tor` or system-installed). The browser works fully without Tor in normal mode.
- **Config files**: Runtime config is in `config/config.json`; user-agents for anti-fingerprinting are in `config/user_agents.json`.
- **Entry point**: `python -m ultrabrowser.main` (launchers `run.bat`, `run.ps1`, `run.sh`). `pyproject.toml` has no `[project.scripts]` entry.

<!-- graft:start -->
## Graft — repo context graph

This repo is indexed in `graft/`: small linked markdown nodes that explain each
system and carry exact file:line spans, kept in sync with the code through git.

For ANY task here — understanding how something works, finding where code lives,
or scoping a change — get context from the graph before grepping or opening
source files. Re-ask freely (it's cheap) and reuse literal identifiers you
already have (symbol, error string, file name) as the query. New to this repo?
Run `graft map` first — a token-budgeted orientation (dir clusters, hubs,
hotspots), no LLM, no key.

- Run `graft ask "<your question>" --source` → ranked nodes with the relevant
  code spans inlined (each hit's ≤8-line crux by default; `--full` for whole
  definitions when the crux isn't enough). Match the tool to the task shape:
  for understanding or editing, the top node IS the answer — cite its
  `covers:` file:line spans and edit straight from `--source`. For
  exhaustive tasks ("every occurrence / every caller of this pattern"), ranked
  results are top-N, not complete — run `graft grep "<literal>"` instead
  (exhaustive over indexed files, grouped by enclosing symbol), falling back
  to raw `grep -rn` only for unindexed files.
- `graft skeleton <file>` → every definition's signature + span, ~10× cheaper
  than reading the file; use it to skim an API surface.
- `graft callers <symbol>` gives precomputed, exact edges — who calls this.
  Add `--direction out` for what it calls, or `--depth N` to walk
  transitively for the full blast radius. For structural questions, skip
  ranking and use this directly.
- Or browse: `graft/INDEX.md` lists every node; follow the links.
- Monorepos and folders of multiple repos rank fairly across sub-projects —
  hits carry `[scope/]` labels naming which one they're from. Narrow with
  `graft ask "<task>" --in <scope>/` once you know where you're working.

If a returned span is truncated ("+N more lines"), open the file at that exact
range before finalizing. Only open source files when a node genuinely lacks a
needed detail, and then at the exact file:line the node points to — never
re-read whole files.

After big code changes, refresh the graph with `graft build` (deterministic,
no API key, $0).
<!-- graft:end -->

## Flujo de este repo

Decisiones y skills: `docs/agent/decisions.md` y `docs/agent/skills.md`.

- Cada funcionalidad va en su propia rama. La rama es la copia de seguridad.
- Publicar solo con CI en verde: primero `https://gitea.tiizss.internal/tiizss/UltraBrowser`, después `https://github.com/TiiZss/UltraBrowser`, luego merge a `main` y borrar la rama.
- Hoy no hay workflows. Hasta que existan, no hay push.
- Las skills se leen en su sitio de origen. No se copian al repo.
