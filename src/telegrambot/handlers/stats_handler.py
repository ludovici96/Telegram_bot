from pyrogram import Client, filters
from ..services.stats_service import StatsService

class StatsHandler:
    def __init__(self, stats_service: StatsService):
        self.stats = stats_service

    async def handle_stats_command(self, client, message):
        user_id = message.from_user.id
        stats = self.stats.get_user_stats(user_id)
        
        if not stats:
            await message.reply_text("No stats found for you.")
            return

        # Corrected field names to match MongoDB and update operations
        response = (
            "📊 User Stats:\n\n"
            f"Messages sent: {stats.get('text_messages', 0)}\n"
            f"Group contribution: {stats.get('percentage_of_total', 0.0):.2f}%\n"
            f"Average message length: {stats.get('total_chars', 0) / max(stats.get('text_messages', 1), 1):.2f} characters\n"
            f"Stickers sent: {stats.get('stickers', 0)}\n"
            f"Voice messages: {stats.get('voices', 0)}\n"
            f"Images shared: {stats.get('images_posted', 0)}\n"
            f"Popularity rank: #{stats.get('popularity_position', 1)}\n"
            f"Most active on: {stats.get('favorite_day', 'Unknown')}\n"
            f"Peak activity date: {stats.get('highest_posting_date', 'Unknown')} ({stats.get('highest_posting_date_total', 0)} messages)\n"
            f"Peak activity week: Week {stats.get('highest_posting_week', 'Unknown')} ({stats.get('highest_posting_week_total', 0)} messages)"
        )
        
        await message.reply_text(response)