# -*- coding: utf-8 -*-
"""
SeedController — API для заполнения БД тестовыми новостями.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from fastapi import APIRouter, HTTPException, Depends
from backend.deps import get_current_user
from database.init_db import SessionLocal
from database.models import News
from sqlalchemy import select

router = APIRouter(prefix="/api/seed", tags=["seed"])

SAMPLE_NEWS = [
    {"channel": "ТАСС", "source": "tg", "body": "Президент России провёл встречу с лидерами стран БРИКС. Обсуждались вопросы экономического сотрудничества и международной безопасности. Стороны договорились о расширении торговых отношений.", "subject": "Политика"},
    {"channel": "ТАСС", "source": "tg", "body": "Государственная дума приняла в первом чтении законопроект о развитии цифровой экономики. Документ предполагает меры поддержки IT-сектора и стимулирование инноваций.", "subject": "Экономика"},
    {"channel": "РБК", "source": "tg", "body": "Рынок акций РФ вырос на фоне новостей о снижении ключевой ставки. Индекс Мосбиржи обновил годовой максимум. Аналитики ожидают дальнейшего роста.", "subject": "Финансы"},
    {"channel": "РБК", "source": "tg", "body": "Крупнейшие российские компании объявили о запуске совместного проекта в сфере искусственного интеллекта. Инвестиции в проект составят более 10 миллиардов рублей.", "subject": "Технологии"},
    {"channel": "Пул N3", "source": "tg", "body": "Новый космический аппарат успешно выведен на орбиту. Спутник будет использоваться для дистанционного зондирования Земли и мониторинга климатических изменений.", "subject": "Наука"},
    {"channel": "Пул N3", "source": "tg", "body": "Российские учёные разработали новый материал для аккумуляторов, увеличивающий их ёмкость на 40%. Технология уже готова к внедрению в производство.", "subject": "Технологии"},
    {"channel": "Lenta.ru", "source": "lenta", "body": "В Москве прошёл международный экономический форум. Участие приняли представители более 50 стран. Основной темой стало развитие транспортных коридоров.", "subject": "Экономика"},
    {"channel": "Lenta.ru", "source": "lenta", "body": "Утверждён новый национальный проект «Экология». В рамках проекта планируется снизить выбросы загрязняющих веществ на 20% к 2030 году.", "subject": "Экология"},
    {"channel": "Интерфакс", "source": "tg", "body": "Банк России сохранил ключевую ставку на уровне 7.5% годовых. Регулятор отметил замедление инфляции и улучшение экономических показателей.", "subject": "Финансы"},
    {"channel": "Интерфакс", "source": "tg", "body": "Объём внешней торговли России вырос на 15% по итогам первого полугодия. Основной рост обеспечен за счёт увеличения экспорта энергоносителей.", "subject": "Экономика"},
    {"channel": "Коммерсантъ", "source": "tg", "body": "Крупнейшие ритейлеры объявили о запуске программы импортозамещения в сфере программного обеспечения. Переход на отечественные решения займёт около двух лет.", "subject": "Технологии"},
    {"channel": "Коммерсантъ", "source": "tg", "body": "Минцифры разработало стратегию развития искусственного интеллекта до 2030 года. План включает подготовку кадров, развитие инфраструктуры и поддержку стартапов.", "subject": "Технологии"},
]


@router.post("/news")
async def seed_news(current_user: dict = Depends(get_current_user)):
    """Заполняет БД тестовыми новостями (для отладки)."""
    added = 0
    now = datetime.now(timezone.utc)

    async with SessionLocal() as db:
        for i, item in enumerate(SAMPLE_NEWS):
            link = f"https://example.com/demo/{i}"
            stmt = select(News).where(News.news_link == link)
            exists = (await db.execute(stmt)).scalar_one_or_none()
            if exists:
                continue

            news = News(
                published_at=now - timedelta(hours=i * 2),
                channel=item["channel"],
                news_body=item["body"],
                news_link=link,
                subject=item["subject"],
                news_source=item["source"],
                views=0,
                forwarded=0,
            )
            db.add(news)
            added += 1

        if added:
            await db.commit()

    return {
        "success": True,
        "added": added,
        "message": f"Добавлено {added} демо-новостей",
    }
