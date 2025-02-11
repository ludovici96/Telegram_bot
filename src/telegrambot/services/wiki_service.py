import wikipediaapi
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class WikiService:
    def __init__(self):
        self.wiki = wikipediaapi.Wikipedia(
            language='en',
            extract_format=wikipediaapi.ExtractFormat.WIKI,
            user_agent='TelegramBot/1.0'
        )
        
        # Emoji mappings for different content types
        self.emojis = {
            'search': '🔍',
            'article': '📄',
            'summary': '📝',
            'reference': '📚',
            'link': '🔗',
            'error': '⚠️',
            'success': '✅',
            'disambiguation': '❓'
        }

        # Add section type emojis
        self.section_emojis = {
            'history': '📅',
            'overview': '📋',
            'description': '📝',
            'biography': '👤',
            'career': '💼',
            'early life': '👶',
            'education': '🎓',
            'works': '📚',
            'legacy': '🏆',
            'death': '✝️',
            'personal life': '👥',
            'politics': '🏛️',
            'science': '🔬',
            'technology': '💻',
            'sports': '⚽',
            'arts': '🎨',
            'music': '🎵',
            'awards': '🏆',
            'controversy': '⚠️',
            'see also': '👉',
            'references': '📚',
            'external links': '🔗',
            'notes': '📝'
        }

    def _format_section_title(self, title: str) -> str:
        """Format section title with appropriate emoji"""
        lower_title = title.lower()
        for key, emoji in self.section_emojis.items():
            if key in lower_title:
                return f"{emoji} {title}"
        return f"📌 {title}"

    async def search_wikipedia(self, query: str, limit: int = 3) -> Dict:
        """Search Wikipedia articles"""
        try:
            if not query or len(query.strip()) == 0:
                return {
                    "status": "error",
                    "message": f"{self.emojis['error']} Empty search query"
                }
                
            page = self.wiki.page(query)
            
            if not page.exists():
                return {
                    "status": "error",
                    "message": f"{self.emojis['error']} No articles found for '{query}'"
                }
                
            # Validate page content
            if not page.summary or len(page.summary.strip()) == 0:
                return {
                    "status": "error",
                    "message": f"{self.emojis['error']} Article found but content is empty"
                }
                
            # Fix disambiguation check
            if "may refer to:" in page.summary.lower() or "disambiguation" in page.title.lower():
                # Handle disambiguation pages
                disamb_links = []
                for link in list(page.links.keys())[:limit]:
                    link_page = self.wiki.page(link)
                    if link_page.exists() and "disambiguation" not in link_page.title.lower():
                        disamb_links.append({
                            "title": link,
                            "summary": link_page.summary[:100] + "..."
                        })
                
                return {
                    "status": "disambiguation",
                    "message": f"{self.emojis['disambiguation']} Multiple matches found",
                    "results": disamb_links
                }
            
            # For recent/future events, check the summary for specific dates
            if any(year in page.summary for year in ['2024', '2025']):
                return {
                    "status": "success",
                    "result": {
                        "title": page.title,
                        "summary": page.summary,
                        "url": page.fullurl,
                        "is_recent": True,
                        "last_modified": page.touched  # Add last modified date
                    }
                }
            
            return {
                "status": "success",
                "result": {
                    "title": page.title,
                    "summary": page.summary,
                    "url": page.fullurl,
                    "is_recent": False
                }
            }
            
        except Exception as e:
            logger.error(f"Error searching Wikipedia: {e}")
            return {
                "status": "error",
                "message": f"{self.emojis['error']} Error searching Wikipedia. Please try again."
            }

    async def get_article_summary(self, title: str, max_length: int = 1500) -> Dict:
        """Get a concise summary of a Wikipedia article"""
        try:
            page = self.wiki.page(title)
            
            if not page.exists():
                return {
                    "status": "error",
                    "message": f"{self.emojis['error']} Article not found: '{title}'"
                }
            
            # Format the summary with sections
            formatted_summary = f"{self.emojis['article']} **{page.title}**\n\n"
            formatted_summary += f"{self.emojis['summary']} **Quick Summary:**\n{page.summary[:max_length]}...\n\n"
            
            # Add metadata
            formatted_summary += f"\n{self.emojis['reference']} **Article Info:**\n"
            formatted_summary += f"• References: {len(page.references)}\n"
            formatted_summary += f"• Sections: {len(page.sections)}\n"
            formatted_summary += f"• {self.emojis['link']} Full article: {page.fullurl}\n"
                
            return {
                "status": "success",
                "result": {
                    "title": page.title,
                    "formatted_content": formatted_summary,
                    "url": page.fullurl,
                    "references": len(page.references),
                    "sections": len(page.sections)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting article summary: {e}")
            return {
                "status": "error",
                "message": f"{self.emojis['error']} Error fetching article summary: {str(e)}"
            }

    async def get_article_sections(self, title: str) -> Dict:
        """Get the section structure of a Wikipedia article"""
        try:
            page = self.wiki.page(title)
            
            if not page.exists():
                return {
                    "status": "error",
                    "message": f"{self.emojis['error']} Article not found: '{title}'"
                }
                
            formatted_sections = []
            current_section = None
            
            for section in page.sections:
                # Format section based on level
                if section.level == 0:  # Main sections
                    current_section = {
                        "title": self._format_section_title(section.title),
                        "content": section.text[:300] + "..." if len(section.text) > 300 else section.text,
                        "subsections": []
                    }
                    formatted_sections.append(current_section)
                else:  # Subsections
                    if current_section:
                        current_section["subsections"].append({
                            "title": self._format_section_title(section.title),
                            "content": section.text[:200] + "..." if len(section.text) > 200 else section.text
                        })
                
            return {
                "status": "success",
                "result": {
                    "title": f"{self.emojis['article']} {page.title}",
                    "url": page.fullurl,
                    "sections": formatted_sections,
                    "total_sections": len(page.sections),
                    "last_modified": getattr(page, "touched", "Unknown")
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting article sections: {e}")
            return {
                "status": "error",
                "message": f"{self.emojis['error']} Error fetching article sections: {str(e)}"
            }
