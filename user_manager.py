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
                        registration_date TEXT DEFAULT CURRENT_TIMESTAMP,
                        message_count INTEGER DEFAULT 0
                    )
                """)
                conn.commit()
                logger.info("Database initialized successfully using SQLite.")
        except Exception as e:
            logger.error(f"Error initializing SQLite database: {e}")

    def get_user(self, user_id: int) -> Optional[UserProfile]:
        """Get user profile by user_id"""
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                row = cur.fetchone()

                if row:
                    return UserProfile(
                        user_id=row["user_id"],
                        telegram_username=row["telegram_username"],
                        display_name=row["display_name"],
                        user_number=row["user_number"],
                        registration_date=row["registration_date"],
                        message_count=row["message_count"]
                    )
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
        return None

    def register_user(self, user_id: int, telegram_username: str) -> UserProfile:
        """Register new user and return profile"""
        existing_user = self.get_user(user_id)
        if existing_user:
            return existing_user

        try:
            with self._get_connection() as conn:
                cur = conn.cursor()
                next_user_num = self.get_next_user_number()
                display_name = f"کاربر شماره {next_user_num}"

                cur.execute("""
                    INSERT INTO users (user_id, telegram_username, display_name, user_number, message_count)
                    VALUES (?, ?, ?, ?, 0)
                """, (user_id, telegram_username, display_name, next_user_num))
                conn.commit()
                logger.info(f"Registered new user {user_id} with number {next_user_num}")

                # Get the newly created user
                return self.get_user(user_id)
        except sqlite3.IntegrityError:
             # This can happen in a race condition, so we just fetch the existing user
             return self.get_user(user_id)
        except Exception as e:
            logger.error(f"Error registering user {user_id}: {e}")
            # Return a default profile if database fails
            return UserProfile(
                user_id=user_id,
                telegram_username=telegram_username,
                display_name=f"کاربر شماره {user_id % 10000}",
                user_number=user_id % 10000,
                registration_date="2025-01-01 00:00",
                message_count=0
            )


    def get_next_user_number(self) -> int:
        """Get next available user number"""
        try:
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM users")
                count = cur.fetchone()[0]
                return count + 1
        except Exception as e:
            logger.error(f"Error getting next user number: {e}")
            return 1

    def set_display_name(self, user_id: int, display_name: str) -> Tuple[bool, str]:
        """Set custom display name for user"""
        if not display_name or len(display_name.strip()) == 0:
            return False, "نام نمایشی نمی‌تواند خالی باشد."
        display_name = display_name.strip()
        if len(display_name) > 20:
            return False, "نام نمایشی نمی‌تواند بیش از 20 کاراکتر باشد."

        prohibited = ["ادمین", "admin", "مدیر", "bot", "ربات", "channel", "کانال"]
        if any(word in display_name.lower() for word in prohibited):
            return False, "این نام مجاز نیست. لطفاً نام دیگری انتخاب کنید."

        try:
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT user_id FROM users WHERE display_name = ?", (display_name,))
                if cur.fetchone():
                    return False, "این نام قبلاً انتخاب شده است. لطفاً نام دیگری انتخاب کنید."

                cur.execute("UPDATE users SET display_name = ? WHERE user_id = ?", (display_name, user_id))
                conn.commit()
                self.stop_name_setting(user_id) # Exit name setting mode
                return True, f"نام نمایشی شما به '{display_name}' تغییر یافت."
        except Exception as e:
            logger.error(f"Error setting display name for user {user_id}: {e}")
            return False, "خطا در تنظیم نام نمایشی. لطفاً دوباره تلاش کنید."

    def is_setting_name(self, user_id: int) -> bool:
        """Check if user is in name setting mode using cache"""
        return self._setting_name_cache.get(user_id, False)

    def start_name_setting(self, user_id: int):
        """Put user in name setting mode using cache"""
        self._setting_name_cache[user_id] = True

    def stop_name_setting(self, user_id: int):
        """Remove user from name setting mode"""
        if user_id in self._setting_name_cache:
            del self._setting_name_cache[user_id]
            
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