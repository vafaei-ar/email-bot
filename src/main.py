"""Main loop: poll email, extract codes, send to Telegram, schedule delete."""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

from src.config import get_imap_host, load_config, load_credentials
from src.email_client import fetch_matching_codes
from src.store import add_processed_uid, load_processed_uids
from src.telegram_client import send_code_and_schedule_delete

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    config = load_config()
    creds_path = config["_credentials_path"]
    credentials = load_credentials(creds_path)

    email_cfg = config.get("email") or {}
    telegram_cfg = config.get("telegram") or {}
    provider = email_cfg.get("provider", "gmail")
    subject_filter = email_cfg.get("subject_filter", "")
    sender_filter = email_cfg.get("sender_filter", "")
    code_pattern = email_cfg.get("code_pattern", r"\b\d{2}\b")
    poll_interval = int(email_cfg.get("poll_interval_seconds", 60))
    chat_id = telegram_cfg.get("chat_id")
    delete_after = int(telegram_cfg.get("message_delete_after_seconds", 3600))
    message_template = telegram_cfg.get("message_template") or "Code: {code}"

    if not subject_filter or not sender_filter:
        logger.error("config.email.subject_filter and config.email.sender_filter are required")
        sys.exit(1)
    if chat_id is None:
        logger.error("config.telegram.chat_id is required")
        sys.exit(1)

    email_user = credentials.get("email_user") or credentials.get("email")
    email_password = credentials.get("email_password") or credentials.get("password")
    telegram_token = credentials.get("telegram_bot_token") or credentials.get("telegram_token")
    if not email_user or not email_password:
        logger.error("credentials: email_user and email_password are required")
        sys.exit(1)
    if not telegram_token:
        logger.error("credentials: telegram_bot_token is required")
        sys.exit(1)

    host, port = get_imap_host(provider)
    config_dir = config.get("_config_dir", Path.cwd())
    store_path = config_dir / "processed_uids.json"

    logger.info("Starting email poll (provider=%s, poll_interval=%ss)", provider, poll_interval)

    while True:
        try:
            processed = load_processed_uids(store_path)
            matches = fetch_matching_codes(
                host=host,
                port=port,
                user=email_user,
                password=email_password,
                subject_filter=subject_filter,
                sender_filter=sender_filter,
                code_pattern=code_pattern,
            )
            for m in matches:
                if m.uid in processed:
                    continue
                text = message_template.format(code=m.code)
                send_code_and_schedule_delete(
                    token=telegram_token,
                    chat_id=chat_id,
                    text=text,
                    delete_after_seconds=delete_after,
                )
                add_processed_uid(m.uid, store_path)
                logger.info("Sent code (uid=%s) to Telegram, will delete in %ss", m.uid, delete_after)
        except Exception as e:
            errmsg = str(e)
            if "socket" in errmsg.lower() or "imap" in errmsg.lower() or "eof" in errmsg.lower():
                logger.warning(
                    "IMAP connection failed (will retry next poll): %s. "
                    "Check app password, firewall, and that IMAP is enabled for your account.",
                    errmsg,
                )
            else:
                logger.exception("Poll cycle error: %s", e)
        try:
            time.sleep(poll_interval)
        except KeyboardInterrupt:
            logger.info("Stopped by user")
            break


if __name__ == "__main__":
    main()
