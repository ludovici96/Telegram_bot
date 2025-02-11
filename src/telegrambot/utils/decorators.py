from functools import wraps
from ..config.settings import ALLOWED_CHAT_ID

def group_only(func):
    """Decorator to restrict commands to allowed group chats"""
    @wraps(func)
    async def wrapper(client, message, *args, **kwargs):
        if message.chat.id == ALLOWED_CHAT_ID:  # Changed from 'in' to '=='
            return await func(client, message, *args, **kwargs)
        else:
            await message.reply_text("This command can only be used in allowed groups.")
    return wrapper