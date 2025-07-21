#!/usr/bin/env python3
"""
Cleanup script to remove duplicate recommendations and improve recommendation quality.
"""

import sys
import sqlite3
from pathlib import Path
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_duplicate_recommendations():
    """Remove duplicate recommendations from the database."""
    
    DB_PATH = Path("/tmp/optischema_recommendations.db")
    
    if not DB_PATH.exists():
        logger.info("No recommendations database found.")
        return
    
    logger.info("🧹 Starting cleanup of duplicate recommendations...")
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Get all recommendations grouped by query_hash
    cursor.execute('''
        SELECT id, query_hash, recommendation_type, title, created_at, sql_fix
        FROM recommendations 
        ORDER BY query_hash, created_at DESC
    ''')
    
    all_recs = cursor.fetchall()
    logger.info(f"Found {len(all_recs)} total recommendations")
    
    # Group by query_hash
    query_groups = defaultdict(list)
    for rec in all_recs:
        rec_id, query_hash, rec_type, title, created_at, sql_fix = rec
        query_groups[query_hash].append({
            'id': rec_id,
            'query_hash': query_hash,
            'type': rec_type,
            'title': title,
            'created_at': created_at,
            'sql_fix': sql_fix
        })
    
    # Find duplicates and decide which to keep
    to_delete = []
    kept_count = 0
    
    for query_hash, recs in query_groups.items():
        if len(recs) <= 1:
            kept_count += len(recs)
            continue
            
        logger.info(f"Query {query_hash[:8]}... has {len(recs)} recommendations")
        
        # Priority order: ai with sql_fix > ai without sql_fix > index > rewrite
        def get_priority(rec):
            if rec['type'] == 'ai' and rec['sql_fix']:
                return 1  # Highest priority - executable AI recommendations
            elif rec['type'] == 'ai':
                return 2  # Advisory AI recommendations
            elif rec['type'] == 'index':
                return 3  # Heuristic index recommendations
            elif rec['type'] == 'rewrite':
                return 4  # Query rewrite recommendations
            else:
                return 5  # Others
        
        # Sort by priority (lower number = higher priority), then by creation time (newer first)
        recs.sort(key=lambda x: (get_priority(x), x['created_at']), reverse=True)
        
        # Keep the best 1-2 recommendations per query
        to_keep = []
        
        # Always keep the highest priority one
        to_keep.append(recs[0])
        
        # If we have an executable AI recommendation, that's enough
        if recs[0]['type'] == 'ai' and recs[0]['sql_fix']:
            pass  # Keep only the executable AI rec
        else:
            # If the first one is advisory, also keep an executable one if available
            for rec in recs[1:]:
                if rec['sql_fix'] and len(to_keep) < 2:
                    to_keep.append(rec)
                    break
        
        # Mark the rest for deletion
        for rec in recs:
            if rec not in to_keep:
                to_delete.append(rec['id'])
                logger.info(f"   Deleting: {rec['type']} - {rec['title'][:50]}")
            else:
                logger.info(f"   Keeping:  {rec['type']} - {rec['title'][:50]}")
        
        kept_count += len(to_keep)
    
    # Delete duplicates
    if to_delete:
        logger.info(f"Deleting {len(to_delete)} duplicate recommendations...")
        cursor.executemany('DELETE FROM recommendations WHERE id = ?', [(rec_id,) for rec_id in to_delete])
        conn.commit()
    
    conn.close()
    
    logger.info(f"✅ Cleanup completed:")
    logger.info(f"   Original: {len(all_recs)} recommendations")
    logger.info(f"   Deleted:  {len(to_delete)} duplicates")
    logger.info(f"   Kept:     {kept_count} recommendations")
    
    return {
        'original_count': len(all_recs),
        'deleted_count': len(to_delete),
        'kept_count': kept_count
    }

def improve_recommendation_quality():
    """Update recommendation titles and descriptions to be more user-friendly."""
    
    DB_PATH = Path("/tmp/optischema_recommendations.db")
    
    if not DB_PATH.exists():
        return
    
    logger.info("✨ Improving recommendation quality...")
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Get all recommendations
    cursor.execute('SELECT id, title, description, recommendation_type FROM recommendations')
    recs = cursor.fetchall()
    
    updated_count = 0
    
    for rec_id, title, description, rec_type in recs:
        # Clean up title
        new_title = title
        if title.startswith('#') or title.startswith('##'):
            new_title = title.lstrip('#').strip()
        
        # Remove numbered prefixes
        import re
        new_title = re.sub(r'^\d+\.\s*\*\*?([^*]+)\*\*?', r'\1', new_title).strip()
        new_title = re.sub(r'^\d+\.\s*', '', new_title).strip()
        
        # Remove markdown formatting
        new_title = re.sub(r'\*\*([^*]+)\*\*', r'\1', new_title)
        new_title = new_title.replace('*', '').strip()
        
        # Clean up description - remove duplicate "Description:" prefixes
        new_description = description
        if new_description.startswith('Description:\n\nDescription:'):
            new_description = new_description.replace('Description:\n\nDescription:', 'Description:', 1)
        elif new_description.startswith('Description:\n\n'):
            new_description = new_description[14:]  # Remove "Description:\n\n"
        
        # Update if changed
        if new_title != title or new_description != description:
            cursor.execute(
                'UPDATE recommendations SET title = ?, description = ? WHERE id = ?',
                (new_title, new_description, rec_id)
            )
            updated_count += 1
    
    conn.commit()
    conn.close()
    
    logger.info(f"✅ Updated {updated_count} recommendations")

if __name__ == "__main__":
    results = cleanup_duplicate_recommendations()
    improve_recommendation_quality()
    
    print(f"\n🎯 CLEANUP SUMMARY:")
    print(f"   Removed {results['deleted_count']} duplicate recommendations")
    print(f"   Kept {results['kept_count']} high-quality recommendations")
    print(f"   Your UI should now show much cleaner results!") 