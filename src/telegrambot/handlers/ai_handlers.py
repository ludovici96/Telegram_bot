from pyrogram import Client, filters
from ..config.settings import ALLOWED_CHAT_ID
from ..services.groq_service import generate_ai_response, get_user_messages

def register_ai_handlers(app: Client):
    @app.on_message(filters.regex(r'^/me') & filters.chat(ALLOWED_CHAT_ID))
    def generate_ai_response_command(client, message):
        try:
            user_id = message.from_user.id
            print(f"User ID from /me command: {user_id}")
            user_messages = get_user_messages(user_id)

            if user_messages:
                input_text = "\n".join(user_messages)
                ai_response = generate_ai_response(input_text)
                message.reply_text(ai_response)
            else:
                message.reply_text("No past messages found for this user.")
        except Exception as e:
            print(f"Error generating AI response: {e}")
            message.reply_text("An error occurred while processing your request.")

    @app.on_message(filters.regex(r'^/you') & filters.chat(ALLOWED_CHAT_ID))
    def generate_user_ai_response_command(client, message):
        try:
            if message.reply_to_message and message.reply_to_message.from_user:
                user_id = message.reply_to_message.from_user.id
                user_messages = get_user_messages(user_id)

                if user_messages:
                    input_text = "\n".join(user_messages)
                    ai_response = generate_ai_response(input_text)
                    message.reply_text(ai_response)
                else:
                    message.reply_text("No past messages found for this user.")
            else:
                message.reply_text("Please reply to a user's message to use this command.")
        except Exception as e:
            print(f"Error generating AI response: {e}")
            message.reply_text("An error occurred while processing your request.")