"""
Multi-model LLM integration for OptiSchema backend.
Supports Gemini (Google) and DeepSeek for query analysis and recommendations.
"""

import os
import logging
import json
import aiohttp
from typing import Dict, Any, Optional
from config import settings
from analysis.core import fingerprint_query
from cache import make_cache_key, get_cache, set_cache

logger = logging.getLogger(__name__)

# Model configuration
GEMINI_API_KEY = settings.gemini_api_key
DEEPSEEK_API_KEY = settings.deepseek_api_key
ACTIVE_MODEL = settings.llm_provider

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
You are a PostgreSQL tuning assistant. Given the following query metrics and analysis, generate a specific, actionable recommendation to improve performance.

**Critical Requirements:**
1. For HIGH-IMPACT, LOW-RISK optimizations (missing indexes, redundant queries), provide executable SQL
2. Only suggest CREATE INDEX CONCURRENTLY, ALTER SYSTEM, or SET commands for safety
3. Always include rollback_sql for any sql_fix provided
4. Be transparent about data source and impact assessment

**Response Format (JSON):**
```json
{{
  "title": "Short, descriptive title (no markdown formatting)",
  "description": "Detailed explanation with problem identification, root cause analysis, specific steps, and expected benefits",
  "sql_fix": "CREATE INDEX CONCURRENTLY idx_table_column ON table(column); -- Only if HIGH-impact, LOW-risk",
  "rollback_sql": "DROP INDEX CONCURRENTLY idx_table_column; -- Required if sql_fix provided",
  "confidence": 85,
  "estimated_improvement": "15%",
  "risk_level": "Low"
}}
```

**SQL Fix Guidelines:**
- Only for clear, high-impact optimizations (missing indexes on WHERE/JOIN columns)
- Use CREATE INDEX CONCURRENTLY for safety (non-blocking)
- Include proper index naming: idx_tablename_columnname
- Provide accurate rollback_sql
- Skip sql_fix for advisory-only recommendations

**Data Analysis Guidelines:**
1. If actual_metrics available: Use precise values (execution time, calls, cache hits)
2. If no actual_metrics: State "Based on query pattern analysis"
3. Always mention data source used for analysis
4. For execution plans: Focus on sequential scans, missing indexes, large sorts

Query Data:
{query_data}

**Examples of HIGH-impact, LOW-risk fixes:**
- Sequential scans with WHERE clauses → CREATE INDEX CONCURRENTLY
- Missing indexes on JOIN columns → CREATE INDEX CONCURRENTLY
- Unindexed ORDER BY columns → CREATE INDEX CONCURRENTLY

**Examples requiring advisory-only (no sql_fix):**
- Complex query rewrites
- Schema changes
- Application-level optimizations
- Multi-table restructuring
"""

async def call_gemini_api(prompt: str, max_tokens: int = 512) -> str:
    """Call Gemini API."""
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": GEMINI_API_KEY
    }
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.2
        }
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                return result["candidates"][0]["content"]["parts"][0]["text"].strip()
            else:
                error_text = await response.text()
                raise Exception(f"Gemini API error: {response.status} - {error_text}")

async def call_deepseek_api(prompt: str, max_tokens: int = 512) -> str:
    """Call DeepSeek API."""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.2
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                return result["choices"][0]["message"]["content"].strip()
            else:
                error_text = await response.text()
                raise Exception(f"DeepSeek API error: {response.status} - {error_text}")

async def call_llm_api(prompt: str, max_tokens: int = 512) -> str:
    """Call the active LLM API."""
    if ACTIVE_MODEL == "gemini":
        return await call_gemini_api(prompt, max_tokens)
    elif ACTIVE_MODEL == "deepseek":
        return await call_deepseek_api(prompt, max_tokens)
    else:
        raise ValueError(f"Unknown model: {ACTIVE_MODEL}")

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
        logger.info(f"{ACTIVE_MODEL.title()} plan explanation generated.")
        return explanation
    except Exception as e:
        logger.error(f"{ACTIVE_MODEL.title()} plan explanation failed: {e}")
        return f"[{ACTIVE_MODEL.title()} explanation unavailable]"

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
        logger.info(f"{ACTIVE_MODEL.title()} query rewrite generated.")
        return optimized_sql
    except Exception as e:
        logger.error(f"{ACTIVE_MODEL.title()} query rewrite failed: {e}")
        return sql

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
        logger.info(f"{ACTIVE_MODEL.title()} recommendation generated with executable SQL: {bool(result.get('sql_fix'))}")
        return result
    except Exception as e:
        logger.error(f"{ACTIVE_MODEL.title()} recommendation failed: {e}")
        return {
            "title": f"[{ACTIVE_MODEL.title()} recommendation unavailable]",
            "description": str(e),
            "sql_fix": None,
            "rollback_sql": None,
            "confidence": 0,
            "estimated_improvement": "Unknown",
            "risk_level": "Unknown"
        } 