from setuptools import setup, find_packages
import os
from setuptools.command.install import install
from setuptools.command.develop import develop

def read_requirements(filename):
    with open(os.path.join("requirements", filename)) as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

# Read the README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

def create_env_template():
    env_template = """# Telegram API Credentials
TG_API_ID=
TG_API_HASH=
TG_BOT_TOKEN=
TG_SERVER=http://localhost
TG_PORT=8081

# Chat Configuration
ALLOWED_CHAT_ID="-100chatid"
ADMIN_USER_IDS=["admin user ids"]

# AI Service API Keys
GROQ_API_KEY=
NEWS_API_KEY=
FXRATES_API_KEY=
OPENWEATHER_API_KEY=
ELEVENLABS_API_KEY=

# Database Configuration
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DB=telegram_bot

# Media Download Settings
DOWNLOAD_FOLDER=gallery-dl
YT_DLP_FOLDER=yt-dlp
SUPPORTED_SITES_FILE=config/supportedsites.md

# AI Model Settings
WHISPER_MODEL=base
WHISPER_LANGUAGE=en"""

    if not os.path.exists('.env'):
        with open('.env.example', 'w') as f:
            f.write(env_template)
        print("\nCreated .env.example file. Please copy it to .env and update with your credentials.")
        print("cp .env.example .env")

class PostInstallCommand(install):
    def run(self):
        install.run(self)
        create_env_template()
        # Create necessary directories
        os.makedirs("gallery-dl", exist_ok=True)
        os.makedirs("yt-dlp", exist_ok=True)
        os.makedirs("src/audio", exist_ok=True)

class PostDevelopCommand(develop):
    def run(self):
        develop.run(self)
        create_env_template()
        # Create necessary directories
        os.makedirs("gallery-dl", exist_ok=True)
        os.makedirs("yt-dlp", exist_ok=True)
        os.makedirs("src/audio", exist_ok=True)

setup(
    name="telegram-multipurpose-bot",
    version="0.1.0",  # Matching version from __init__.py
    author="ludovici96",
    description="A feature-rich Telegram bot with AI services and utilities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ludovici96/telegram-bot",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Communications :: Chat",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Multimedia :: Video",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements("requirements.txt"),
    extras_require={
        "dev": read_requirements("dev-requirements.txt"),
    },
    entry_points={
        "console_scripts": [
            "telegram-bot=telegrambot.bot:main",
        ],
    },
    cmdclass={
        'install': PostInstallCommand,
        'develop': PostDevelopCommand,
    },
    include_package_data=True,
    package_data={
        'telegrambot': [
            'config/*.conf',
            'config/*.md',
            'config/*.py',
        ],
    },
    zip_safe=False,
    project_urls={
        "Bug Tracker": "https://github.com/ludovici96/telegram-bot/issues",
        "Documentation": "https://github.com/ludovici96/telegram-bot/wiki",
        "Source Code": "https://github.com/ludovici96/telegram-bot",
    },
)
