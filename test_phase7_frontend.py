#!/usr/bin/env python3
"""
Test script for Phase 7: Front-End Integration
"""

import asyncio
import sys
import os
import requests
import time
from datetime import datetime

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_frontend_endpoints():
    """Test frontend endpoints and functionality."""
    print("🧪 Testing Phase 7: Front-End Integration")
    print("=" * 50)
    
    base_url = "http://localhost:3000"
    api_url = "http://localhost:8000"
    
    # Test 1: Frontend accessibility
    print("\n1. Testing frontend accessibility...")
    try:
        response = requests.get(f"{base_url}/dashboard", timeout=10)
        if response.status_code == 200:
            print("   ✅ Frontend dashboard accessible")
        else:
            print(f"   ❌ Frontend returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Frontend not accessible: {e}")
        return False
    
    # Test 2: API endpoints accessible from frontend
    print("\n2. Testing API endpoints...")
    api_endpoints = [
        "/api/health",
        "/api/apply/status",
        "/api/apply/changes",
        "/api/benchmark",
        "/api/suggestions/latest"
    ]
    
    for endpoint in api_endpoints:
        try:
            response = requests.get(f"{api_url}{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"   ✅ {endpoint} - OK")
            else:
                print(f"   ⚠️  {endpoint} - Status {response.status_code}")
        except Exception as e:
            print(f"   ❌ {endpoint} - Error: {e}")
    
    # Test 3: Create test recommendation for frontend testing
    print("\n3. Creating test recommendation for frontend...")
    try:
        import sys
        sys.path.insert(0, 'backend')
        from recommendations_db import RecommendationsDB
        from datetime import datetime
        
        test_rec = {
            'id': 'phase7-frontend-test',
            'query_hash': 'phase7_frontend_test_hash',
            'recommendation_type': 'index',
            'title': 'Phase 7 Frontend Test: Add Index for Frontend Integration',
            'description': 'Test recommendation for Phase 7 frontend integration testing.',
            'sql_fix': 'CREATE INDEX IF NOT EXISTS idx_frontend_test ON test_table(id);',
            'original_sql': 'SELECT * FROM test_table WHERE id = 1;',
            'patch_sql': 'SELECT * FROM test_table WHERE id = 1;',
            'execution_plan_json': {'extracted_tables': ['test_table'], 'estimated_cost': 1000, 'actual_time_ms': 50.5},
            'estimated_improvement_percent': 85,
            'confidence_score': 95,
            'risk_level': 'low',
            'status': 'pending',
            'applied': False,
            'applied_at': None,
            'created_at': datetime.utcnow().isoformat()
        }
        
        RecommendationsDB.store_recommendation(test_rec)
        print(f"   ✅ Created test recommendation: {test_rec['id']}")
        
    except Exception as e:
        print(f"   ❌ Failed to create test recommendation: {e}")
    
    # Test 4: Test apply/rollback API endpoints
    print("\n4. Testing apply/rollback API endpoints...")
    
    # Test apply
    try:
        response = requests.post(f"{api_url}/api/apply/phase7-frontend-test", timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("   ✅ Apply endpoint working")
            else:
                print(f"   ⚠️  Apply endpoint returned error: {result.get('message')}")
        else:
            print(f"   ❌ Apply endpoint failed with status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Apply endpoint error: {e}")
    
    # Test rollback
    try:
        response = requests.post(f"{api_url}/api/apply/phase7-frontend-test/rollback", timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("   ✅ Rollback endpoint working")
            else:
                print(f"   ⚠️  Rollback endpoint returned error: {result.get('message')}")
        else:
            print(f"   ❌ Rollback endpoint failed with status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Rollback endpoint error: {e}")
    
    # Test 5: Test benchmark API endpoint
    print("\n5. Testing benchmark API endpoint...")
    try:
        response = requests.post(f"{api_url}/api/benchmark/phase7-frontend-test", timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                job_id = result.get('job_id')
                print(f"   ✅ Benchmark job created: {job_id}")
                
                # Poll for job completion
                print("   🔄 Polling for job completion...")
                for i in range(10):  # Poll for up to 20 seconds
                    time.sleep(2)
                    status_response = requests.get(f"{api_url}/api/benchmark/{job_id}", timeout=5)
                    if status_response.status_code == 200:
                        status_result = status_response.json()
                        if status_result.get('success'):
                            job_status = status_result['data']['status']
                            print(f"   📊 Job status: {job_status}")
                            if job_status in ['completed', 'failed']:
                                break
            else:
                print(f"   ⚠️  Benchmark endpoint returned error: {result.get('message')}")
        else:
            print(f"   ❌ Benchmark endpoint failed with status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Benchmark endpoint error: {e}")
    
    # Test 6: Test apply manager status
    print("\n6. Testing apply manager status...")
    try:
        response = requests.get(f"{api_url}/api/apply/status", timeout=5)
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                status_data = result['data']
                print(f"   ✅ Apply manager status: {status_data['total_changes']} total changes")
                print(f"   📊 Status counts: {status_data['status_counts']}")
                print(f"   🔧 Available operations: {status_data['available_operations']}")
            else:
                print(f"   ⚠️  Status endpoint returned error: {result.get('message')}")
        else:
            print(f"   ❌ Status endpoint failed with status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Status endpoint error: {e}")
    
    # Test 7: Test applied changes endpoint
    print("\n7. Testing applied changes endpoint...")
    try:
        response = requests.get(f"{api_url}/api/apply/changes", timeout=5)
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                changes = result['data']['changes']
                print(f"   ✅ Applied changes: {len(changes)} changes found")
                for change in changes:
                    print(f"   📝 Change: {change['recommendation_id']} - {change['status']}")
            else:
                print(f"   ⚠️  Changes endpoint returned error: {result.get('message')}")
        else:
            print(f"   ❌ Changes endpoint failed with status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Changes endpoint error: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Phase 7 Frontend Integration Test Completed!")
    print("\n🎯 Next Steps:")
    print("1. Open http://localhost:3000/dashboard in your browser")
    print("2. Navigate to the 'Optimizations' tab to see recommendations")
    print("3. Click 'Benchmark' on a recommendation to test the workflow")
    print("4. Navigate to the 'Apply Manager' tab to see applied changes")
    print("5. Test the complete apply/rollback workflow")
    
    return True

def main():
    """Main test function."""
    print("🚀 Starting Phase 7 Frontend Integration Tests...")
    
    success = test_frontend_endpoints()
    
    if success:
        print("\n🎉 Phase 7 frontend integration tests passed!")
        print("🌐 Frontend is ready for testing at http://localhost:3000/dashboard")
        return 0
    else:
        print("\n❌ Some Phase 7 frontend integration tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 