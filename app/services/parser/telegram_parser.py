from typing import List, Dict, Any
from datetime import datetime
from telethon import TelegramClient
from telethon.errors import UsernameNotOccupiedError
import os

from app.config import config

class TelegramParser:
    """Реальный парсер Telegram через Telethon"""
    
    def __init__(self):
        self.client = None
        self.api_id = config.TG_API_ID
        self.api_hash = config.TG_API_HASH
    
    async def _get_client(self):
        if self.client is None:
            if not self.api_id or not self.api_hash:
                print("Telegram API ключи не настроены")
                return None
            
            session_file = config.DATA_DIR / "telegram_session"
            self.client = TelegramClient(str(session_file), self.api_id, self.api_hash)
            await self.client.start()
            
            if not await self.client.is_user_authorized():
                print("Telegram не авторизован")
                return None
        
        return self.client
    
    async def parse(self, channels: List[str], limit: int = 30) -> List[Dict[str, Any]]:
        news_list = []
        
        client = await self._get_client()
        if not client:
            return []
        
        for channel in channels:
            try:
                channel_name = channel.lstrip('@')
                entity = await client.get_entity(channel_name)
                messages = await client.get_messages(entity, limit=limit)
                
                for msg in messages:
                    if not msg.message:
                        continue
                    
                    news_list.append({
                        'published_at': msg.date,
                        'channel': channel_name,
                        'news_body': msg.message[:2000],
                        'news_link': f"https://t.me/{channel_name}/{msg.id}",
                        'views': msg.views or 0,
                        'forwarded': msg.forwards or 0,
                        'subject': None,
                        'source': 'TG'
                    })
                
                print(f"Telegram @{channel_name}: {len(messages)} сообщений")
                
            except UsernameNotOccupiedError:
                print(f"Канал {channel} не найден")
            except Exception as e:
                print(f"Ошибка {channel}: {e}")
        
        return news_list
    
    async def close(self):
        if self.client:
            await self.client.disconnect()
            self.client = None