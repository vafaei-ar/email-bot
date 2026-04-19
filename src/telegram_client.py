"""Send code to Telegram group and schedule message deletion after delay."""

from __future__ import annotations

import asyncio
import threading
import time

from telegram import Bot


async def _send_message(token: str, chat_id: int | str, text: str):
    bot = Bot(token=token)
    return await bot.send_message(chat_id=chat_id, text=text)


async def _delete_message(token: str, chat_id: int | str, message_id: int) -> None:
    bot = Bot(token=token)
    await bot.delete_message(chat_id=chat_id, message_id=message_id)


def send_code_and_schedule_delete(
    token: str,
    chat_id: int | str,
    text: str,
    delete_after_seconds: int,
) -> None:
    sent = asyncio.run(_send_message(token, chat_id, text))
    message_id = sent.message_id

    def delete_later() -> None:
        time.sleep(delete_after_seconds)
        try:
            asyncio.run(_delete_message(token, chat_id, message_id))
        except Exception:
            pass  # Message may already be deleted or bot restarted

    threading.Thread(target=delete_later, daemon=True).start()
