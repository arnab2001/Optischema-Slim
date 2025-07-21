#!/usr/bin/env python3
"""
Generate clean, non-duplicate recommendations for testing the improved system.
"""

import asyncio
import uuid
from datetime import datetime
from recommendations_db import RecommendationsDB

async def generate_test_recommendations():
    """Generate a few clean test recommendations."""
    
    print("🎯 Generating clean test recommendations...")
    
    # Sample test recommendations (non-duplicate, high quality)
    test_recs = [
        {
            'id': str(uuid.uuid4()),
            'query_hash': 'test_query_001',
            'recommendation_type': 'ai',
            'title': 'Add Index on users.email for Authentication Queries',
            'description': 'Create an index on the email column in the users table to improve login and user lookup performance. This index will significantly speed up WHERE clauses filtering by email address.',
            'sql_fix': 'CREATE INDEX CONCURRENTLY idx_users_email ON users(email);',
            'estimated_improvement_percent': 25,
            'confidence_score': 85,
            'risk_level': 'low',
            'status': 'pending',
            'applied': False,
            'created_at': datetime.utcnow().isoformat()
        },
        {
            'id': str(uuid.uuid4()),
            'query_hash': 'test_query_002', 
            'recommendation_type': 'ai',
            'title': 'Optimize Order Status Queries with Composite Index',
            'description': 'Create a composite index on (status, created_at) for the orders table to improve performance of status-based queries with date filtering. This is commonly used in order management dashboards.',
            'sql_fix': 'CREATE INDEX CONCURRENTLY idx_orders_status_date ON orders(status, created_at);',
            'estimated_improvement_percent': 40,
            'confidence_score': 90,
            'risk_level': 'low', 
            'status': 'pending',
            'applied': False,
            'created_at': datetime.utcnow().isoformat()
        },
        {
            'id': str(uuid.uuid4()),
            'query_hash': 'test_query_003',
            'recommendation_type': 'ai',
            'title': 'Database Connection Pool Optimization',
            'description': 'Based on query pattern analysis, consider increasing the database connection pool size from the default 10 to 20 connections. Monitor connection utilization after applying this change.',
            'sql_fix': None,  # Advisory recommendation
            'estimated_improvement_percent': 15,
            'confidence_score': 70,
            'risk_level': 'medium',
            'status': 'pending', 
            'applied': False,
            'created_at': datetime.utcnow().isoformat()
        }
    ]
    
    # Store recommendations
    stored_count = 0
    for rec in test_recs:
        try:
            rec_id = RecommendationsDB.store_recommendation(rec)
            print(f"✅ Stored: {rec['title']}")
            stored_count += 1
        except Exception as e:
            print(f"❌ Failed to store recommendation: {e}")
    
    print(f"\n🎉 Generated {stored_count} clean recommendations!")
    print("✅ No duplicates, mix of executable and advisory recommendations")
    return stored_count

if __name__ == "__main__":
    count = asyncio.run(generate_test_recommendations())
    print(f"\n🚀 Ready to test! Refresh your frontend to see {count} clean recommendations.") 