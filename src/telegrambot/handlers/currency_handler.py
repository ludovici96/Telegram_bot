
from telegram import Update
from telegram.ext import ContextTypes
from ..services.currency_service import CurrencyService

async def latest_rates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    currency_service = context.bot_data['currency_service']
    try:
        rates = await currency_service.get_latest_rates()
        message = "Latest Exchange Rates (USD base):\n"
        for currency, rate in rates['rates'].items():
            message += f"{currency}: {rate}\n"
        await update.message.reply_text(message)
    except Exception as e:
        await update.message.reply_text(f"Error fetching rates: {str(e)}")