"""Send code to Telegram group and schedule message deletion after delay."""

from __future__ import annotations

import threading
import time
from telegram import Bot


def send_code_and_schedule_delete(
    token: str,
    chat_id: int | str,
    text: str,
    delete_after_seconds: int,
) -> None:
    bot = Bot(token=token)
    sent = bot.send_message(chat_id=chat_id, text=text)
    message_id = sent.message_id

    def delete_later() -> None:
        time.sleep(delete_after_seconds)
        try:
            bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception:
            pass  # Message may already be deleted or bot restarted

    threading.Thread(target=delete_later, daemon=True).start()
