#!/usr/bin/env python3
"""
Test script for validating AI-generated executable recommendations.
Tests the new prompt system with real query data and validates SQL syntax.
"""

import asyncio
import json
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from analysis.llm import generate_recommendation
from analysis.core import fingerprint_query
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test cases with different query patterns
TEST_CASES = [
    {
        "name": "Sequential Scan with WHERE",
        "query_data": {
            "query_text": "SELECT * FROM users WHERE email = 'john@example.com'",
            "actual_metrics": {
                "calls": 150,
                "total_time": 1250.5,
                "mean_time": 8.34,
                "percentage_of_total_time": 2.3
            },
            "execution_plan": {
                "Plan": {
                    "Node Type": "Seq Scan",
                    "Relation Name": "users",
                    "Filter": "((email)::text = 'john@example.com'::text)",
                    "Rows Removed by Filter": 9850,
                    "Actual Rows": 1,
                    "Actual Total Time": 7.234
                }
            }
        }
    },
    {
        "name": "Missing Index on JOIN",
        "query_data": {
            "query_text": "SELECT u.id, p.title FROM users u JOIN posts p ON u.id = p.user_id WHERE u.status = 'active'",
            "actual_metrics": {
                "calls": 85,
                "total_time": 2140.8,
                "mean_time": 25.18,
                "percentage_of_total_time": 4.1
            },
            "execution_plan": {
                "Plan": {
                    "Node Type": "Hash Join",
                    "Join Type": "Inner",
                    "Plans": [
                        {
                            "Node Type": "Seq Scan",
                            "Relation Name": "users",
                            "Filter": "((status)::text = 'active'::text)",
                            "Actual Rows": 2500
                        },
                        {
                            "Node Type": "Seq Scan", 
                            "Relation Name": "posts",
                            "Actual Rows": 15000
                        }
                    ]
                }
            }
        }
    },
    {
        "name": "Unindexed ORDER BY",
        "query_data": {
            "query_text": "SELECT * FROM orders WHERE status = 'pending' ORDER BY created_at DESC LIMIT 50",
            "actual_metrics": {
                "calls": 45,
                "total_time": 890.2,
                "mean_time": 19.78,
                "percentage_of_total_time": 1.7
            },
            "execution_plan": {
                "Plan": {
                    "Node Type": "Limit",
                    "Plans": [
                        {
                            "Node Type": "Sort",
                            "Sort Key": ["created_at DESC"],
                            "Sort Method": "external merge",
                            "Plans": [
                                {
                                    "Node Type": "Seq Scan",
                                    "Relation Name": "orders",
                                    "Filter": "((status)::text = 'pending'::text)",
                                    "Actual Rows": 5000
                                }
                            ]
                        }
                    ]
                }
            }
        }
    },
    {
        "name": "Complex Query (Advisory Only)",
        "query_data": {
            "query_text": """
            SELECT u.email, COUNT(o.id) as order_count, 
                   AVG(oi.price * oi.quantity) as avg_order_value
            FROM users u
            LEFT JOIN orders o ON u.id = o.user_id  
            LEFT JOIN order_items oi ON o.id = oi.order_id
            LEFT JOIN user_roles ur ON u.id = ur.user_id
            LEFT JOIN roles r ON ur.role_id = r.id
            WHERE u.created_at > NOW() - INTERVAL '1 year'
            GROUP BY u.id, u.email
            HAVING COUNT(o.id) > 5
            ORDER BY avg_order_value DESC
            """,
            "actual_metrics": {
                "calls": 12,
                "total_time": 15678.9,
                "mean_time": 1306.58,
                "percentage_of_total_time": 8.2
            }
        }
    }
]

def validate_sql_syntax(sql: str) -> tuple[bool, str]:
    """
    Basic SQL syntax validation for CREATE INDEX statements.
    Returns (is_valid, error_message)
    """
    if not sql:
        return True, "No SQL provided"
    
    sql_upper = sql.upper().strip()
    
    # Check if it's a CREATE INDEX statement
    if not sql_upper.startswith('CREATE INDEX'):
        return False, "SQL must start with CREATE INDEX"
    
    # Check for CONCURRENTLY
    if 'CONCURRENTLY' not in sql_upper:
        return False, "Must use CREATE INDEX CONCURRENTLY for safety"
    
    # Basic structure check
    if ' ON ' not in sql_upper:
        return False, "Missing ON clause"
    
    if '(' not in sql and ')' not in sql:
        return False, "Missing column specification"
    
    # Check for proper naming convention
    if 'idx_' not in sql:
        return False, "Index name should follow idx_tablename_columnname convention"
    
    return True, "Valid SQL syntax"

def validate_rollback_sql(rollback_sql: str, sql_fix: str) -> tuple[bool, str]:
    """
    Validate that rollback SQL properly undoes the sql_fix.
    """
    if not sql_fix:
        return True, "No sql_fix to rollback"
    
    if not rollback_sql:
        return False, "rollback_sql required when sql_fix is provided"
    
    rollback_upper = rollback_sql.upper().strip()
    
    # Should be DROP INDEX
    if not rollback_upper.startswith('DROP INDEX'):
        return False, "rollback_sql should start with DROP INDEX"
    
    # Extract index name from sql_fix
    try:
        sql_fix_parts = sql_fix.split()
        create_idx = sql_fix_parts.index('INDEX')
        if create_idx + 1 < len(sql_fix_parts):
            # Skip CONCURRENTLY if present
            idx_name_pos = create_idx + 2 if sql_fix_parts[create_idx + 1].upper() == 'CONCURRENTLY' else create_idx + 1
            if idx_name_pos < len(sql_fix_parts):
                index_name = sql_fix_parts[idx_name_pos]
                if index_name not in rollback_sql:
                    return False, f"rollback_sql should reference index name '{index_name}'"
    except (ValueError, IndexError):
        return False, "Could not extract index name from sql_fix"
    
    return True, "Valid rollback SQL"

async def test_recommendation_generation():
    """Test the AI recommendation generation with all test cases."""
    print("🧪 Testing AI Recommendation Generation with Executable SQL\n")
    
    results = []
    
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"📝 Test Case {i}: {test_case['name']}")
        print(f"   Query: {test_case['query_data']['query_text'][:60]}...")
        
        try:
            # Generate recommendation
            recommendation = await generate_recommendation(test_case['query_data'])
            
            # Debug: Print the raw recommendation
            print(f"   🔍 Raw Response: {json.dumps(recommendation, indent=2)}")
            
            # Validate structure
            required_fields = ['title', 'description', 'confidence', 'estimated_improvement', 'risk_level']
            missing_fields = [field for field in required_fields if field not in recommendation]
            
            if missing_fields:
                print(f"   ❌ Missing fields: {missing_fields}")
                continue
            
            # Validate SQL syntax if provided
            sql_fix = recommendation.get('sql_fix')
            rollback_sql = recommendation.get('rollback_sql')
            
            sql_valid, sql_error = validate_sql_syntax(sql_fix)
            rollback_valid, rollback_error = validate_rollback_sql(rollback_sql, sql_fix)
            
            # Print results
            print(f"   📋 Title: {recommendation['title']}")
            print(f"   🎯 Confidence: {recommendation['confidence']}%")
            print(f"   📈 Estimated Improvement: {recommendation['estimated_improvement']}")
            print(f"   ⚠️  Risk Level: {recommendation['risk_level']}")
            
            if sql_fix:
                print(f"   🔧 SQL Fix: {sql_fix}")
                print(f"   ↩️  Rollback: {rollback_sql}")
                print(f"   ✅ SQL Valid: {sql_valid} {'✓' if sql_valid else '✗ ' + sql_error}")
                print(f"   ✅ Rollback Valid: {rollback_valid} {'✓' if rollback_valid else '✗ ' + rollback_error}")
            else:
                print(f"   📝 Advisory Only (no executable SQL)")
            
            # Store results
            results.append({
                'test_case': test_case['name'],
                'recommendation': recommendation,
                'sql_valid': sql_valid,
                'rollback_valid': rollback_valid,
                'has_executable_sql': bool(sql_fix)
            })
            
            print(f"   {'✅ PASS' if sql_valid and rollback_valid else '❌ NEEDS FIX'}\n")
            
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            print(f"   📋 Error Type: {type(e).__name__}")
            import traceback
            print(f"   📋 Traceback: {traceback.format_exc()}")
            print()
            results.append({
                'test_case': test_case['name'],
                'error': str(e)
            })
    
    # Summary
    print("📊 Test Summary:")
    total_tests = len(results)
    executable_sql_count = sum(1 for r in results if r.get('has_executable_sql'))
    valid_sql_count = sum(1 for r in results if r.get('sql_valid') and r.get('rollback_valid'))
    error_count = sum(1 for r in results if 'error' in r)
    
    print(f"   Total Tests: {total_tests}")
    print(f"   With Executable SQL: {executable_sql_count}")
    print(f"   Valid SQL Syntax: {valid_sql_count}")
    print(f"   Errors: {error_count}")
    print(f"   Success Rate: {((total_tests - error_count) / total_tests * 100):.1f}%")
    
    if executable_sql_count > 0:
        print(f"\n🎯 Executable SQL Generation: {(executable_sql_count / total_tests * 100):.1f}%")
        print(f"🛡️  SQL Safety Validation: {(valid_sql_count / executable_sql_count * 100):.1f}%")
    
    return results

if __name__ == "__main__":
    asyncio.run(test_recommendation_generation()) 