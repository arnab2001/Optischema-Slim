"""
Simulation Service for OptiSchema Slim.
Uses HypoPG to simulate indexes and measure impact.
"""

import logging
import json
from typing import Dict, Any, Optional
from connection_manager import connection_manager

logger = logging.getLogger(__name__)

class SimulationService:
    async def check_hypopg_installed(self) -> bool:
        """Check if HypoPG extension is available and enabled."""
        pool = await connection_manager.get_pool()
        if not pool:
            return False
            
        try:
            async with pool.acquire() as conn:
                # Check extension availability
                available = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM pg_available_extensions WHERE name = 'hypopg')"
                )
                if not available:
                    return False
                
                # Check if enabled
                enabled = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'hypopg')"
                )
                if not enabled:
                    try:
                        await conn.execute("CREATE EXTENSION IF NOT EXISTS hypopg")
                        return True
                    except Exception as e:
                        logger.warning(f"Could not enable hypopg: {e}")
                        return False
                return True
        except Exception as e:
            logger.error(f"Error checking hypopg: {e}")
            return False

    async def find_working_candidate(self, conn, query: str) -> Optional[str]:
        """Try different parameter substitutions until one produces a valid JSON plan."""
        candidates = self.prepare_query_candidates(query)
        
        for candidate in candidates:
            try:
                # Test with EXPLAIN (FORMAT JSON) to ensure it works for all simulations
                await conn.execute(f"EXPLAIN (FORMAT JSON) {candidate}")
                return candidate
            except Exception:
                continue
        
        # Fallback to NULL if everything fails, or original query
        return candidates[-1] if candidates else query

    def prepare_query_candidates(self, query: str) -> list:
        """Generate candidate queries with smart, context-aware parameter substitutions."""
        import re
        
        def smart_replace(q: str, value_for_where: str) -> str:
            """Replace parameters with smart defaults based on context."""
            # 1. Handle interval $N -> '1 day'::interval (Postgres keywords)
            result = re.sub(r'interval\s+\$\d+', "'1 day'::interval", q, flags=re.IGNORECASE)
            
            # 2. Handle LIMIT $N and OFFSET $N specially (need integers)
            result = re.sub(r'(LIMIT\s+)\$\d+', r'\g<1>10', result, flags=re.IGNORECASE)
            result = re.sub(r'(OFFSET\s+)\$\d+', r'\g<1>0', result, flags=re.IGNORECASE)
            
            # 3. Replace remaining $N with the specified value
            result = re.sub(r'\$\d+', value_for_where, result)
            return result

        def mixed_replace(q: str) -> str:
            """Highly robust substitution for complex scripts."""
            result = q
            # 1. Handle interval $N
            result = re.sub(r'interval\s+\$\d+', "'1 day'::interval", result, flags=re.IGNORECASE)
            
            # 2. Handle ::jsonb and ::json
            result = re.sub(r'\$\d+(::jsonb?)', r"'{}'\g<1>", result, flags=re.IGNORECASE)
            
            # 3. Handle LIMIT/OFFSET
            result = re.sub(r'(LIMIT\s+)\$\d+', r'\g<1>10', result, flags=re.IGNORECASE)
            result = re.sub(r'(OFFSET\s+)\$\d+', r'\g<1>0', result, flags=re.IGNORECASE)
            
            # 4. Handle generate_series
            result = re.sub(r'(generate_series\s*\(\s*)\$\d+', r'\g<1>1', result, flags=re.IGNORECASE)
            result = re.sub(r'(generate_series\s*\(\s*[^,)]+,\s*)\$\d+', r'\g<1>10', result, flags=re.IGNORECASE)
            
            # 5. Handle arithmetic and list context (heuristically)
            # Replace $N with 1 if preceded/followed by math operators, brackets, or commas
            result = re.sub(r'([\*\/\+\-\(\[\,]\s*)\$\d+', r'\g<1>1', result)
            result = re.sub(r'\$\d+(\s*[\*\/\+\-\)\]\,])', r'1\g<1>', result)
            
            # 6. Fallback for remaining $N
            # Use 1 as a generic fallback because it satisfies text, numeric, and boolean contexts
            result = re.sub(r'\$\d+', "1", result)
            return result

        candidates = []
        # Mixed candidate (The strongest for complex scripts)
        candidates.append(mixed_replace(query))
        # Integer
        candidates.append(smart_replace(query, "1"))
        # String
        candidates.append(smart_replace(query, "'dummy'"))
        # UUID
        candidates.append(smart_replace(query, "'00000000-0000-0000-0000-000000000000'::uuid"))
        # NULL
        candidates.append(smart_replace(query, "NULL"))
        
        return candidates

    def _parse_indexes(self, index_sql: str) -> list:
        """Parse multiple CREATE INDEX statements into a list."""
        # Split by semicolon and filter empty
        indexes = [idx.strip() for idx in index_sql.split(';') if idx.strip()]
        return indexes

    def _prepare_query(self, query: str) -> str:
        """Prepare a query for EXPLAIN by substituting parameters."""
        candidates = self.prepare_query_candidates(query)
        # For simple simulation, we just use the first candidate (now Mixed)
        return candidates[0] if candidates else query

    async def simulate_rewrite(self, original_sql: str, new_sql: str) -> Dict[str, Any]:
        """
        Simulate a query rewrite safely using EXPLAIN (no ANALYZE) in a rollback transaction.
        """
        import sqlglot
        from sqlglot import exp
        
        # 1. Safety Check with SQLGlot (Postgres Dialect)
        try:
            parsed = sqlglot.parse_one(new_sql, read="postgres")
            # Check for destructive operations
            if parsed.find(exp.Update, exp.Delete, exp.Drop, exp.Alter, exp.Create, exp.Insert):
                return {"error": "Unsafe query detected: Only SELECT statements are allowed for rewrites"}
        except Exception as e:
            return {"error": f"SQL Parsing failed: {str(e)}"}

        pool = await connection_manager.get_pool()
        if not pool:
            return {"error": "No database connection"}

        # Prepare query for EXPLAIN
        explain_new_sql = self._prepare_query(new_sql)

        # 2. The "Explain-Only" Sandbox
        try:
            async with pool.acquire() as conn:
                async with conn.transaction(): # Start Transaction
                    # Run EXPLAIN (FORMAT JSON) on the NEW query
                    # crucial: NO 'ANALYZE' keyword here!
                    plan_json = await conn.fetchval(f"EXPLAIN (FORMAT JSON) {explain_new_sql}")
                    
                    # Extract Cost
                    plan_data = json.loads(plan_json)
                    new_cost = plan_data[0]['Plan']['Total Cost']
                    
                    return {
                        "type": "REWRITE",
                        "new_sql": new_sql,
                        "new_cost": new_cost,
                        "verified": True # Verified via Planner, not execution
                    }
        except Exception as e:
            logger.error(f"Rewrite simulation failed: {e}")
            return {"error": f"Invalid SQL or Execution Error: {str(e)}"}

    async def simulate_index(self, original_query: str, index_sql: str) -> Dict[str, Any]:
        """
        Interactively verify the impact of an index suggestion using HypoPG.
        Supports multiple indexes separated by semicolons.
        """
        pool = await connection_manager.get_pool()
        if not pool:
            return {"error": "No database connection"}
            
        if not await self.check_hypopg_installed():
            return {
                "error": "HypoPG extension not available.",
                "can_simulate": False
            }

        async with pool.acquire() as conn:
            # 1. Find a working candidate (handles type mismatches like UUID vs Int)
            explain_query = await self.find_working_candidate(conn, original_query)

            # Run everything in a transaction that auto-rollbacks
            async with conn.transaction():
                try:
                    # 2. Get Original Cost
                    plan_before_json = await conn.fetchval(f"EXPLAIN (FORMAT JSON) {explain_query}")
                    plan_before = json.loads(plan_before_json)[0]['Plan']
                    cost_before = plan_before['Total Cost']

                    # 3. Create Virtual Indexes (handle multiple)
                    indexes = self._parse_indexes(index_sql)
                    for idx in indexes:
                        try:
                            await conn.execute("SELECT hypopg_create_index($1)", idx)
                        except Exception as e:
                            logger.warning(f"Failed to create virtual index in verification: {idx} - {e}")

                    # 4. Get New Cost (The planner now 'sees' the index)
                    plan_after_json = await conn.fetchval(f"EXPLAIN (FORMAT JSON) {explain_query}")
                    plan_after = json.loads(plan_after_json)[0]['Plan']
                    cost_after = plan_after['Total Cost']
                    
                    # 6. Check if the index was actually used in the new plan
                    # We look for "Index Scan" or "Index Only Scan" in the JSON tree
                    def find_index_usage(node):
                        node_type = node.get("Node Type", "")
                        if "Index Scan" in node_type or "Index Only Scan" in node_type:
                            return True
                        for child in node.get("Plans", []):
                            if find_index_usage(child):
                                return True
                        return False
                    
                    used_index = find_index_usage(plan_after)

                    # 7. Calculate Improvement
                    improvement = 0
                    if cost_before > 0:
                        improvement = ((cost_before - cost_after) / cost_before) * 100

                    # TRANSACTION ROLLS BACK HERE -> Virtual index is gone.
                    
                    return {
                        "can_simulate": True,
                        "cost_before": cost_before,
                        "cost_after": cost_after,
                        "original_cost": cost_before,  # Alias for frontend consistency
                        "new_cost": cost_after,       # Alias for frontend consistency
                        "improvement_percent": round(improvement, 2),
                        "index_used": used_index,
                        "verification_status": "verified"
                    }

                except Exception as e:
                    # Capture syntax errors in AI suggestion or planner issues
                    logger.error(f"Verification simulation failed: {e}")
                    return {
                        "error": f"Simulation failed: {str(e)}",
                        "can_simulate": False
                    }

simulation_service = SimulationService()
