#!/usr/bin/env python3
"""
Test script for Phase 6: Apply / Rollback Flow
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apply_manager import get_apply_manager
from recommendations_db import RecommendationsDB
from replica_manager import get_replica_manager


async def test_phase6_apply_rollback():
    """Test the apply/rollback functionality."""
    print("🧪 Testing Phase 6: Apply / Rollback Flow")
    print("=" * 50)
    
    # Initialize managers
    apply_manager = get_apply_manager()
    replica_manager = get_replica_manager()
    
    # Test 1: Check replica availability
    print("\n1. Checking replica availability...")
    replica_available = await replica_manager.is_available()
    print(f"   Replica available: {replica_available}")
    
    if not replica_available:
        print("   ❌ Replica not available - cannot test apply functionality")
        return False
    
    # Test 2: Create a test recommendation
    print("\n2. Creating test recommendation...")
    test_rec = {
        'id': 'phase6-test-apply',
        'query_hash': 'phase6_test_hash',
        'recommendation_type': 'index',
        'title': 'Phase 6 Test: Add Index for Apply/Rollback',
        'description': 'Test recommendation for Phase 6 apply/rollback functionality.',
        'sql_fix': 'CREATE INDEX IF NOT EXISTS idx_test_table_name ON information_schema.tables(table_name);',
        'original_sql': 'SELECT table_name, table_type FROM information_schema.tables WHERE table_schema = \'public\' ORDER BY table_name;',
        'patch_sql': 'SELECT table_name, table_type FROM information_schema.tables WHERE table_schema = \'public\' ORDER BY table_name;',
        'execution_plan_json': {'extracted_tables': ['information_schema.tables'], 'estimated_cost': 1000, 'actual_time_ms': 50.5},
        'estimated_improvement_percent': 75,
        'confidence_score': 90,
        'risk_level': 'low',
        'status': 'pending',
        'applied': False,
        'applied_at': None,
        'created_at': datetime.utcnow().isoformat()
    }
    
    RecommendationsDB.store_recommendation(test_rec)
    print(f"   ✅ Created test recommendation: {test_rec['id']}")
    
    # Test 3: Apply the recommendation
    print("\n3. Applying recommendation...")
    try:
        apply_result = await apply_manager.apply_recommendation(test_rec['id'])
        print(f"   ✅ Applied successfully!")
        print(f"   SQL executed: {apply_result['sql_executed']}")
        print(f"   Schema created: {apply_result['schema_name']}")
        print(f"   Rollback available: {apply_result['rollback_available']}")
    except Exception as e:
        print(f"   ❌ Failed to apply: {e}")
        return False
    
    # Test 4: Check applied changes
    print("\n4. Checking applied changes...")
    changes = await apply_manager.get_applied_changes()
    print(f"   Total applied changes: {len(changes)}")
    
    change_status = await apply_manager.get_change_status(test_rec['id'])
    if change_status:
        print(f"   Change status: {change_status['status']}")
        print(f"   Applied at: {change_status['applied_at']}")
    
    # Test 5: Rollback the recommendation
    print("\n5. Rolling back recommendation...")
    try:
        rollback_result = await apply_manager.rollback_recommendation(test_rec['id'])
        print(f"   ✅ Rolled back successfully!")
        print(f"   SQL executed: {rollback_result['sql_executed']}")
        print(f"   Rolled back at: {rollback_result['rolled_back_at']}")
    except Exception as e:
        print(f"   ❌ Failed to rollback: {e}")
        return False
    
    # Test 6: Check final status
    print("\n6. Checking final status...")
    changes_after = await apply_manager.get_applied_changes()
    print(f"   Total changes after rollback: {len(changes_after)}")
    
    change_status_after = await apply_manager.get_change_status(test_rec['id'])
    if change_status_after:
        print(f"   Final status: {change_status_after['status']}")
    
    # Test 7: Test apply manager status
    print("\n7. Testing apply manager status...")
    try:
        # This would normally be called via API, but we can test the logic
        changes = await apply_manager.get_applied_changes()
        status_counts = {}
        for change in changes:
            status = change.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"   Total changes: {len(changes)}")
        print(f"   Status counts: {status_counts}")
    except Exception as e:
        print(f"   ❌ Failed to get status: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Phase 6 Apply/Rollback Flow Test Completed Successfully!")
    return True


async def test_apply_manager_cleanup():
    """Test the cleanup functionality."""
    print("\n🧹 Testing Apply Manager Cleanup...")
    
    apply_manager = get_apply_manager()
    
    try:
        cleaned_count = await apply_manager.cleanup_old_schemas(max_age_hours=1)
        print(f"   Cleaned up {cleaned_count} old schemas")
        return True
    except Exception as e:
        print(f"   ❌ Cleanup failed: {e}")
        return False


async def main():
    """Main test function."""
    print("🚀 Starting Phase 6 Tests...")
    
    # Test apply/rollback functionality
    success1 = await test_phase6_apply_rollback()
    
    # Test cleanup functionality
    success2 = await test_apply_manager_cleanup()
    
    if success1 and success2:
        print("\n🎉 All Phase 6 tests passed!")
        return 0
    else:
        print("\n❌ Some Phase 6 tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 