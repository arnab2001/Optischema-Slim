"""
Benchmark Service for OptiSchema Slim.
Handles saving benchmark results to the target PostgreSQL database.
"""

import logging
from typing import Dict, Any
from connection_manager import connection_manager

logger = logging.getLogger(__name__)

class BenchmarkService:
    async def save_benchmark_result(self, scenario_id: str, query: str, result: Dict[str, Any]) -> bool:
        """
        Save benchmark results (including prompt and raw response) to the golden.benchmark_results table.
        """
        pool = await connection_manager.get_pool()
        if not pool:
            logger.warning("No active database connection to save benchmark results")
            return False

        try:
            metadata = result.get("_benchmark_metadata", {})
            prompt = metadata.get("prompt", "")
            
            raw_response_data = metadata.get("raw_response", {})
            if isinstance(raw_response_data, dict):
                import json
                raw_response = json.dumps(raw_response_data)
            else:
                raw_response = str(raw_response_data)
            
            logger.info(f"Saving benchmark result for {scenario_id} to Postgres (Prompt len: {len(prompt)})")
            
            suggestion = result.get("suggestion", {})
            actual_category = suggestion.get("category", "UNKNOWN")
            actual_sql = suggestion.get("sql", "")
            
            # Note: alignment_score calculation is usually done by the runner,
            # but we'll store a default or provided score.
            alignment_score = result.get("_benchmark_score", 0.0)

            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO golden.benchmark_results 
                    (scenario_id, query_text, prompt, raw_response, actual_category, actual_sql, alignment_score)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, scenario_id, query, prompt, raw_response, actual_category, actual_sql, alignment_score)
                
            return True
        except Exception as e:
            logger.error(f"Failed to save benchmark result to PostgreSQL: {e}")
            return False

benchmark_service = BenchmarkService()
