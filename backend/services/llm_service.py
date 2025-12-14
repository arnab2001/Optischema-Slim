"""
LLM Service for OptiSchema Slim.
Handles interaction with LLM providers and prompt building.
"""

import logging
import json
from typing import Dict, Any, Optional
from config import settings
from llm.factory import LLMFactory

logger = logging.getLogger(__name__)

class LLMService:
    async def analyze_query(self, query: str, schema_context: str, plan_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a query using the configured LLM provider.
        Gets provider dynamically from database settings.
        """
        # Get provider from database settings (async)
        provider = await LLMFactory.get_provider_async()
        prompt = self._build_analysis_prompt(query, schema_context, plan_context)
        return await provider.analyze(prompt)

    def _build_analysis_prompt(self, query: str, schema_info: str, plan: Dict[str, Any]) -> str:
        """
        Build the analysis prompt with rich context.
        """
        # Extract cost and basic plan info
        total_cost = plan.get('Total Cost', 'Unknown')
        
        return f"""
You are a PostgreSQL Expert. Optimize this query.

=== CONTEXT ===
TARGET QUERY: {query}

=== DATABASE STATS ===
{schema_info}

=== EXECUTION PLAN (Current) ===
Total Cost: {total_cost}
Plan Details: {json.dumps(plan, indent=2)}

=== INSTRUCTIONS ===
1. If an index is missing, return category="INDEX" and the CREATE INDEX SQL.
2. If the query is written poorly, return category="REWRITE" and the optimized SQL.
3. If it's a config issue, return category="ADVISORY".

Respond in JSON format with the following structure:
{{
  "category": "INDEX" | "REWRITE" | "ADVISORY",
  "reasoning": "Explanation of why...",
  "sql": "CREATE INDEX ... OR SELECT ...",
  "confidence": 0.9
}}
"""

llm_service = LLMService()

