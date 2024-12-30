from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from typing import Optional
import tldextract

class WebService:
    def __init__(self):
        self.blocked_domains = {'example.com', 'malicious.com'}  # Add blocked domains u dont like or what to be used.
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def is_safe_url(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            ext = tldextract.extract(url)
            domain = f"{ext.domain}.{ext.suffix}"
            return all([
                parsed.scheme in ('http', 'https'),
                domain not in self.blocked_domains,
                not any(c in url for c in ['<', '>', '"', "'"]),
            ])
        except Exception:
            return False

    def scrape_web_content(self, url: str) -> str:
        if not self.is_safe_url(url):
            return "Invalid or unsafe URL"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer']):
                element.decompose()
                
            return soup.get_text(strip=True)[:4000]
        except Exception as e:
            print(f"Error fetching web content: {str(e)}")
            return "Error fetching web content."

    def extract_x_com_content(self, url: str) -> str:
        if not self.is_safe_url(url):
            return "Invalid or unsafe URL"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            tweet_content = soup.find('div', {'data-testid': 'tweetText'})
            if tweet_content:
                return tweet_content.get_text(strip=True)
            
            article = soup.find('article')
            if article:
                paragraphs = article.find_all('p')
                return ' '.join([p.get_text(strip=True) for p in paragraphs])
            
            return "Unable to extract X.com post content."
        except Exception as e:
            print(f"Error extracting X.com content: {str(e)}")
            return "Error extracting X.com post content."
