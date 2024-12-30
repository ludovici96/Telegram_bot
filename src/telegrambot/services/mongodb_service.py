from pymongo import MongoClient, ASCENDING
from pymongo.errors import OperationFailure
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)

class MongoDBService:
    def __init__(self, uri):
        self.client = MongoClient(uri)
        self.db = self.client['telegram_bot']
        
        # Initialize collections
        self.user_stats = self.db['user_stats']
        self.popularity = self.db['popularity']
        self.message_metadata = self.db['message_metadata']
        self.messages = self.db['messages']
        
        # Create indexes safely
        self._ensure_indexes()

    def _ensure_indexes(self):
        """Ensure all required indexes exist"""
        indexes = {
            'user_stats': [
                {'keys': [('user_id', ASCENDING)], 'unique': True}
            ],
            'popularity': [
                {'keys': [('user_id', ASCENDING)]}
            ],
            'message_metadata': [
                {'keys': [('user_id', ASCENDING)]},
                {'keys': [('message_date', ASCENDING)]},
                {'keys': [('day_of_week', ASCENDING)]},
                {'keys': [('week_number', ASCENDING)]}
            ],
            'messages': [
                {'keys': [('user_id', ASCENDING)]},
                {'keys': [('timestamp', ASCENDING)]}
            ]
        }

        for collection_name, collection_indexes in indexes.items():
            collection = self.db[collection_name]
            
            try:
                existing_indexes = list(collection.list_indexes())
                existing_keys = [
                    tuple((k, v) for k, v in idx['key'].items())
                    for idx in existing_indexes
                ]

                for index_spec in collection_indexes:
                    keys = index_spec['keys']
                    index_key = tuple((k, v) for k, v in keys)
                    
                    if index_key not in existing_keys:
                        try:
                            collection.create_index(
                                keys,
                                unique=index_spec.get('unique', False)
                            )
                            logger.info(f"Created index {index_key} on {collection_name}")
                        except OperationFailure as e:
                            logger.warning(f"Failed to create index on {collection_name}: {e}")
                            continue

            except Exception as e:
                logger.error(f"Error managing indexes for collection {collection_name}: {e}")
                continue

    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user statistics"""
        return self.user_stats.find_one({"user_id": user_id})

    def update_user_stats(self, user_id: int, update_data: Dict[str, Any], upsert: bool = True) -> None:
        """Update user statistics with the given data"""
        try:
            logger.debug(f"Attempting to update stats for user {user_id}")
            current_stats = self.get_user_stats(user_id)
            logger.debug(f"Current stats before update: {current_stats}")
            
            # Separate increment fields from set fields
            inc_fields = {}
            set_fields = {}
            
            for key, value in update_data.items():
                if key in ['text_messages', 'total_chars', 'media_messages', 'stickers', 'voices', 'images_posted', 'commands_used', 'warnings', 'gay_count', 'reply_count']:
                    inc_fields[key] = value
                else:
                    set_fields[key] = value
            
            # Initialize all counters if they don't exist
            init_result = self.user_stats.update_one(
                {"user_id": user_id},
                {"$setOnInsert": {
                    "text_messages": 0,
                    "total_chars": 0,
                    "media_messages": 0,
                    "stickers": 0,
                    "voices": 0,
                    "images_posted": 0,
                    "commands_used": 0,
                    "warnings": 0,
                    "gay_count": 0,
                    "reply_count": 0,
                    "joined_date": datetime.now(timezone.utc)
                }},
                upsert=True
            )
            
            # Build update dictionary
            update_dict = {}
            if inc_fields:
                update_dict["$inc"] = inc_fields
            if set_fields:
                update_dict["$set"] = set_fields
            
            # Perform the update
            result = self.user_stats.update_one(
                {"user_id": user_id},
                update_dict,
                upsert=False
            )
            
            logger.debug(f"Update result - matched: {result.matched_count}, modified: {result.modified_count}")
            final_stats = self.get_user_stats(user_id)
            logger.debug(f"Stats after update: {final_stats}")
            
        except Exception as e:
            logger.error(f"Error updating user stats: {str(e)}", exc_info=True)

    def store_message(self, message_data: Dict[str, Any]) -> None:
        """Store a message in the messages collection"""
        try:
            # Ensure message has timestamp in UTC
            if 'timestamp' not in message_data:
                message_data['timestamp'] = datetime.now(timezone.utc)
                
            result = self.messages.insert_one(message_data)
            logger.debug(f"Stored message {result.inserted_id} for user {message_data.get('user_id')} in chat {message_data.get('chat_id')}")
        except Exception as e:
            logger.error(f"Error storing message: {e}")

    def get_messages_last_24_hours(self, chat_id=None):
        """Retrieve messages from the last 24 hours"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=1)
            query = {'timestamp': {'$gte': cutoff_time}}
            
            # Add chat_id filter if provided
            if chat_id:
                query['chat_id'] = chat_id
                
            cursor = self.messages.find(
                query,
                {'message_text': 1}
            ).sort('timestamp', -1).limit(1000)
            
            return [msg['message_text'] for msg in cursor if msg.get('message_text')]
        except Exception as e:
            logger.error(f"Error retrieving messages: {e}")
            return []

    def store_metadata(self, metadata: Dict[str, Any]) -> None:
        """Store message metadata"""
        try:
            result = self.message_metadata.insert_one(metadata)
            logger.debug(f"Stored metadata {result.inserted_id}")
        except Exception as e:
            logger.error(f"Error storing metadata: {e}")

    def update_popularity(self, user_id: int, increment: int = 1) -> None:
        """Update user popularity count"""
        try:
            result = self.popularity.update_one(
                {"user_id": user_id},
                {"$inc": {"reply_count": increment}},
                upsert=True
            )
            logger.debug(f"Updated popularity for user {user_id}")
        except Exception as e:
            logger.error(f"Error updating popularity: {e}")

    def get_user_activity(self, user_id: int, days: int) -> List[Dict[str, Any]]:
        """Get user activity for the last N days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        pipeline = [
            {"$match": {
                "user_id": user_id,
                "message_date": {"$gte": cutoff_date.strftime("%Y-%m-%d")}
            }},
            {"$group": {
                "_id": "$message_date",
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        return list(self.message_metadata.aggregate(pipeline))

    def cleanup_old_messages(self, days_to_keep: int = 30) -> None:
        """Remove messages older than specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        result = self.messages.delete_many({"timestamp": {"$lt": cutoff_date}})
        logger.info(f"Cleaned up {result.deleted_count} messages older than {days_to_keep} days")

    def get_collection(self, collection_name: str):
        """Get a MongoDB collection by name"""
        return self.db[collection_name]

    def close(self):
        """Close the MongoDB connection"""
        self.client.close()

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        self.close()