"""
User management for handling display names and user data using SQLite
"""

import sqlite3
import logging
import os
from typing import Optional, Tuple, Dict
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class UserProfile:
    """Data class for user profile"""
    user_id: int
    telegram_username: str
    display_name: str
    user_number: int
    registration_date: str
    message_count: int = 0

class UserManager:
    """Manager for handling user profiles and display names with SQLite"""

    def __init__(self, db_path: str = "data/users.db"):
        self.db_path = db_path
        # Ensure the data directory exists
        Path("data").mkdir(exist_ok=True)
        self.init_database()
        # A simple dictionary to cache user's name setting mode
        self._setting_name_cache: Dict[int, bool] = {}


    def _get_connection(self):
        """Creates a database connection."""
        return sqlite3.connect(self.db_path)

    def init_database(self):
        """Initialize database table"""
        try:
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        telegram_username TEXT,
                        display_name TEXT UNIQUE,
                        user_number INTEGER UNIQUE,
                        registration_date TEXT,
                        message_count INTEGER DEFAULT 0
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Error initializing database: {e}")

    def register_user(self, user_id: int, telegram_username: str) -> UserProfile:
        """Register a new user or return existing profile"""
        user_profile = self.get_user_profile(user_id)
        if user_profile:
            return user_profile

        try:
            with self._get_connection() as conn:
                cur = conn.cursor()
                
                # Get the next available user number
                cur.execute("SELECT MAX(user_number) FROM users")
                last_user_number = cur.fetchone()[0]
                new_user_number = (last_user_number or 0) + 1
                
                display_name = f"کاربر شماره {new_user_number}"
                registration_date = str(int(time.time())) # Unix timestamp
                
                cur.execute(
                    "INSERT INTO users (user_id, telegram_username, display_name, user_number, registration_date) VALUES (?, ?, ?, ?, ?)",
                    (user_id, telegram_username, display_name, new_user_number, registration_date)
                )
                conn.commit()
                logger.info(f"Registered new user: {user_id} with display name {display_name}")
                return UserProfile(user_id, telegram_username, display_name, new_user_number, registration_date)
        except sqlite3.IntegrityError as e:
            logger.warning(f"User {user_id} already exists or display name/user number conflict: {e}")
            # If there's an integrity error, try to fetch the existing user
            return self.get_user_profile(user_id)
        except Exception as e:
            logger.error(f"Error registering user {user_id}: {e}")
            # Fallback to a basic profile if DB fails
            return UserProfile(user_id, telegram_username, "Unknown User", 0, str(int(time.time())))

    def get_user_profile(self, user_id: int) -> Optional[UserProfile]:
        """Get user profile by user ID"""
        try:
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT user_id, telegram_username, display_name, user_number, registration_date, message_count FROM users WHERE user_id = ?", (user_id,))
                row = cur.fetchone()
                if row:
                    return UserProfile(*row)
            return None
        except Exception as e:
            logger.error(f"Error getting user profile for {user_id}: {e}")
            return None

    def set_display_name(self, user_id: int, new_name: str) -> bool:
        """Set a new display name for the user"""
        # Check for existing display name
        if self.get_user_profile_by_display_name(new_name):
            return False # Name already taken

        try:
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("UPDATE users SET display_name = ? WHERE user_id = ?", (new_name, user_id))
                conn.commit()
                if cur.rowcount > 0:
                    logger.info(f"User {user_id} set display name to '{new_name}'")
                    return True
                return False
        except sqlite3.IntegrityError:
            # This handles cases where another user might try to set the same unique name concurrently
            logger.warning(f"Attempt to set duplicate display name '{new_name}' for user {user_id}")
            return False
        except Exception as e:
            logger.error(f"Error setting display name for user {user_id}: {e}")
            return False

    def get_user_profile_by_display_name(self, display_name: str) -> Optional[UserProfile]:
        """Get user profile by display name"""
        try:
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT user_id, telegram_username, display_name, user_number, registration_date, message_count FROM users WHERE display_name = ?", (display_name,))
                row = cur.fetchone()
                if row:
                    return UserProfile(*row)
            return None
        except Exception as e:
            logger.error(f"Error getting user profile by display name '{display_name}': {e}")
            return None
            
    def get_display_name(self, user_id: int) -> Optional[str]:
        """Get user's current display name"""
        profile = self.get_user_profile(user_id)
        return profile.display_name if profile else None

    # New methods for managing name setting mode
    def set_user_setting_name_mode(self, user_id: int, setting: bool):
        """Set the user's name setting mode."""
        self._setting_name_cache[user_id] = setting
        logger.debug(f"User {user_id} setting name mode set to {setting}")

    def is_user_setting_name_mode(self, user_id: int) -> bool:
        """Check if a user is currently in name setting mode."""
        return self._setting_name_cache.get(user_id, False)

    def increment_message_count(self, user_id: int):
        """Increment user's message count"""
        try:
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("UPDATE users SET message_count = message_count + 1 WHERE user_id = ?", (user_id,))
                conn.commit()
        except Exception as e:
            logger.error(f"Error incrementing message count for user {user_id}: {e}")

    def get_user_stats(self) -> dict:
        """Get general user statistics"""
        try:
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM users")
                total_users = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM users WHERE display_name LIKE 'کاربر شماره%'")
                default_names = cur.fetchone()[0]

                cur.execute("SELECT SUM(message_count) FROM users")
                total_messages = cur.fetchone()[0] or 0

                return {
                    "total_users": total_users,
                    "custom_names": total_users - default_names,
                    "default_names": default_names,
                    "total_messages": total_messages
                }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {"total_users": 0, "custom_names": 0, "default_names": 0, "total_messages": 0}