"""
Execution plan analysis module for OptiSchema backend.
Handles EXPLAIN plan execution, parsing, and performance bottleneck detection.
"""

import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from db import get_pool
from models import ExecutionPlan

logger = logging.getLogger(__name__)


async def execute_explain_plan(query_text: str) -> Optional[Dict[str, Any]]:
    """
    Execute EXPLAIN (FORMAT JSON) on a query and return the plan.
    
    Args:
        query_text: The SQL query to explain
        
    Returns:
        Execution plan as JSON dict or None if execution fails
    """
    try:
        # Wrap query in EXPLAIN
        explain_query = f"EXPLAIN (FORMAT JSON, ANALYZE, BUFFERS) {query_text}"
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Execute the explain query
            result = await conn.fetchval(explain_query)
            
            if result:
                # Parse the JSON result
                if isinstance(result, str):
                    plan_data = json.loads(result)
                else:
                    plan_data = result
                
                logger.info(f"Successfully generated execution plan for query")
                return plan_data
            else:
                logger.warning("EXPLAIN query returned no results")
                return None
                
    except Exception as e:
        logger.error(f"Failed to execute EXPLAIN plan: {e}")
        return None


def extract_plan_metrics(plan_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract key performance metrics from an execution plan.
    
    Args:
        plan_json: Raw execution plan JSON
        
    Returns:
        Extracted metrics and analysis
    """
    if not plan_json:
        return {}
    
    # Handle different plan structures
    if isinstance(plan_json, list):
        if len(plan_json) == 0:
            return {}
        plan = plan_json[0]
    elif isinstance(plan_json, dict):
        plan = plan_json
    else:
        return {}
    
    metrics = {
        'total_cost': 0.0,
        'total_time': 0.0,
        'planning_time': 0.0,
        'execution_time': 0.0,
        'total_rows': 0,
        'shared_hit_blocks': 0,
        'shared_read_blocks': 0,
        'shared_written_blocks': 0,
        'temp_read_blocks': 0,
        'temp_written_blocks': 0,
        'nodes': [],
        'bottlenecks': []
    }
    
    # Extract timing information
    if 'Planning Time' in plan:
        metrics['planning_time'] = float(plan['Planning Time'])
    if 'Execution Time' in plan:
        metrics['execution_time'] = float(plan['Execution Time'])
    
    metrics['total_time'] = metrics['planning_time'] + metrics['execution_time']
    
    # Extract buffer information
    if 'Shared Hit Blocks' in plan:
        metrics['shared_hit_blocks'] = int(plan['Shared Hit Blocks'])
    if 'Shared Read Blocks' in plan:
        metrics['shared_read_blocks'] = int(plan['Shared Read Blocks'])
    if 'Shared Written Blocks' in plan:
        metrics['shared_written_blocks'] = int(plan['Shared Written Blocks'])
    if 'Temp Read Blocks' in plan:
        metrics['temp_read_blocks'] = int(plan['Temp Read Blocks'])
    if 'Temp Written Blocks' in plan:
        metrics['temp_written_blocks'] = int(plan['Temp Written Blocks'])
    
    # Analyze plan nodes
    def analyze_node(node: Dict[str, Any], depth: int = 0) -> Dict[str, Any]:
        """Recursively analyze plan nodes."""
        node_info = {
            'node_type': node.get('Node Type', 'Unknown'),
            'cost': float(node.get('Total Cost', 0)),
            'rows': int(node.get('Plan Rows', 0)),
            'width': int(node.get('Plan Width', 0)),
            'actual_time': float(node.get('Actual Time', 0)),
            'actual_rows': int(node.get('Actual Rows', 0)),
            'loops': int(node.get('Loops', 1)),
            'depth': depth,
            'relation_name': node.get('Relation Name', ''),
            'index_name': node.get('Index Name', ''),
            'scan_direction': node.get('Scan Direction', ''),
            'filter': node.get('Filter', ''),
            'join_type': node.get('Join Type', ''),
            'hash_condition': node.get('Hash Cond', ''),
            'merge_condition': node.get('Merge Cond', ''),
            'sort_key': node.get('Sort Key', []),
            'group_key': node.get('Group Key', []),
            'children': []
        }
        
        # Update total metrics
        metrics['total_cost'] += node_info['cost']
        metrics['total_rows'] += node_info['actual_rows']
        
        # Analyze children
        if 'Plans' in node:
            for child in node['Plans']:
                child_info = analyze_node(child, depth + 1)
                node_info['children'].append(child_info)
        
        return node_info
    
    # Start analysis from the root plan
    if 'Plan' in plan:
        root_node = analyze_node(plan['Plan'])
        metrics['nodes'].append(root_node)
    
    # Detect bottlenecks
    bottlenecks = detect_plan_bottlenecks(metrics['nodes'])
    metrics['bottlenecks'] = bottlenecks
    
    return metrics


def extract_tables_from_plan(plan_json: Dict[str, Any]) -> List[str]:
    """
    Extract all table names referenced in an execution plan.
    
    Args:
        plan_json: Raw execution plan JSON
        
    Returns:
        List of unique table names
    """
    tables = set()
    
    def extract_from_node(node: Dict[str, Any]):
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


def extract_table_dependencies(plan_json: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Extract table dependencies and relationships from execution plan.
    
    Args:
        plan_json: Raw execution plan JSON
        
    Returns:
        Dictionary mapping table names to their dependencies
    """
    dependencies = {}
    
    def analyze_node_dependencies(node: Dict[str, Any], parent_table: str = None):
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


def extract_tables_from_condition(condition: str) -> List[str]:
    """
    Extract table names from a SQL condition string.
    This is a simplified implementation - in production, use proper SQL parsing.
    
    Args:
        condition: SQL condition string (e.g., "table1.column = table2.column")
        
    Returns:
        List of table names found in the condition
    """
    tables = set()
    
    # Simple regex-based extraction
    import re
    
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


def detect_plan_bottlenecks(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Detect performance bottlenecks in execution plan nodes.
    
    Args:
        nodes: List of analyzed plan nodes
        
    Returns:
        List of detected bottlenecks
    """
    bottlenecks = []
    
    def check_node_bottlenecks(node: Dict[str, Any]):
        """Check individual node for bottlenecks."""
        node_type = node['node_type']
        actual_time = node['actual_time']
        actual_rows = node['actual_rows']
        loops = node['loops']
        
        # Sequential Scan on large tables
        if node_type == 'Seq Scan' and actual_rows > 1000:
            bottlenecks.append({
                'type': 'sequential_scan',
                'severity': 'high' if actual_rows > 10000 else 'medium',
                'node_type': node_type,
                'description': f'Sequential scan on {node.get("relation_name", "table")} returning {actual_rows} rows',
                'recommendation': 'Consider adding an index on the WHERE clause columns',
                'impact': 'High - scans entire table'
            })
        
        # Sort operations on large datasets
        if node_type == 'Sort' and actual_rows > 1000:
            bottlenecks.append({
                'type': 'large_sort',
                'severity': 'medium',
                'node_type': node_type,
                'description': f'Sort operation on {actual_rows} rows',
                'recommendation': 'Consider adding an index with the same sort order',
                'impact': 'Medium - requires temporary storage'
            })
        
        # Hash operations
        if node_type == 'Hash' and actual_rows > 5000:
            bottlenecks.append({
                'type': 'large_hash',
                'severity': 'medium',
                'node_type': node_type,
                'description': f'Hash operation on {actual_rows} rows',
                'recommendation': 'Consider using nested loop joins for smaller datasets',
                'impact': 'Medium - requires building hash table in memory'
            })
        
        # Nested Loop with large outer relation
        if node_type == 'Nested Loop' and actual_rows > 10000:
            bottlenecks.append({
                'type': 'large_nested_loop',
                'severity': 'high',
                'node_type': node_type,
                'description': f'Nested loop join with {actual_rows} rows',
                'recommendation': 'Consider using hash or merge joins for large datasets',
                'impact': 'High - quadratic complexity'
            })
        
        # Check for missing indexes (Index Scan vs Seq Scan)
        if node_type == 'Seq Scan' and node.get('filter'):
            bottlenecks.append({
                'type': 'missing_index',
                'severity': 'high',
                'node_type': node_type,
                'description': f'Sequential scan with filter: {node.get("filter", "")}',
                'recommendation': 'Add index on filtered columns',
                'impact': 'High - scans entire table instead of using index'
            })
        
        # Recursively check children
        for child in node.get('children', []):
            check_node_bottlenecks(child)
    
    # Check all nodes
    for node in nodes:
        check_node_bottlenecks(node)
    
    return bottlenecks


async def analyze_execution_plan(query_text: str) -> Optional[ExecutionPlan]:
    """
    Analyze a query's execution plan and return detailed analysis.
    
    Args:
        query_text: The SQL query to analyze
        
    Returns:
        ExecutionPlan object with analysis results
    """
    try:
        # Execute EXPLAIN plan
        plan_json = await execute_explain_plan(query_text)
        if not plan_json:
            logger.warning("Failed to generate execution plan")
            return None
        
        # Extract metrics from plan
        metrics = extract_plan_metrics(plan_json)
        
        # Extract tables from plan
        tables = extract_tables_from_plan(plan_json)
        table_dependencies = extract_table_dependencies(plan_json)
        
        # Add table information to plan JSON
        enhanced_plan_json = {
            **plan_json,
            'extracted_tables': tables,
            'table_dependencies': table_dependencies
        }
        
        # Create ExecutionPlan object
        execution_plan = ExecutionPlan(
            plan_json=enhanced_plan_json,
            total_cost=metrics.get('total_cost'),
            total_time=metrics.get('total_time'),
            planning_time=metrics.get('planning_time'),
            execution_time=metrics.get('execution_time'),
            nodes=metrics.get('nodes', [])
        )
        
        logger.info(f"Execution plan analysis complete: {len(metrics.get('bottlenecks', []))} bottlenecks detected, {len(tables)} tables extracted")
        
        return execution_plan
        
    except Exception as e:
        logger.error(f"Failed to analyze execution plan: {e}")
        return None


def get_plan_summary(execution_plan: ExecutionPlan) -> Dict[str, Any]:
    """
    Generate a human-readable summary of execution plan analysis.
    
    Args:
        execution_plan: The analyzed execution plan
        
    Returns:
        Summary with key insights and recommendations
    """
    if not execution_plan:
        return {}
    
    summary = {
        'total_cost': execution_plan.total_cost,
        'total_time': execution_plan.total_time,
        'planning_time': execution_plan.planning_time,
        'execution_time': execution_plan.execution_time,
        'node_count': len(execution_plan.nodes),
        'performance_rating': 'good',
        'key_insights': [],
        'recommendations': []
    }
    
    # Analyze performance rating
    if execution_plan.total_time and execution_plan.total_time > 1000:  # > 1 second
        summary['performance_rating'] = 'poor'
    elif execution_plan.total_time and execution_plan.total_time > 100:  # > 100ms
        summary['performance_rating'] = 'fair'
    
    # Extract insights from nodes
    for node in execution_plan.nodes:
        node_type = node.get('node_type', '')
        actual_time = node.get('actual_time', 0)
        actual_rows = node.get('actual_rows', 0)
        
        if node_type == 'Seq Scan' and actual_rows > 1000:
            summary['key_insights'].append(f"Large sequential scan: {actual_rows} rows")
            summary['recommendations'].append("Consider adding indexes on WHERE clause columns")
        
        if node_type == 'Sort' and actual_rows > 1000:
            summary['key_insights'].append(f"Large sort operation: {actual_rows} rows")
            summary['recommendations'].append("Consider adding indexes with appropriate sort order")
        
        if actual_time > 100:  # > 100ms
            summary['key_insights'].append(f"Slow {node_type} operation: {actual_time:.2f}ms")
    
    return summary 