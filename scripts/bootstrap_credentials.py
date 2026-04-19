#!/usr/bin/env python3
"""Interactive prompts when config/credentials still contain example placeholders."""

from __future__ import annotations

import os
import sys
from getpass import getpass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

# Must match placeholders in credentials.example.yaml
_PLACEHOLDER_EMAIL = frozenset({"you@yahoo.com", "you@gmail.com"})
_PLACEHOLDER_PASSWORD = "your-app-password"
_PLACEHOLDER_TOKEN = "123456:ABC-DEF..."

_EXAMPLE_CHAT_ID = -1001234567890


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _save(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Generated or edited by scripts/bootstrap_credentials.py / install.sh\n")
        yaml.safe_dump(
            data,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )


def _needs_credential_prompt(creds: dict) -> bool:
    user = (creds.get("email_user") or creds.get("email") or "").strip()
    pwd = (creds.get("email_password") or creds.get("password") or "").strip()
    token = (creds.get("telegram_bot_token") or creds.get("telegram_token") or "").strip()
    if user in _PLACEHOLDER_EMAIL or not user:
        return True
    if pwd == _PLACEHOLDER_PASSWORD or not pwd:
        return True
    if token == _PLACEHOLDER_TOKEN or not token:
        return True
    return False


def _prompt_credentials(creds: dict) -> dict:
    print("\n--- Email & Telegram credentials ---")
    print("Use an app password for email (not your normal login password). See README.\n")
    user = input(f"Email address [{creds.get('email_user') or 'you@yahoo.com'}]: ").strip()
    if user:
        creds["email_user"] = user
    pwd = getpass("Email app password (hidden): ").strip()
    if pwd:
        creds["email_password"] = pwd
    token = getpass("Telegram bot token from @BotFather (hidden): ").strip()
    if token:
        creds["telegram_bot_token"] = token
    # Normalize keys to project convention
    creds.pop("email", None)
    creds.pop("password", None)
    creds.pop("telegram_token", None)
    return creds


def _needs_chat_id_prompt(cfg: dict) -> bool:
    tid = (cfg.get("telegram") or {}).get("chat_id")
    return tid == _EXAMPLE_CHAT_ID


def _prompt_chat_id(cfg: dict) -> dict:
    print("\n--- Telegram chat_id ---")
    print(
        "Open: https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates\n"
        '  (the path must contain the word "bot" immediately before the token — not /TOKEN/...)\n'
        "Message your bot or group, then read chat.id in the JSON.\n"
    )
    raw = input("Paste numeric chat_id (Enter to skip and edit config.yaml later): ").strip()
    if not raw:
        return cfg
    try:
        chat_id = int(raw)
    except ValueError:
        print("Invalid number; leaving config.yaml unchanged.", file=sys.stderr)
        return cfg
    if "telegram" not in cfg or not isinstance(cfg["telegram"], dict):
        cfg["telegram"] = {}
    cfg["telegram"]["chat_id"] = chat_id
    return cfg


def _config_file() -> Path:
    raw = os.environ.get("CONFIG_PATH", "config.yaml")
    p = Path(raw)
    return p.resolve() if p.is_absolute() else (ROOT / p).resolve()


def main() -> int:
    os.chdir(ROOT)
    config_path = _config_file()
    cred_path = ROOT / "credentials.yaml"

    creds = _load(cred_path)
    if _needs_credential_prompt(creds):
        creds = _prompt_credentials(creds)
        _save(cred_path, creds)
        print(f"Wrote {cred_path.relative_to(ROOT)}\n")
        if _needs_credential_prompt(creds):
            print(
                "Warning: credentials may still be incomplete or placeholders. Edit credentials.yaml before relying on the bot.",
                file=sys.stderr,
            )

    cfg = _load(config_path)
    if cfg and _needs_chat_id_prompt(cfg):
        old_id = (cfg.get("telegram") or {}).get("chat_id")
        cfg = _prompt_chat_id(cfg)
        new_id = (cfg.get("telegram") or {}).get("chat_id")
        if old_id != new_id:
            _save(config_path, cfg)
            print(f"Updated {config_path.relative_to(ROOT)}\n")
        elif _needs_chat_id_prompt(cfg):
            print(
                "Warning: telegram.chat_id is still the example value. Edit config.yaml with your real chat_id.",
                file=sys.stderr,
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
