# Telegram Multi-Purpose Bot

A rich Telegram bot using modern AI services and Python practices to enhance group chat experiences. This bot combines multiple AI capabilities, media processing, and information services into a modular architecture.

## Key Highlights
- 🤖 Advanced AI Integration with Groq, Whisper, and ElevenLabs
- 📊 Analytics and User Statistics
- 🔒 Security-First Approach with Docker Secrets
- 📱 Rich Media Processing and Downloads
- 🌐 Multiple Information Service Integrations
- 📦 Modular Architecture with Clean Code Practices

Built with scalability and maintainability in mind, this bot features:
- Secure credential management using Docker secrets
- Logging and monitoring
- MongoDB integration for data persistence
- Extensive error handling and input validation
- Docker containerization with health checks
- Well-documented codebase following PEP 8 guidelines

Perfect for developers looking to implement a feature-rich Telegram bot with modern AI capabilities and security practices.

## Project Structure
```
.
├── src/
│   └── telegrambot/
│       ├── __init__.py
│       ├── bot.py                 # bot entry point
│       ├── config/               # Configuration management
│       │   ├── config.py
│       │   ├── settings.py
│       │   ├── gallery-dl.conf
|       |   |── supportedsites.md
│       │   └── textconfig.conf
│       ├── handlers/             # Command and event handlers
│       │   ├── ai_handlers.py
│       │   ├── command_handlers.py
│       │   ├── conversion_handlers.py
│       │   ├── currency_handler.py
│       │   ├── media_handlers.py
│       │   ├── message_handlers.py
│       │   └── stats_handler.py
│       ├── models/              # Database models
│       │   ├── base_model.py
|       |   |── group_model.py
│       │   ├── message_model.py
│       │   └── user_model.py
│       ├── services/            # External service integrations
│       │   ├── base_service.py
│       │   ├── currency_service.py
│       │   ├── downloader_service.py
│       │   ├── groq_service.py
│       │   ├── mongodb_service.py
│       │   ├── news_service.py
│       │   ├── stats_service.py
│       │   ├── text_to_speech_service.py
│       │   ├── weather_service.py
│       │   ├── web_service.py
│       │   ├── whisper_service.py
│       │   └── wiki_service.py
│       └── utils/               # Utility functions
│           ├── decorators.py
│           ├── file_utils.py
│           ├── image_utils.py
│           └── text_utils.py
├── requirements/               # Project dependencies
│   ├── requirements.txt       # Core requirements
│   └── dev-requirements.txt   # Development requirements
├── setup-files/               # Installation and setup files
├── Dockerfile                 # Docker configuration
├── run.py                     # Main bot entry point 
├── docker-compose.yml         # Docker Compose configuration
└── setup.py                   # Package installation script
```

## Features
- Modular command handling system
- Configuration management with environment variables
- MongoDB integration for data persistence
- Multiple AI service integrations:
  - Groq AI for text generation
  - Whisper for voice transcription
  - ElevenLabs for text-to-speech
- Media processing:
  - Image processing and manipulation
  - Video and audio conversion
  - Gallery and YouTube downloads
- Information services:
  - News retrieval
  - Weather updates
  - Currency conversion
  - Wikipedia integration
- Advanced chat features:
  - Chat statistics and analytics
  - Message summarization
  - User activity tracking

## Installation

### Prerequisites
- Python 3.8+
- MongoDB
- Telegram Bot API credentials
- Required API keys:
  - Groq API key
  - News API key
  - OpenWeather API key
  - ElevenLabs API key
  - FX Rates API key

### API Keys Setup

To use all features of this bot, you'll need to obtain API keys from various services:

1. **Telegram Bot Credentials**
   - Create a bot through [@BotFather](https://t.me/botfather)
   - Get API ID and Hash from [Telegram's developer portal](https://my.telegram.org/apps)

2. **Groq API Key**
   - Sign up at [Groq's platform](https://console.groq.com)
   - Create new API key from the dashboard

3. **News API Key**
   - Register at [NewsAPI](https://newsapi.org)
   - Get API key from your account dashboard

4. **OpenWeather API Key**
   - Create account at [OpenWeather](https://openweathermap.org/api)
   - Subscribe to their free tier
   - Get API key from your account settings

5. **ElevenLabs API Key**
   - Sign up at [ElevenLabs](https://elevenlabs.io)
   - Navigate to your profile settings
   - Generate new API key

6. **FX Rates API Key**
   - Register at [Fixer.io](https://fixer.io)
   - Choose a subscription plan
   - Get your API access key

Each API key should be added to your `.env` file or configured as Docker secrets for production deployment. See the Configuration section for more details about environment setup.

Note: Free tiers of these services should be sufficient for personal use, but you may need paid subscriptions for higher usage limits.

### Setup
The project includes Docker support for easy deployment with secure credential management using Docker secrets:

Prerequisites:
- Docker
- Docker Compose

1. Clone the repository:
   ```bash
   git clone https://github.com/ludovici96/Telegram.git

   cd Telegram
   ```

2. Configure environment variables:
   - Copy the example environment file:
     ```bash
     cp .env.example .env
     ```
   - Edit the `.env` file with your credentials (see `.env.example` for all required variables)

3. After populating the `.env` file, run the `logout.py` file :
   ```bash
   python3 logout.py
   ```
   - You need to logout the telegram bot from the offical telegram bot api so you can you the local one. (local bot api also gives you higher upload limits of files. offcial only allowes 50mb uploads)

4. After populating the `.env` file, run these commands:
   ```bash
   chmod +x setup_secrets.sh

   ./setup_secrets.sh
   ```
   This script will create individual secret files for:
   - Telegram API credentials (API ID, API Hash, Bot Token)
   - Service API keys (Groq, News, Weather, ElevenLabs, etc.)

5. create the docker image, and run it:
   - The project includes Docker support for easy deployment with secure credential management using Docker secrets:
   ```bash   
   docker build -t telegram-bot-api .

   docker compose up -d
   ```
The Bot will take around 2 minutes to fully start up (This is done on purpose so that everything is functioning.)

#### Docker Configuration Features
- Multi-stage build for optimized image size
- Secure credential management using Docker secrets
- Integrated MongoDB database
- Automatic download directories management
- Health checks for both MongoDB and Telegram Bot API
- Proper volume management for data persistence
- Container auto-restart on failure

##### Container Services
- Telegram Bot API server (port 8081)
- MongoDB server (port 27017)
- Python bot application

##### Volume Management
- MongoDB data persistence

##### Health Monitoring
The container includes health checks that monitor:
- MongoDB connection and responsiveness
- Telegram Bot API availability
- Combined health status in Docker

##### Security Features
- No sensitive data in environment variables
- All credentials managed through Docker secrets
- Secure volume permissions
- Isolated network configuration

##### Troubleshooting
To check container status:
```bash
# View container logs
docker-compose logs -f

# Check container health
docker ps

# Inspect detailed health status
docker inspect telegram-bot | grep -A 10 Health
```

To restart the service:
```bash
docker-compose down
docker-compose up -d
```


### Available Commands

#### AI Commands
- `/ask [question]` - Ask the AI a question
- `/ask [question about weather]` - Ask about weather for any city
- `/wiki [factual question]` - Groq (llama) will query wikipedia and answer the question. (example: `/wiki paris` or `/wiki Explain the history of the french revolution`). it works best when you ask about a specific topic.
- `/summary` - Get chat summary (combines all the users messages and generates a summary)
- `/tldr` - Summarize text (use this command to summarize a message from a user or text after `/tldr`)
- `/me` - Generate AI response about yourself (combines all the users messages and generates a response)
- `/you` - Generate AI response about another users (combines all the users messages and generates a response)
- `/4chan` - Generate 4chan-style greentext

#### Statistics Commands
- `/stats` - Get detailed user statistics:
  - Message count
  - Character percentage
  - Media shares (stickers, voices, images)
  - Activity patterns
  - Popularity ranking
- `/top10` - View top 10 most active users with:
  - Ranking with medals (🥇, 🥈, 🥉)
  - Message counts
  - Activity percentages
- `/pie` - Visual pie chart showing:
  - Message distribution
  - User activity percentages
  - Top 10 most active users

#### Information Commands
- `/news [topic]` - Get latest news
- `/convert [amount] [from] [to]` - Currency conversion
  Example: `/convert 100 usd to eur`
- `/p [crypto ticker]` - get latest crypto price. (Example: `/p btc` to get price of btc.) 

#### Media Commands
- Auto-download from supported URLs (Blocked YouTube downloads to limit bandwith usage, since not many will watch the video in a chat instead of using the YouTube App)
- Voice message transcription
- `/audio` - Convert text to speech (using ElevenLabs)

#### Group Management Commands
- `/joingroup <GroupName>` - Join or create a mention group
- `/leavegroup <GroupName>` - Leave a mention group
- `/rmgroup <GroupName>` - Delete a group (admin only, update the `ADMIN_USER_IDS` in the `.env` file with admin user ids.)
- `/groups` - To list all groups and their members.
- Use `/<GroupName>` to mention all members in a group (example `/football` to mention everyone in the "football" group)

### Supported Download Sites
The bot supports automatic media downloads from various websites using gallery-dl and yt-dlp. To manage supported sites:

1. Navigate to `src/telegrambot/config/supportedsites.md`
2. go to`https://raw.githubusercontent.com/mikf/gallery-dl/refs/heads/master/docs/supportedsites.md`and add sites from this list to the `src/telegrambot/config/supportedsites.md`file 

The bot will automatically detect and handle downloads from any site listed in this file. For full compatibility lists, see:
- [gallery-dl supported sites](https://github.com/mikf/gallery-dl/blob/master/docs/supportedsites.md)
- [yt-dlp supported sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

## Configuration

### Environment Variables
All configuration is done through environment variables. The `.env` file in the root directory should contain all required credentials. See `.env.example` for all required variables.

### MongoDB Setup
The bot requires a MongoDB instance running locally. Default connection string: `mongodb://localhost:27017/`

## Development

### Code Organization
- `handlers/` - Command and event handlers
- `services/` - External service integrations
- `models/` - MongoDB models and data structures
- `config/` - Configuration management
- `utils/` - Helper functions and utilities

### Contributing
- Follow PEP 8 style guide
- Write unit tests for new features
- Document code with docstrings
- Update CHANGELOG.md for changes

### Testing (Not yet implemented)
```bash
pytest tests/ (Not yet implemented)
```

## Credits

This bot is made possible thanks to these amazing projects and services:

### AI & Speech Services
- [Groq](https://groq.com) - Large Language Model API
- [Whisper](https://github.com/openai/whisper) by OpenAI - Speech recognition
- [ElevenLabs](https://elevenlabs.io) - Text-to-speech generation

### Media Processing
- [gallery-dl](https://github.com/mikf/gallery-dl) - Media downloader for various sites
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube and video platform downloader
- [Pillow](https://python-pillow.org) - Image processing library
- [OpenCV Python](https://github.com/opencv/opencv-python) - Computer vision and image processing
- [pydub](https://github.com/jiaaro/pydub) - Audio processing

### Core Technologies
- [Pyrogram](https://github.com/pyrogram/pyrogram) - Telegram MTProto API framework
- [MongoDB](https://www.mongodb.com) - Database backend
- [Docker](https://www.docker.com) - Containerization

### Information Services
- [NewsAPI](https://newsapi.org) - News aggregation
- [OpenWeather](https://openweathermap.org) - Weather data
- [Fixer.io](https://fixer.io) - Currency exchange rates
- [Wikipedia-API](https://github.com/martin-majlis/Wikipedia-API) - Wikipedia integration

### Data Visualization
- [Matplotlib](https://matplotlib.org) - Plotting library
- [Seaborn](https://seaborn.pydata.org) - Statistical data visualization

Special thanks to all the maintainers and contributors of these projects that make this bot possible.

## License
MIT License - See LICENSE file for details