import telethon

import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = int(os.getenv("API_KEY"))
API_HASH = os.getenv("API_HASH")


class TGParser:
    def __init__(self):
        self.client = telethon.TelegramClient("news_parser", API_KEY, API_HASH)

    async def parse_channel(self, channel, limit=50):
        rows = []
        async for message in self.client.iter_messages(channel, limit=limit):
            if not message.text:
                continue

            rows.append({
                "Date": message.date.strftime("%Y-%m-%d %H:%M:%S"),
                "Body": message.text.replace("\n", " "),
                "Link": f"https://t.me/{channel}/{message.id}",
                "Views": message.views or 0,
                "Forwards": message.forwards or 0
            })
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
