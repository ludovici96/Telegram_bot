import os
import logging
import re
import time
import sys
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from .services.groq_service import GroqService
from .services.news_service import NewsService
from .services.web_service import WebService
from .services.whisper_service import WhisperService
from .services.downloader_service import DownloaderService
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
import schedule
import threading
from time import sleep
from .config.settings import (
    TG_API_ID,
    TG_API_HASH,
    TG_BOT_TOKEN,
    ALLOWED_CHAT_ID,
    GROQ_API_KEY,
    MONGODB_URI,
    MONGODB_DB,
    WHISPER_MODEL,
    WHISPER_LANGUAGE
)
from .handlers.command_handlers import register_command_handlers
from .handlers.media_handlers import register_media_handlers
from .handlers.ai_handlers import register_ai_handlers
from .services.currency_service import CurrencyService
from .handlers.message_handlers import MessageHandlers
from .handlers.stats_handler import StatsHandler
from .services.mongodb_service import MongoDBService
from .services.stats_service import StatsService
from .handlers.conversion_handlers import register_conversion_handlers
from .services.crypto_price_service import CryptoPriceService

# Add custom filters to exclude sensitive information
class SensitiveDataFilter(logging.Filter):
    def __init__(self):
        super().__init__()
        # Enhanced patterns for sensitive data
        self.patterns = [
            (r'bot[0-9]+:[A-Za-z0-9-_]+', 'bot:***'),  # Bot tokens
            (r'api_key=[a-zA-Z0-9-_]+', 'api_key=***'),  # API keys
            (r'hash=[a-zA-Z0-9]+', 'hash=***'),  # Hashes
            (r'\b[0-9]{10,}:[A-Za-z0-9_-]{35}\b', 'BOT_TOKEN:***'),  # Telegram bot tokens
            (r'\b[0-9a-f]{32}\b', 'API_HASH:***'),  # API hashes
            (r'\b[0-9]{5,15}\b', 'API_ID:***'),  # API IDs
            (r'Bearer\s+[A-Za-z0-9-_.]+', 'Bearer ***'),  # Bearer tokens
            (r'key-[A-Za-z0-9-_]+', 'key-***'),  # API keys
            (r'mongodb(\+srv)?:\/\/[^\s]+', 'mongodb://*****'),  # MongoDB URIs
            (r'sk-[A-Za-z0-9]{32,}', 'sk-***'),  # API secret keys
            (r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}', 'email@***'),  # Email addresses
            (r'(\d{1,3}\.){3}\d{1,3}', 'IP-ADDR'),  # IP addresses
            (r'password["\']?\s*[:=]\s*["\']?[^"\'\s]+["\']?', 'password=***'),  # Passwords
            (r'secret["\']?\s*[:=]\s*["\']?[^"\'\s]+["\']?', 'secret=***'),  # Secrets
            (r'token["\']?\s*[:=]\s*["\']?[^"\'\s]+["\']?', 'token=***'),  # Tokens
            (r'key["\']?\s*[:=]\s*["\']?[^"\'\s]+["\']?', 'key=***'),  # Generic keys
            # URLs and endpoints
            (r'https?://[^\s<>"]+|www\.[^\s<>"]+', 'URL-REDACTED'),  # URLs
            (r'/v[0-9]+/[^\s]+', 'API-ENDPOINT-REDACTED'),  # API endpoints
            
            # Authentication related
            (r'session["\']?\s*[:=]\s*["\']?[^"\'\s]+["\']?', 'session=***'),  # Session tokens
            (r'auth["\']?\s*[:=]\s*["\']?[^"\'\s]+["\']?', 'auth=***'),  # Auth tokens
            (r'jwt["\']?\s*[:=]\s*["\']?[^"\'\s]+["\']?', 'jwt=***'),  # JWT tokens
            
            # Database related
            (r'database["\']?\s*[:=]\s*["\']?[^"\'\s]+["\']?', 'database=***'),  # Database names
            (r'collection["\']?\s*[:=]\s*["\']?[^"\'\s]+["\']?', 'collection=***'),  # Collection names
            
            # File paths and system info
            (r'/(?:home|Users)/[^\s/]+', '/USER-HOME'),  # Home directories
            (r'[A-Za-z]:\\(?:Users|Documents and Settings)\\[^\s\\]+', 'WIN-USER-PATH'),  # Windows paths
            
            # Cryptocurrency related
            (r'0x[a-fA-F0-9]{40}', 'ETH-ADDRESS'),  # Ethereum addresses
            (r'[13][a-km-zA-HJ-NP-Z1-9]{25,34}', 'BTC-ADDRESS'),  # Bitcoin addresses
            
            # Device and system identifiers
            (r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', 'MAC-ADDRESS'),  # MAC addresses
            (r'([0-9A-Fa-f]{8}[-]?([0-9A-Fa-f]{4}[-]?){3}[0-9A-Fa-f]{12})', 'UUID'),  # UUIDs
        ]

    def filter(self, record):
        if isinstance(record.msg, str):
            record.msg = self._redact_sensitive_data(record.msg)
        if hasattr(record, 'args') and isinstance(record.args, tuple):
            record.args = tuple(
                self._redact_sensitive_data(arg) if isinstance(arg, str) else arg
                for arg in record.args
            )
        return True

    def _redact_sensitive_data(self, text):
        if not isinstance(text, str):
            return text
        
        # Additional custom redactions
        if 'error' in text.lower():
            # Redact detailed error messages
            text = re.sub(r'(error:?).*', r'\1 [REDACTED]', text, flags=re.IGNORECASE)
        
        # Redact numerical sequences that might be sensitive
        text = re.sub(r'\b\d{6,}\b', '[NUMERIC-REDACTED]', text)
        
        # Apply existing patterns
        for pattern, replacement in self.patterns:
            text = re.sub(pattern, replacement, text)
            
        return text

# Add custom filter to exclude ping-pong messages in debug
class PingPongFilter(logging.Filter):
    def filter(self, record):
        return not any(msg in record.getMessage() for msg in ['"_": "types.Pong"', '"_": "functions.PingDelayDisconnect"'])

# Configure logging with filters
logging.basicConfig(
    level=logging.WARNING,  # Ensure this is WARNING
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create and configure the sensitive filter
sensitive_filter = SensitiveDataFilter()

# Apply filter to all relevant loggers
loggers_to_filter = [
    'urllib3.connectionpool',
    'src.telegrambot.bot',  # Uncommented this line
    'pyrogram.session.session',  # Uncommented this line
    'requests',  # Uncommented this line
    'urllib3',
    'http.client',
]

# Set PyMongo logging to WARNING level to hide debug messages
logging.getLogger("pymongo").setLevel(logging.WARNING)
logging.getLogger("pymongo.topology").setLevel(logging.WARNING)
logging.getLogger("pymongo.connection").setLevel(logging.WARNING)

for logger_name in loggers_to_filter:
    logger = logging.getLogger(logger_name)
    logger.addFilter(sensitive_filter)
    # Set level to INFO to reduce debug messages
    logger.setLevel(logging.WARNING)

# Set specific logger levels
logging.getLogger("whisper").setLevel(logging.DEBUG)
logging.getLogger("src.telegrambot.services.whisper_service").setLevel(logging.DEBUG)

# Get the main logger
logger = logging.getLogger(__name__)

# Add ping-pong filter only to pyrogram logger
pyrogram_logger = logging.getLogger("pyrogram.session.session")
pyrogram_logger.addFilter(PingPongFilter())

# Add filter to main logger explicitly
logger.addFilter(sensitive_filter)
logger.setLevel(logging.WARNING)

# Add filter to root logger as well
root_logger = logging.getLogger()
root_logger.addFilter(sensitive_filter)

# Ensure all new loggers get the filter
logging.getLogger().addFilter(sensitive_filter)

# Add after existing logger configurations
def setup_advanced_logging():
    # Filter sensitive data from exception tracebacks
    def custom_excepthook(type, value, tb):
        filtered_value = sensitive_filter._redact_sensitive_data(str(value))
        sys.__excepthook__(type, Exception(filtered_value), tb)
    
    sys.excepthook = custom_excepthook

    # Add filter to werkzeug logger if using Flask
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.addFilter(sensitive_filter)
    
    # Add filter to urllib3 logger
    urllib3_logger = logging.getLogger('urllib3.connectionpool')
    urllib3_logger.addFilter(sensitive_filter)

# Add this line after logger configurations
setup_advanced_logging()

class TelegramBot:
    def __init__(self):
        # Load configuration from secret files
        try:
            with open('/run/secrets/tg_api_id', 'r') as f:
                tg_api_id = f.read().strip()
            with open('/run/secrets/tg_api_hash', 'r') as f:
                tg_api_hash = f.read().strip()
            with open('/run/secrets/tg_bot_token', 'r') as f:
                tg_bot_token = f.read().strip()
            with open('/run/secrets/allowed_chat_id', 'r') as f:
                allowed_chat_id = int(f.read().strip())
        except Exception as e:
            logger.error(f"Failed to load secret files: {e}")
            raise

        self.settings = {
            "TG_API_ID": tg_api_id,
            "TG_API_HASH": tg_api_hash,
            "TG_BOT_TOKEN": tg_bot_token,
            "ALLOWED_CHAT_ID": allowed_chat_id,
            "MONGODB_URI": MONGODB_URI,
            "WHISPER_MODEL": WHISPER_MODEL,
            "WHISPER_LANGUAGE": WHISPER_LANGUAGE
        }

        # Initialize services with secret file paths instead of environment variables
        time.sleep(2)
        self.mongodb_service = MongoDBService(self.settings["MONGODB_URI"])
        time.sleep(1)
        self.stats_service = StatsService(self.mongodb_service)
        time.sleep(1)
        self.groq_service = GroqService('/run/secrets/groq_api_key')
        time.sleep(1)
        self.news_service = NewsService('/run/secrets/news_api_key')
        time.sleep(1)
        self.web_service = WebService()
        time.sleep(1)
        self.whisper_service = WhisperService(model=self.settings["WHISPER_MODEL"])
        time.sleep(1)
        self.currency_service = CurrencyService('/run/secrets/fxrates_api_key')
        time.sleep(1)
        self.crypto_service = CryptoPriceService('/run/secrets/coinmarketcap_key')
        time.sleep(1)
        self.downloader_service = DownloaderService()
        time.sleep(1)

        # Initialize MongoDB connection
        self.db_client = MongoClient(self.settings["MONGODB_URI"])
        self.db = self.db_client['telegram_bot']
        self.message_collection = self.db['messages']

        # Initialize Pyrogram client
        self.app = Client(
            "my_bot_session",
            api_id=self.settings["TG_API_ID"],
            api_hash=self.settings["TG_API_HASH"],
            bot_token=self.settings["TG_BOT_TOKEN"]
        )

        # Register handlers and initialize other components
        self._register_handlers()
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)

        # Update audio directory path
        self.audio_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "src", "audio")
        os.makedirs(self.audio_folder, exist_ok=True)
        logger.info(f"Audio folder set to: {self.audio_folder}")

    def _register_handlers(self):
        message_handlers = MessageHandlers(
            mongodb_service=self.mongodb_service,
            whisper_service=self.whisper_service
        )



        #print("DEBUG: Registering handlers with ALLOWED_CHAT_ID:", self.settings["ALLOWED_CHAT_ID"])

        # Register text handler BEFORE command handlers to ensure text messages are caught first
        @self.app.on_message(filters.chat(self.settings["ALLOWED_CHAT_ID"]) & filters.text & ~filters.regex("^(\\/|https?://)")) 
        async def text_handler(client, message):
            #print(f"DEBUG: Text handler received message: {message.text[:50]}")
            await message_handlers.handle_text(client, message)

        # Now register command handlers
        register_command_handlers(
            self.app,
            mongodb_service=self.mongodb_service,
            stats_service=self.stats_service
        )

        # Register other handlers

        register_media_handlers(self.app)
        register_ai_handlers(self.app)
        register_conversion_handlers(self.app, self.currency_service)

        # Keep existing sticker/voice/photo handlers
        @self.app.on_message(filters.sticker & filters.chat(self.settings["ALLOWED_CHAT_ID"]))
        async def sticker_handler(client, message):
            await message_handlers.handle_sticker(client, message)

        @self.app.on_message(filters.voice & filters.chat(self.settings["ALLOWED_CHAT_ID"]))
        async def voice_handler(client, message):
            await message_handlers.handle_voice(client, message)

        @self.app.on_message(filters.photo & filters.chat(self.settings["ALLOWED_CHAT_ID"]))
        async def photo_handler(client, message):
            await message_handlers.handle_photo(client, message)

    def _store_message(self, message):
        """Store message in MongoDB"""
        message_data = {
            'message_id': message.id,
            'user_id': message.from_user.id,
            'message_text': message.text,
            'timestamp': datetime.now(timezone.utc)
        }
        self.message_collection.insert_one(message_data)

    def _get_messages_last_24_hours(self):
        """Retrieve messages from the last 24 hours"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=1)
        messages = self.message_collection.find(
            {'timestamp': {'$gte': cutoff_time}},
            {'message_text': 1}
        )
        return [msg['message_text'] for msg in messages]

    def _get_user_messages(self, user_id):
        """Retrieve messages for a specific user"""
        messages = self.message_collection.find(
            {'user_id': user_id},
            {'message_text': 1}
        )
        return [msg['message_text'] for msg in messages]

    def _run_scheduler(self):
        """Run the scheduler for periodic tasks"""
        while True:
            schedule.run_pending()
            sleep(1)

    def run(self):
        """Start the bot"""
        logger.info("Starting bot...")
        self.scheduler_thread.start()
        while True:
            try:
                self.app.run()
            except FloodWait as e:
                logger.warning(f"Hit flood wait limit. Sleeping for {e.value} seconds")
                sleep(e.value)
                continue

def main():
    """Main entry point for the bot"""
    bot = TelegramBot()
    bot.run()

if __name__ == "__main__":
    main()