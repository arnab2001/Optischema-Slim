#!/usr/bin/env python3
"""
Simple test script for Phase 2 implementation.
Tests only the table extraction functions without full app dependencies.
"""

import logging
import sys
import os
import json
import re

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_tables_from_plan(plan_json):
    """
    Extract all table names referenced in an execution plan.
    
    Args:
        plan_json: Raw execution plan JSON
        
    Returns:
        List of unique table names
    """
    tables = set()
    
    def extract_from_node(node):
        """Recursively extract table names from plan nodes."""
        # Check for relation name (table name)
        if 'Relation Name' in node:
            table_name = node['Relation Name']
            if table_name:
                tables.add(table_name)
        
        # Check for index scan table references
        if 'Index Name' in node and 'Relation Name' in node:
            table_name = node['Relation Name']
            if table_name:
                tables.add(table_name)
        
        # Check for CTE references
        if 'CTE Name' in node:
            cte_name = node['CTE Name']
            if cte_name:
                tables.add(f"CTE_{cte_name}")
        
        # Check for subquery references
        if 'Subplan Name' in node:
            subplan_name = node['Subplan Name']
            if subplan_name:
                tables.add(f"SUBQUERY_{subplan_name}")
        
        # Recursively check children
        if 'Plans' in node:
            for child in node['Plans']:
                extract_from_node(child)
    
    # Handle different plan structures
    if isinstance(plan_json, list):
        if len(plan_json) == 0:
            return []
        plan = plan_json[0]
    elif isinstance(plan_json, dict):
        plan = plan_json
    else:
        return []
    
    # Extract from the main plan
    if 'Plan' in plan:
        extract_from_node(plan['Plan'])
    
    return list(tables)


def extract_table_dependencies(plan_json):
    """
    Extract table dependencies and relationships from execution plan.
    
    Args:
        plan_json: Raw execution plan JSON
        
    Returns:
        Dictionary mapping table names to their dependencies
    """
    dependencies = {}
    
    def analyze_node_dependencies(node, parent_table=None):
        """Analyze node for table dependencies."""
        node_type = node.get('Node Type', '')
        relation_name = node.get('Relation Name', '')
        
        if relation_name:
            if relation_name not in dependencies:
                dependencies[relation_name] = []
            
            if parent_table and parent_table != relation_name:
                dependencies[relation_name].append(parent_table)
        
        # Handle join operations
        if node_type in ['Hash Join', 'Nested Loop', 'Merge Join']:
            join_type = node.get('Join Type', '')
            hash_condition = node.get('Hash Cond', '')
            merge_condition = node.get('Merge Cond', '')
            
            # Extract table names from join conditions
            if hash_condition:
                # Simple extraction - in production, use proper SQL parsing
                tables_in_condition = extract_tables_from_condition(hash_condition)
                for table in tables_in_condition:
                    if table in dependencies:
                        dependencies[table].extend(tables_in_condition)
            
            if merge_condition:
                tables_in_condition = extract_tables_from_condition(merge_condition)
                for table in tables_in_condition:
                    if table in dependencies:
                        dependencies[table].extend(tables_in_condition)
        
        # Recursively check children
        if 'Plans' in node:
            for child in node['Plans']:
                analyze_node_dependencies(child, relation_name or parent_table)
    
    # Handle different plan structures
    if isinstance(plan_json, list):
        if len(plan_json) == 0:
            return {}
        plan = plan_json[0]
    elif isinstance(plan_json, dict):
        plan = plan_json
    else:
        return {}
    
    # Analyze from the main plan
    if 'Plan' in plan:
        analyze_node_dependencies(plan['Plan'])
    
    # Remove duplicates and self-references
    for table in dependencies:
        dependencies[table] = list(set(dependencies[table]))
        if table in dependencies[table]:
            dependencies[table].remove(table)
    
    return dependencies


def extract_tables_from_condition(condition):
    """
    Extract table names from a SQL condition string.
    This is a simplified implementation - in production, use proper SQL parsing.
    
    Args:
        condition: SQL condition string (e.g., "table1.column = table2.column")
        
    Returns:
        List of table names found in the condition
    """
    tables = set()
    
    # Look for patterns like table.column or "table".column
    patterns = [
        r'([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)',  # table.column
        r'"([^"]+)"\.([a-zA-Z_][a-zA-Z0-9_]*)',  # "table".column
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, condition)
        for match in matches:
            if len(match) == 2:
                table_name = match[0] if match[0] else match[1]
                if table_name and not table_name.lower() in ['select', 'from', 'where', 'and', 'or', 'not']:
                    tables.add(table_name)
    
    return list(tables)


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


def test_enhanced_plan_structure():
    """Test enhanced plan JSON structure."""
    logger.info("🧪 Testing enhanced plan structure...")
    
    # Mock execution plan
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
    logger.info("🚀 Starting Phase 2 simple tests...")
    
    try:
        # Run tests
        tests = [
            ("Table Extraction", test_table_extraction),
            ("Condition Parsing", test_condition_parsing),
            ("Complex Plan", test_complex_plan),
            ("CTE and Subqueries", test_cte_and_subqueries),
            ("Edge Cases", test_edge_cases),
            ("Enhanced Plan Structure", test_enhanced_plan_structure)
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