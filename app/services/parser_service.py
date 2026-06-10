from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.parser.lenta_parser import LentaParser
from app.services.parser.telegram_parser import TelegramParser
from app.database.crud import NewsCRUD
from app.database.session import AsyncSessionLocal

class ParserService:
    def __init__(self):
        self.lenta_parser = LentaParser()
        self.telegram_parser = TelegramParser()
    
    async def parse_lenta(self, limit: int = 30) -> List[Dict]:
        print("Парсинг Lenta.ru...")
        news_items = await self.lenta_parser.parse(limit)
        
        saved = 0
        async with AsyncSessionLocal() as db:
            news_crud = NewsCRUD(db)
            for item in news_items:
                if not await news_crud.exists_by_link(item['news_link']):
                    await news_crud.add(**item)
                    saved += 1
            await db.commit()
        
        print(f"Lenta.ru: {len(news_items)} новостей, новых {saved}")
        return news_items
    
    async def parse_telegram(self, channels: List[str], limit: int = 30) -> List[Dict]:
        print(f"Парсинг Telegram: {channels}")
        news_items = await self.telegram_parser.parse(channels, limit)
        
        saved = 0
        async with AsyncSessionLocal() as db:
            news_crud = NewsCRUD(db)
            for item in news_items:
                if not await news_crud.exists_by_link(item['news_link']):
                    await news_crud.add(**item)
                    saved += 1
            await db.commit()
        
        print(f"Telegram: {len(news_items)} новостей, новых {saved}")
        return news_items
    
    async def close(self):
        await self.telegram_parser.close()