
import logging
from pyrogram import Client, filters
from ..config.settings import ALLOWED_CHAT_ID
from ..utils.decorators import group_only

logger = logging.getLogger(__name__)

def register_conversion_handlers(app: Client, currency_service):
    @app.on_message(filters.command("latest") & filters.chat(ALLOWED_CHAT_ID))
    @group_only
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
    @group_only
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