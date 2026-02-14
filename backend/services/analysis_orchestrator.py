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

            # WORKLOAD IMPACT TEST: Test this index against other queries
            # Only if simulation succeeded and we have tables
            if result["verification_status"] == "verified" and tables:
                try:
                    # Extract table name from the first table (or from index SQL)
                    # Prefer getting it from the index SQL to be more accurate
                    import re
                    match = re.search(r'ON\s+([^\s(]+)', suggested_sql, re.IGNORECASE)
                    target_table = match.group(1).strip() if match else (tables[0] if tables else None)

                    if target_table:
                        # Remove schema prefix if present for matching
                        table_only = target_table.split('.')[-1]
                        workload_impact = await simulation_service.test_workload_impact(
                            index_sql=suggested_sql,
                            table_name=table_only,
                            limit=20
                        )

                        if "error" not in workload_impact:
                            result["workload_impact"] = workload_impact
                except Exception as e:
                    logger.warning(f"Workload impact test failed: {e}")
                    # Don't fail the entire analysis if workload test fails
            
        elif category == "REWRITE" and suggested_sql:
            # Tier 2: Estimatable (Safe Rewrite)
            estimation = await simulation_service.simulate_rewrite(query, suggested_sql)
            result["estimation"] = estimation
            result["verification_status"] = "estimated" if "new_cost" in estimation else "failed"
            
        else:
            # Tier 3: Advisory
            result["verification_status"] = "advisory"

        # 4. BUILD CONFIDENCE FACTORS
        result["confidence_factors"] = self._build_confidence_factors(result, schema_context)
        result["confidence_score"] = self._compute_confidence_score(result)

        return result

    def _build_confidence_factors(self, result: Dict[str, Any], schema_context: str) -> list:
        """
        Derive confidence factors from analysis result and context.
        These explain *why* we trust or distrust the recommendation.
        """
        factors = []
        verification = result.get("verification_status", "")
        simulation = result.get("simulation", {})
        estimation = result.get("estimation", {})

        # Factor: verification method
        if verification == "verified":
            improvement = simulation.get("improvement_percent", 0)
            factors.append(f"HypoPG verified {improvement}% cost reduction")
        elif verification == "estimated":
            new_cost = estimation.get("new_cost")
            original = result.get("original_cost")
            if new_cost and original and original > 0:
                reduction = ((original - new_cost) / original) * 100
                factors.append(f"EXPLAIN estimation shows {reduction:.0f}% cost reduction")
            else:
                factors.append("EXPLAIN-based estimation (no HypoPG)")
        elif verification == "advisory":
            factors.append("Advisory only - no automated verification available")

        # Factor: table size (parse from schema context)
        try:
            import re
            row_counts = re.findall(r'Rows:\s*([\d,]+)', schema_context)
            for rc in row_counts:
                count = int(rc.replace(',', ''))
                if count > 1_000_000:
                    factors.append(f"Table has {count:,} rows (high impact)")
                    break
                elif count > 100_000:
                    factors.append(f"Table has {count:,} rows (moderate impact)")
                    break
        except Exception:
            pass

        # Factor: column warnings
        col_warnings = result.get("suggestion", {}).get("_column_warnings", [])
        if col_warnings:
            factors.append(f"Column validation: {len(col_warnings)} warning(s)")
        else:
            if result.get("suggestion", {}).get("sql"):
                factors.append("All referenced columns validated against schema")

        # Factor: category alignment
        category = result.get("analysis_type", "")
        if category == "INDEX" and simulation.get("improvement_percent", 0) > 30:
            factors.append("High-impact index suggestion (>30% improvement)")

        # Factor: workload impact
        workload = result.get("workload_impact", {})
        if workload and "tested_queries" in workload:
            improved = workload.get("improved", 0)
            regressed = workload.get("regressed", 0)
            tested = workload.get("tested_queries", 0)

            if regressed == 0 and improved > 0:
                factors.append(f"Workload test: {improved}/{tested} queries improved, none regressed")
            elif regressed > 0:
                factors.append(f"⚠️  Workload test: {regressed}/{tested} queries regressed")
            elif improved == 0 and tested > 0:
                factors.append(f"Workload test: No queries benefited from this index")

        return factors

    def _compute_confidence_score(self, result: Dict[str, Any]) -> int:
        """
        Compute a 0-100 confidence score based on verification status and results.
        Includes workload impact if available.
        """
        verification = result.get("verification_status", "")
        simulation = result.get("simulation", {})
        workload = result.get("workload_impact", {})

        base_score = 0
        if verification == "verified":
            improvement = simulation.get("improvement_percent", 0)
            # Verified + high improvement = high confidence
            if improvement > 30:
                base_score = 90
            elif improvement > 10:
                base_score = 80
            else:
                base_score = 70
        elif verification == "estimated":
            base_score = 60
        elif verification == "advisory":
            base_score = 40
        else:
            base_score = 30

        # Adjust based on workload impact
        if workload and "tested_queries" in workload:
            improved = workload.get("improved", 0)
            regressed = workload.get("regressed", 0)
            tested = workload.get("tested_queries", 0)

            if tested > 0:
                # Boost if many queries improved and none regressed
                if regressed == 0 and improved >= tested * 0.5:
                    base_score = min(100, base_score + 5)
                # Penalize if queries regressed
                elif regressed > 0:
                    penalty = min(20, regressed * 5)  # Max -20 points
                    base_score = max(0, base_score - penalty)

        return base_score


analysis_orchestrator = AnalysisOrchestrator()

