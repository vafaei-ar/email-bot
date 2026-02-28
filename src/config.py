"""Load and validate config and credentials from YAML files."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


def _load_yaml(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_config_path() -> Path:
    path = os.environ.get("CONFIG_PATH") or "config.yaml"
    return Path(path).resolve()


def get_credentials_path(config: dict[str, Any], config_dir: Path) -> Path:
    creds = (config.get("credentials_path") or os.environ.get("CREDENTIALS_PATH") or "credentials.yaml")
    p = Path(creds)
    if not p.is_absolute():
        p = config_dir / p
    return p.resolve()


def load_config() -> dict[str, Any]:
    config_path = get_config_path()
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    config = _load_yaml(config_path)
    config["_config_dir"] = config_path.parent

    # Resolve credentials path
    creds_path = get_credentials_path(config, config_path.parent)
    config["_credentials_path"] = creds_path
    return config


def load_credentials(credentials_path: Path) -> dict[str, Any]:
    if not credentials_path.exists():
        raise FileNotFoundError(f"Credentials file not found: {credentials_path}")
    return _load_yaml(credentials_path)


def get_imap_host(provider: str) -> tuple[str, int]:
    provider = (provider or "").lower()
    if provider == "gmail":
        return "imap.gmail.com", 993
    if provider == "yahoo":
        return "imap.mail.yahoo.com", 993
    raise ValueError(f"Unknown email provider: {provider}. Use 'gmail' or 'yahoo'.")
