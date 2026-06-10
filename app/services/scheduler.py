import asyncio
import threading
import time
from datetime import datetime
from app.services.parser_service import ParserService
from app.database.crud import NewsCRUD
from app.database.session import AsyncSessionLocal

class ParseScheduler:
    def __init__(self, interval_hours: int = 1):
        self.interval_seconds = interval_hours * 3600
        self.running = False
        self.thread = None
    
    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        print(f"Парсер запущен: каждые {self.interval_seconds // 3600} часов")
    
    def stop(self):
        self.running = False
    
    def _run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        while self.running:
            try:
                loop.run_until_complete(self._parse_all())
            except Exception as e:
                print(f"Ошибка парсинга: {e}")
            
            time.sleep(self.interval_seconds)
    
    async def _parse_all(self):
        print(f"[{datetime.now()}] Запуск фонового парсинга...")
        parser = ParserService()
        
        # Парсим Lenta.ru
        await parser.parse_lenta(limit=30)
        
        # Парсим Telegram каналы
        tg_channels = ['rian_ru', 'rt_russian', 'kommersant', 'tass_agency']
        await parser.parse_telegram(tg_channels, limit=20)
        
        await parser.close()
        print(f"[{datetime.now()}] Парсинг завершён")


scheduler = ParseScheduler(interval_hours=1)