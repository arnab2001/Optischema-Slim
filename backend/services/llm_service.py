"""
LLM Service for OptiSchema Slim.
Handles interaction with LLM providers and prompt building.
"""

import logging
import json
import re
from typing import Dict, Any, Optional
import sqlglot
from sqlglot import exp
from config import settings
from llm.factory import LLMFactory

logger = logging.getLogger(__name__)

class LLMService:
    async def get_completion(self, prompt: str, json_mode: bool = True) -> Dict[str, Any]:
        """
        Generic completion method for any prompt.
        """
        provider = await LLMFactory.get_provider_async()
        
        # Log prompt
        try:
            with open("last_llm_prompt_generic.txt", "w") as f:
                f.write(prompt)
        except:
            pass
            
        result = await provider.analyze(prompt)
        
        if json_mode:
            return self._clean_llm_result(result)
            
        return result

    async def analyze_query(self, query: str, schema_context: str, plan_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a query using the configured LLM provider.
        Gets provider dynamically from database settings.
        """
        # Get provider from database settings (async)
        provider = await LLMFactory.get_provider_async()
        
        # Prune schema to only relevant tables
        pruned_schema = self._prune_schema(query, schema_context)
        
        # Select prompt strategy based on model name
        is_reasoning_model = "deepseek-r1" in provider.model_name.lower()
        
        if is_reasoning_model:
            logger.info(f"Using Reasoning Prompt for model: {provider.model_name}")
            prompt = self._build_reasoning_prompt(query, pruned_schema, plan_context)
        else:
            logger.info(f"Using Standard Prompt for model: {provider.model_name}")
            prompt = self._build_standard_prompt(query, pruned_schema, plan_context)
        
        # Log prompt to file for debugging
        try:
            with open("last_llm_prompt.txt", "w") as f:
                f.write(prompt)
        except Exception as e:
            logger.warning(f"Failed to log prompt: {e}")

        result = await provider.analyze(prompt)
        
        # Clean up common LLM hallucinations in JSON keys
        cleaned_result = self._clean_llm_result(result)
        
        # Add metadata for benchmarking/tuning (copy to avoid circular reference)
        cleaned_result["_benchmark_metadata"] = {
            "prompt": prompt,
            "raw_response": result.copy() if isinstance(result, dict) else result
        }
        
        return cleaned_result

    def _prune_schema(self, query: str, full_schema: str) -> str:
        """
        Extract table names from query and filter schema context.
        Handles both unqualified ('users') and schema-qualified ('public.users') names.
        """
        try:
            # Parse query to get table names (both qualified and unqualified)
            table_names = set()
            for table in sqlglot.parse_one(query).find_all(exp.Table):
                # Always add the bare table name for matching
                table_names.add(table.name.lower())
                # Also add schema-qualified name if present (e.g. "public.users")
                if table.db:
                    table_names.add(f"{table.db.lower()}.{table.name.lower()}")

            if not table_names:
                return full_schema

            # Scan full_schema for blocks containing table names
            # Schema format is typically: "Table: public.table_name\n..."
            relevant_lines = []
            lines = full_schema.split('\n')
            current_table_block = []
            block_is_relevant = False

            for line in lines:
                if line.strip().lower().startswith("table:"):
                    # Flush previous block
                    if current_table_block and block_is_relevant:
                        relevant_lines.extend(current_table_block)
                        relevant_lines.append("")  # Spacer

                    # Start new block
                    current_table_block = [line]
                    # Extract table name from line like "Table: public.demo_logs"
                    line_lower = line.lower()
                    # Match against both bare name and qualified name
                    block_is_relevant = any(t in line_lower for t in table_names)
                else:
                    current_table_block.append(line)

            # Flush last block
            if current_table_block and block_is_relevant:
                relevant_lines.extend(current_table_block)

            if not relevant_lines:
                # Fallback if parsing failed or format didn't match
                return full_schema

            return "\n".join(relevant_lines)

        except Exception as e:
            logger.warning(f"Schema pruning failed: {e}")
            return full_schema

    @staticmethod
    def _extract_json_block(text: str) -> Optional[str]:
        """
        Extract the first balanced JSON object from a ```json code fence.
        Uses brace counting instead of regex to handle nested objects correctly.
        """
        marker = text.find('```json')
        if marker == -1:
            return None
        # Find the opening brace after the marker
        start = text.find('{', marker)
        if start == -1:
            return None
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if escape:
                escape = False
                continue
            if ch == '\\' and in_string:
                escape = True
                continue
            if ch == '"' and not escape:
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        return None

    def _clean_llm_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean up common LLM hallucinations in JSON keys.
        Handles Markdown blocks and DeepSeek <think> tags.
        """
        if not isinstance(result, dict):
            return result

        # If "reasoning" contains a ```json block, extract it using balanced braces
        if "reasoning" in result and isinstance(result["reasoning"], str):
            json_str = self._extract_json_block(result["reasoning"])
            if json_str:
                try:
                    inner_json = json.loads(json_str)
                    result.update(inner_json)
                except (json.JSONDecodeError, ValueError):
                    pass

        # Validate SQL keys — only check known SQL-related key names
        # to avoid false positives from reasoning text like "Create a backup..."
        sql_fallbacks = ["sql_query", "suggested_sql", "fix", "index_sql", "rewrite_sql", "code"]

        if "sql" not in result:
            for fallback in sql_fallbacks:
                if fallback in result and isinstance(result[fallback], str) and result[fallback].strip():
                    result["sql"] = result[fallback]
                    break
        
        # Smarter category inference: If the model says ADVISORY but provides a CREATE INDEX, it's an INDEX.
        if "sql" in result and isinstance(result["sql"], str):
            sql_upper = result["sql"].strip().upper()
            if "CREATE INDEX" in sql_upper or "CREATE UNIQUE INDEX" in sql_upper:
                result["category"] = "INDEX"
            elif sql_upper.startswith("SELECT") or sql_upper.startswith("WITH"):
                # If it's a SELECT but categorized as ADVISORY, it's likely a REWRITE
                if result.get("category") == "ADVISORY":
                     result["category"] = "REWRITE"

        # Ensure category is present and uppercase
        if "category" in result:
            result["category"] = str(result["category"]).upper()
            if result["category"] not in ["INDEX", "REWRITE", "ADVISORY"]:
                result["category"] = "ADVISORY"
        else:
            result["category"] = "ADVISORY"

        # Ensure reasoning is present
        if "reasoning" not in result:
            # Check for error first
            if "error" in result:
                result["reasoning"] = f"LLM Error: {result['error']}"
                if "raw_response" in result:
                     result["reasoning"] += f" (Raw: {str(result['raw_response'])[:100]}...)"
            else:
                # Check fallbacks for reasoning
                reasoning_fallbacks = ["explanation", "thought", "analysis", "comment"]
                for fallback in reasoning_fallbacks:
                    if fallback in result:
                        result["reasoning"] = result[fallback]
                        break
                
                # Default if still missing
                if "reasoning" not in result:
                    debug_info = f"Keys: {list(result.keys())}"
                    if "raw_response" in result:
                        debug_info += f", Raw: {str(result['raw_response'])[:200]}"
                    else:
                        debug_info += f", Dump: {str(result)[:200]}"
                    result["reasoning"] = f"No explanation provided by the AI model. ({debug_info})"

        return result

    def _extract_plan_bottlenecks(self, plan: Dict[str, Any]) -> str:
        """
        Extract key bottleneck nodes from an execution plan instead of dumping the full JSON.
        This reduces token usage and focuses the LLM on what matters.
        """
        lines = []
        total_cost = plan.get('Total Cost', 0)
        lines.append(f"Total Cost: {total_cost}")

        def walk(node, depth=0):
            node_type = node.get('Node Type', '')
            relation = node.get('Relation Name', '')
            idx_name = node.get('Index Name', '')
            cost = node.get('Total Cost', 0)
            rows = node.get('Plan Rows', 0)
            filt = node.get('Filter', '')
            join_cond = node.get('Hash Cond', '') or node.get('Merge Cond', '') or node.get('Join Filter', '')
            sort_key = node.get('Sort Key', [])

            indent = "  " * depth
            parts = [f"{indent}{node_type}"]
            if relation:
                parts.append(f"on {relation}")
            if idx_name:
                parts.append(f"using {idx_name}")
            parts.append(f"(cost={cost}, rows={rows})")
            if filt:
                parts.append(f"filter: {filt}")
            if join_cond:
                parts.append(f"cond: {join_cond}")
            if sort_key:
                parts.append(f"sort: {', '.join(str(k) for k in sort_key)}")
            lines.append(" ".join(parts))

            for child in node.get('Plans', []):
                walk(child, depth + 1)

        walk(plan)
        return "\n".join(lines)

    def _build_standard_prompt(self, query: str, schema_info: str, plan: Dict[str, Any]) -> str:
        """
        Standard Prompt (Path A) for Qwen, Llama, SQLCoder.
        Forces CoT inside JSON.
        """
        plan_summary = self._extract_plan_bottlenecks(plan)

        return f"""
ROLE: PostgreSQL Performance Architect.

=== GOAL ===
Optimize the provided query based on the Schema and Plan.
Focus on safety and high-impact changes only.

=== POLICY (RULES OF ENGAGEMENT) ===
1. JOIN KEY PRIORITY: If a JOIN results in a Sequential Scan on a table with more than 100 rows, you MUST suggest an index on the join columns (Foreign Keys). Do not be vague. Provide the exact `CREATE INDEX CONCURRENTLY` SQL to avoid locking the table during creation.
2. MULTI-INDEX SUPPORT: If multiple indexes are needed to optimize the query (e.g., across multiple tables), provide ALL of them in the "sql" field, separated by semicolons. Always use `CREATE INDEX CONCURRENTLY` to prevent table locks in production.
3. NO INDEX SPAM: If the query scans >20% of the table (e.g. Group By on the whole table), B-Tree indexes rarely help. Also avoid suggesting indexes on low-cardinality columns (few distinct values). Prefer "ADVISORY".
4. NO DUPLICATE INDEXES: Check the "Existing Indexes" section. Do NOT suggest an index that already exists or is a subset of an existing index.
5. UNKNOWN PARAMS: The query uses parameters ($1, $2). Use these in your index logic if appropriate.
6. VALIDITY: Only use columns listed in the schema. Do not hallucinate columns.
7. ACTIONS: If you suggest a fix, set category to "INDEX" or "REWRITE". Use "ADVISORY" only as a last resort.

=== CONTEXT ===
TARGET QUERY: {query}

=== DATABASE SCHEMA & STATISTICS ===
(Columns annotated with [PK], [FK -> ref], cardinality. Indexes show scan count and definition.)
{schema_info}

=== EXECUTION PLAN ===
{plan_summary}

INSTRUCTIONS:
1. Identify the primary bottleneck (Sequential Scan on a large table in a Join, or expensive Sort).
2. Check existing indexes — do NOT suggest indexes that already cover the bottleneck columns.
3. Provide the EXACT SQL to fix it. If multiple indexes are needed, provide them all. Always use CREATE INDEX CONCURRENTLY.
4. You must output a valid JSON object.

JSON FORMAT:
{{
  "reasoning": "Explain exactly which join/table is causing the seq scan, what existing indexes cover, and why a new index helps.",
  "category": "INDEX" | "REWRITE" | "ADVISORY",
  "sql": "CREATE INDEX CONCURRENTLY..." or null
}}
"""

    def _build_reasoning_prompt(self, query: str, schema_info: str, plan: Dict[str, Any]) -> str:
        """
        Reasoning Prompt (Path B) for DeepSeek R1.
        Encourages unconstrained thinking before JSON.
        """
        plan_summary = self._extract_plan_bottlenecks(plan)

        return f"""
ROLE: PostgreSQL Performance Architect.

=== GOAL ===
Optimize the provided query based on the Schema and Plan.
Focus on safety and high-impact changes only.

=== POLICY (RULES OF ENGAGEMENT) ===
1. JOIN KEY PRIORITY: If a JOIN results in a Sequential Scan on a table with more than 100 rows, you MUST suggest an index on the join columns (Foreign Keys). Do not be vague. Provide the exact `CREATE INDEX CONCURRENTLY` SQL to avoid locking the table during creation.
2. MULTI-INDEX SUPPORT: If multiple indexes are needed to optimize the query (e.g., across multiple tables), provide ALL of them in the "sql" field, separated by semicolons. Always use `CREATE INDEX CONCURRENTLY` to prevent table locks in production.
3. NO INDEX SPAM: If the query scans >20% of the table (e.g. Group By on the whole table), B-Tree indexes rarely help. Also avoid suggesting indexes on low-cardinality columns (few distinct values). Prefer "ADVISORY".
4. NO DUPLICATE INDEXES: Check the "Existing Indexes" section. Do NOT suggest an index that already exists or is a subset of an existing index.
5. UNKNOWN PARAMS: The query uses parameters ($1, $2). Use these in your index logic if appropriate.
6. VALIDITY: Only use columns listed in the schema. Do not hallucinate columns.
7. ACTIONS: If you suggest a fix, set category to "INDEX" or "REWRITE". Use "ADVISORY" only as a last resort.

=== CONTEXT ===
TARGET QUERY: {query}

=== DATABASE SCHEMA & STATISTICS ===
(Columns annotated with [PK], [FK -> ref], cardinality. Indexes show scan count and definition.)
{schema_info}

=== EXECUTION PLAN ===
{plan_summary}

INSTRUCTIONS:
1. Analyze the query execution plan deeply.
2. Check existing indexes — do NOT suggest indexes that already cover the bottleneck columns.
3. Verify if the suggested index(es) cover the specific filters and sort keys.
4. Suggest the optimal fix(es). If multiple indexes are needed, provide them all.

OUTPUT FORMAT:
First, output your reasoning process enclosed in <think> tags.
Then, output the final result in a strictly formatted JSON block wrapped in ```json code fence.

Example JSON output:
```json
{{
  "category": "INDEX",
  "reasoning": "Join on table X is slow because of Seq Scan. Existing index idx_x_a covers column a but not the join column y. Suggested index for FK column Y.",
  "sql": "CREATE INDEX CONCURRENTLY idx_x_y ON x(y); CREATE INDEX CONCURRENTLY idx_a_b ON a(b);"
}}
```
"""

    def _build_analysis_prompt(self, query: str, schema_info: str, plan: Dict[str, Any]) -> str:
        """
        Legacy method kept for compatibility, now delegates to standard prompt.
        """
        return self._build_standard_prompt(query, schema_info, plan)

llm_service = LLMService()
