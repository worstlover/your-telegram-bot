"""
Media manager for handling pending media approvals
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class PendingMedia:
    """Data class for pending media items"""
    id: str
    user_id: int
    username: str
    message_id: int
    media_type: str
    file_id: str
    caption: str
    timestamp: float
    approved: Optional[bool] = None
    admin_decision_time: Optional[float] = None
    admin_id: Optional[int] = None

class MediaManager:
    """Manager for handling media approval workflow"""
    
    def __init__(self, file_path: str = "data/pending_media.json"):
        self.file_path = file_path
        self.pending_media: Dict[str, PendingMedia] = {}
        self.load_pending_media()
        
    def load_pending_media(self):
        """Load pending media from JSON file"""
        try:
            Path("data").mkdir(exist_ok=True)
            file_path = Path(self.file_path)
            
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Convert dict data back to PendingMedia objects
                for media_id, media_data in data.items():
                    self.pending_media[media_id] = PendingMedia(**media_data)
                    
                logger.info(f"Loaded {len(self.pending_media)} pending media items")
            else:
                logger.info("No pending media file found, starting fresh")
                
        except Exception as e:
            logger.error(f"Error loading pending media: {e}")
            self.pending_media = {}
    
    def save_pending_media(self):
        """Save pending media to JSON file"""
        try:
            Path("data").mkdir(exist_ok=True)
            
            # Convert PendingMedia objects to dict
            data = {}
            for media_id, media in self.pending_media.items():
                data[media_id] = asdict(media)
            
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving pending media: {e}")
    
    def add_pending_media(self, user_id: int, username: str, message_id: int, 
                         media_type: str, file_id: str, caption: str = "") -> str:
        """
        Add new media to pending approval list
        Returns: media_id for tracking
        """
        # Create unique ID
        media_id = f"{user_id}_{message_id}_{int(time.time())}"
        
        # Clean up old pending items (older than 7 days)
        self._cleanup_old_media()
        
        # Check if we have too many pending items
        if len(self.get_pending_media()) >= 100:
            # Remove oldest item
            oldest_id = min(self.pending_media.keys(), 
                          key=lambda k: self.pending_media[k].timestamp)
            del self.pending_media[oldest_id]
            logger.info(f"Removed oldest pending media: {oldest_id}")
        
        # Create pending media object
        pending_media = PendingMedia(
            id=media_id,
            user_id=user_id,
            username=username or "Unknown",
            message_id=message_id,
            media_type=media_type,
            file_id=file_id,
            caption=caption,
            timestamp=time.time()
        )
        
        self.pending_media[media_id] = pending_media
        self.save_pending_media()
        
        logger.info(f"Added pending media: {media_id} from user {username}")
        return media_id
    
    def approve_media(self, media_id: str, admin_id: int) -> Optional[PendingMedia]:
        """
        Approve a pending media item
        Returns: PendingMedia object if found, None otherwise
        """
        if media_id in self.pending_media:
            media = self.pending_media[media_id]
            media.approved = True
            media.admin_decision_time = time.time()
            media.admin_id = admin_id
            
            self.save_pending_media()
            logger.info(f"Media {media_id} approved by admin {admin_id}")
            return media
        
        return None
    
    def reject_media(self, media_id: str, admin_id: int) -> Optional[PendingMedia]:
        """
        Reject a pending media item
        Returns: PendingMedia object if found, None otherwise
        """
        if media_id in self.pending_media:
            media = self.pending_media[media_id]
            media.approved = False
            media.admin_decision_time = time.time()
            media.admin_id = admin_id
            
            self.save_pending_media()
            logger.info(f"Media {media_id} rejected by admin {admin_id}")
            return media
        
        return None
    
    def get_pending_media(self) -> List[PendingMedia]:
        """Get list of media items pending approval"""
        return [media for media in self.pending_media.values() 
                if media.approved is None]
    
    def get_media_by_id(self, media_id: str) -> Optional[PendingMedia]:
        """Get specific media item by ID"""
        return self.pending_media.get(media_id)
    
    def get_user_pending_count(self, user_id: int) -> int:
        """Get count of pending media for a specific user"""
        return len([media for media in self.pending_media.values() 
                   if media.user_id == user_id and media.approved is None])
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about media management"""
        total = len(self.pending_media)
        pending = len(self.get_pending_media())
        approved = len([m for m in self.pending_media.values() if m.approved is True])
        rejected = len([m for m in self.pending_media.values() if m.approved is False])
        
        # Media type breakdown
        media_types = {}
        for media in self.pending_media.values():
            media_types[media.media_type] = media_types.get(media.media_type, 0) + 1
        
        return {
            "total": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "media_types": media_types,
            "oldest_pending": self._get_oldest_pending_time()
        }
    
    def _get_oldest_pending_time(self) -> Optional[float]:
        """Get timestamp of oldest pending media"""
        pending = self.get_pending_media()
        if pending:
            return min(media.timestamp for media in pending)
        return None
    
    def _cleanup_old_media(self):
        """Remove media older than 7 days"""
        cutoff_time = time.time() - (7 * 24 * 60 * 60)  # 7 days
        old_media_ids = [
            media_id for media_id, media in self.pending_media.items()
            if media.timestamp < cutoff_time
        ]
        
        for media_id in old_media_ids:
            del self.pending_media[media_id]
            logger.info(f"Cleaned up old media: {media_id}")
        
        if old_media_ids:
            self.save_pending_media()
    
    def remove_processed_media(self, media_id: str) -> bool:
        """Remove media after it has been processed"""
        if media_id in self.pending_media:
            del self.pending_media[media_id]
            self.save_pending_media()
            return True
        return False
