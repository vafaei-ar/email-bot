"""Persist processed email UIDs so we don't re-send the same code."""

from __future__ import annotations

import json
from pathlib import Path


def _default_store_path() -> Path:
    return Path("processed_uids.json").resolve()


def load_processed_uids(store_path: Path | None = None) -> set[str]:
    path = store_path or _default_store_path()
    if not path.exists():
        return set()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return set(data.get("uids", []))
    except (json.JSONDecodeError, OSError):
        return set()


def save_processed_uids(uids: set[str], store_path: Path | None = None) -> None:
    path = store_path or _default_store_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"uids": list(uids)}, f, indent=2)


def add_processed_uid(uid: str, store_path: Path | None = None) -> None:
    uids = load_processed_uids(store_path)
    uids.add(uid)
    save_processed_uids(uids, store_path)
