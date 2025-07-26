# Telegram Anonymous Content Filter Bot

## Overview

This is a Telegram bot designed for anonymous content sharing in Persian/Farsi channels. It filters text messages for profanity in multiple languages (Persian, English, and Persian-Latin transliterations) and manages media approval workflows through admin moderation. The bot automatically posts approved text messages anonymously to a designated channel while queuing media content for manual admin review. All content is published without user attribution to ensure complete anonymity.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Language**: Python 3.x
- **Framework**: `python-telegram-bot` library for Telegram API integration
- **Architecture Pattern**: Modular component-based design with separation of concerns
- **Data Storage**: SQLite database for user profiles and persistent data; JSON files for pending media
- **Logging**: File and console logging with configurable levels

### Key Design Decisions
- **Hybrid storage**: SQLite database for user profiles and persistent data; JSON files for temporary pending media queue
- **Modular design**: Separate classes for different concerns (handlers, filtering, media management, user management, configuration)
- **Multi-language support**: Built-in support for Persian, English, and Persian-Latin profanity filtering
- **Admin approval workflow**: Manual moderation system for media content to ensure channel quality
- **Anonymity**: All user content (text and media) is posted without revealing the original sender's identity.
- **Scalability**: Designed with modularity to allow for future expansion and easier maintenance.
- **Error Handling**: Robust error logging and graceful failure mechanisms.
- **Deployment**: Includes a simple Flask web server to keep the bot alive on cloud platforms like Render.

### Core Components
- `main.py`: Main entry point, sets up Flask server, initializes bot, and registers handlers.
- `config.py`: Handles all bot configuration, including API tokens, channel IDs, admin IDs, and other settings.
- `user_manager.py`: Manages user profiles, assigns unique display names/numbers, tracks user activity, and uses SQLite for persistence.
- `profanity_filter.py`: Implements multi-language profanity detection and replacement.
- `media_manager.py`: Manages the queue for media awaiting admin approval, handles storage/retrieval from JSON files.
- `bot_handlers.py`: Contains all Telegram bot command and message handlers.

### Libraries and Tools
- **Python**: 3.x
- **Dependencies (from `requirements.txt`)**:
  - `python-telegram-bot`: Telegram Bot API wrapper
  - `python-dotenv`: For loading environment variables (if used locally)
  - `Flask`: Simple web framework for keeping the bot alive on web hosts
- **Standard Library**: `json`, `logging`, `os`, `pathlib`, `re`, `time`, `typing`, `sqlite3`, `datetime`, `uuid`

### Required Environment Variables
- `BOT_TOKEN`: Telegram bot token from BotFather
- `CHANNEL_ID`: Target channel ID for posting content (e.g., `@your_channel_username`)
- `ADMIN_USER_ID`: Primary admin user ID for approvals (your Telegram User ID)
- `ADDITIONAL_ADMIN_IDS`: Optional comma-separated additional admin IDs (e.g., `12345,67890`)
- `MAX_MESSAGE_LENGTH`: Maximum allowed message length (default: `4096`)
- `MAX_PENDING_MEDIA`: Maximum pending media queue size (default: `100`)
- `STRICT_FILTERING`: Enable/disable strict profanity filtering (`true` or `false`, default: `true`)

## Deployment Strategy

### File Structure Requirements

data/
├── pending_media.json     # Media approval queue
├── profanity_words.json   # Profanity word lists
└── users.db               # SQLite database for user data (newly added)
logs/
└── bot.log               # Application logs

(Directories `data/` and `logs/` are automatically created on startup if they don't exist.)

### Deployment Options
- **Simple VPS**: Single Python process with file-based storage
- **Container**: Dockerized deployment with mounted volume for data persistence (recommended for production)
- **Cloud Platform (e.g., Render)**: Single Python process using built-in persistent disk for `data/` directory (if available) or treating data as ephemeral (for simpler cases). Includes Flask web server to satisfy uptime requirements.

### Configuration Management
- Environment variables for sensitive data (tokens, IDs)
- JSON files for configurable content (profanity words)
- File-based persistence for runtime data (pending media queue, user profiles in SQLite)

### Monitoring and Maintenance
- Built-in statistics tracking
- File-based logging with rotation capability
- Admin commands for operational monitoring
- JSON-based data backup and recovery (for `pending_media.json` and `profanity_words.json`, `users.db` is SQLite)

## Notable Features

### Multi-language Profanity Detection
- Supports Persian script, English, and Persian-Latin transliterations
- Regex-based pattern matching for efficient filtering
- Customizable word lists through JSON configuration

### Admin Moderation System
- Inline keyboard-based approval interface
- Support for multiple administrators
- Audit trail for all moderation decisions
- Basic commands for adding/removing profanity words and admins

### User Management
- Assigns anonymous "User Number" and allows custom display names.
- Tracks user's message count.
- Prevents duplicate display names.

### Robust Error Handling
- Comprehensive logging throughout the application
- Graceful handling of Telegram API errors
- Data persistence protection with atomic operations (for JSON files)
- Configuration validation on startup