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
import tempfile
import os
from pathlib import Path

logger = logging.getLogger(__name__)

class SimpleRecommendationStore:
    """Single, thread-safe recommendation store with file persistence."""
    
    _recommendations: List[Dict[str, Any]] = []
    _lock = threading.Lock()
    _storage_file = Path("/tmp/simple_recommendations.json")
    
    @classmethod
    def _load_from_file(cls):
        """Load recommendations from file with better error handling."""
        try:
            if cls._storage_file.exists():
                with open(cls._storage_file, 'r') as f:
                    content = f.read().strip()
                    if content:
                        cls._recommendations = json.loads(content)
                    else:
                        cls._recommendations = []
                logger.info(f"📂 Loaded {len(cls._recommendations)} recommendations from file")
            else:
                cls._recommendations = []
                logger.info("📂 No existing recommendations file found, starting fresh")
        except json.JSONDecodeError as e:
            logger.error(f"❌ Corrupted JSON file detected: {e}")
            # Backup corrupted file and start fresh
            backup_file = cls._storage_file.with_suffix('.json.bak')
            try:
                if cls._storage_file.exists():
                    cls._storage_file.rename(backup_file)
                    logger.info(f"📦 Backed up corrupted file to {backup_file}")
            except Exception as backup_error:
                logger.error(f"Failed to backup corrupted file: {backup_error}")
            cls._recommendations = []
        except Exception as e:
            logger.warning(f"Failed to load recommendations from file: {e}")
            cls._recommendations = []
    
    @classmethod
    def _save_to_file(cls):
        """Save recommendations to file using atomic write."""
        try:
            # Ensure directory exists
            cls._storage_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Create temporary file for atomic write
            temp_file = cls._storage_file.with_suffix('.tmp')
            
            # Write to temporary file first
            with open(temp_file, 'w') as f:
                json.dump(cls._recommendations, f, indent=2, ensure_ascii=False)
            
            # Atomic move to final location
            temp_file.replace(cls._storage_file)
            
            logger.debug(f"💾 Saved {len(cls._recommendations)} recommendations to file")
        except Exception as e:
            logger.error(f"Failed to save recommendations to file: {e}")
            # Clean up temp file if it exists
            temp_file = cls._storage_file.with_suffix('.tmp')
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except:
                    pass
    
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
            try:
                if not cls._recommendations:
                    cls._load_from_file()
                
                logger.info(f"🔍 Looking for recommendation ID: {rec_id}")
                logger.info(f"📊 Total recommendations in store: {len(cls._recommendations)}")
                
                # Convert search ID to string for comparison
                search_id_str = str(rec_id)
                
                for i, rec in enumerate(cls._recommendations):
                    rec_id_in_store = rec.get('id')
                    # Convert stored ID to string for comparison
                    rec_id_str = str(rec_id_in_store)
                    logger.debug(f"Checking recommendation {i}: {rec_id_str}")
                    if rec_id_str == search_id_str:
                        logger.info(f"✅ Found recommendation {rec_id}")
                        return rec.copy()
                
                logger.warning(f"❌ Recommendation {rec_id} not found in store")
                logger.info(f"Available IDs: {[str(r.get('id')) for r in cls._recommendations]}")
                return None
            except Exception as e:
                logger.error(f"💥 Exception in get_recommendation for {rec_id}: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
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