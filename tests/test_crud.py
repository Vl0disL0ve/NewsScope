import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

from app.database.session import AsyncSessionLocal
from app.database.crud import UserCRUD, SettingsCRUD, NewsCRUD, ClusterCRUD, HistoryCRUD, StatsCRUD
from app.services.auth_service import AuthService
from sqlalchemy import delete
from app.models.news import News
from app.models.cluster import Cluster

async def test_crud():
    print("=" * 50)
    print("🧪 ТЕСТ CRUD (БАЗА ДАННЫХ)")
    print("=" * 50)
    
    async with AsyncSessionLocal() as db:
        print("\n📌 1. ТЕСТ UserCRUD")
        user_crud = UserCRUD(db)
        
        existing_user = await user_crud.get_by_login("testuser")
        if existing_user:
            await user_crud.delete(existing_user.id)
        
        test_user = await user_crud.create(
            login="testuser",
            password_hash=generate_password_hash("testpass123"),
            role="user"
        )
        print(f"   ✅ Создан пользователь: {test_user.login} (id={test_user.id})")
        
        print("\n📌 2. ТЕСТ SettingsCRUD")
        settings_crud = SettingsCRUD(db)
        await settings_crud.update(test_user.id, num_clusters=10, selected_channels=["lenta.ru", "tass.ru"])
        num_clusters = await settings_crud.get_num_clusters(test_user.id)
        print(f"   ✅ Настройки обновлены: clusters={num_clusters}")
        
        print("\n📌 3. ТЕСТ NewsCRUD")
        news_crud = NewsCRUD(db)
        news = await news_crud.add(
            published_at=datetime.now(),
            channel="lenta.ru",
            news_body="Тестовая новость",
            news_link="https://lenta.ru/test",
            source="LENTA"
        )
        print(f"   ✅ Добавлена новость: id={news.id}")
        
        print("\n📌 4. ТЕСТ ClusterCRUD")
        cluster_crud = ClusterCRUD(db)
        cluster = await cluster_crud.create(
            user_id=test_user.id,
            topic="Тестовый кластер",
            summary="Тестовое саммари",
            news_ids=[news.id],
            news_sources=["lenta.ru"],
            period_start=datetime.now() - timedelta(days=1),
            period_end=datetime.now()
        )
        print(f"   ✅ Создан кластер: id={cluster.id}")
        
        print("\n📌 5. ТЕСТ HistoryCRUD")
        history_crud = HistoryCRUD(db)
        await history_crud.add(test_user.id, "CLUSTER", {"test": True}, "Тест")
        history = await history_crud.get_user_history(test_user.id, 5)
        print(f"   ✅ История: {len(history)} записей")
        
        print("\n📌 6. ТЕСТ StatsCRUD")
        stats_crud = StatsCRUD(db)
        stats = await stats_crud.get_db_stats()
        print(f"   ✅ Статистика БД: users={stats['users_count']}, news={stats['news_count']}")
        
        print("\n📌 7. ОЧИСТКА")
        await history_crud.clear_user_history(test_user.id)
        await db.execute(delete(Cluster).where(Cluster.id == cluster.id))
        await db.execute(delete(News).where(News.id == news.id))
        await user_crud.delete(test_user.id)
        print(f"   ✅ Все тестовые данные удалены")
        
        print("\n" + "=" * 50)
        print("🎉 CRUD ТЕСТ ПРОЙДЕН!")
        print("=" * 50)

if __name__ == "__main__":
    asyncio.run(test_crud())