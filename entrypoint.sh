#!/bin/bash

# Set permissions for secret files
echo "Setting secret file permissions..."
find /run/secrets -type f -exec chmod 400 {} \;

# Start MongoDB with proper binding
echo "Starting MongoDB..."
mongod --fork --logpath /var/log/mongodb/mongod.log --bind_ip 127.0.0.1 --wiredTigerCacheSizeGB 0.25

# Wait for MongoDB to be ready
echo "Waiting for MongoDB to start..."
timeout 30 bash -c 'until mongosh --eval "db.adminCommand(\"ping\")" > /dev/null 2>&1; do sleep 1; done'

# Verify required secret files exist
REQUIRED_SECRETS=(
    "/run/secrets/tg_api_id"
    "/run/secrets/tg_api_hash"
    "/run/secrets/tg_bot_token"
    "/run/secrets/groq_api_key"
    "/run/secrets/news_api_key"
    "/run/secrets/fxrates_api_key"
    "/run/secrets/openweather_api_key"
    "/run/secrets/elevenlabs_api_key"
    "/run/secrets/allowed_chat_id"
    "/run/secrets/admin_user_ids"
    "/run/secrets/coinmarketcap_key"
)

for secret in "${REQUIRED_SECRETS[@]}"; do
    if [ ! -f "$secret" ]; then
        echo "Error: Required secret file $secret not found"
        exit 1
    fi
done

# Start services with gradual delays
echo "Starting services with gradual delays..."
sleep 15  # Initial delay for MongoDB and system stability

# Start telegram-bot-api and wait for it
echo "Starting Telegram Bot API..."
telegram-bot-api --local \
    --api-id=$(cat /run/secrets/tg_api_id) \
    --api-hash=$(cat /run/secrets/tg_api_hash) &
sleep 20  # Give the API server time to fully initialize

# Clean download directories
echo "Cleaning download directories..."
rm -rf /app/gallery-dl/*
rm -rf /app/yt-dlp/*

# Final preparation delay
echo "Final preparation before bot startup..."
sleep 10

# Activate virtual environment and start the Python bot
echo "Starting Python bot..."
source /app/venv/bin/activate
cd /app
python run.py