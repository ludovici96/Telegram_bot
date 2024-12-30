from datetime import datetime
from collections import Counter
from typing import Dict, Any, Tuple, List
import logging

logger = logging.getLogger(__name__)

class StatsService:
    def __init__(self, mongodb_service):
        self.db = mongodb_service
        
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        logger.debug(f"Fetching stats for user {user_id}")
        user_stats = self.db.get_user_stats(user_id)
        logger.debug(f"Raw user stats from DB: {user_stats}")
        
        if not user_stats:
            logger.debug("No stats found for user")
            return None
            
        # Get basic stats
        text_messages = user_stats.get('text_messages', 0)
        total_chars = user_stats.get('total_chars', 0)
        stickers = user_stats.get('stickers', 0)
        voices = user_stats.get('voices', 0)
        images_posted = user_stats.get('images_posted', 0)
        
        # Calculate percentage of total messages
        total_messages = self.db.user_stats.aggregate([
            {"$group": {"_id": None, "total": {"$sum": "$text_messages"}}}
        ]).next()["total"]
        percentage_of_total = (text_messages / total_messages * 100) if total_messages > 0 else 0
        
        # Get favorite day of the week
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$day_of_week", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 1}
        ]
        favorite_day_result = list(self.db.message_metadata.aggregate(pipeline))
        favorite_day = favorite_day_result[0]["_id"] if favorite_day_result else "Unknown"
        
        # Get highest posting date and count
        highest_date, highest_date_count = self._get_highest_posting(user_id)
        
        # Get highest posting week and count
        highest_week, highest_week_count = self._get_highest_posting_week(user_id)
        
        # Calculate popularity rank
        pipeline = [
            {"$group": {"_id": "$user_id", "reply_count": {"$sum": 1}}},
            {"$sort": {"reply_count": -1}},
            {"$group": {"_id": None, "users": {"$push": "$_id"}}}
        ]
        rank_result = list(self.db.popularity.aggregate(pipeline))
        if rank_result:
            users_by_rank = rank_result[0]["users"]
            try:
                popularity_position = users_by_rank.index(user_id) + 1
            except ValueError:
                popularity_position = 0
        else:
            popularity_position = 0
        
        return {
            "text_messages": text_messages,
            "percentage_of_total": percentage_of_total,
            "total_chars": total_chars,
            "stickers": stickers,
            "voices": voices,
            "images_posted": images_posted,
            "popularity_position": popularity_position,
            "favorite_day": favorite_day,
            "highest_posting_date": highest_date,
            "highest_posting_date_total": highest_date_count,
            "highest_posting_week": highest_week,
            "highest_posting_week_total": highest_week_count
        }

    def get_message_distribution(self) -> List[Tuple[str, int]]:
        """
        Get message distribution data for all users.
        
        Returns:
            List of tuples containing (username, message_count)
        """
        try:
            # Aggregate message counts by user with user information
            pipeline = [
                {
                    "$group": {
                        "_id": "$user_id",
                        "total_messages": {"$sum": "$text_messages"},
                        "username": {"$first": "$username"},
                        "first_name": {"$first": "$first_name"},
                        "last_name": {"$first": "$last_name"}
                    }
                },
                {"$sort": {"total_messages": -1}}
            ]
            
            results = list(self.db.user_stats.aggregate(pipeline))
            
            # Format the results
            distribution_data = []
            for result in results:
                message_count = result["total_messages"]
                
                # Get user display name in order of preference:
                # 1. Username (@username)
                # 2. Full name (first + last)
                # 3. First name only
                # 4. User ID as last resort
                if result.get("username"):
                    display_name = f"@{result['username']}"
                elif result.get("first_name") and result.get("last_name"):
                    display_name = f"{result['first_name']} {result['last_name']}"
                elif result.get("first_name"):
                    display_name = result["first_name"]
                else:
                    display_name = f"User {result['_id']}"
                
                if message_count > 0:  # Only include users with messages
                    distribution_data.append((display_name, message_count))
            
            # Sort by message count descending
            distribution_data.sort(key=lambda x: x[1], reverse=True)
            
            # Limit to top 10 users for readability
            return distribution_data[:10]
            
        except Exception as e:
            logger.error(f"Error getting message distribution: {e}")
            return []

    def _get_highest_posting(self, user_id: int) -> Tuple[str, int]:
        """Get the date with the most messages"""
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$message_date", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 1}
        ]
        result = list(self.db.message_metadata.aggregate(pipeline))
        if result:
            return result[0]["_id"], result[0]["count"]
        return "Unknown", 0

    def _get_highest_posting_week(self, user_id: int) -> Tuple[str, int]:
        """Get the week with the most messages"""
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$week_number", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 1}
        ]
        result = list(self.db.message_metadata.aggregate(pipeline))
        if result:
            return result[0]["_id"], result[0]["count"]
        return "Unknown", 0