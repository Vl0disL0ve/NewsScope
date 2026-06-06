import telethon

import os
from dotenv import load_dotenv
from datetime import datetime, timezone
from typing import Optional

load_dotenv()

API_KEY = int(os.getenv("API_KEY"))
API_HASH = os.getenv("API_HASH")


class TGParser:
    def __init__(self):
        self.client = telethon.TelegramClient("news_parser", API_KEY, API_HASH)

    async def parse_channel(self, channel: str,
                            start_date: datetime = None,
                            end_date: datetime = None,
                            limit: Optional[int] = None) -> dict:

        if start_date and start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date and end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)

        offset = end_date if end_date else None

        rows = []

        async for message in self.client.iter_messages(channel, limit=limit, offset_date=offset):
            if start_date and message.date < start_date:
                break

            if not message.text:
                continue

            rows.append([
                message.date.strftime("%Y-%m-%d %H:%M:%S"),
                message.text.replace("\n", " "),
                f"https://t.me/{channel}/{message.id}",
                message.views or 0,
                message.forwards or 0
            ])
        return rows

    async def __aenter__(self):
        await self.client.connect()
        if not await self.client.is_user_authorized():
            print("Authorisation is required:")
            await self.client.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.disconnect()
        return False
