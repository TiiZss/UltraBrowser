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
- **Entry point**: `ultrabrowser.main:main` (defined in `pyproject.toml` under `[project.scripts]`).

### Workflow decisions

`AGENTS.md` is the agent map for this repo. `CLAUDE.md` only points here. The 2026-10-27 audit of extra workflow rules is in `decisions.md`. Follow that file.

- Python dependencies go through `uv`. Keep the working tree in UTF-8.
- Leave working behavior in place unless the requested change requires the edit.
- One feature per branch (`cursor/<description>-1332` in this environment). Commit on that branch before a wide edit. That commit is the backup.
- Write a non-trivial plan into `decisions.md` or `docs/` before coding it.
- Do not add a Gitea remote, flip the GitHub repo to private, merge to `main`, cut a release, or install Graft, Caveman, Napkin, or diagram tooling unless a later decision records that the missing access and the scope are settled.
- Context7 is the docs MCP when a library question needs current docs. Verify this PyQt app on the display server. Playwright does not drive it.
- This cloud session is not Almansa4. Do not import skills from `D:\Scripts\...` here; those directories live on Almansa4 and are not mounted. On Almansa4, read the skill a task actually needs.
