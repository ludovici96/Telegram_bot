import os
import time
from typing import Optional, Dict
import requests
from datetime import datetime, timedelta
import logging
from ..config.settings import NEWS_API_KEY
from .base_service import BaseService

logger = logging.getLogger(__name__)

class NewsService(BaseService):
    def __init__(self, api_key_file: str):
        try:
            with open(api_key_file, 'r') as f:
                self.api_key = f.read().strip()
            logger.debug(f"Initialized NewsService with API key from {api_key_file}")
        except Exception as e:
            logger.error(f"Failed to read API key from {api_key_file}: {e}")
            self.api_key = None
        super().__init__()
        self.base_url = "https://newsapi.org/v2/everything"

    def fetch_news(self, query, limit=5):
        """Fetch news articles based on query"""
        try:
            params = {
                'q': query,
                'apiKey': self.api_key,
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': limit
            }
            
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            
            articles = response.json().get('articles', [])
            
            if not articles:
                return f"No news found for: {query}"
            
            news_text = f"📰 Latest news for: {query}\n\n"
            for article in articles:
                news_text += f"• {article['title']}\n{article['url']}\n\n"
            
            return news_text.strip()
            
        except Exception as e:
            self.logger.error(f"Error fetching news: {e}")
            return f"Error fetching news: {str(e)}"
