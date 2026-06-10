from app.database.session import init_db, AsyncSessionLocal
from app.models.user import User
from app.models.user_settings import UserSettings
from app.models.news import News
from app.models.cluster import Cluster
from app.models.news_cluster import NewsCluster
from app.models.user_history import UserHistory
from app.models.entry_log import EntryLog
from werkzeug.security import generate_password_hash
from app.config import config
import asyncio

async def create_first_admin():
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        stmt = select(User).where(User.login == config.ADMIN_LOGIN)
        result = await db.execute(stmt)
        admin = result.scalar_one_or_none()
        
        if not admin:
            admin = User(
                login=config.ADMIN_LOGIN,
                password_hash=generate_password_hash(config.ADMIN_PASSWORD),
                role="admin"
            )
            db.add(admin)
            await db.commit()
            print(f"✅ Админ создан: {config.ADMIN_LOGIN}")
            print(f"📝 Пароль: {config.ADMIN_PASSWORD}")

async def force_parse_news():
    """Принудительный парсинг новостей при создании БД"""
    print("🔄 Запуск принудительного парсинга новостей...")
    
    from app.services.parser_service import ParserService
    parser = ParserService()
    
    # Парсим Lenta.ru
    lenta_count = await parser.parse_lenta(limit=30)
    print(f"  Lenta.ru: {len(lenta_count)} новостей")
    
    # Парсим Telegram каналы
    tg_channels = ['rian_ru', 'rt_russian', 'kommersant', 'tass_agency']
    tg_count = await parser.parse_telegram(tg_channels, limit=20)
    print(f"  Telegram: {len(tg_count)} новостей")
    
    await parser.close()
    print("✅ Принудительный парсинг завершён")

async def main():
    print("🔧 Создаю таблицы...")
    await init_db()
    print("✅ Таблицы созданы")
    
    print("👑 Создаю первого админа...")
    await create_first_admin()
    
    print("📰 Загружаю новости (парсинг)...")
    await force_parse_news()
    
    print("🎉 Готово!")

if __name__ == "__main__":
    asyncio.run(main())