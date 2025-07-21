#!/usr/bin/env python3
"""
Test the simplified recommendation storage system.
"""

from simple_recommendations import SimpleRecommendationStore

def test_simple_store():
    print("🧪 Testing Simple Recommendation Store")
    print("=" * 40)
    
    # Clear any existing data
    SimpleRecommendationStore.clear_all()
    print("🗑️ Cleared store")
    
    # Test 1: Add unique recommendations
    rec1 = {
        'title': 'Add index on users.email',
        'description': 'Improve login performance',
        'sql_fix': 'CREATE INDEX idx_users_email ON users(email);',
        'recommendation_type': 'ai',
        'confidence_score': 85
    }
    
    rec2 = {
        'title': 'Optimize ORDER BY queries',
        'description': 'Add index for sorting',
        'sql_fix': 'CREATE INDEX idx_products_name ON products(name);',
        'recommendation_type': 'ai',
        'confidence_score': 75
    }
    
    # Test 2: Add duplicate (should be ignored)
    rec1_duplicate = {
        'title': 'Add index on users.email',  # Same title
        'description': 'Different description but same SQL',
        'sql_fix': 'CREATE INDEX idx_users_email ON users(email);',  # Same SQL
        'recommendation_type': 'ai',
        'confidence_score': 90
    }
    
    print("\n📝 Adding recommendations...")
    id1 = SimpleRecommendationStore.add_recommendation(rec1)
    id2 = SimpleRecommendationStore.add_recommendation(rec2)
    id3 = SimpleRecommendationStore.add_recommendation(rec1_duplicate)  # Should be None (duplicate)
    
    print(f"   Rec 1 ID: {id1}")
    print(f"   Rec 2 ID: {id2}")
    print(f"   Rec 3 ID: {id3} (should be None - duplicate)")
    
    # Test 3: Check stats
    stats = SimpleRecommendationStore.get_stats()
    print(f"\n📊 Storage Stats:")
    print(f"   Total: {stats['total_recommendations']}")
    print(f"   Storage: {stats['storage_type']}")
    print(f"   Types: {stats['types']}")
    
    # Test 4: Get all recommendations
    all_recs = SimpleRecommendationStore.get_all_recommendations()
    print(f"\n📋 All Recommendations ({len(all_recs)}):")
    for i, rec in enumerate(all_recs, 1):
        print(f"   {i}. {rec['title'][:40]}...")
    
    # Test 5: Expected results
    print(f"\n✅ Test Results:")
    print(f"   Expected: 2 recommendations (duplicate ignored)")
    print(f"   Actual: {len(all_recs)} recommendations")
    print(f"   Deduplication: {'✅ WORKING' if len(all_recs) == 2 else '❌ FAILED'}")
    
    return len(all_recs) == 2

if __name__ == "__main__":
    success = test_simple_store()
    print(f"\n🎉 Test {'PASSED' if success else 'FAILED'}!") 