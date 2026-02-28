"""IMAP client: connect, filter by subject/sender, extract code from body."""

from __future__ import annotations

import imaplib
import logging
import re
import socket
import time
from dataclasses import dataclass
from typing import Any

from imap_tools import MailBox

logger = logging.getLogger(__name__)

# Retry settings for flaky IMAP (e.g. Yahoo sometimes closes with EOF)
IMAP_CONNECT_TIMEOUT = 30
IMAP_RETRY_ATTEMPTS = 3
IMAP_RETRY_DELAY_SECONDS = 5


@dataclass
class Match:
    uid: str
    code: str


def _body_text(msg: Any) -> str:
    if getattr(msg, "text", None) and msg.text.strip():
        return msg.text
    html = getattr(msg, "html", None) or ""
    if not html:
        return ""
    # Strip tags roughly
    return re.sub(r"<[^>]+>", " ", html).replace("&nbsp;", " ").strip()


def _extract_code(body: str, pattern: str) -> str | None:
    try:
        m = re.search(pattern, body)
    except re.error:
        return None
    if not m:
        return None
    if m.lastindex and m.lastindex >= 1:
        return m.group(1)
    return m.group(0)


def _matches_filters(
    subject: str,
    from_addr: str,
    subject_filter: str,
    sender_filter: str,
) -> bool:
    return (
        subject_filter.strip().lower() in (subject or "").lower()
        and sender_filter.strip().lower() in (from_addr or "").lower()
    )


def _fetch_once(
    host: str,
    port: int,
    user: str,
    password: str,
    subject_filter: str,
    sender_filter: str,
    code_pattern: str,
    limit: int,
) -> list[Match]:
    results: list[Match] = []
    with MailBox(host, port=port).login(user, password) as mailbox:
        messages = list(mailbox.fetch(limit=limit, reverse=True))
        for msg in messages:
            if not _matches_filters(
                msg.subject or "",
                msg.from_ or "",
                subject_filter,
                sender_filter,
            ):
                continue
            body = _body_text(msg)
            code = _extract_code(body, code_pattern)
            if code is not None:
                results.append(Match(uid=str(msg.uid), code=code))
    return results


def fetch_matching_codes(
    host: str,
    port: int,
    user: str,
    password: str,
    subject_filter: str,
    sender_filter: str,
    code_pattern: str,
    limit: int = 100,
) -> list[Match]:
    last_error: Exception | None = None
    old_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(IMAP_CONNECT_TIMEOUT)
        for attempt in range(1, IMAP_RETRY_ATTEMPTS + 1):
            try:
                return _fetch_once(
                    host, port, user, password,
                    subject_filter, sender_filter, code_pattern, limit,
                )
            except (imaplib.IMAP4.abort, imaplib.IMAP4.error, OSError, ConnectionError) as e:
                last_error = e
                if attempt < IMAP_RETRY_ATTEMPTS:
                    logger.warning(
                        "IMAP connection failed (attempt %d/%d): %s. Retrying in %ds...",
                        attempt, IMAP_RETRY_ATTEMPTS, e, IMAP_RETRY_DELAY_SECONDS,
                    )
                    time.sleep(IMAP_RETRY_DELAY_SECONDS)
                else:
                    logger.error("IMAP connection failed after %d attempts: %s", IMAP_RETRY_ATTEMPTS, e)
                    raise
    finally:
        socket.setdefaulttimeout(old_timeout)
    assert last_error is not None
    raise last_error
