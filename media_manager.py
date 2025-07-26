"""
Media manager for handling pending media approvals
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import uuid # For generating unique media IDs

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
                    # Ensure all fields are present for older entries
                    # Using asdict and then converting back handles this cleanly
                    full_media_data = {field.name: media_data.get(field.name) for field in PendingMedia.__dataclass_fields__.values()}
                    self.pending_media[media_id] = PendingMedia(**full_media_data)
                logger.info(f"Loaded {len(self.pending_media)} pending media items.")
            else:
                logger.info("No pending_media.json found, starting with empty media queue.")
        except Exception as e:
            logger.error(f"Error loading pending media: {e}. Starting with empty queue.")

    def save_pending_media(self):
        """Save pending media to JSON file"""
        try:
            Path("data").mkdir(exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                # Convert dataclass objects to dicts for JSON serialization
                json.dump({k: asdict(v) for k, v in self.pending_media.items()}, f, ensure_ascii=False, indent=4)
            logger.info(f"Saved {len(self.pending_media)} pending media items.")
        except Exception as e:
            logger.error(f"Error saving pending media: {e}")

    def add_pending_media(self, user_id: int, username: str, message_id: int, 
                          media_type: str, file_id: str, caption: str) -> Optional[str]:
        """Add a new media item to the pending queue."""
        if len(self.get_pending_media()) >= 100: # Limit to avoid excessive memory usage/admin burden
            logger.warning(f"Pending media queue is full. Cannot add new media from user {user_id}")
            return None

        media_id = str(uuid.uuid4()) # Generate a unique ID
        new_media = PendingMedia(
            id=media_id,
            user_id=user_id,
            username=username,
            message_id=message_id,
            media_type=media_type,
            file_id=file_id,
            caption=caption,
            timestamp=time.time(),
            approved=None, # Pending
            admin_decision_time=None,
            admin_id=None
        )
        self.pending_media[media_id] = new_media
        self.save_pending_media()
        self._cleanup_old_media() # Clean up periodically
        logger.info(f"Added new pending media: {media_id} from user {user_id}")
        return media_id

    def get_media(self, media_id: str) -> Optional[PendingMedia]:
        """Get a specific media item by its ID."""
        return self.pending_media.get(media_id)

    def get_pending_media(self) -> List[PendingMedia]:
        """Get all media items that are pending approval."""
        return [media for media in self.pending_media.values() if media.approved is None]

    def approve_media(self, media_id: str, admin_id: int) -> bool:
        """Mark a media item as approved."""
        media = self.pending_media.get(media_id)
        if media and media.approved is None:
            media.approved = True
            media.admin_decision_time = time.time()
            media.admin_id = admin_id
            self.save_pending_media()
            self.remove_processed_media(media_id) # Remove after processing
            logger.info(f"Media {media_id} approved by admin {admin_id}")
            return True
        return False

    def reject_media(self, media_id: str, admin_id: int) -> bool:
        """Mark a media item as rejected."""
        media = self.pending_media.get(media_id)
        if media and media.approved is None:
            media.approved = False
            media.admin_decision_time = time.time()
            media.admin_id = admin_id
            self.save_pending_media()
            self.remove_processed_media(media_id) # Remove after processing
            logger.info(f"Media {media_id} rejected by admin {admin_id}")
            return True
        return False
    
    def get_media_stats(self) -> Dict[str, Any]:
        """Get statistics about media items."""
        total = len(self.pending_media)
        pending = len(self.get_pending_media())
        approved = len([media for media in self.pending_media.values() if media.approved is True])
        rejected = len([media for media in self.pending_media.values() if media.approved is False])
        
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
        """Remove media older than 7 days that have been processed (approved/rejected)."""
        cutoff_time = time.time() - (7 * 24 * 60 * 60)  # 7 days
        
        # Filter out media that are old AND have been processed (approved or rejected)
        old_processed_media_ids = [\
            media_id for media_id, media in self.pending_media.items()\
            if media.timestamp < cutoff_time and media.approved is not None\
        ]
        
        for media_id in old_processed_media_ids:
            del self.pending_media[media_id]
            logger.info(f"Cleaned up old processed media: {media_id}")
        
        if old_processed_media_ids:
            self.save_pending_media()
    
    def remove_processed_media(self, media_id: str) -> bool:
        """Remove media after it has been processed (approved/rejected) to keep queue clean."""
        media = self.pending_media.get(media_id)
        if media and media.approved is not None: # Only remove if it has a decision
            del self.pending_media[media_id]
            self.save_pending_media()
            logger.info(f"Removed processed media {media_id} from queue.")
            return True
        return False