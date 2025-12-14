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

    def _prepare_query_candidates(self, query: str) -> list:
        """Generate candidate queries with smart parameter substitutions."""
        import re
        
        def smart_replace(q: str, value_for_where: str) -> str:
            """Replace LIMIT/OFFSET params with integers, other params with given value."""
            result = re.sub(r'(LIMIT\s+)\$\d+', r'\g<1>10', q, flags=re.IGNORECASE)
            result = re.sub(r'(OFFSET\s+)\$\d+', r'\g<1>0', result, flags=re.IGNORECASE)
            result = re.sub(r'\$\d+', value_for_where, result)
            return result
        
        candidates = []
        # UUID candidate (for UUID columns)
        candidates.append(smart_replace(query, "'00000000-0000-0000-0000-000000000000'::uuid"))
        # Integer candidate (for INT columns)
        candidates.append(smart_replace(query, "1"))
        # String candidate (for TEXT columns)
        candidates.append(smart_replace(query, "'dummy'"))
        # NULL fallback
        candidates.append(smart_replace(query, "NULL"))
        return candidates

    def _parse_indexes(self, index_sql: str) -> list:
        """Parse multiple CREATE INDEX statements into a list."""
        # Split by semicolon and filter empty
        indexes = [idx.strip() for idx in index_sql.split(';') if idx.strip()]
        return indexes

    async def simulate_index(self, query: str, index_sql: str) -> Dict[str, Any]:
        """
        Simulate an index and return the cost reduction.
        If HypoPG is missing, return a special status to downgrade to Advisory.
        """
        pool = await connection_manager.get_pool()
        if not pool:
            return {"error": "No database connection"}
            
        if not await self.check_hypopg_installed():
            # Fallback for missing HypoPG
            return {
                "verification_status": "advisory",
                "message": "HypoPG extension not available. Suggestion cannot be verified but may still be valid.",
                "index_sql": index_sql
            }

        # Try parameter substitutions to get a valid plan
        candidates = self._prepare_query_candidates(query)
        original_cost = 0.0
        new_cost = 0.0

        async with pool.acquire() as conn:
            # Find a candidate that works
            explain_query = None
            for candidate in candidates:
                try:
                    test_result = await conn.fetchval(f"EXPLAIN (FORMAT JSON) {candidate}")
                    test_plan = json.loads(test_result)[0]['Plan']
                    if test_plan['Total Cost'] > 0:
                        explain_query = candidate
                        break
                except Exception:
                    continue
            
            if not explain_query:
                explain_query = candidates[-1]  # Use NULL fallback

            try:
                # 1. Get original plan cost
                original_explain = await conn.fetchval(f"EXPLAIN (FORMAT JSON) {explain_query}")
                original_plan = json.loads(original_explain)[0]['Plan']
                original_cost = original_plan['Total Cost']
                
                # 2. Create hypothetical indexes (handle multiple)
                indexes = self._parse_indexes(index_sql)
                for idx in indexes:
                    try:
                        await conn.execute(f"SELECT hypopg_create_index($1)", idx)
                    except Exception as e:
                        logger.warning(f"Failed to create hypothetical index: {idx} - {e}")
                
                # 3. Get new plan cost
                new_explain = await conn.fetchval(f"EXPLAIN (FORMAT JSON) {explain_query}")
                new_plan = json.loads(new_explain)[0]['Plan']
                new_cost = new_plan['Total Cost']
                
                # 4. Clean up hypothetical indexes
                await conn.execute("SELECT hypopg_reset()")
                
            except Exception as e:
                logger.error(f"Simulation failed: {e}")
                return {"error": str(e)}

        # Calculate improvement
        improvement = 0.0
        if original_cost > 0:
            improvement = ((original_cost - new_cost) / original_cost) * 100

        return {
            "original_cost": original_cost,
            "new_cost": new_cost,
            "improvement_percent": round(improvement, 2),
            "index_sql": index_sql,
            "verification_status": "verified"
        }

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

simulation_service = SimulationService()
