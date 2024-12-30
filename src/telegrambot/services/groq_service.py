import os
import logging
import aiohttp
import json
from dotenv import load_dotenv
from groq import AsyncGroq
from datetime import datetime, timedelta
from pymongo import MongoClient
from ..config.settings import GROQ_API_KEY, MONGODB_URI
from .base_service import BaseService
import base64
from .weather_service import WeatherService
from .wiki_service import WikiService  # Add this import
from ..utils.file_utils import clear_directory  # Add this import

logger = logging.getLogger(__name__)

VISION_MODEL = "llama-3.2-90b-vision-preview"
TEXT_MODEL = "llama-3.3-70b-versatile"
TEXT_MODEL_MAX_TOKENS = 32768  # Max output tokens for TEXT_MODEL
VISION_MODEL_MAX_TOKENS = 4096  # Default max tokens for vision model
TELEGRAM_MAX_LENGTH = 4096

class GroqService(BaseService):
    def __init__(self, api_key_file: str):
        super().__init__()
        load_dotenv()
        try:
            with open(api_key_file, 'r') as f:
                self.api_key = f.read().strip()
            logger.debug(f"Initialized GroqService with API key from {api_key_file}")
        except Exception as e:
            logger.error(f"Failed to read API key from {api_key_file}: {e}")
            self.api_key = None
            
        # Initialize other services with correct secret paths
        self.weather_service = WeatherService('/run/secrets/openweather_api_key')
        self.wiki_service = WikiService()
        
        self.client = AsyncGroq(api_key=self.api_key)
        self.db_client = MongoClient(MONGODB_URI)
        self.db = self.db_client['telegram_bot']
        self.message_collection = self.db['messages']
        self.downloads_dir = "./downloads"
        os.makedirs(self.downloads_dir, exist_ok=True)

    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def cleanup_downloads(self):
        """Clean up the downloads directory"""
        try:
            clear_directory(self.downloads_dir)
            logger.debug("Cleaned up downloads directory")
        except Exception as e:
            logger.error(f"Error cleaning up downloads directory: {e}")

    def _split_response(self, text: str) -> list[str]:
        """Split long responses into Telegram-friendly chunks"""
        if len(text) <= TELEGRAM_MAX_LENGTH:
            return [text]
            
        parts = []
        while text:
            if len(text) <= TELEGRAM_MAX_LENGTH:
                parts.append(text)
                break
                
            # Find the last complete sentence within the limit
            split_index = text[:TELEGRAM_MAX_LENGTH].rfind('. ') + 1
            if split_index <= 0:  # No sentence break found, fall back to space
                split_index = text[:TELEGRAM_MAX_LENGTH].rfind(' ') + 1
            if split_index <= 0:  # No space found, just split at limit
                split_index = TELEGRAM_MAX_LENGTH
                
            parts.append(text[:split_index])
            text = text[split_index:].strip()
            
        return parts

    async def generate_ai_response(self, prompt: str, image_path: str = None, force_wiki: bool = False) -> str | list[str]:
        try:
            if not prompt or not prompt.strip():
                return "Please provide a valid question or prompt."

            messages = []
            
            # Choose model and max tokens based on whether we're processing an image
            model = VISION_MODEL if image_path else TEXT_MODEL
            max_tokens = VISION_MODEL_MAX_TOKENS if image_path else TEXT_MODEL_MAX_TOKENS
            
            # Prepare request parameters
            request_params = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": 0.7,  # Add temperature for more natural responses
            }

            if image_path:
                try:
                    base64_image = self.encode_image(image_path)
                    messages.append({
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    })
                finally:
                    self.cleanup_downloads()
            else:
                # Add system message only for non-image requests
                if force_wiki:
                    messages.append({
                        "role": "system",
                        "content": """Format Wikipedia content clearly:
1. Use bold for article titles and section headings
2. Keep emojis provided in the content
3. Maintain proper paragraph breaks
4. Include source links at the end
5. For disambiguation pages, list alternatives with bullet points
6. Highlight important dates and facts"""
                    })
                else:
                    messages.append({
                        "role": "system",
                        "content": """Provide brief, focused responses in 2-3 sentences unless specifically asked for more detail. Be direct and highlight only the most important points.

Only use tools for:
1. Weather and Air Quality Queries:
   - Use weather/air quality tools for current conditions
   - Show temperatures in both °C and °F
   - Include relevant weather emojis
   - Format air quality data with appropriate units

For all other queries (philosophical, historical, analytical, etc.), provide a concise response without using any tools."""
                    })
                messages.append({"role": "user", "content": prompt})
                
                # Define available tools based on force_wiki
                tools = []
                if force_wiki:
                    tools.append({
                        "type": "function",
                        "function": {
                            "name": "wiki_search",
                            "description": "Search Wikipedia for information",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string", "description": "Search term"},
                                    "limit": {"type": "integer", "default": 3}
                                },
                                "required": ["query"]
                            }
                        }
                    })
                else:
                    tools.extend([
                        {
                            "type": "function",
                            "function": {
                                "name": "get_weather",
                                "description": "Get current weather information for a location",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "location": {"type": "string", "description": "City name or coordinates"},
                                        "units": {"type": "string", "enum": ["metric", "imperial"], "default": "metric"}
                                    },
                                    "required": ["location"]
                                }
                            }
                        },
                        {
                            "type": "function",
                            "function": {
                                "name": "get_forecast",
                                "description": "Get weather forecast for a location",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "location": {"type": "string", "description": "City name or coordinates"},
                                        "units": {"type": "string", "enum": ["metric", "imperial"], "default": "metric"}
                                    },
                                    "required": ["location"]
                                }
                            }
                        },
                        {
                            "type": "function",
                            "function": {
                                "name": "get_air_quality",
                                "description": "Get current air quality information for a location",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "location": {"type": "string", "description": "City name or coordinates"}
                                    },
                                    "required": ["location"]
                                }
                            }
                        }
                    ])
                
                if tools:
                    request_params["tools"] = tools
                    request_params["tool_choice"] = "auto"

            request_params["messages"] = messages
            chat_completion = await self.client.chat.completions.create(**request_params)

            # Handle tool calls only for non-image requests
            if (not image_path and 
                hasattr(chat_completion.choices[0].message, 'tool_calls') and 
                chat_completion.choices[0].message.tool_calls):
                
                tool_call = chat_completion.choices[0].message.tool_calls[0]
                args = json.loads(tool_call.function.arguments)
                
                tool_response = None
                if tool_call.function.name == "wiki_search":
                    tool_response = await self.wiki_service.search_wikipedia(
                        query=args["query"],
                        limit=args.get("limit", 3)
                    )
                elif tool_call.function.name == "get_weather":
                    tool_response = await self.weather_service.get_current_weather(
                        location=args["location"],
                        units=args.get("units", "metric")
                    )
                elif tool_call.function.name == "get_forecast":
                    tool_response = await self.weather_service.get_forecast(
                        location=args["location"],
                        units=args.get("units", "metric")
                    )
                elif tool_call.function.name == "get_air_quality":
                    tool_response = await self.weather_service.get_air_quality(
                        location=args["location"]
                    )

                if tool_response:
                    if tool_call.function.name.startswith("wiki_"):
                        messages.append({
                            "role": "system",
                            "content": """Format Wikipedia content clearly:
1. Use bold for article titles and section headings
2. Keep emojis provided in the content
3. Maintain proper paragraph breaks
4. Include source links at the end
5. For disambiguation pages, list alternatives with bullet points
6. Highlight important dates and facts"""
                        })
                    elif tool_call.function.name == "get_forecast":
                        messages.append({
                            "role": "system",
                            "content": """Format forecast data clearly:
1. Group by date with clear headings
2. Show temperatures in both units
3. Include weather emojis for conditions
4. Show precipitation chances
5. Use proper spacing and time periods"""
                        })
                    
                    messages.extend([
                        {"role": "assistant", "content": None, "tool_calls": [tool_call]},
                        {"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(tool_response)}
                    ])
                    
                    # Add system message for formatting air quality responses
                    if tool_call.function.name == "get_air_quality":
                        messages.append({
                            "role": "system",
                            "content": """Format air quality data clearly:
1. Show AQI rating with emoji
2. List all pollutants with units
3. Include health recommendations if available
4. Use proper spacing and formatting"""
                        })
                    
                    final_response = await self.client.chat.completions.create(
                        messages=messages,
                        model=TEXT_MODEL  # Use TEXT_MODEL for final response
                    )
                    return final_response.choices[0].message.content

            # Add validation for the response
            response = chat_completion.choices[0].message.content
            if not response or not response.strip():
                return "I received an empty response. Please try asking your question differently."

            response = response.strip()
            # Split response if it exceeds Telegram's limit
            if len(response) > TELEGRAM_MAX_LENGTH:
                return self._split_response(response)
            return response
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return f"I encountered an error while processing your request: {str(e)}"

    async def generate_summary(self, messages, time_range=None):
        if not messages:
            return "No messages to summarize."
            
        try:
            # Limit and chunk messages for processing
            MAX_MESSAGES = 1000  # Maximum messages to process
            MAX_CHUNK_SIZE = 15000  # Characters per chunk
            
            # Take only the most recent messages if we have too many
            messages = messages[-MAX_MESSAGES:]
            
            # Join messages and split into chunks
            input_text = " ".join(messages)
            chunks = []
            current_chunk = ""
            
            for message in input_text.split('\n'):
                if len(current_chunk) + len(message) > MAX_CHUNK_SIZE:
                    chunks.append(current_chunk)
                    current_chunk = message
                else:
                    current_chunk += "\n" + message if current_chunk else message
                    
            if current_chunk:
                chunks.append(current_chunk)
                
            # Process each chunk
            summaries = []
            for chunk in chunks:
                system_prompt = """Provide a very concise summary of this chat conversation fragment.
Focus on main topics and key points only.
Keep the summary short and direct.
Avoid mentioning timestamps or specific details."""

                response = await self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Summarize these messages{f' from {time_range}' if time_range else ''}:\n\n{chunk}"}
                    ],
                    model=TEXT_MODEL,
                    max_tokens=2000,
                    temperature=0.7
                )
                
                summaries.append(response.choices[0].message.content.strip())
                
            # If we have multiple summaries, combine them
            if len(summaries) > 1:
                final_summary = await self.client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": "Combine these summary fragments into one coherent, concise summary. Focus on the main points and remove any redundancy."
                        },
                        {
                            "role": "user",
                            "content": "\n\n".join(summaries)
                        }
                    ],
                    model=TEXT_MODEL,
                    max_tokens=2000,
                    temperature=0.7
                )
                summary = final_summary.choices[0].message.content.strip()
            else:
                summary = summaries[0] if summaries else "No meaningful content to summarize."
                
            # Split if exceeds Telegram's limit
            if len(summary) > TELEGRAM_MAX_LENGTH:
                return self._split_response(summary)
            return summary
                
        except Exception as e:
            logger.error(f"Error generating summary: {e}", exc_info=True)
            # Return a more specific error message
            return f"Could not generate summary: {str(e)[:100]}... Please try with a shorter time range or fewer messages."

    async def generate_greentext(self, prompt: str) -> str:
        # Update greentext generation to use TEXT_MODEL
        try:
            messages = [
                {
                    "role": "system",
                    "content": """You are a 4chan greentext story generator. Create a short, humorous story in greentext format following these rules:
1. Each line must start with '>'
2. Keep it concise and entertaining
3. Use first-person perspective
4. Include typical 4chan storytelling elements and humor
5. Keep it relatively short (5-10 lines)
6. Make it relate to the given prompt
7. Use common 4chan terminology and style
8. End with some kind of punchline or twist"""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            response = await self.client.chat.completions.create(
                messages=messages,
                model=TEXT_MODEL,  # Use TEXT_MODEL for greentext
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error generating greentext: {e}")
            return f"Error generating greentext: {str(e)}"

    def get_user_messages(self, user_id, limit=100):  # Increased from 50 to 100
        try:
            messages = self.message_collection.find(
                {'user_id': user_id},
                {'message_text': 1}
            ).sort('timestamp', -1).limit(limit)
            return [msg['message_text'] for msg in messages]
        except Exception as e:
            logger.error(f"Error retrieving user messages: {e}")
            return []

    def get_messages_last_24_hours(self):
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=1)
            # Increased limit since we can handle more context
            messages = self.message_collection.find(
                {'timestamp': {'$gte': cutoff_time}},
                {'message_text': 1}
            ).limit(1000)  # Increased from default to 1000
            return [msg['message_text'] for msg in messages]
        except Exception as e:
            logger.error(f"Error retrieving messages: {e}")
            return []

# Create functions for direct import
def generate_ai_response(prompt):
    service = GroqService()
    return service.generate_ai_response(prompt)

def get_user_messages(user_id, limit=50):
    service = GroqService()
    return service.get_user_messages(user_id, limit)

def get_messages_last_24_hours():
    service = GroqService()
    return service.get_messages_last_24_hours()
