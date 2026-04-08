"""
Utilidades de diagnostico y resolucion de rutas de runtime.
"""

from __future__ import annotations

import argparse
import os
import platform
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import BrowserConfig


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_runtime_data_dir() -> Path:
    if platform.system() == "Windows":
        base_dir = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base_dir / "UltraBrowser"
    return Path.home() / ".ultrabrowser"


def resolve_configured_path(path_value: Path | None, base_dir: Path) -> Path | None:
    if path_value is None:
        return None
    return path_value if path_value.is_absolute() else (base_dir / path_value).resolve()


def get_diagnostics_paths(config: "BrowserConfig", base_dir: Path | None = None) -> dict[str, Path]:
    base_dir = base_dir or project_root()

    log_dir = resolve_configured_path(config.diagnostics_dir, base_dir)
    if log_dir is None:
        log_dir = default_runtime_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    chromium_log = resolve_configured_path(config.chromium_log_file, base_dir)
    if chromium_log is None:
        chromium_log = log_dir / "qtwebengine-chromium.log"

    fault_log = resolve_configured_path(config.fault_log_file, base_dir)
    if fault_log is None:
        fault_log = log_dir / "python-fault.log"

    uncaught_log = resolve_configured_path(config.uncaught_exceptions_file, base_dir)
    if uncaught_log is None:
        uncaught_log = log_dir / "uncaught-exceptions.log"

    for file_path in (chromium_log, fault_log, uncaught_log):
        file_path.parent.mkdir(parents=True, exist_ok=True)

    return {
        "log_dir": log_dir,
        "chromium_log": chromium_log,
        "fault_log": fault_log,
        "uncaught_log": uncaught_log,
    }


def load_runtime_config() -> "BrowserConfig":
    from .config import BrowserConfig

    config_path = project_root() / "config" / "config.json"
    try:
        return BrowserConfig.from_file(config_path)
    except Exception:
        return BrowserConfig()


def _main() -> int:
    parser = argparse.ArgumentParser(description="Utilidades de diagnostico de UltraBrowser")
    parser.add_argument("--print-log-dir", action="store_true")
    parser.add_argument("--print-open-on-failure", action="store_true")
    args = parser.parse_args()

    config = load_runtime_config()
    diagnostics = get_diagnostics_paths(config, project_root())

    if args.print_log_dir:
        print(diagnostics["log_dir"])
    elif args.print_open_on_failure:
        print("1" if config.open_diagnostics_on_failure else "0")
    else:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(_main())