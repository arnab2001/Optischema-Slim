#!/usr/bin/env python3
"""
Cleanup script to remove test recommendations from the database.
This removes hardcoded test data that was created during development.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from recommendations_db import RecommendationsDB
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_test_recommendations():
    """Remove test recommendations from the database."""
    
    # Test recommendation IDs to remove
    test_ids = [
        'phase6-final-test',
        'phase6-test-real-table', 
        'phase6-test-apply',
        'phase5-sandbox-test',
        'phase7-frontend-test',
        'phase4-test-rec',
        'phase4-test-rec-2',
        'phase4-test-rec-3'
    ]
    
    # Also remove any recommendations with test-related patterns
    test_patterns = [
        '%phase6%',
        '%phase7%', 
        '%phase4%',
        '%phase5%',
        '%test%',
        '%final-test%'
    ]
    
    logger.info("🧹 Starting cleanup of test recommendations...")
    
    # Get all recommendations
    all_recs = RecommendationsDB.list_recommendations(limit=1000)
    logger.info(f"Found {len(all_recs)} total recommendations")
    
    # Find test recommendations
    test_recs = []
    for rec in all_recs:
        rec_id = rec.get('id', '')
        title = rec.get('title', '')
        
        # Check if it matches test patterns
        is_test = False
        for pattern in test_patterns:
            if pattern.replace('%', '') in rec_id.lower() or pattern.replace('%', '') in title.lower():
                is_test = True
                break
        
        if is_test:
            test_recs.append(rec)
    
    logger.info(f"Found {len(test_recs)} test recommendations to remove:")
    
    # Remove test recommendations
    removed_count = 0
    for rec in test_recs:
        rec_id = rec.get('id')
        title = rec.get('title')
        
        try:
            if RecommendationsDB.delete_recommendation(rec_id):
                logger.info(f"✅ Removed: {rec_id} - {title}")
                removed_count += 1
            else:
                logger.warning(f"⚠️  Failed to remove: {rec_id}")
        except Exception as e:
            logger.error(f"❌ Error removing {rec_id}: {e}")
    
    logger.info(f"🎉 Cleanup complete! Removed {removed_count} test recommendations")
    
    # Show remaining recommendations
    remaining = RecommendationsDB.list_recommendations(limit=1000)
    logger.info(f"📊 Remaining recommendations: {len(remaining)}")
    
    if remaining:
        logger.info("Remaining recommendations:")
        for rec in remaining[:5]:  # Show first 5
            logger.info(f"  - {rec.get('id')}: {rec.get('title')}")
        if len(remaining) > 5:
            logger.info(f"  ... and {len(remaining) - 5} more")

if __name__ == "__main__":
    cleanup_test_recommendations() 