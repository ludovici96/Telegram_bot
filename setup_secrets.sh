#!/bin/bash

# Exit on any error
set -e

# Create secrets directory with restricted permissions
mkdir -p secrets
chmod 700 secrets

# Function to validate and write secret
write_secret() {
    local key="$1"
    local value="$2"
    local file="secrets/${key}.txt"
    
    # Validate value is not empty
    if [ -z "$value" ]; then
        echo "Error: Empty value for ${key}"
        exit 1
    fi
    
    # Write value to file with immediate permission setting
    echo -n "$value" > "$file"
    chmod 400 "$file"
    
    # Verify file was written correctly
    if [ ! -f "$file" ] || [ ! -s "$file" ]; then
        echo "Error: Failed to write ${key} to ${file}"
        exit 1
    fi
    
    echo "Created secret: ${key}"
}

# Clear any existing secrets
rm -rf secrets/*

# Read from .env and create secret files
while IFS='=' read -r key value; do
    # Skip empty lines and comments
    [ -z "$key" ] && continue
    [[ "$key" =~ ^# ]] && continue
    
    # Remove any whitespace
    key=$(echo "$key" | tr -d '[:space:]')
    value=$(echo "$value" | tr -d '[:space:]')
    
    # Convert to lowercase for comparison
    key_lower=$(echo "$key" | tr '[:upper:]' '[:lower:]')
    
    # Create secret files for sensitive data
    case "$key_lower" in
        tg_api_id|tg_api_hash|tg_bot_token|groq_api_key|news_api_key|\
        fxrates_api_key|openweather_api_key|elevenlabs_api_key|\
        allowed_chat_id|admin_user_ids|coinmarketcap_key)
            write_secret "$key_lower" "$value"
            ;;
    esac
done < .env

# Final permission check
find secrets/ -type f -exec chmod 400 {} \;
find secrets/ -type d -exec chmod 700 {} \;

echo "Secrets have been created successfully"
echo "Verifying permissions..."
ls -la secrets/

# Verify all required secrets exist
REQUIRED_SECRETS=(
    "tg_api_id"
    "tg_api_hash"
    "tg_bot_token"
    "groq_api_key"
    "news_api_key"
    "fxrates_api_key"
    "openweather_api_key"
    "elevenlabs_api_key"
    "allowed_chat_id"
    "admin_user_ids"
    "coinmarketcap_key"
)

for secret in "${REQUIRED_SECRETS[@]}"; do
    if [ ! -f "secrets/${secret}.txt" ]; then
        echo "Error: Missing required secret: ${secret}"
        exit 1
    fi
done

echo "All required secrets are present and properly secured"