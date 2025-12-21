"""
Multi-model LLM integration for OptiSchema backend.
Supports Gemini, DeepSeek, and Ollama (Local) via provider pattern.
"""

import logging
import json
from typing import Dict, Any, Optional
from config import settings
from analysis.core import fingerprint_query
from tenant_cache import make_cache_key, get_cache, set_cache
from llm.factory import LLMFactory
from llm.base import LLMProvider

logger = logging.getLogger(__name__)

# Prompt templates
EXPLAIN_PLAN_PROMPT = """
You are a PostgreSQL performance expert. Given the following execution plan (in JSON), explain the main performance bottlenecks and suggest optimizations in clear, actionable language for a database engineer.

**Format your response in Markdown:**

- **Key Issues**: List the main performance problems
- **Root Causes**: Explain why these issues occur
- **Optimizations**: Provide specific, actionable recommendations
- **Expected Impact**: What improvements to expect

Execution Plan JSON:
{plan_json}
"""

REWRITE_QUERY_PROMPT = """
You are an expert SQL query optimizer. Given the following SQL query, rewrite it for better performance on PostgreSQL.

**Requirements:**
- Only output the optimized SQL query
- No explanations or markdown formatting
- Ensure the query is syntactically correct
- Preserve the original query's functionality

Original Query:
{sql}
"""

RECOMMENDATION_PROMPT = """
You are a PostgreSQL performance expert. Given the following query metrics and analysis, generate a specific, actionable recommendation to improve performance.

**Goal:** Identify the most effective optimization, whether it's an index, query rewrite, schema change, or configuration tuning.

**Optimization Categories:**
1. **Index Optimization**: Creating/dropping indexes (High Impact, Low Risk)
2. **Query Rewrite**: Modifying SQL structure (High Impact, Medium Risk)
3. **Schema Design**: Partitioning, normalization, data types (High Impact, High Risk)
4. **Configuration**: Tuning PostgreSQL parameters (Medium Impact, Low Risk)
5. **Maintenance**: VACUUM, ANALYZE, reindexing (Medium Impact, Low Risk)

**Response Format (JSON):**
```json
{{
  "title": "Short, descriptive title (no markdown)",
  "description": "Detailed explanation: problem identification, root cause, specific steps, and expected benefits.",
  "recommendation_type": "index|rewrite|schema|config|maintenance",
  "sql_fix": "Executable SQL for the fix (if applicable and safe)",
  "rollback_sql": "SQL to revert the fix (required if sql_fix provided)",
  "confidence": 85,
  "estimated_improvement": "15%",
  "risk_level": "Low|Medium|High"
}}
```

**Guidelines for sql_fix:**
- **Indexes**: ALWAYS provide `CREATE INDEX CONCURRENTLY` (safe).
- **Configuration**: Provide `ALTER SYSTEM SET` or `SET` commands.
- **Query Rewrites**: Provide the *rewritten SELECT query* as the `sql_fix` (if it can be run as a test).
- **Schema/Maintenance**: Provide SQL if safe, otherwise leave null (advisory only).

**Safety Rules:**
- Use `CONCURRENTLY` for index operations.
- Do NOT suggest `DROP TABLE` or destructive data operations.

**Data Analysis:**
- Focus on sequential scans, high CPU/IO, missing indexes, and complex joins.
- If `actual_metrics` exist, use them to justify the impact.

Query Data:
{query_data}
"""

async def call_llm_api(prompt: str, max_tokens: int = 512) -> str:
    """Call the active LLM provider."""
    try:
        provider = await LLMFactory.get_provider_async()
        return await provider.generate(prompt, max_tokens)
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        raise

# Core AI functions
async def explain_plan(plan_json: Dict[str, Any], query_text: Optional[str] = None) -> str:
    """
    Use LLM to explain a PostgreSQL execution plan.
    Returns a human-readable explanation and suggestions.
    Caches by query fingerprint + 'explain_plan'.
    """
    fingerprint = fingerprint_query(query_text) if query_text else None
    cache_key = make_cache_key(fingerprint, 'explain_plan') if fingerprint else None
    if cache_key:
        cached = get_cache(cache_key)
        if cached:
            logger.info("Cache hit for plan explanation.")
            return cached
    prompt = EXPLAIN_PLAN_PROMPT.format(plan_json=plan_json)
    try:
        explanation = await call_llm_api(prompt, max_tokens=512)
        if cache_key:
            set_cache(cache_key, explanation)
        
        # Get provider name for logging
        provider = await LLMFactory.get_provider_async()
        logger.info(f"Plan explanation generated using {provider.name}.")
        return explanation
    except Exception as e:
        logger.error(f"Plan explanation failed: {e}")
        return f"[Explanation unavailable: {str(e)}]"

async def rewrite_query(sql: str) -> str:
    """
    Use LLM to rewrite a SQL query for better performance.
    Returns the optimized SQL. Caches by query fingerprint + 'rewrite_query'.
    """
    fingerprint = fingerprint_query(sql)
    cache_key = make_cache_key(fingerprint, 'rewrite_query')
    cached = get_cache(cache_key)
    if cached:
        logger.info("Cache hit for query rewrite.")
        return cached
    prompt = REWRITE_QUERY_PROMPT.format(sql=sql)
    try:
        optimized_sql = await call_llm_api(prompt, max_tokens=256)
        set_cache(cache_key, optimized_sql)
        provider = await LLMFactory.get_provider_async()
        logger.info(f"Query rewrite generated using {provider.name}.")
        return optimized_sql
    except Exception as e:
        logger.error(f"Query rewrite failed: {e}")
        return sql

from database_context_service import DatabaseContextService
from connection_manager import connection_manager

async def generate_recommendation(query_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Use LLM to generate a recommendation for a query.
    Returns a dict with title, description, sql_fix, rollback_sql, and metadata.
    Caches by query fingerprint + 'recommendation'.
    """
    # Use query_text if present for fingerprinting
    query_text = query_data.get('query_text') or json.dumps(query_data)
    fingerprint = fingerprint_query(query_text)
    cache_key = make_cache_key(fingerprint, 'recommendation')
    cached = get_cache(cache_key)
    if cached:
        logger.info("Cache hit for recommendation.")
        try:
            return json.loads(cached)
        except Exception:
            pass
            
    # 🧠 ENHANCEMENT: Gather Rich Database Context
    try:
        pool = await connection_manager.get_pool()
        if pool:
            # Extract SQL from query_data
            sql = query_data.get('query_text', '')
            if sql:
                logger.info("Gathering database context for AI...")
                context = await DatabaseContextService.get_query_context(pool, sql)
                formatted_context = DatabaseContextService.format_context_for_prompt(context)
                
                # Add context to query_data for the prompt
                query_data['schema_context'] = formatted_context['schema_context']
                query_data['index_context'] = formatted_context['existing_indexes']
                query_data['statistics_context'] = formatted_context['table_statistics']
    except Exception as e:
        logger.warning(f"Failed to gather database context: {e}")

    prompt = RECOMMENDATION_PROMPT.format(query_data=query_data)
    try:
        content = await call_llm_api(prompt, max_tokens=1024)
        
        # Try to parse as JSON first (new format)
        try:
            # Extract JSON from content if it's wrapped in markdown code blocks
            if '```json' in content:
                json_start = content.find('```json') + 7
                json_end = content.find('```', json_start)
                if json_end != -1:
                    content = content[json_start:json_end].strip()
            elif '```' in content:
                # Handle cases where it's just wrapped in ```
                lines = content.split('\n')
                in_code_block = False
                json_lines = []
                for line in lines:
                    if line.strip() == '```':
                        in_code_block = not in_code_block
                        continue
                    if in_code_block:
                        json_lines.append(line)
                content = '\n'.join(json_lines)
            
            # Parse the JSON
            result = json.loads(content)
            
            # Validate required fields and set defaults
            result = {
                "title": result.get("title", "Optimization Recommendation"),
                "description": result.get("description", "No description provided"),
                "recommendation_type": result.get("recommendation_type", "optimization"),
                "sql_fix": result.get("sql_fix"),
                "rollback_sql": result.get("rollback_sql"),
                "confidence": result.get("confidence", 75),
                "estimated_improvement": result.get("estimated_improvement", "Unknown"),
                "risk_level": result.get("risk_level", "Medium")
            }
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse JSON response, falling back to text parsing: {e}")
            # Fallback to old text parsing method
            lines = content.split('\n')
            title = lines[0].strip() if lines else "Recommendation"
            description = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
            
            # Look for SQL fix in content
            sql_fix = None
            rollback_sql = None
            for line in lines:
                if line.strip().upper().startswith("SQL:") or "CREATE INDEX" in line.upper():
                    sql_fix = line.split(":", 1)[-1].strip() if ":" in line else line.strip()
                    break
            
            # Clean up title - remove any markdown formatting
            if title.startswith('#') or title.startswith('##'):
                title = title.lstrip('#').strip()
            
            result = {
                "title": title,
                "description": description,
                "sql_fix": sql_fix,
                "rollback_sql": rollback_sql,
                "confidence": 75,
                "estimated_improvement": "Unknown", 
                "risk_level": "Medium"
            }
        
        set_cache(cache_key, json.dumps(result))
        provider = await LLMFactory.get_provider_async()
        logger.info(f"Recommendation generated using {provider.name}.")
        return result
    except Exception as e:
        logger.error(f"Recommendation generation failed: {e}")
        return {
            "title": f"[Recommendation unavailable]",
            "description": f"Error generating recommendation: {str(e)}",
            "sql_fix": None,
            "rollback_sql": None,
            "confidence": 0,
            "estimated_improvement": "Unknown",
            "risk_level": "Unknown"
        }