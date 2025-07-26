"""
User management for handling display names and user data using SQLite
"""

import sqlite3
import logging
import os
import time # Add this line
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
    is_banned: bool = False # Added is_banned attribute

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
        """Initialize database table and add is_banned column if not exists"""
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
                        message_count INTEGER DEFAULT 0,
                        is_banned INTEGER DEFAULT 0 -- Added is_banned column
                    )
                """)
                # Add 'is_banned' column if it doesn't exist (for existing databases)
                try:
                    cur.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0")
                    logger.info("Added 'is_banned' column to 'users' table.")
                except sqlite3.OperationalError as e:
                    if "duplicate column name: is_banned" in str(e):
                        logger.info("'is_banned' column already exists in 'users' table.")
                    else:
                        raise e # Re-raise other operational errors

                conn.commit()
            logger.info("Database initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")


    def _get_next_user_number(self) -> int:
        """Get the next available sequential user number"""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT MAX(user_number) FROM users")
            max_number = cur.fetchone()[0]
            return (max_number or 0) + 1

    def register_user(self, user_id: int, telegram_username: str) -> UserProfile:
        """Register a new user or return existing profile"""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user_data = cur.fetchone()

            if user_data:
                # User already exists, return existing profile
                return UserProfile(
                    user_id=user_data[0],
                    telegram_username=user_data[1],
                    display_name=user_data[2],
                    user_number=user_data[3],
                    registration_date=user_data[4],
                    message_count=user_data[5],
                    is_banned=bool(user_data[6]) # Convert integer to boolean
                )
            else:
                # Register new user
                user_number = self._get_next_user_number()
                display_name = f"کاربر شماره {user_number}"
                registration_date = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
                try:
                    cur.execute(
                        "INSERT INTO users (user_id, telegram_username, display_name, user_number, registration_date, message_count, is_banned) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (user_id, telegram_username, display_name, user_number, registration_date, 0, 0)
                    )
                    conn.commit()
                    logger.info(f"New user registered: {user_id} ({telegram_username}) as '{display_name}'")
                    return UserProfile(user_id, telegram_username, display_name, user_number, registration_date, 0, False)
                except sqlite3.IntegrityError as e:
                    logger.error(f"Integrity error during user registration for {user_id}: {e}")
                    # This can happen if user_number or display_name unique constraint fails (rare but possible)
                    # Try to re-register with a new number or handle appropriately
                    conn.rollback()
                    return self.register_user(user_id, telegram_username) # Recursive call, be careful with infinite loops


    def get_user_profile(self, user_id: int) -> Optional[UserProfile]:
        """Get user profile by user ID"""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user_data = cur.fetchone()
            if user_data:
                return UserProfile(
                    user_id=user_data[0],
                    telegram_username=user_data[1],
                    display_name=user_data[2],
                    user_number=user_data[3],
                    registration_date=user_data[4],
                    message_count=user_data[5],
                    is_banned=bool(user_data[6])
                )
            return None

    def set_display_name(self, user_id: int, new_name: str) -> bool:
        """Set user's display name, returns True on success, False if name is taken"""
        with self._get_connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute("UPDATE users SET display_name = ? WHERE user_id = ?", (new_name, user_id))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                # display_name is UNIQUE, so this means the new_name is already taken
                return False

    def set_user_setting_name_mode(self, user_id: int, mode: bool):
        """Set a flag indicating if the user is currently in name setting mode"""
        self._setting_name_cache[user_id] = mode

    def is_user_setting_name_mode(self, user_id: int) -> bool:
        """Check if a user is currently in name setting mode"""
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

    #region Ban Management Methods (Added to fix missing attributes)

    def is_user_banned(self, user_id: int) -> bool:
        """Check if a user is banned"""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
            result = cur.fetchone()
            if result:
                return bool(result[0]) # Convert integer (0 or 1) to boolean
            return False # User not found or not banned by default

    def ban_user(self, user_id: int) -> bool:
        """Ban a user"""
        with self._get_connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
                conn.commit()
                if cur.rowcount > 0:
                    logger.info(f"User {user_id} banned successfully.")
                    return True
                else:
                    logger.warning(f"User {user_id} not found in database for banning.")
                    return False
            except Exception as e:
                logger.error(f"Error banning user {user_id}: {e}")
                return False

    def unban_user(self, user_id: int) -> bool:
        """Unban a user"""
        with self._get_connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
                conn.commit()
                if cur.rowcount > 0:
                    logger.info(f"User {user_id} unbanned successfully.")
                    return True
                else:
                    logger.warning(f"User {user_id} not found in database for unbanning.")
                    return False
            except Exception as e:
                logger.error(f"Error unbanning user {user_id}: {e}")
                return False

    #endregion