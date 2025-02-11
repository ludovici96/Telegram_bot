
from typing import List
from urllib.parse import urlparse
import re

def extract_urls(text: str) -> List[str]:
    """
    Extract URLs from text.
    
    Args:
        text (str): Text to extract URLs from
    
    Returns:
        List[str]: List of extracted URLs
    """
    return re.findall(r'(https?://\S+)', text)

def is_valid_url(url: str) -> bool:
    """
    Check if a URL is valid.
    
    Args:
        url (str): URL to validate
    
    Returns:
        bool: True if URL is valid, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def chunk_text(text: str, chunk_size: int = 4096) -> List[str]:
    """
    Split text into chunks of specified size.
    
    Args:
        text (str): Text to split
        chunk_size (int): Maximum size of each chunk
    
    Returns:
        List[str]: List of text chunks
    """
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

def truncate_text(text: str, max_length: int = 4096, suffix: str = "...") -> str:
    """
    Truncate text to specified length.
    
    Args:
        text (str): Text to truncate
        max_length (int): Maximum length of text
        suffix (str): String to append to truncated text
    
    Returns:
        str: Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix