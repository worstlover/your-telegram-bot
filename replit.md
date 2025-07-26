# Telegram Anonymous Content Filter Bot

## Overview

This is a Telegram bot designed for anonymous content sharing in Persian/Farsi channels. It filters text messages for profanity in multiple languages (Persian, English, and Persian-Latin transliterations) and manages media approval workflows through admin moderation. The bot automatically posts approved text messages anonymously to a designated channel while queuing media content for manual admin review. All content is published without user attribution to ensure complete anonymity.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Language**: Python 3.x
- **Framework**: python-telegram-bot library for Telegram API integration
- **Architecture Pattern**: Modular component-based design with separation of concerns
- **Data Storage**: SQLite database for user profiles and persistent data; JSON files for pending media
- **Logging**: File and console logging with configurable levels

### Key Design Decisions
- **Hybrid storage**: SQLite database for user profiles and persistent data; JSON files for temporary pending media queue
- **Modular design**: Separate classes for different concerns (handlers, filtering, media management, user management, configuration)
- **Multi-language support**: Built-in support for Persian, English, and Persian-Latin profanity filtering
- **Admin approval workflow**: Manual moderation system for media content to ensure quality control
- **User identification system**: Users can choose custom display names or receive auto-assigned user numbers

## Key Components

### 1. Configuration Management (`config.py`)
- Environment variable-based configuration
- Admin user management with support for multiple admins
- Validation of required settings
- Configurable message length limits and media queue size

### 2. Bot Handlers (`bot_handlers.py`)
- Command processing (start, help, stats)
- Message filtering and processing
- Media handling and admin notifications
- Statistics tracking and reporting

### 3. Profanity Filter (`profanity_filter.py`)
- Multi-language profanity detection
- Pattern matching with regex compilation
- Support for Persian, English, and Persian-Latin scripts
- Configurable word lists stored in JSON

### 4. Media Manager (`media_manager.py`)
- Pending media queue management
- Admin approval workflow
- Media metadata tracking
- JSON-based persistence for pending items

### 5. User Manager (`user_manager.py`)
- SQLite database integration for user profiles
- Display name management and validation
- User registration and auto-numbering system
- Message count tracking and user statistics

### 6. Main Application (`main.py`)
- Application initialization and startup
- Component wiring and dependency injection
- Error handling and logging setup
- Telegram bot registration and event handling

## Data Flow

### Text Message Processing
1. User sends text message to bot
2. Bot gets or registers user profile with display name
3. Message is checked against profanity filter
4. If clean, message is automatically posted to channel **with user's display name**
5. If contains profanity, user is notified and message is rejected
6. User receives confirmation with display name attribution
7. User message count and statistics are updated

### Media Processing
1. User sends media (photo/video) to bot
2. Bot gets or registers user profile with display name
3. Media is added to pending approval queue
4. Admin receives notification with approve/reject buttons
5. Admin decision is recorded and user is notified
6. Approved media is posted to channel **with user's display name**
7. User receives confirmation with display name attribution
8. User message count and statistics are updated

### User Profile Management
1. New users get auto-assigned display names (e.g., "کاربر شماره 1")
2. Users can choose custom display names via inline button
3. Display names are validated for appropriateness and uniqueness
4. Once set, display names cannot be changed
5. All channel posts include the user's display name

### Admin Commands
1. Admins can view pending media queue
2. Admins can bulk approve/reject media
3. Admins can view bot statistics
4. Admins can restart or reload bot settings

## External Dependencies

### Core Dependencies
- **python-telegram-bot**: Official Telegram Bot API wrapper
- **Standard Library**: json, logging, os, pathlib, re, time, typing

### Required Environment Variables
- `BOT_TOKEN`: Telegram bot token from BotFather
- `CHANNEL_ID`: Target channel ID for posting content
- `ADMIN_USER_ID`: Primary admin user ID for approvals
- `ADDITIONAL_ADMIN_IDS`: Optional comma-separated additional admin IDs
- `MAX_MESSAGE_LENGTH`: Maximum allowed message length (default: 4096)
- `MAX_PENDING_MEDIA`: Maximum pending media queue size (default: 100)
- `STRICT_FILTERING`: Enable/disable strict profanity filtering (default: true)

## Deployment Strategy

### File Structure Requirements

data/
├── pending_media.json     # Media approval queue
└── profanity_words.json   # Profanity word lists
└── users.db               # SQLite database for user data (newly added)
logs/
└── bot.log               # Application logs


### Deployment Options
- **Simple VPS**: Single Python process with file-based storage
- **Container**: Dockerized deployment with mounted volume for data persistence
- **Cloud Function**: Serverless deployment with external storage for data files

### Configuration Management
- Environment variables for sensitive data (tokens, IDs)
- JSON files for configurable content (profanity words)
- File-based persistence for runtime data (pending media queue)

### Monitoring and Maintenance
- Built-in statistics tracking
- File-based logging with rotation capability
- Admin commands for operational monitoring
- JSON-based data backup and recovery

