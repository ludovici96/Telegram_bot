from pyrogram import Client, filters
import re
import os
from ..services.mongodb_service import MongoDBService
from ..services.whisper_service import WhisperService
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class MessageHandlers:
    def __init__(self, mongodb_service: MongoDBService, whisper_service: WhisperService):
        self.db = mongodb_service
        self.whisper = whisper_service

    async def handle_text(self, client, message):
        """Handle text messages"""
        try:
            logger.debug("Handling text message")
            user_id = message.from_user.id
            text_length = len(message.text)

            # Store the actual message with complete user information
            message_data = {
                'message_id': message.id,
                'user_id': user_id,
                'chat_id': message.chat.id,
                'message_text': message.text,
                'timestamp': datetime.now(timezone.utc),
                'from_user': {
                    'id': message.from_user.id,
                    'username': message.from_user.username,
                    'first_name': message.from_user.first_name,
                    'last_name': message.from_user.last_name
                }
            }
            self.db.store_message(message_data)
            
            # Update user stats with both message stats and user information
            stats_update = {
                "text_messages": 1,
                "total_chars": text_length,
                "username": message.from_user.username,
                "first_name": message.from_user.first_name,
                "last_name": message.from_user.last_name,
                "last_active": datetime.now(timezone.utc)
            }
            
            self.db.update_user_stats(user_id, stats_update)

            current_time = datetime.now(timezone.utc)
            # Store metadata for activity tracking
            metadata = {
                "user_id": user_id,
                "username": message.from_user.username,
                "first_name": message.from_user.first_name,
                "last_name": message.from_user.last_name,
                "message_type": "text",
                "message_date": current_time.strftime("%Y-%m-%d"),
                "day_of_week": current_time.strftime("%A"),
                "week_number": current_time.strftime("%U")
            }
            
            # If message is a reply, update popularity
            if message.reply_to_message and message.reply_to_message.from_user:
                replied_to_user = message.reply_to_message.from_user.id
                self.db.update_popularity(replied_to_user)
                
            self.db.store_metadata(metadata)
            
        except Exception as e:
            logger.error(f"Error handling text message: {e}", exc_info=True)

    async def handle_sticker(self, client, message):
        """Handle sticker messages"""
        try:
            logger.debug("Handling sticker message")
            user_id = message.from_user.id
            self.db.update_user_stats(
                user_id,
                {"stickers": 1}
            )
            # Store metadata like text messages
            current_time = datetime.now(timezone.utc)
            self.db.store_metadata({
                "user_id": user_id,
                "message_date": current_time.strftime("%Y-%m-%d"),
                "day_of_week": current_time.strftime("%A"),
                "week_number": current_time.strftime("%U")
            })
        except Exception as e:
            logger.error(f"Error handling sticker: {e}", exc_info=True)

    async def handle_voice(self, client, message):
        """Handle voice messages"""
        try:
            # Update stats first
            self.db.user_stats.update_one(
                {'user_id': message.from_user.id},
                {'$inc': {'voices': 1}},
                upsert=True
            )

            # Download voice message directly to the audio folder
            voice_file = await message.download(
                file_name=os.path.join(self.whisper.audio_folder, f"{message.voice.file_unique_id}.ogg")
            )
            
            if voice_file:
                try:
                    transcription = self.whisper.transcribe(voice_file)
                    if transcription:
                        await message.reply_text(
                            f"🎙️ Transcription:\n{transcription}",
                            quote=True
                        )
                    else:
                        await message.reply_text(
                            "❌ Could not transcribe audio",
                            quote=True
                        )
                except Exception as e:
                    logger.error(f"Error transcribing voice message: {e}")
                    await message.reply_text(
                        "❌ Error transcribing voice message",
                        quote=True
                    )

        except Exception as e:
            logger.error(f"Error handling voice message: {e}")
            await message.reply_text("❌ Error processing voice message")

    async def handle_photo(self, client, message):
        """Handle image messages"""
        self.db.user_stats.update_one(  # Remove await
            {'user_id': message.from_user.id},
            {'$inc': {'images_posted': 1}},
            upsert=True
        )