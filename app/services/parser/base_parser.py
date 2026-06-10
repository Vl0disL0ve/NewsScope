from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime

class BaseParser(ABC):
    """Базовый класс для всех парсеров"""
    
    @abstractmethod
    async def parse(self) -> List[Dict[str, Any]]:
        """
        Парсит новости и возвращает список словарей с полями:
        {
            'published_at': datetime,
            'channel': str,
            'news_body': str,
            'news_link': str,
            'views': int,
            'forwarded': int,
            'subject': str (опционально),
            'source': str ('LENTA' или 'TG')
        }
        """
        pass
    
    def _clean_text(self, text: str) -> str:
        """Очищает текст от лишних пробелов и символов"""
        if not text:
            return ""
        import re
        text = re.sub(r'\s+', ' ', text)
        return text.strip()