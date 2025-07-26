"""
User management for handling display names and user data
"""

import psycopg2
import logging
import os
from typing import Optional, Tuple
from dataclasses import dataclass

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
    """Manager for handling user profiles and display names"""
    
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        self.init_database()
        
    def init_database(self):
        """Initialize database tables"""
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS users (
                            user_id BIGINT PRIMARY KEY,
                            telegram_username VARCHAR(255),
                            display_name VARCHAR(50) UNIQUE,
                            user_number SERIAL,
                            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            message_count INTEGER DEFAULT 0,
                            is_setting_name BOOLEAN DEFAULT FALSE
                        )
                    """)
                    conn.commit()
                    logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    def get_user(self, user_id: int) -> Optional[UserProfile]:
        """Get user profile by user_id"""
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT user_id, telegram_username, display_name, user_number, 
                               registration_date, message_count
                        FROM users WHERE user_id = %s
                    """, (user_id,))
                    row = cur.fetchone()
                    
                    if row:
                        return UserProfile(
                            user_id=row[0],
                            telegram_username=row[1],
                            display_name=row[2],
                            user_number=row[3],
                            registration_date=row[4].strftime('%Y-%m-%d %H:%M'),
                            message_count=row[5]
                        )
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
        return None
    
    def register_user(self, user_id: int, telegram_username: str) -> UserProfile:
        """Register new user and return profile"""
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    # Check if user already exists
                    existing_user = self.get_user(user_id)
                    if existing_user:
                        return existing_user
                    
                    # Insert new user with auto-generated user number
                    cur.execute("""
                        INSERT INTO users (user_id, telegram_username, display_name, is_setting_name)
                        VALUES (%s, %s, %s, %s)
                        RETURNING user_number
                    """, (user_id, telegram_username, f"کاربر شماره {self.get_next_user_number()}", False))
                    
                    user_number = cur.fetchone()[0]
                    conn.commit()
                    
                    # Get the created user
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
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM users")
                    count = cur.fetchone()[0]
                    return count + 1
        except Exception as e:
            logger.error(f"Error getting next user number: {e}")
            return 1
    
    def set_display_name(self, user_id: int, display_name: str) -> Tuple[bool, str]:
        """
        Set custom display name for user
        Returns: (success, message)
        """
        # Validate display name
        if not display_name or len(display_name.strip()) == 0:
            return False, "نام نمایشی نمی‌تواند خالی باشد."
        
        display_name = display_name.strip()
        
        if len(display_name) > 20:
            return False, "نام نمایشی نمی‌تواند بیش از 20 کاراکتر باشد."
        
        # Check for prohibited words
        prohibited = ["ادمین", "admin", "مدیر", "bot", "ربات", "channel", "کانال"]
        if any(word in display_name.lower() for word in prohibited):
            return False, "این نام مجاز نیست. لطفاً نام دیگری انتخاب کنید."
        
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    # Check if display name already exists
                    cur.execute("SELECT user_id FROM users WHERE display_name = %s AND user_id != %s", 
                              (display_name, user_id))
                    if cur.fetchone():
                        return False, "این نام قبلاً انتخاب شده است. لطفاً نام دیگری انتخاب کنید."
                    
                    # Update display name
                    cur.execute("""
                        UPDATE users 
                        SET display_name = %s, is_setting_name = FALSE 
                        WHERE user_id = %s
                    """, (display_name, user_id))
                    conn.commit()
                    
                    return True, f"نام نمایشی شما به '{display_name}' تغییر یافت."
        except Exception as e:
            logger.error(f"Error setting display name for user {user_id}: {e}")
            return False, "خطا در تنظیم نام نمایشی. لطفاً دوباره تلاش کنید."
    
    def is_setting_name(self, user_id: int) -> bool:
        """Check if user is in name setting mode"""
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT is_setting_name FROM users WHERE user_id = %s", (user_id,))
                    row = cur.fetchone()
                    return row[0] if row else False
        except Exception as e:
            logger.error(f"Error checking name setting mode for user {user_id}: {e}")
            return False
    
    def start_name_setting(self, user_id: int):
        """Put user in name setting mode"""
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("UPDATE users SET is_setting_name = TRUE WHERE user_id = %s", (user_id,))
                    conn.commit()
        except Exception as e:
            logger.error(f"Error starting name setting for user {user_id}: {e}")
    
    def increment_message_count(self, user_id: int):
        """Increment user's message count"""
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("UPDATE users SET message_count = message_count + 1 WHERE user_id = %s", (user_id,))
                    conn.commit()
        except Exception as e:
            logger.error(f"Error incrementing message count for user {user_id}: {e}")
    
    def get_user_stats(self) -> dict:
        """Get general user statistics"""
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
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