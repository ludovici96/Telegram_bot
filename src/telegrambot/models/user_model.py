
from datetime import datetime
from typing import Dict, Any, Optional
from .base_model import BaseModel

class UserModel(BaseModel):
    def create_user(self, user_id: int, username: str) -> str:
        document = {
            "user_id": user_id,
            "username": username,
            "created_at": datetime.utcnow(),
            "message_count": 0,
            "last_active": datetime.utcnow()
        }
        return self.insert_one(document)

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        return self.find_one({"user_id": user_id})

    def update_user_activity(self, user_id: int) -> bool:
        update = {
            "last_active": datetime.utcnow(),
            "message_count": {"$inc": 1}
        }
        return self.update_one({"user_id": user_id}, update)

    def get_user_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        user = self.get_user(user_id)
        if not user:
            return None
        return {
            "message_count": user.get("message_count", 0),
            "joined_date": user.get("created_at"),
            "last_active": user.get("last_active")
        }