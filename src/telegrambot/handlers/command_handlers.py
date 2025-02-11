import os
from datetime import datetime, timedelta, timezone
from PIL import Image
import requests
import io
import re
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from ..config.settings import ALLOWED_CHAT_ID, ADMIN_USER_IDS
from ..services.news_service import NewsService
from ..services.groq_service import GroqService, get_messages_last_24_hours
from ..services.currency_service import CurrencyService
from ..services.mongodb_service import MongoDBService
from ..services.stats_service import StatsService
from ..services.text_to_speech_service import TextToSpeechService
from ..services.chart_service import ChartService
from ..models.group_model import GroupModel
from ..utils.decorators import group_only
from ..services.crypto_price_service import CryptoPriceService
from ..services.weather_service import WeatherService
import logging

logger = logging.getLogger(__name__)

    # This file contains command handlers
    # It registers various commands like /news, /summary, /ask etc.
    # The bot uses different services like NewsService, GroqService, CurrencyService etc.
    # to process user commands and provide responses
    # Commands are restricted to allowed chat IDs for security
    # The bot can handle text, images, audio and provides features like
    # news search, chat summaries, currency conversion and stats tracking

    # IF YOU ADD NEW HANDLERS PLEASE UPDATE "if group_name in" LINE WITH THE NEW COMMAND.

def register_command_handlers(app: Client, mongodb_service: MongoDBService, stats_service: StatsService):
    # Initialize services with file paths
    news_service = NewsService('/run/secrets/news_api_key')
    groq_service = GroqService('/run/secrets/groq_api_key')
    currency_service = CurrencyService('/run/secrets/fxrates_api_key')
    text_to_speech_service = TextToSpeechService('/run/secrets/elevenlabs_api_key')
    weather_service = WeatherService('/run/secrets/openweather_api_key')
    crypto_service = CryptoPriceService('/run/secrets/coinmarketcap_key')
    chart_service = ChartService()

    # Initialize GroupModel
    group_model = GroupModel(mongodb_service.get_collection('groups'))

    @app.on_message(filters.command("news") & filters.chat(ALLOWED_CHAT_ID))
    async def news_command(client, message):
        user_query = " ".join(message.command[1:])
        
        if not user_query:
            await message.reply_text("Please provide a search term.\nUsage: /news search_term")
            return
        
        news_result = news_service.fetch_news(user_query)
        await message.reply_text(news_result, disable_web_page_preview=False)

    @app.on_message(filters.command("wiki") & filters.chat(ALLOWED_CHAT_ID))
    async def wiki_command(client, message):
        query = " ".join(message.command[1:])
        
        if not query:
            await message.reply_text("Please provide a search term.\nUsage: /wiki search_term")
            return
            
        waiting_message = await message.reply_text("🔍 Searching Wikipedia...")
        
        try:
            response = await groq_service.generate_ai_response(
                prompt=query,
                force_wiki=True
            )
            
            # Add validation for empty response
            if not response or len(response.strip()) == 0:
                await waiting_message.delete()
                await message.reply_text("❌ Received empty response. Please try again.")
                return
                
            # Add length check and truncate if necessary
            if len(response) > 4096:  # Telegram's message length limit
                response = response[:4093] + "..."
                
            await waiting_message.delete()
            await message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Error in wiki command: {e}")
            await waiting_message.delete()
            await message.reply_text(f"Error searching Wikipedia: {str(e)}. Please try again.")

    @app.on_message(filters.command("summary") & filters.chat(ALLOWED_CHAT_ID))
    async def handle_summary(client, message):
        try:
            # Send initial status
            status_message = await message.reply_text("Generating summary, please wait...")
            
            # Get messages from the last 24 hours
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            
            # Modified query to only filter by timestamp
            messages = mongodb_service.messages.find(
                {'timestamp': {'$gte': cutoff_time}},
                {'message_text': 1}
            ).sort('timestamp', -1).limit(1000)  # Limit to 1000 most recent messages
            
            message_texts = [msg['message_text'] for msg in messages if msg.get('message_text')]
            
            if not message_texts:
                await status_message.edit_text("No messages found to summarize.")
                return
                
            groq_service = GroqService('/run/secrets/groq_api_key')
            summary = await groq_service.generate_summary(
                message_texts,
                time_range="the last 24 hours"
            )
            
            if isinstance(summary, list):
                # Handle multi-part summary
                for i, part in enumerate(summary, 1):
                    await message.reply_text(f"Summary Part {i}/{len(summary)}:\n\n{part}")
                await status_message.delete()
            else:
                await status_message.edit_text(summary)
                
        except Exception as e:
            logger.error(f"Error in summary command: {e}", exc_info=True)
            await status_message.edit_text(
                "An error occurred while generating the summary. "
                "Please try with a shorter time range or when the chat is less active."
            )

    @app.on_message(filters.command("ask") & filters.chat(ALLOWED_CHAT_ID))
    async def ask_command(client, message):
        # Get the question from the command
        query = " ".join(message.command[1:]) if len(message.command) > 1 else None
        
        try:
            # Handle context from replied message
            context = ""
            if message.reply_to_message:
                if message.reply_to_message.text:
                    context = f"Previous message: {message.reply_to_message.text}\n\n"
                elif message.reply_to_message.caption:
                    context = f"Previous message (caption): {message.reply_to_message.caption}\n\n"

            # If no explicit query but replying to a message, use a default question
            if not query and context:
                query = "What do you think about this?"
            elif not query:
                await message.reply_text("Please provide a question after /ask\nExample: /ask what is the capital of France?")
                return

            # Combine context with query
            full_prompt = f"{context}Question: {query}" if context else query

            # Check if this is a reply to a message with an image
            image_path = None
            if message.reply_to_message and message.reply_to_message.photo:
                # Download the image
                photo = message.reply_to_message.photo.file_id
                download_path = os.path.join("./downloads", f"{photo}.jpg")
                await client.download_media(message.reply_to_message, download_path)
                image_path = download_path

            waiting_message = await message.reply_text("🤔 Thinking...")
            
            # Generate response with context and/or image
            response = await groq_service.generate_ai_response(full_prompt, image_path)
            
            # Clean up downloaded image
            if image_path and os.path.exists(image_path):
                os.remove(image_path)

            await waiting_message.delete()

            # Handle potentially split responses
            if isinstance(response, list):
                for i, part in enumerate(response, 1):
                    part_text = f"Part {i}/{len(response)}:\n\n{part}" if len(response) > 1 else part
                    await message.reply_text(part_text)
            else:
                await message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Error in ask command: {e}")
            error_message = "Sorry, I encountered an error while processing your request. Please try again."
            if 'waiting_message' in locals():
                await waiting_message.delete()
            await message.reply_text(error_message)

    @app.on_message(filters.command("latest") & filters.chat(ALLOWED_CHAT_ID))
    async def latest_command(client, message):
        try:
            rates = await currency_service.get_latest_rates()
            logger.debug(f"Received rates: {rates}")
            
            if 'rates' not in rates:
                await message.reply_text("Error: Unexpected API response format")
                return
                
            response = "💱 Latest Exchange Rates (USD base):\n\n"
            for currency, rate in rates['rates'].items():
                response += f"{currency}: {rate:.4f}\n"
            await message.reply_text(response)
        except Exception as e:
            logger.error(f"Error in latest_command: {str(e)}")
            await message.reply_text(f"❌ Error fetching rates: {str(e)}")

    @app.on_message(filters.command("convert") & filters.chat(ALLOWED_CHAT_ID))
    async def convert_command(client, message):
        try:
            args = message.text.split()[1:]
            if len(args) != 4 or args[2].lower() != "to":
                await message.reply_text("⚠️ Usage: `/convert <amount> <from_currency> to <to_currency>`\nExample: `/convert 100 USD to EUR`")
                return
                
            try:
                amount = float(args[0])
            except ValueError:
                await message.reply_text("❌ Error: Amount must be a number")
                return
                
            from_currency = args[1].upper()
            to_currency = args[3].upper()
            
            waiting_msg = await message.reply_text("💱 Converting...")
            result = await currency_service.convert_currency(from_currency, to_currency, amount)
            await waiting_msg.delete()
            
            response = f"💱 Currency Conversion:\n\n"
            response += f"{amount:,.2f} {from_currency} = {result['result']:,.2f} {to_currency}\n"
            await message.reply_text(response)
                
        except Exception as e:
            logger.error(f"Error in convert_command: {str(e)}")
            await message.reply_text(f"❌ Error converting currency: {str(e)}")

    @app.on_message(filters.command("stats") & filters.chat(ALLOWED_CHAT_ID))
    @group_only
    async def stats_command(client, message):
        user_id = message.reply_to_message.from_user.id if message.reply_to_message else message.from_user.id
        logger.debug(f"Getting stats for user_id: {user_id}")
        stats = stats_service.get_user_stats(user_id)
        
        if not stats:
            await message.reply_text("No stats found for this user.")
            return

        response = (
            "📊 User Stats:\n\n"
            f"Messages sent: {stats.get('text_messages', 0)}\n"
            f"Group contribution: {stats.get('percentage_of_total', 0.0):.2f}%\n"
            f"Average message length: {stats.get('total_chars', 0) / max(stats.get('text_messages', 1), 1):.2f} characters\n"
            f"Stickers sent: {stats.get('stickers', 0)}\n"
            f"Voice messages: {stats.get('voices', 0)}\n"
            f"Images shared: {stats.get('images_posted', 0)}\n"
            f"Popularity rank: #{stats.get('popularity_position', 0)}\n"
            f"Most active on: {stats.get('favorite_day', 'Unknown')}\n"
            f"Peak activity date: {stats.get('highest_posting_date', 'Unknown')} ({stats.get('highest_posting_date_total', 0)} messages)\n"
            f"Peak activity week: Week {stats.get('highest_posting_week', 'Unknown')} ({stats.get('highest_posting_week_total', 0)} messages)"
        )
        
        await message.reply_text(response)

    @app.on_message(filters.command("audio") & filters.chat(ALLOWED_CHAT_ID))
    async def audio_command(client, message):
        try:
            # Check if this is a reply to a message
            if message.reply_to_message and message.reply_to_message.text:
                text = message.reply_to_message.text
            else:
                # Get the text after the command
                text = " ".join(message.command[1:])
            
            if not text:
                await message.reply_text("Please provide text after the /audio command or reply to a message with text.")
                return
                
            # Generate a unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_path = os.path.join("src", "audio", f"speech_{timestamp}.mp3")
            
            # Generate the audio file
            await text_to_speech_service.generate_speech(text, audio_path)
            
            # Send the audio file as a voice message
            await message.reply_voice(audio_path)
            
            # Delete the audio file after sending
            if os.path.exists(audio_path):
                os.remove(audio_path)
                
        except Exception as e:
            logger.error(f"Error in audio command: {e}")
            await message.reply_text(f"Error generating audio: {str(e)}")

    @app.on_message(filters.command("me") & filters.chat(ALLOWED_CHAT_ID))
    async def me_command(client, message):
        try:
            user_id = message.from_user.id
            
            # Get messages from MongoDB for this specific user
            messages = mongodb_service.get_collection('messages').find(
                {'user_id': user_id},
                {'message_text': 1, 'timestamp': 1}
            ).sort('timestamp', -1).limit(1000)  # Get last 1000 messages
            
            # Convert cursor to list of message texts
            message_texts = [msg['message_text'] for msg in messages if 'message_text' in msg]
            
            if not message_texts:
                await message.reply_text("No messages found to summarize.")
                return
                
            # Generate summary using GroqService
            summary = await groq_service.generate_summary(message_texts)
            
            # Handle potentially split responses
            if isinstance(summary, list):
                for i, part in enumerate(summary, 1):
                    part_text = f"Part {i}/{len(summary)}:\n\n{part}" if len(summary) > 1 else part
                    await message.reply_text(part_text)
            else:
                await message.reply_text(summary)
            
        except Exception as e:
            logger.error(f"Error generating personal summary: {e}")
            await message.reply_text("An error occurred while generating your message summary.")

    @app.on_message(filters.command("you") & filters.chat(ALLOWED_CHAT_ID))
    async def you_command(client, message):
        try:
            # Check if the command is a reply to someone's message
            if not message.reply_to_message:
                await message.reply_text("Please reply to a user's message with /you to get their summary.")
                return
                
            target_user_id = message.reply_to_message.from_user.id
            target_user_name = message.reply_to_message.from_user.first_name
            
            # Get messages from MongoDB for the target user
            messages = mongodb_service.get_collection('messages').find(
                {'user_id': target_user_id},
                {'message_text': 1, 'timestamp': 1}
            ).sort('timestamp', -1).limit(1000)  # Get last 1000 messages
            
            # Convert cursor to list of message texts
            message_texts = [msg['message_text'] for msg in messages if 'message_text' in msg]
            
            if not message_texts:
                await message.reply_text(f"No messages found to summarize for {target_user_name}.")
                return
                
            # Generate summary using GroqService
            summary = await groq_service.generate_summary(message_texts)
            
            # Handle potentially split responses
            if isinstance(summary, list):
                for i, part in enumerate(summary, 1):
                    part_text = f"Part {i}/{len(summary)}:\n\n{part}" if len(summary) > 1 else part
                    await message.reply_text(part_text)
            else:
                await message.reply_text(summary)
            
        except Exception as e:
            logger.error(f"Error generating user summary: {e}")
            await message.reply_text("An error occurred while generating the message summary.")

    @app.on_message(filters.command("tldr") & filters.chat(ALLOWED_CHAT_ID))
    async def tldr_command(client, message):
        try:
            if message.reply_to_message and message.reply_to_message.text:
                text_to_summarize = message.reply_to_message.text
            else:
                text_to_summarize = " ".join(message.command[1:])
            
            if not text_to_summarize:
                await message.reply_text("Please provide text after the /tldr command or reply to a message you want to summarize.")
                return

            waiting_message = await message.reply_text("🤔 Summarizing...")
            summary = await groq_service.generate_summary([text_to_summarize])
            await waiting_message.delete()
            
            if isinstance(summary, list):
                for i, part in enumerate(summary, 1):
                    prefix = "TL;DR (Part {i}/{len(summary)}):\n" if len(summary) > 1 else "TL;DR:\n"
                    await message.reply_text(f"{prefix}{part}")
            else:
                await message.reply_text(f"TL;DR:\n{summary}")
                
        except Exception as e:
            logger.error(f"Error in tldr command: {e}")
            await message.reply_text("An error occurred while generating the summary.")

    @app.on_message(filters.command("4chan") & filters.chat(ALLOWED_CHAT_ID))
    async def greentext_command(client, message):
        try:
            prompt = ""
            # Check if this is a reply to a message
            if message.reply_to_message and message.reply_to_message.text:
                # Use the replied message as the prompt
                prompt = message.reply_to_message.text
                # Add any additional context from the command if provided
                additional_context = " ".join(message.command[1:])
                if additional_context:
                    prompt = f"{additional_context} - based on this message: {prompt}"
            else:
                # Get the prompt after the command
                prompt = " ".join(message.command[1:])
            
            # If no prompt is provided, use user's message history
            if not prompt:
                # Get messages from MongoDB for the current user
                user_messages = mongodb_service.get_collection('messages').find(
                    {'user_id': message.from_user.id},
                    {'message_text': 1, 'timestamp': 1}
                ).sort('timestamp', -1).limit(100)  # Get last 100 messages
                
                # Convert cursor to list of message texts
                message_texts = [msg['message_text'] for msg in user_messages if 'message_text' in msg]
                
                if not message_texts:
                    await message.reply_text("No messages found in your history to create a greentext story.")
                    return
                    
                # Join messages and use them as context
                prompt = f"Create a greentext story based on these messages from the user: {' '.join(message_texts)}"

            # Send a waiting message
            waiting_message = await message.reply_text("🤔 Generating greentext story...")
            
            # Generate greentext using GroqService
            greentext = await groq_service.generate_greentext(prompt)
            
            # Delete the waiting message
            await waiting_message.delete()
            
            # Format the response in a code block to preserve formatting
            formatted_response = f"```\n{greentext}\n```"
            await message.reply_text(formatted_response)
            
        except Exception as e:
            logger.error(f"Error in greentext command: {e}")
            await message.reply_text("An error occurred while generating the greentext story.")

    @app.on_message(filters.command("pie") & filters.chat(ALLOWED_CHAT_ID))
    @group_only
    async def pie_command(client, message):
        """Generate a pie chart showing message distribution among users"""
        try:
            # Send a "processing" message
            status_message = await message.reply_text("📊 Generating message distribution chart...")
            
            # Get message distribution data
            distribution_data = stats_service.get_message_distribution()
            
            if not distribution_data:
                await status_message.edit_text("No message data found to generate chart.")
                return
            
            # Generate pie chart
            chart_buffer = chart_service.generate_pie_chart(
                distribution_data,
                title="Message Distribution by User"
            )
            
            # Send the chart as a photo
            await message.reply_photo(
                photo=chart_buffer,
                caption="📊 Message Distribution\nShowing top 10 most active users"
            )
            
            # Delete the status message
            await status_message.delete()
            
        except Exception as e:
            logger.error(f"Error generating pie chart: {e}")
            await message.reply_text("❌ An error occurred while generating the chart.")

    @app.on_message(filters.command("top10") & filters.chat(ALLOWED_CHAT_ID))
    @group_only
    async def top10_command(client, message):
        """Show top 10 most active users in the chat"""
        try:
            # Send a "processing" message
            status_message = await message.reply_text("📊 Fetching top users data...")
            
            # Get message distribution data
            distribution_data = stats_service.get_message_distribution()
            
            if not distribution_data:
                await status_message.edit_text("No message data found.")
                return
            
            # Calculate total messages for percentage
            total_messages = sum(count for _, count in distribution_data)
            
            # Create formatted response
            response = "🏆 Top 10 Most Active Users:\n\n"
            
            for index, (username, count) in enumerate(distribution_data, 1):
                # Calculate percentage
                percentage = (count / total_messages) * 100
                
                # Add medal emoji for top 3
                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(index, "👤")
                
                # Format each line
                response += (
                    f"{medal} #{index}. {username}\n"
                    f"   ├ Messages: {count:,}\n"
                    f"   └ Activity: {percentage:.1f}%\n\n"
                )
            
            # Add total at the bottom
            response += f"📝 Total Messages: {total_messages:,}"
            
            # Send the formatted response
            await message.reply_text(response)
            
            # Delete the status message
            await status_message.delete()
            
        except Exception as e:
            logger.error(f"Error generating top 10 list: {e}")
            await message.reply_text("❌ An error occurred while generating the top 10 list.")

    @app.on_message(filters.command("help") & filters.chat(ALLOWED_CHAT_ID))
    async def help_command(client, message):
        """Show available bot commands and their descriptions"""
        help_text = """
🤖 **Available Commands:**

**AI Commands:**
• `/ask [question]` - Ask the AI a question
• `/ask [question about weather]` - Ask about weather
• `/wiki [factual question]` - Query Wikipedia using Groq
• `/summary` - Get chat summary
• `/tldr` - Summarize text
• `/me` - Generate AI response about yourself
• `/you` - Generate AI response about another user
• `/4chan` - Generate 4chan-style greentext

**Statistics Commands:**
• `/stats` - Get detailed user statistics
• `/top10` - View top 10 most active users
• `/pie` - Visual pie chart of message distribution

**Information Commands:**
• `/news [topic]` - Get latest news
• `/convert [amount] [from] [to]` - Currency conversion
• `/p [crypto ticker]` - Get latest crypto price

**Media Commands:**
• `/audio` - Convert text to speech
• Just send a voice message to get a text transcript

**Group Management:**
• `/joingroup <GroupName>` - Join/create a mention group
• `/leavegroup <GroupName>` - Leave a mention group
• `/rmgroup <GroupName>` - Delete a group (admin only)
• `/groups` - List all groups and members
• Use `/<GroupName>` to mention group members

The bot also supports automatic media downloads from various websites.
"""
        await message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


    @app.on_message(filters.command("joingroup") & filters.chat(ALLOWED_CHAT_ID))
    @group_only
    async def join_group_command(client, message):
        """Handle /joingroup command to joingroup or create a group"""
        try:
            # Get group name from command
            if len(message.command) != 2:
                await message.reply_text("Usage: /joingroup groupname")
                return
                
            group_name = message.command[1].lower()
            user_id = message.from_user.id
            
            # Try to add member to group
            success, msg = await group_model.add_member(group_name, user_id)
            await message.reply_text(msg)
            
        except Exception as e:
            logger.error(f"Error in join command: {e}")
            await message.reply_text("❌ An error occurred while processing your request.")

    @app.on_message(filters.command("leavegroup") & filters.chat(ALLOWED_CHAT_ID))
    @group_only
    async def leave_group_command(client, message):
        """Handle /leavegroup command"""
        try:
            # Get group name from command
            if len(message.command) != 2:
                await message.reply_text("Usage: /leavegroup groupname")
                return
                
            group_name = message.command[1].lower()
            user_id = message.from_user.id
            
            # Try to remove member from group
            success, msg = await group_model.remove_member(group_name, user_id)
            await message.reply_text(msg)
            
        except Exception as e:
            logger.error(f"Error in leavegroup command: {e}")
            await message.reply_text("❌ An error occurred while processing your request.")

    @app.on_message(filters.command("rmgroup") & filters.chat(ALLOWED_CHAT_ID))
    @group_only
    async def remove_group_command(client, message):
        """Handle /rmgroup command to delete a group (admin only)"""
        try:
            # Check if user is admin
            if message.from_user.id not in ADMIN_USER_IDS:
                await message.reply_text("❌ This command is only available to group administrators.")
                return

            # Get group name from command
            if len(message.command) != 2:
                await message.reply_text("Usage: /rmgroup groupname")
                return
                
            group_name = message.command[1].lower()
            
            # Try to delete the group
            success, msg = await group_model.delete_group(group_name)
            await message.reply_text(msg)
            
        except Exception as e:
            logger.error(f"Error in rmgroup command: {e}")
            await message.reply_text("❌ An error occurred while removing the group.")

    @app.on_message(filters.command("groups") & filters.chat(ALLOWED_CHAT_ID))
    @group_only
    async def list_groups_command(client, message):
        """List all available groups and their members"""
        try:
            # Get all groups from database
            groups = mongodb_service.get_collection('groups').find({})
            groups_list = list(groups)

            if not groups_list:
                await message.reply_text("📝 No groups have been created yet.\nUse /joingroup to create one!")
                return

            # Sort groups by name
            groups_list.sort(key=lambda x: x['group_name'])

            response = "📋 Available Groups:\n\n"

            for group in groups_list:
                group_name = group['group_name']
                members = group['members']
                member_count = len(members)

                # Get usernames/names for all members
                member_names = []
                for member_id in members:
                    try:
                        user = await client.get_users(member_id)
                        if user:
                            name = user.username or f"{user.first_name or ''} {user.last_name or ''}".strip() or f"User{user.id}"
                            member_names.append(name)
                    except Exception as e:
                        logger.error(f"Error getting user data for {member_id}: {e}")
                        member_names.append(f"User{member_id}")

                # Format group entry
                response += f"👥 {group_name}\n"
                response += f"   ├ Members: {member_count}\n"
                response += f"   └ Users: {', '.join(member_names)}\n\n"

            # Add usage instructions at the bottom
            response += "ℹ️ Commands:\n"
            response += "• /joingroup <name> - Join/create a group\n"
            response += "• /leavegroup <name> - Leave a group\n"
            response += "• /<groupname> - Mention group members"

            await message.reply_text(response)

        except Exception as e:
            logger.error(f"Error in groups command: {e}")
            await message.reply_text("❌ An error occurred while fetching groups.")

    @app.on_message(filters.regex(r'^/[a-zA-Z0-9_]{3,32}(?:\s+.*)?$') & filters.chat(ALLOWED_CHAT_ID))
    @group_only
    async def mention_group_command(client, message):
        """Handle /<groupname> command to mention all members"""
        try:
            # Check if it looks like a URL
            if 'http' in message.text.lower():
                return
            
            # Extract group name (everything between / and first space, or whole string if no space)
            group_name = message.text.split()[0][1:].lower()  # Remove the '/' prefix and get first word
            
            # Skip if it's a known command
            if group_name in ["join", "leavegroup", "stats", "ask", "summary", "news", 
                            "convert", "audio", "me", "you", "tldr", "4chan", "pie", "top10", "rmgroup", "help"]:
                return
                
            # Get group info
            group_info = group_model.get_group_info(group_name)
            if not group_info or not group_info.get('members'):
                return  # Silently ignore if not a valid group
                
            # Get user data for all members
            user_data = []
            for member_id in group_info['members']:
                try:
                    user = await client.get_users(member_id)
                    if user:
                        name = user.username or f"{user.first_name or ''} {user.last_name or ''}".strip() or f"User{user.id}"
                        user_data.append(f"[{name}](tg://user?id={user.id})")
                except Exception as e:
                    logger.error(f"Error getting user data for {member_id}: {e}")
                    continue
            
            if user_data:
                # Just send the mentions without any additional text
                mentions = " ".join(user_data)
                await message.reply_text(
                    f"🔔 Mentioning members of '{group_name}':\n{mentions}",
                    parse_mode=ParseMode.MARKDOWN
                )
            
        except Exception as e:
            logger.error(f"Error in mention group command: {e}", exc_info=True)

    @app.on_message(filters.command("p") & filters.chat(ALLOWED_CHAT_ID))
    async def price_command(client, message):
        """Get cryptocurrency price information"""
        try:
            if len(message.command) != 2:
                await message.reply_text("Usage: /p <ticker>\nExample: /p BTC")
                return

            ticker = message.command[1]
            logger.debug(f"Processing price command for ticker: {ticker}")
            
            waiting_msg = await message.reply_text("💰 Fetching price data...")
            
            result = await crypto_service.get_price(ticker)
            logger.debug(f"Price command result: {result}")
            
            await waiting_msg.delete()
            
            if result['status'] == 'error':
                await message.reply_text(f"❌ {result['message']}")
                return

            data = result['data']
            change_emoji = "📈" if data['percent_change_24h'] > 0 else "📉"
            
            response = (
                f"💎 {data['name']} ({data['symbol']})\n\n"
                f"💵 Price: ${data['price']:,.2f}\n"
                f"{change_emoji} 24h Change: {data['percent_change_24h']:,.2f}%\n"
                f"💰 Market Cap: ${data['market_cap']:,.0f}\n"
                f"📊 24h Volume: ${data['volume_24h']:,.0f}"
            )
            
            await message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Error in price command: {e}", exc_info=True)
            await message.reply_text("❌ Error fetching cryptocurrency price")