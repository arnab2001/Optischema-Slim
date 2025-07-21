#!/usr/bin/env python3
"""
Test script to verify deduplication works correctly.
"""

from recommendations_db import RecommendationsDB
import uuid
from datetime import datetime

def test_deduplication():
    print('🔧 Initializing recommendations database...')
    
    # Initialize the database
    RecommendationsDB._init_db()
    
    # Add test recommendations to simulate the duplicate issue
    test_recs = [
        {
            'id': str(uuid.uuid4()),
            'query_hash': 'test_hash_001', 
            'recommendation_type': 'ai',
            'title': 'Add index to usm-auth.user_tenant_map.user_id to improve JOIN performance',
            'description': 'Test description',
            'sql_fix': 'CREATE INDEX CONCURRENTLY idx_user_tenant_map_user_id ON "usm-auth".user_tenant_map(user_id);',
            'confidence_score': 85,
            'estimated_improvement_percent': 15,
            'risk_level': 'low'
        },
        {
            'id': str(uuid.uuid4()),
            'query_hash': 'test_hash_001',  # Same query hash (duplicate!)
            'recommendation_type': 'ai', 
            'title': 'Add index to usm-auth.user_tenant_map.user_id to improve JOIN performance',
            'description': 'Test description 2',
            'sql_fix': 'CREATE INDEX CONCURRENTLY idx_user_tenant_map_user_id ON "usm-auth".user_tenant_map(user_id);',
            'confidence_score': 85,
            'estimated_improvement_percent': 15,
            'risk_level': 'low'
        },
        {
            'id': str(uuid.uuid4()),
            'query_hash': 'test_hash_002', 
            'recommendation_type': 'ai',
            'title': 'Different recommendation',
            'description': 'Different description',
            'sql_fix': 'CREATE INDEX CONCURRENTLY idx_orders_status ON orders(status);',
            'confidence_score': 90,
            'estimated_improvement_percent': 25,
            'risk_level': 'low'
        }
    ]
    
    print('📝 Adding test recommendations...')
    for i, rec in enumerate(test_recs):
        rec_id = RecommendationsDB.store_recommendation(rec)
        print(f'   ✅ Added recommendation {i+1}: {rec_id}')
    
    # Check current count
    total = RecommendationsDB.get_recommendations_count()
    print(f'\n📊 Total recommendations in database: {total}')
    
    # List all recommendations
    recs = RecommendationsDB.list_recommendations()
    print(f'\n📋 All recommendations:')
    for rec in recs:
        print(f'   - {rec["title"][:50]}... (hash: {rec["query_hash"][:8]})')
    
    print('\n✅ Database initialized successfully!')
    return total

if __name__ == "__main__":
    test_deduplication() 