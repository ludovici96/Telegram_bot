
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from .base_model import BaseModel

class MessageModel(BaseModel):
    def save_message(self, user_id: int, message_text: str, timestamp: datetime) -> str:
        document = {
            "user_id": user_id,
            "message_text": message_text,
            "timestamp": timestamp
        }
        return self.insert_one(document)

    def get_user_messages(self, user_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        return self.find_many({"user_id": user_id}).limit(limit)

    def get_messages_by_timeframe(self, hours: int = 24) -> List[Dict[str, Any]]:
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return self.find_many({"timestamp": {"$gte": cutoff_time}})

    def delete_old_messages(self, days: int = 30) -> int:
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        result = self.collection.delete_many({"timestamp": {"$lt": cutoff_time}})
        return result.deleted_count