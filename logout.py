
import requests
import os
from dotenv import load_dotenv

def log_out_from_telegram_cloud(bot_token):
    url = f'https://api.telegram.org/bot{bot_token}/logOut'
    response = requests.post(url)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to log out: {response.status_code}, {response.text}")

def main():
    load_dotenv()
    TOKEN = os.getenv('BOT_TOKEN')
    
    try:
        result = log_out_from_telegram_cloud(TOKEN)
        print("Log out successful:", result)
    except Exception as e:
        print("Error:", e)
        return

if __name__ == "__main__":
    main()