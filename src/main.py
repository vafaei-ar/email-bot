"""Main loop: poll email, extract codes, send to Telegram, schedule delete."""

from __future__ import annotations

import logging
import re
import sys
import time
from pathlib import Path

from imap_tools.errors import MailboxLoginError
from telegram.error import BadRequest, InvalidToken, NetworkError, TelegramError

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
    try:
        config = load_config()
    except FileNotFoundError as e:
        logger.error(
            "Config file missing (%s). Copy the example and edit it:\n"
            "  cp config.example.yaml config.yaml",
            e,
        )
        sys.exit(1)
    except ValueError as e:
        logger.error("%s", e)
        sys.exit(1)

    creds_path = config["_credentials_path"]
    try:
        credentials = load_credentials(creds_path)
    except FileNotFoundError as e:
        logger.error(
            "Credentials file missing (%s). Copy the example and edit it:\n"
            "  cp credentials.example.yaml credentials.yaml",
            e,
        )
        sys.exit(1)
    except ValueError as e:
        logger.error("%s", e)
        sys.exit(1)

    email_cfg = config.get("email") or {}
    telegram_cfg = config.get("telegram") or {}
    provider = email_cfg.get("provider", "gmail")
    subject_filter = email_cfg.get("subject_filter", "")
    sender_filter = email_cfg.get("sender_filter", "")
    code_pattern = email_cfg.get("code_pattern", r"\b\d{2}\b")
    poll_interval = int(email_cfg.get("poll_interval_seconds", 30))
    chat_id = telegram_cfg.get("chat_id")
    delete_after = int(telegram_cfg.get("message_delete_after_seconds", 300))
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

    try:
        re.compile(code_pattern)
    except re.error as e:
        logger.error(
            "Invalid email.code_pattern (regex): %s\n"
            "  Fix the pattern in config.yaml (must be a valid Python regex).",
            e,
        )
        sys.exit(1)

    try:
        host, port = get_imap_host(provider)
    except ValueError as e:
        logger.error("%s\n  Set email.provider to 'gmail' or 'yahoo' in config.yaml.", e)
        sys.exit(1)
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
        except MailboxLoginError as e:
            logger.error(
                "IMAP login failed — the mail server rejected your username or password.\n"
                "  • Do not use your normal email password. Use an app password (with 2FA enabled).\n"
                "  • Yahoo: Account security → generate app password; ensure IMAP is enabled for the account.\n"
                "  • Gmail: Google Account → Security → 2-Step Verification → App passwords.\n"
                "  • email_user must be the full address for that mailbox (e.g. you@yahoo.com).\n"
                "Server message: %s",
                e,
            )
        except InvalidToken:
            logger.error(
                "Telegram rejected the bot token (invalid or revoked).\n"
                "  • In @BotFather use /mybots → your bot → API Token → create a new token if needed.\n"
                "  • Put the new token in credentials.yaml as telegram_bot_token.",
            )
        except BadRequest as e:
            if "chat not found" in str(e).lower() or "chat_id is empty" in str(e).lower():
                logger.error(
                    "Telegram: chat not found or wrong chat_id.\n"
                    "  • Use https://api.telegram.org/bot<TOKEN>/getUpdates (note the word \"bot\" before the token).\n"
                    "  • For groups, chat_id is usually negative (e.g. -100…). Add the bot to the group first.\n"
                    "  • In groups, send /start@YourBotName or mention the bot if privacy mode hides normal messages.\n"
                    "Details: %s",
                    e,
                )
            else:
                logger.error("Telegram BadRequest: %s", e)
        except NetworkError as e:
            logger.warning(
                "Telegram network error (will retry next poll): %s. Check internet / firewall.",
                e,
            )
        except TelegramError as e:
            logger.error("Telegram API error: %s", e)
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
