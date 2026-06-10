import aiohttp
import json
from typing import Tuple, List, Dict, Any
from app.config import config

class LLMService:
    """Сервис для работы с LLM (Ollama)"""
    
    def __init__(self):
        self.llm_url = config.LLM_URL
        self.llm_model = config.LLM_MODEL
    
    async def generate_topic_and_summary(self, news_texts: List[str]) -> Tuple[str, str]:
        """
        Генерирует тему и краткое саммари для кластера новостей
        Возвращает (topic, summary)
        """
        if not news_texts:
            return ("Без темы", "Нет новостей для анализа")
        
        # Объединяем тексты (ограничиваем длину)
        combined_text = "\n\n".join(news_texts[:5])  # Берём первые 5 новостей
        combined_text = combined_text[:3000]  # Ограничиваем для LLM
        
        prompt = f"""Ты аналитик новостей. Проанализируй следующие новости и выполни задачи:

1. Придумай КОРОТКУЮ тему (2-5 слов), которая объединяет все эти новости
2. Напиши краткий пересказ на русском (2-4 предложения), что произошло

Формат ответа:
ТЕМА: [тема]
ПЕРЕСКАЗ: [пересказ]

Новости:
{combined_text}
"""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.llm_url,
                    json={
                        "model": self.llm_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                        "options": {"num_predict": 500, "temperature": 0.7}
                    },
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status != 200:
                        return ("Новости", f"Ошибка LLM: {response.status}")
                    
                    result = await response.json()
                    content = result.get("message", {}).get("content", "")
                    
                    # Парсим ответ
                    topic = "Новости"
                    summary = content
                    
                    for line in content.split("\n"):
                        if line.startswith("ТЕМА:"):
                            topic = line.replace("ТЕМА:", "").strip()
                        elif line.startswith("ПЕРЕСКАЗ:"):
                            summary = line.replace("ПЕРЕСКАЗ:", "").strip()
                    
                    return (topic[:100], summary[:500])
                    
        except Exception as e:
            print(f"  ❌ Ошибка LLM: {e}")
            return ("Новости", f"Ошибка генерации: {e}")
    
    async def generate_timeline(self, cluster_topic: str, news_items: List[Dict]) -> str:
        """
        Генерирует хронологию событий по кластеру
        """
        if not news_items:
            return "Нет данных для хронологии"
        
        # Сортируем по дате
        sorted_items = sorted(news_items, key=lambda x: x.get('published_at', ''))
        
        timeline_text = f"Хронология: {cluster_topic}\n\n"
        
        for item in sorted_items[:10]:  # Не более 10 событий
            date = item.get('published_at', '').strftime("%Y-%m-%d %H:%M") if item.get('published_at') else "Дата неизвестна"
            text = item.get('news_body', '')[:150]
            timeline_text += f"📅 {date}\n   {text}...\n\n"
        
        return timeline_text[:2000]