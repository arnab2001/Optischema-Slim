"""
Analysis Orchestrator for OptiSchema Slim.
Coordinates the 3-Tier Strategy: Verifiable (Index), Estimatable (Rewrite), Advisory.
"""

import logging
import sqlglot
from typing import Dict, Any, List

from services.metric_service import metric_service
from services.schema_service import schema_service
from services.simulation_service import simulation_service
from services.llm_service import llm_service
from connection_manager import connection_manager

logger = logging.getLogger(__name__)

class AnalysisOrchestrator:
    def detect_statement_type(self, query: str) -> str:
        """
        Detect the SQL statement type from a query string.
        Returns uppercase statement type (e.g., 'SELECT', 'COPY', 'CREATE').
        """
        import re
        # Remove comments and normalize whitespace
        cleaned = re.sub(r'--.*?$', '', query, flags=re.MULTILINE)
        cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
        cleaned = cleaned.strip()
        
        # Match first significant keyword
        match = re.match(r'^\s*(\w+)', cleaned, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        
        return "UNKNOWN"
    
    async def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Orchestrate the analysis process:
        1. Gather Context (Schema, Stats, Plan)
        2. Ask AI (LLM)
        3. Route based on Category (Index -> Simulate, Rewrite -> Estimate, Advisory -> Return)
        """
        # Check for unsupported statement types before proceeding
        stmt_type = self.detect_statement_type(query)
        unsupported_types = ["COPY", "CREATE", "ALTER", "DROP", "TRUNCATE", "VACUUM", "ANALYZE", "REINDEX", "CLUSTER"]
        
        if stmt_type in unsupported_types:
            suggestions = {
                "COPY": "For COPY statements, analyze the underlying table structure and SELECT queries that populate it.",
                "CREATE": "For DDL statements like CREATE TABLE, analyze the SELECT queries that will use these tables.",
                "ALTER": "For ALTER statements, analyze the SELECT/UPDATE queries that will benefit from the changes.",
                "DROP": "DDL statements cannot be analyzed. Analyze the queries that depend on the objects being dropped.",
                "TRUNCATE": "TRUNCATE cannot be analyzed. Analyze the SELECT queries that read from the truncated tables.",
                "VACUUM": "Maintenance statements cannot be analyzed. Use the health scan feature to check table bloat.",
                "ANALYZE": "Maintenance statements cannot be analyzed. Use the health scan feature to check statistics.",
                "REINDEX": "Maintenance statements cannot be analyzed. Use the health scan feature to check index usage.",
                "CLUSTER": "Maintenance statements cannot be analyzed. Use the health scan feature to check table organization."
            }
            
            return {
                "error": f"{stmt_type} statements cannot be analyzed",
                "message": f"EXPLAIN is not supported for {stmt_type} statements.",
                "suggestion": suggestions.get(stmt_type, "For DDL statements, analyze the SELECT queries they depend on."),
                "statement_type": stmt_type
            }
        
        # 1. GATHER CONTEXT
        # Extract table names using sqlglot (preserving schema qualification)
        try:
            parsed = sqlglot.parse_one(query)
            tables = []
            for t in parsed.find_all(sqlglot.exp.Table):
                # Use sql() to get qualified name, remove quotes if any
                qualified_name = t.sql().replace('"', '')
                tables.append(qualified_name)
        except Exception as e:
            logger.warning(f"Failed to parse query tables: {e}")
            tables = []

        # Get Schema Context
        schema_context = await schema_service.get_context_for_query(tables)
        
        # Get Current Plan (Baseline)
        pool = await connection_manager.get_pool()
        if not pool:
            return {"error": "No database connection"}
        
        async with pool.acquire() as conn:
            # 1.5 Find a working candidate (handles parameter substitution)
            explain_query = await simulation_service.find_working_candidate(conn, query)
            
            try:
                plan_json = await conn.fetchval(f"EXPLAIN (FORMAT JSON) {explain_query}")
                import json
                current_plan = json.loads(plan_json)[0]['Plan']
                current_cost = current_plan['Total Cost']
            except Exception as e:
                return {"error": f"Failed to get execution plan: {str(e)}"}

        # 2. ASK AI
        suggestion = await llm_service.analyze_query(query, schema_context, current_plan)
        
        if "error" in suggestion:
            return suggestion

        category = suggestion.get("category")
        suggested_sql = suggestion.get("sql")
        
        result = {
            "original_query": query,
            "original_cost": current_cost,
            "original_plan": current_plan,
            "suggestion": suggestion,
            "analysis_type": category
        }
        
        # Preserve benchmark metadata if present
        if "_benchmark_metadata" in suggestion:
            result["_benchmark_metadata"] = suggestion["_benchmark_metadata"]

        # 3. ROUTE BASED ON CATEGORY
        if category == "INDEX" and suggested_sql:
            # Tier 1: Verifiable (HypoPG)
            simulation = await simulation_service.simulate_index(query, suggested_sql)
            result["simulation"] = simulation
            
            # Check if simulation fell back to advisory
            if simulation.get("verification_status") == "advisory":
                result["verification_status"] = "advisory"
                result["message"] = simulation.get("message")
            else:
                result["verification_status"] = "verified" if "improvement_percent" in simulation else "failed"
            
        elif category == "REWRITE" and suggested_sql:
            # Tier 2: Estimatable (Safe Rewrite)
            estimation = await simulation_service.simulate_rewrite(query, suggested_sql)
            result["estimation"] = estimation
            result["verification_status"] = "estimated" if "new_cost" in estimation else "failed"
            
        else:
            # Tier 3: Advisory
            result["verification_status"] = "advisory"
            
        return result


analysis_orchestrator = AnalysisOrchestrator()

