"""Marcadores elegidos por el usuario, fuera del perfil de navegación."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from .diagnostics import default_runtime_data_dir


def bookmarks_path(runtime_dir: Path | None = None) -> Path:
    base = runtime_dir if runtime_dir is not None else default_runtime_data_dir()
    return base / "bookmarks.json"


def is_bookmark_url(url: str) -> bool:
    parsed = urlparse((url or "").strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


class BookmarkStore:
    """Lista de título y URL. El fichero no es el perfil off-the-record."""

    def __init__(self, path: Path):
        self.path = path
        self.items: list[tuple[str, str]] = []
        self.unreadable = False
        self.load()

    def load(self) -> None:
        self.unreadable = False
        if not self.path.exists():
            self.items = []
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self.items = []
            self.unreadable = True
            return
        if not isinstance(raw, list):
            self.items = []
            self.unreadable = True
            return

        loaded: list[tuple[str, str]] = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            url = entry.get("url")
            title = entry.get("title")
            if not isinstance(url, str) or not is_bookmark_url(url):
                continue
            url = url.strip()
            if not isinstance(title, str) or not title.strip():
                title = url
            loaded.append((title.strip()[:200], url))
        self.items = loaded

    def add(self, url: str, title: str) -> str:
        url = (url or "").strip()
        if not is_bookmark_url(url):
            return "rejected"
        clean_title = (title or "").strip()[:200] or url
        for index, (_old_title, old_url) in enumerate(self.items):
            if old_url == url:
                self.items[index] = (clean_title, url)
                self._save()
                return "updated"
        self.items.append((clean_title, url))
        self._save()
        return "added"

    def remove(self, url: str) -> bool:
        kept = [item for item in self.items if item[1] != url]
        if len(kept) == len(self.items):
            return False
        self.items = kept
        self._save()
        return True

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.unreadable and self.path.exists():
            backup = self.path.with_name("bookmarks.json.bak")
            if not backup.exists():
                self.path.replace(backup)
            self.unreadable = False
        payload = [{"title": title, "url": url} for title, url in self.items]
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)
