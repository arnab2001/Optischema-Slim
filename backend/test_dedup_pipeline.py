#!/usr/bin/env python3
"""
Test script to simulate the analysis pipeline and verify deduplication works.
"""

from recommendations_db import RecommendationsDB
import uuid
from datetime import datetime

def simulate_analysis_pipeline():
    """Simulate the fixed analysis pipeline logic."""
    print('🧪 Testing deduplication in analysis pipeline...')
    
    # Simulate new recommendations from analysis (including potential duplicates)
    new_recommendations = [
        {
            'id': str(uuid.uuid4()),
            'query_hash': 'test_hash_001',  # This should be deduplicated
            'recommendation_type': 'ai',
            'title': 'Add index to usm-auth.user_tenant_map.user_id to improve JOIN performance',
            'description': 'Another duplicate attempt',
            'sql_fix': 'CREATE INDEX CONCURRENTLY idx_user_tenant_map_user_id ON "usm-auth".user_tenant_map(user_id);',
            'confidence_score': 85,
            'estimated_improvement_percent': 15,
            'risk_level': 'low'
        },
        {
            'id': str(uuid.uuid4()),
            'query_hash': 'test_hash_003',  # This should be stored (new)
            'recommendation_type': 'ai',
            'title': 'Optimize slow ORDER BY queries',
            'description': 'New recommendation',
            'sql_fix': 'CREATE INDEX CONCURRENTLY idx_products_name ON products(name);',
            'confidence_score': 75,
            'estimated_improvement_percent': 20,
            'risk_level': 'low'
        }
    ]
    
    # Apply the same deduplication logic as in the fixed pipeline
    stored_count = 0
    skipped_count = 0
    
    for rec_dict in new_recommendations:
        # Check for existing recommendations for this query_hash
        existing_recs = RecommendationsDB.get_recommendations_by_query_hash(rec_dict['query_hash'])
        
        # Skip if we already have a recommendation for this query with same sql_fix
        duplicate_found = False
        for existing in existing_recs:
            if (existing.get('recommendation_type') == 'ai' and 
                existing.get('sql_fix') == rec_dict.get('sql_fix') and
                existing.get('title') == rec_dict.get('title')):
                duplicate_found = True
                print(f'⏭️  Skipping duplicate: {rec_dict["title"][:50]}... (query: {rec_dict["query_hash"][:8]})')
                skipped_count += 1
                break
        
        if not duplicate_found:
            RecommendationsDB.store_recommendation(rec_dict)
            stored_count += 1
            print(f'✅ Stored new recommendation: {rec_dict["title"][:50]}... (query: {rec_dict["query_hash"][:8]})')
    
    print(f'\n📊 Pipeline Results:')
    print(f'   ✅ Stored: {stored_count} new recommendations')
    print(f'   ⏭️  Skipped: {skipped_count} duplicates')
    
    # Check final state
    total = RecommendationsDB.get_recommendations_count()
    print(f'   📋 Total in database: {total}')
    
    # List all recommendations by query hash
    recs = RecommendationsDB.list_recommendations()
    query_counts = {}
    for rec in recs:
        query_hash = rec['query_hash'][:8]
        if query_hash not in query_counts:
            query_counts[query_hash] = []
        query_counts[query_hash].append(rec['title'][:40])
    
    print(f'\n📋 Final recommendations by query:')
    for query_hash, titles in query_counts.items():
        print(f'   Query {query_hash}: {len(titles)} recommendations')
        for title in titles:
            print(f'     - {title}...')
    
    return stored_count, skipped_count

if __name__ == "__main__":
    simulate_analysis_pipeline() 