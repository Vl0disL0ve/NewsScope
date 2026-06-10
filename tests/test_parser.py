import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.parser_service import ParserService

async def test_parser():
    print("=" * 50)
    print("🧪 ТЕСТ ПАРСЕРА")
    print("=" * 50)
    
    parser = ParserService()
    
    print("\n📌 1. ПАРСИНГ Telegram")
    tg_news = await parser.parse_telegram(['rian_ru', 'rt_russian'], limit=5)
    print(f"   ✅ Telegram: {len(tg_news)} новостей")
    
    print("\n📌 2. ПАРСИНГ Lenta.ru (может не работать)")
    try:
        lenta_news = await parser.parse_lenta(limit=5)
        print(f"   ✅ Lenta.ru: {len(lenta_news)} новостей")
    except Exception as e:
        print(f"   ⚠️ Lenta.ru: ошибка - {e}")
    
    await parser.close()
    
    print("\n" + "=" * 50)
    print("🎉 ТЕСТ ПАРСЕРА ЗАВЕРШЁН!")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(test_parser())