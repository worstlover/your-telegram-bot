"""
Configuration settings for the Telegram bot
"""

import os
from typing import Optional

class Config:
    """Configuration class for bot settings"""
    
    def __init__(self):
        # Bot token from BotFather
        self.BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
        
        # Channel ID where messages will be posted (must start with @)
        self.CHANNEL_ID: str = os.getenv("CHANNEL_ID", "")
        
        # Admin user ID for media approval
        self.ADMIN_USER_ID: int = int(os.getenv("ADMIN_USER_ID", "0"))
        
        # Optional: Additional admin user IDs (comma-separated)
        additional_admins = os.getenv("ADDITIONAL_ADMIN_IDS", "")
        self.ADDITIONAL_ADMIN_IDS: list = []
        if additional_admins:
            try:
                self.ADDITIONAL_ADMIN_IDS = [int(x.strip()) for x in additional_admins.split(",")]
            except ValueError:
                self.ADDITIONAL_ADMIN_IDS = []
        
        # Bot settings
        self.MAX_MESSAGE_LENGTH: int = int(os.getenv("MAX_MESSAGE_LENGTH", "4096"))
        self.MAX_PENDING_MEDIA: int = int(os.getenv("MAX_PENDING_MEDIA", "100"))
        
        # File paths
        self.PENDING_MEDIA_FILE: str = "data/pending_media.json"
        self.PROFANITY_WORDS_FILE: str = "data/profanity_words.json"
        
        # Profanity filter settings
        self.STRICT_FILTERING: bool = os.getenv("STRICT_FILTERING", "true").lower() == "true"
        
    def is_admin(self, user_id: int) -> bool:
        """Check if user is an admin"""
        return user_id == self.ADMIN_USER_ID or user_id in self.ADDITIONAL_ADMIN_IDS
    
    def validate(self) -> bool:
        """Validate configuration"""
        if not self.BOT_TOKEN:
            return False
        if not self.CHANNEL_ID:
            return False
        if self.ADMIN_USER_ID == 0:
            return False
        return True
