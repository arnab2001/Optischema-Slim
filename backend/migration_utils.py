"""
Migration utilities for OptiSchema backend.
Handles migration from in-memory cache to Postgres storage.
"""

import logging
import asyncio
from typing import List, Dict, Any
from analysis.pipeline import get_recommendations_cache
from recommendations_service import RecommendationsService
from datetime import datetime

logger = logging.getLogger(__name__)


def migrate_in_memory_to_sqlite() -> Dict[str, Any]:
    """
    Migrate existing in-memory recommendations to Postgres storage.

    Returns:
        Migration results with statistics
    """
    try:
        logger.info("Starting migration from in-memory cache to Postgres...")
        
        # Get existing recommendations from in-memory cache
        existing_recommendations = get_recommendations_cache()
        
        if not existing_recommendations:
            logger.info("No existing recommendations found in memory cache")
            return {
                "success": True,
                "migrated_count": 0,
                "message": "No recommendations to migrate"
            }
        
        # Convert to list if it's not already
        if not isinstance(existing_recommendations, list):
            existing_recommendations = [existing_recommendations]
        
        migrated_count = 0
        failed_count = 0
        errors = []
        
        for rec in existing_recommendations:
            try:
                # Ensure we have the required fields
                if not isinstance(rec, dict):
                    logger.warning(f"Skipping non-dict recommendation: {type(rec)}")
                    failed_count += 1
                    continue
                
                # Add default values for new fields if missing
                rec_dict = {
                    'id': rec.get('id'),
                    'query_hash': rec.get('query_hash', ''),
                    'recommendation_type': rec.get('recommendation_type', 'unknown'),
                    'title': rec.get('title', 'Unknown Recommendation'),
                    'description': rec.get('description', ''),
                    'sql_fix': rec.get('sql_fix'),
                    'original_sql': rec.get('original_sql'),
                    'patch_sql': rec.get('patch_sql'),
                    'execution_plan_json': rec.get('execution_plan_json'),
                    'estimated_improvement_percent': rec.get('estimated_improvement_percent'),
                    'confidence_score': rec.get('confidence_score'),
                    'risk_level': rec.get('risk_level', 'medium'),
                    'status': rec.get('status', 'pending'),
                    'applied': rec.get('applied', False),
                    'applied_at': rec.get('applied_at'),
                    'created_at': rec.get('created_at')
                }
                
                # Store in Postgres (tenant-aware)
                rec_id = asyncio.run(RecommendationsService.add_recommendation(rec_dict))
                migrated_count += 1
                logger.debug(f"Migrated recommendation {rec_id}")
                
            except Exception as e:
                failed_count += 1
                error_msg = f"Failed to migrate recommendation: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        result = {
            "success": True,
            "migrated_count": migrated_count,
            "failed_count": failed_count,
            "total_in_memory": len(existing_recommendations),
            "errors": errors,
            "message": f"Successfully migrated {migrated_count} recommendations to Postgres"
        }
        
        logger.info(f"Migration completed: {migrated_count} migrated, {failed_count} failed")
        return result
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return {
            "success": False,
            "migrated_count": 0,
            "failed_count": 0,
            "error": str(e),
            "message": f"Migration failed: {str(e)}"
        }


def validate_migration() -> Dict[str, Any]:
    """
    Validate that migration was successful by comparing counts.
    
    Returns:
        Validation results
    """
    try:
        # Get in-memory count
        in_memory_recs = get_recommendations_cache()
        in_memory_count = len(in_memory_recs) if isinstance(in_memory_recs, list) else 1 if in_memory_recs else 0
        
        # Get Postgres count
        pg_count = asyncio.run(RecommendationsService.get_count())
        
        # Get Postgres recommendations
        pg_recs = asyncio.run(RecommendationsService.get_all_recommendations())
        
        validation_result = {
            "success": True,
            "in_memory_count": in_memory_count,
            "postgres_count": pg_count,
            "counts_match": in_memory_count == pg_count,
            "postgres_recommendations": len(pg_recs),
            "message": f"In-memory: {in_memory_count}, Postgres: {pg_count}"
        }
        
        if in_memory_count != pg_count:
            validation_result["warning"] = "Count mismatch detected"
            logger.warning(f"Count mismatch: in-memory={in_memory_count}, postgres={pg_count}")
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Validation failed: {str(e)}"
        }


def backup_in_memory_recommendations() -> List[Dict[str, Any]]:
    """
    Create a backup of in-memory recommendations before migration.
    
    Returns:
        List of recommendation dictionaries
    """
    try:
        recommendations = get_recommendations_cache()
        
        if not recommendations:
            return []
        
        # Convert to list if needed
        if not isinstance(recommendations, list):
            recommendations = [recommendations]
        
        # Create backup with additional metadata
        backup = []
        for i, rec in enumerate(recommendations):
            backup_rec = {
                'backup_index': i,
                'backup_timestamp': datetime.utcnow().isoformat(),
                'recommendation': rec
            }
            backup.append(backup_rec)
        
        logger.info(f"Created backup of {len(backup)} recommendations")
        return backup
        
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        return []


def restore_from_backup(backup: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Restore recommendations from backup.
    
    Args:
        backup: List of backup recommendation dictionaries
        
    Returns:
        Restoration results
    """
    try:
        restored_count = 0
        failed_count = 0
        errors = []
        
        for backup_item in backup:
            try:
                rec = backup_item.get('recommendation', {})
                if rec:
                    rec_id = asyncio.run(RecommendationsService.add_recommendation(rec))
                    restored_count += 1
                    logger.debug(f"Restored recommendation {rec_id}")
            except Exception as e:
                failed_count += 1
                error_msg = f"Failed to restore recommendation: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        return {
            "success": True,
            "restored_count": restored_count,
            "failed_count": failed_count,
            "total_in_backup": len(backup),
            "errors": errors,
            "message": f"Successfully restored {restored_count} recommendations"
        }
        
    except Exception as e:
        logger.error(f"Restoration failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Restoration failed: {str(e)}"
        } 
