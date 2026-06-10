import aiohttp
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from datetime import datetime
from urllib.parse import urljoin
import re

class LentaParser:
    """Реальный парсер Lenta.ru"""
    
    BASE_URL = "https://lenta.ru"
    
    async def parse(self, limit: int = 30) -> List[Dict[str, Any]]:
        news_list = []
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(self.BASE_URL, timeout=30) as response:
                    if response.status != 200:
                        print(f"Lenta.ru: HTTP {response.status}")
                        return []
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Берём все ссылки с главной
                    all_links = soup.find_all('a', href=True)
                    
                    for link in all_links:
                        href = link.get('href', '')
                        title = link.get_text(strip=True)
                        
                        if not href or not title or len(title) < 30:
                            continue
                        
                        # Фильтруем только новости
                        if '/news/' in href or '/articles/' in href or href.startswith('/202'):
                            if href.startswith('/'):
                                full_url = self.BASE_URL + href
                            else:
                                full_url = href
                            
                            # Получаем полный текст статьи
                            full_text = await self._get_article_text(full_url, session)
                            
                            news_list.append({
                                'published_at': datetime.now(),
                                'channel': 'Lenta.ru',
                                'news_body': full_text if full_text else title,
                                'news_link': full_url,
                                'views': 0,
                                'forwarded': 0,
                                'subject': title[:100],
                                'source': 'LENTA'
                            })
                            
                            if len(news_list) >= limit:
                                break
                    
                    print(f"Lenta.ru: спарсено {len(news_list)} новостей")
                    return news_list
                    
            except Exception as e:
                print(f"Lenta.ru ошибка: {e}")
                return []
    
    async def _get_article_text(self, url: str, session) -> str:
        """Получает полный текст статьи"""
        try:
            async with session.get(url, timeout=15) as response:
                if response.status != 200:
                    return ""
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Ищем текст статьи
                article_body = soup.find('div', class_='article__text')
                if not article_body:
                    article_body = soup.find('div', class_='b-article__text')
                if not article_body:
                    article_body = soup.find('div', class_='news-text')
                if not article_body:
                    article_body = soup.find('article')
                
                if article_body:
                    paragraphs = article_body.find_all('p')
                    text = ' '.join([p.get_text(strip=True) for p in paragraphs])
                    return text[:2000]
                
                return ""
        except Exception:
            return ""