"""
User management for handling display names and user data using SQLite
"""

import sqlite3
import logging
import os
from typing import Optional, Tuple, Dict
from dataclasses import dataclass
from pathlib import Path
import datetime

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
            logger.info("Database initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")

    def _get_next_user_number(self) -> int:
        """Get the next available sequential user number."""
        try:
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT MAX(user_number) FROM users")
                max_number = cur.fetchone()[0]
                return (max_number or 0) + 1
        except Exception as e:
            logger.error(f"Error getting next user number: {e}")
            return 1 # Fallback to 1

    def register_user(self, user_id: int, telegram_username: str) -> UserProfile:
        """Register a new user or return existing profile."""
        existing_profile = self.get_user_profile(user_id)
        if existing_profile:
            return existing_profile

        user_number = self._get_next_user_number()
        display_name = f"کاربر شماره {user_number}"
        registration_date = datetime.datetime.now().isoformat()

        try:
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO users (user_id, telegram_username, display_name, user_number, registration_date) VALUES (?, ?, ?, ?, ?)",
                    (user_id, telegram_username, display_name, user_number, registration_date)
                )
                conn.commit()
            logger.info(f"Registered new user: {user_id} as {display_name}")
            return UserProfile(user_id, telegram_username, display_name, user_number, registration_date)
        except sqlite3.IntegrityError as e:
            # This can happen if display_name or user_number somehow clash
            logger.warning(f"Integrity error when registering user {user_id}: {e}. Retrying with new user_number.")
            # Recursive call, but should be rare
            return self.register_user(user_id, telegram_username) 
        except Exception as e:
            logger.error(f"Error registering user {user_id}: {e}")
            raise # Re-raise to indicate failure

    def get_user_profile(self, user_id: int) -> Optional[UserProfile]:
        """Retrieve a user's profile."""
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

    def set_display_name(self, user_id: int, new_display_name: str) -> bool:
        """Set a custom display name for a user."""
        try:
            with self._get_connection() as conn:
                cur = conn.cursor()
                # Check if display name already exists for another user
                cur.execute("SELECT user_id FROM users WHERE display_name = ? AND user_id != ?", (new_display_name, user_id))
                if cur.fetchone():
                    return False # Name already taken by another user

                cur.execute("UPDATE users SET display_name = ? WHERE user_id = ?", (new_display_name, user_id))
                conn.commit()
            logger.info(f"User {user_id} changed display name to '{new_display_name}'")
            return True
        except Exception as e:
            logger.error(f"Error setting display name for user {user_id} to '{new_display_name}': {e}")
            return False

    def is_setting_name(self, user_id: int) -> bool:
        """Check if user is in name setting mode."""
        return self._setting_name_cache.get(user_id, False)

    def set_setting_name_mode(self, user_id: int, mode: bool):
        """Set user's name setting mode."""
        self._setting_name_cache[user_id] = mode
        logger.debug(f"User {user_id} setting name mode set to {mode}")
            
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

                cur.execute("SELECT COUNT(*) FROM users WHERE display_name LIKE 'کاربر شماره%%'")
                default_names = cur.fetchone()[0]

                cur.execute("SELECT SUM(message_count) FROM users")
                total_messages = cur.fetchone()[0] or 0 # Ensure 0 if no messages

                return {
                    "total_users": total_users,
                    "custom_names": total_users - default_names,
                    "default_names": default_names,
                    "total_messages": total_messages
                }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {"total_users": 0, "custom_names": 0, "default_names": 0, "total_messages": 0}