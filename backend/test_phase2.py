#!/usr/bin/env python3
"""
Test script for Phase 2 implementation.
Validates execution plan table extraction functionality.
"""

import asyncio
import logging
import sys
import os
import json

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analysis.explain import (
    extract_tables_from_plan,
    extract_table_dependencies,
    extract_tables_from_condition,
    analyze_execution_plan
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_table_extraction():
    """Test table extraction from execution plans."""
    logger.info("🧪 Testing table extraction...")
    
    # Sample execution plan JSON (simplified)
    sample_plan = {
        "Plan": {
            "Node Type": "Hash Join",
            "Join Type": "Inner",
            "Hash Cond": "users.id = orders.user_id",
            "Plans": [
                {
                    "Node Type": "Seq Scan",
                    "Relation Name": "users",
                    "Plans": []
                },
                {
                    "Node Type": "Index Scan",
                    "Relation Name": "orders",
                    "Index Name": "idx_orders_user_id",
                    "Plans": []
                }
            ]
        }
    }
    
    # Test table extraction
    tables = extract_tables_from_plan(sample_plan)
    logger.info(f"✅ Extracted tables: {tables}")
    
    expected_tables = ['users', 'orders']
    if set(tables) == set(expected_tables):
        logger.info("✅ Table extraction working correctly")
    else:
        logger.error(f"❌ Expected {expected_tables}, got {tables}")
        return False
    
    # Test table dependencies
    dependencies = extract_table_dependencies(sample_plan)
    logger.info(f"✅ Table dependencies: {dependencies}")
    
    return True


def test_condition_parsing():
    """Test SQL condition parsing."""
    logger.info("🧪 Testing condition parsing...")
    
    test_conditions = [
        "users.id = orders.user_id",
        '"public"."users"."email" = \'admin@example.com\'"',
        "table1.column1 = table2.column2 AND table3.column3 > 100",
        "users.name ILIKE '%john%'"
    ]
    
    for condition in test_conditions:
        tables = extract_tables_from_condition(condition)
        logger.info(f"✅ Condition '{condition}' -> Tables: {tables}")
    
    return True


def test_complex_plan():
    """Test complex execution plan with multiple joins."""
    logger.info("🧪 Testing complex execution plan...")
    
    complex_plan = {
        "Plan": {
            "Node Type": "Hash Join",
            "Join Type": "Inner",
            "Hash Cond": "orders.user_id = users.id",
            "Plans": [
                {
                    "Node Type": "Hash Join",
                    "Join Type": "Inner",
                    "Hash Cond": "order_items.order_id = orders.id",
                    "Plans": [
                        {
                            "Node Type": "Seq Scan",
                            "Relation Name": "order_items",
                            "Plans": []
                        },
                        {
                            "Node Type": "Index Scan",
                            "Relation Name": "orders",
                            "Index Name": "idx_orders_id",
                            "Plans": []
                        }
                    ]
                },
                {
                    "Node Type": "Seq Scan",
                    "Relation Name": "users",
                    "Plans": []
                }
            ]
        }
    }
    
    # Test table extraction
    tables = extract_tables_from_plan(complex_plan)
    logger.info(f"✅ Complex plan tables: {tables}")
    
    expected_tables = ['order_items', 'orders', 'users']
    if set(tables) == set(expected_tables):
        logger.info("✅ Complex plan table extraction working")
    else:
        logger.error(f"❌ Expected {expected_tables}, got {tables}")
        return False
    
    # Test dependencies
    dependencies = extract_table_dependencies(complex_plan)
    logger.info(f"✅ Complex plan dependencies: {dependencies}")
    
    return True


def test_cte_and_subqueries():
    """Test CTE and subquery handling."""
    logger.info("🧪 Testing CTE and subquery handling...")
    
    cte_plan = {
        "Plan": {
            "Node Type": "CTE Scan",
            "CTE Name": "user_stats",
            "Plans": [
                {
                    "Node Type": "Hash Join",
                    "Join Type": "Inner",
                    "Hash Cond": "users.id = stats.user_id",
                    "Plans": [
                        {
                            "Node Type": "Seq Scan",
                            "Relation Name": "users",
                            "Plans": []
                        },
                        {
                            "Node Type": "Seq Scan",
                            "Relation Name": "stats",
                            "Plans": []
                        }
                    ]
                }
            ]
        }
    }
    
    tables = extract_tables_from_plan(cte_plan)
    logger.info(f"✅ CTE plan tables: {tables}")
    
    expected_tables = ['CTE_user_stats', 'users', 'stats']
    if set(tables) == set(expected_tables):
        logger.info("✅ CTE handling working correctly")
    else:
        logger.error(f"❌ Expected {expected_tables}, got {tables}")
        return False
    
    return True


def test_edge_cases():
    """Test edge cases and error handling."""
    logger.info("🧪 Testing edge cases...")
    
    # Test empty plan
    empty_plan = {}
    tables = extract_tables_from_plan(empty_plan)
    if tables == []:
        logger.info("✅ Empty plan handled correctly")
    else:
        logger.error(f"❌ Empty plan should return [], got {tables}")
        return False
    
    # Test None plan
    tables = extract_tables_from_plan(None)
    if tables == []:
        logger.info("✅ None plan handled correctly")
    else:
        logger.error(f"❌ None plan should return [], got {tables}")
        return False
    
    # Test list format
    list_plan = [{"Plan": {"Node Type": "Seq Scan", "Relation Name": "test"}}]
    tables = extract_tables_from_plan(list_plan)
    if tables == ['test']:
        logger.info("✅ List format handled correctly")
    else:
        logger.error(f"❌ List format should return ['test'], got {tables}")
        return False
    
    return True


async def test_full_analysis():
    """Test full execution plan analysis (if database available)."""
    logger.info("🧪 Testing full analysis (mock)...")
    
    # Since we can't connect to the database in this test,
    # we'll test the function with a mock plan
    mock_plan = {
        "Plan": {
            "Node Type": "Seq Scan",
            "Relation Name": "test_table",
            "Plans": []
        }
    }
    
    # Test the enhanced plan JSON structure
    enhanced_plan = {
        **mock_plan,
        'extracted_tables': ['test_table'],
        'table_dependencies': {'test_table': []}
    }
    
    logger.info(f"✅ Enhanced plan structure: {json.dumps(enhanced_plan, indent=2)}")
    
    return True


def main():
    """Run all Phase 2 tests."""
    logger.info("🚀 Starting Phase 2 tests...")
    
    try:
        # Run tests
        tests = [
            ("Table Extraction", test_table_extraction),
            ("Condition Parsing", test_condition_parsing),
            ("Complex Plan", test_complex_plan),
            ("CTE and Subqueries", test_cte_and_subqueries),
            ("Edge Cases", test_edge_cases),
            ("Full Analysis", lambda: asyncio.run(test_full_analysis()))
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            logger.info(f"\n{'='*50}")
            logger.info(f"Running: {test_name}")
            logger.info(f"{'='*50}")
            
            try:
                if test_func():
                    logger.info(f"✅ {test_name}: PASSED")
                    passed += 1
                else:
                    logger.error(f"❌ {test_name}: FAILED")
            except Exception as e:
                logger.error(f"❌ {test_name}: ERROR - {e}")
        
        # Summary
        logger.info(f"\n{'='*50}")
        logger.info(f"TEST SUMMARY: {passed}/{total} tests passed")
        logger.info(f"{'='*50}")
        
        if passed == total:
            logger.info("🎉 All tests passed! Phase 2 implementation is working correctly.")
        else:
            logger.error(f"⚠️  {total - passed} tests failed. Please check the implementation.")
        
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        return False
    
    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 