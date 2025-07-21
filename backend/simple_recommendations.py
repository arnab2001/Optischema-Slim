#!/usr/bin/env python3
"""
Simple, single-source recommendations storage for OptiSchema.
Replaces the complex SQLite + cache + fallback system.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import threading
import uuid
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class SimpleRecommendationStore:
    """Single, thread-safe recommendation store with file persistence."""
    
    _recommendations: List[Dict[str, Any]] = []
    _lock = threading.Lock()
    _storage_file = Path("/tmp/simple_recommendations.json")
    
    @classmethod
    def _load_from_file(cls):
        """Load recommendations from file."""
        try:
            if cls._storage_file.exists():
                with open(cls._storage_file, 'r') as f:
                    cls._recommendations = json.load(f)
                logger.info(f"📂 Loaded {len(cls._recommendations)} recommendations from file")
        except Exception as e:
            logger.warning(f"Failed to load recommendations from file: {e}")
            cls._recommendations = []
    
    @classmethod
    def _save_to_file(cls):
        """Save recommendations to file."""
        try:
            cls._storage_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cls._storage_file, 'w') as f:
                json.dump(cls._recommendations, f, indent=2)
            logger.debug(f"💾 Saved {len(cls._recommendations)} recommendations to file")
        except Exception as e:
            logger.error(f"Failed to save recommendations to file: {e}")
    
    @classmethod
    def _load_from_file(cls):
        """Load recommendations from file."""
        try:
            if cls._storage_file.exists():
                with open(cls._storage_file, 'r') as f:
                    cls._recommendations = json.load(f)
                logger.info(f"📂 Loaded {len(cls._recommendations)} recommendations from file")
        except Exception as e:
            logger.warning(f"Failed to load recommendations from file: {e}")
            cls._recommendations = []
    
    @classmethod
    def _save_to_file(cls):
        """Save recommendations to file."""
        try:
            cls._storage_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cls._storage_file, 'w') as f:
                json.dump(cls._recommendations, f, indent=2)
            logger.debug(f"💾 Saved {len(cls._recommendations)} recommendations to file")
        except Exception as e:
            logger.error(f"Failed to save recommendations to file: {e}")
    
    @classmethod
    def add_recommendation(cls, recommendation: Dict[str, Any]) -> str:
        """Add a recommendation if it doesn't already exist (deduplication built-in)."""
        with cls._lock:
            # Load existing data first
            if not cls._recommendations:
                cls._load_from_file()
            
            # Generate ID if not provided
            if not recommendation.get('id'):
                recommendation['id'] = str(uuid.uuid4())
            
            # Add timestamp if not provided
            if not recommendation.get('created_at'):
                recommendation['created_at'] = datetime.utcnow().isoformat()
            
            # Check for duplicates (simple deduplication)
            duplicate_found = False
            for existing in cls._recommendations:
                if (existing.get('title') == recommendation.get('title') and
                    existing.get('sql_fix') == recommendation.get('sql_fix')):
                    logger.info(f"⏭️ Skipping duplicate: {recommendation['title'][:50]}...")
                    duplicate_found = True
                    break
            
            if not duplicate_found:
                cls._recommendations.append(recommendation)
                cls._save_to_file()  # Persist to file
                logger.info(f"✅ Added recommendation: {recommendation['title'][:50]}...")
                return recommendation['id']
            
            return None
    
    @classmethod
    def get_all_recommendations(cls) -> List[Dict[str, Any]]:
        """Get all recommendations."""
        with cls._lock:
            if not cls._recommendations:
                cls._load_from_file()
            return cls._recommendations.copy()
    
    @classmethod
    def get_recommendation(cls, rec_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific recommendation by ID."""
        with cls._lock:
            if not cls._recommendations:
                cls._load_from_file()
            for rec in cls._recommendations:
                if rec.get('id') == rec_id:
                    return rec.copy()
            return None
    
    @classmethod
    def update_recommendation(cls, rec_id: str, updates: Dict[str, Any]) -> bool:
        """Update a recommendation by ID."""
        with cls._lock:
            if not cls._recommendations:
                cls._load_from_file()
            for i, rec in enumerate(cls._recommendations):
                if rec.get('id') == rec_id:
                    # Update the recommendation in-place
                    cls._recommendations[i].update(updates)
                    cls._save_to_file()  # Persist changes
                    logger.info(f"✅ Updated recommendation {rec_id}: {list(updates.keys())}")
                    return True
            logger.warning(f"⚠️ Recommendation {rec_id} not found for update")
            return False
    
    @classmethod
    def clear_all(cls):
        """Clear all recommendations."""
        with cls._lock:
            cls._recommendations.clear()
            cls._save_to_file()  # Persist the clear operation
            logger.info("🗑️ Cleared all recommendations")
    
    @classmethod
    def get_count(cls) -> int:
        """Get total count of recommendations."""
        with cls._lock:
            if not cls._recommendations:
                cls._load_from_file()
            return len(cls._recommendations)
    
    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """Get storage statistics."""
        with cls._lock:
            if not cls._recommendations:
                cls._load_from_file()
            total = len(cls._recommendations)
            types = {}
            for rec in cls._recommendations:
                rec_type = rec.get('recommendation_type', 'unknown')
                types[rec_type] = types.get(rec_type, 0) + 1
            
            return {
                'total_recommendations': total,
                'storage_type': 'simple_file_persistent',
                'types': types,
                'last_updated': datetime.utcnow().isoformat()
            } 