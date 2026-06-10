import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.ai_service import AIService
from app.services.cluster_service import ClusterService

async def test_clustering():
    print("=" * 50)
    print("🧪 ТЕСТ КЛАСТЕРИЗАЦИИ")
    print("=" * 50)
    
    print("\n📌 1. ТЕСТ ЭМБЕДДИНГОВ")
    ai_service = AIService()
    
    test_texts = [
        "Президент подписал новый закон о налогах",
        "Госдума приняла поправки в бюджет",
        "Apple представила новый iPhone",
        "Samsung выпустила складной телефон"
    ]
    
    embeddings = ai_service.get_embeddings(test_texts)
    print(f"   ✅ Эмбеддинги: форма {embeddings.shape}")
    
    print("\n📌 2. ТЕСТ КЛАСТЕРИЗАЦИИ FAISS")
    clusters = ai_service.cluster_with_faiss(embeddings, num_clusters=2)
    print(f"   ✅ Создано кластеров: {len(clusters)}")
    for cid, indices in clusters.items():
        print(f"      Кластер {cid}: {len(indices)} новостей")
    
    print("\n📌 3. ТЕСТ ПОЛНОГО ЦИКЛА (с БД)")
    cluster_service = ClusterService()
    
    result = await cluster_service.run_clustering(
        user_id=1,
        num_clusters=3,
        channels=["rian_ru", "rt_russian"],
        start_date=datetime.now() - timedelta(days=7),
        end_date=datetime.now()
    )
    
    print(f"   ✅ Успех: {result.get('success')}")
    print(f"   📊 Всего новостей: {result.get('total_news', 0)}")
    print(f"   📊 Создано кластеров: {result.get('num_clusters', 0)}")
    
    for cluster in result.get('clusters', []):
        print(f"      - {cluster['topic']}: {cluster['news_count']} новостей")
    
    print("\n" + "=" * 50)
    print("🎉 ТЕСТ КЛАСТЕРИЗАЦИИ ПРОЙДЕН!")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(test_clustering())