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
        """
        try:
            # Parse query to get table names
            table_names = set()
            for table in sqlglot.parse_one(query).find_all(exp.Table):
                table_names.add(table.name.lower())
                
            if not table_names:
                 return full_schema
            
            # Simple heuristic: scan full_schema for blocks containing table names
            # Schema format is typically: "Table: name\n..."
            relevant_lines = []
            capturing = False
            
            # If schema is just one big block, return it. If it's sectioned, try to filter.
            # Assuming schema_context is line-oriented.
            lines = full_schema.split('\n')
            current_table_block = []
            block_is_relevant = False
            
            for line in lines:
                if line.strip().lower().startswith("table:"):
                    # Flush previous block
                    if current_table_block and block_is_relevant:
                        relevant_lines.extend(current_table_block)
                        relevant_lines.append("") # Spacer
                    
                    # Start new block
                    current_table_block = [line]
                    # Check if this table is relevant
                    # Line format eg: "Table: public.demo_logs"
                    block_is_relevant = any(t in line.lower() for t in table_names)
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

    def _clean_llm_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean up common LLM hallucinations in JSON keys.
        Handles Markdown blocks and DeepSeek <think> tags.
        """
        # If result is already a dict, we might still need to fix keys
        # If result came from a provider that returns raw text (caught in exception), it might be handled there.
        # But if the provider successfully returned a dict but it's weird, we clean it here.
        
        if not isinstance(result, dict):
            return result

        # DeepSeek R1 might interpret "json output" as "raw json string inside a key"
        # Or provider might have returned an advisory dict because parsing failed.
        # If "reasoning" contains raw JSON (extraction fallback), we might want to re-parse.
        
        # But crucially, if the provider's `analyze` method failed to parse JSON, it returns an error dict.
        # We need to handle that.
        
        # If "reasoning" looks like it has a ```json block in it, extract it.
        # (This handles the case where the provider just dumped the whole text into reasoning)
        if "reasoning" in result and isinstance(result["reasoning"], str):
            text = result["reasoning"]
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
            if json_match:
                try:
                    inner_json = json.loads(json_match.group(1))
                    # Update result with inner json values
                    result.update(inner_json)
                    # Keep the original reasoning text as "raw_reasoning" maybe?
                    # Or just prefer the inner json's reasoning if present
                except:
                    pass

        # Validate SQL keys
        sql_fallbacks = ["sql_query", "query", "fix", "suggested_sql", "code", ",  ", " , "]
        
        if "sql" not in result:
            for fallback in sql_fallbacks:
                if fallback in result:
                    result["sql"] = result[fallback]
                    break
            
            # If still not found, look for any key whose value looks like SQL
            if "sql" not in result:
                for k, v in result.items():
                    if isinstance(v, str) and (v.strip().upper().startswith("CREATE") or v.strip().upper().startswith("SELECT")):
                        result["sql"] = v
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

    def _build_standard_prompt(self, query: str, schema_info: str, plan: Dict[str, Any]) -> str:
        """
        Standard Prompt (Path A) for Qwen, Llama, SQLCoder.
        Forces CoT inside JSON.
        """
        total_cost = plan.get('Total Cost', 'Unknown')
        
        return f"""
ROLE: PostgreSQL Performance Architect.

=== GOAL ===
Optimize the provided query based on the Schema and Plan.
Focus on safety and high-impact changes only.

=== POLICY (RULES OF ENGAGEMENT) ===
1. JOIN KEY PRIORITY: If a JOIN results in a Sequential Scan on a table with more than 100 rows, you MUST suggest an index on the join columns (Foreign Keys). Do not be vague. Provide the exact `CREATE INDEX` SQL.
2. MULTI-INDEX SUPPORT: If multiple indexes are needed to optimize the query (e.g., across multiple tables), provide ALL of them in the "sql" field, separated by semicolons.
3. NO INDEX SPAM: If the query scans >20% of the table (e.g. Group By on the whole table), B-Tree indexes rarely help. Prefer "ADVISORY".
4. UNKNOWN PARAMS: The query uses parameters ($1, $2). Use these in your index logic if appropriate.
5. VALIDITY: Only use columns listed in the schema. Do not hallucinate columns.
6. ACTIONS: If you suggest a fix, set category to "INDEX" or "REWRITE". Use "ADVISORY" only as a last resort.

=== CONTEXT ===
TARGET QUERY: {query}

=== DATABASE STATS ===
{schema_info}

=== EXECUTION PLAN ===
Total Cost: {total_cost}
Plan Details: {json.dumps(plan, indent=2)}

INSTRUCTIONS:
1. Identify the primary bottleneck (Sequential Scan on a large table in a Join, or expensive Sort).
2. Provide the EXACT SQL to fix it. If multiple indexes are needed, provide them all.
3. You must output a valid JSON object.

JSON FORMAT:
{{
  "reasoning": "Explain exactly which join/table is causing the seq scan and why the index helps.",
  "category": "INDEX" | "REWRITE" | "ADVISORY",
  "sql": "CREATE INDEX...; CREATE INDEX..." or null
}}
"""

    def _build_reasoning_prompt(self, query: str, schema_info: str, plan: Dict[str, Any]) -> str:
        """
        Reasoning Prompt (Path B) for DeepSeek R1.
        Encourages unconstrained thinking before JSON.
        """
        total_cost = plan.get('Total Cost', 'Unknown')
        
        return f"""
ROLE: PostgreSQL Performance Architect.

=== GOAL ===
Optimize the provided query based on the Schema and Plan.
Focus on safety and high-impact changes only.

=== POLICY (RULES OF ENGAGEMENT) ===
1. JOIN KEY PRIORITY: If a JOIN results in a Sequential Scan on a table with more than 100 rows, you MUST suggest an index on the join columns (Foreign Keys). Do not be vague. Provide the exact `CREATE INDEX` SQL.
2. MULTI-INDEX SUPPORT: If multiple indexes are needed to optimize the query (e.g., across multiple tables), provide ALL of them in the "sql" field, separated by semicolons.
3. NO INDEX SPAM: If the query scans >20% of the table (e.g. Group By on the whole table), B-Tree indexes rarely help. Prefer "ADVISORY".
4. UNKNOWN PARAMS: The query uses parameters ($1, $2). Use these in your index logic if appropriate.
5. VALIDITY: Only use columns listed in the schema. Do not hallucinate columns.
6. ACTIONS: If you suggest a fix, set category to "INDEX" or "REWRITE". Use "ADVISORY" only as a last resort.

=== CONTEXT ===
TARGET QUERY: {query}

=== DATABASE STATS ===
{schema_info}

=== EXECUTION PLAN ===
Total Cost: {total_cost}
Plan Details: {json.dumps(plan, indent=2)}

INSTRUCTIONS:
1. Analyze the query execution plan deeply.
2. Verify if the suggested index(es) cover the specific filters and sort keys.
3. Suggest the optimal fix(es). If multiple indexes are needed, provide them all.

OUTPUT FORMAT:
First, output your reasoning process enclosed in <think> tags.
Then, output the final result in a strictly formatted JSON block wrapped in ```json code fence.

Example JSON output:
```json
{{
  "category": "INDEX",
  "reasoning": "Join on table X is slow because of Seq Scan. Suggested index for FK column Y.",
  "sql": "CREATE INDEX idx_x_y ON x(y); CREATE INDEX idx_a_b ON a(b);"
}}
```
"""

    def _build_analysis_prompt(self, query: str, schema_info: str, plan: Dict[str, Any]) -> str:
        """
        Legacy method kept for compatibility, now delegates to standard prompt.
        """
        return self._build_standard_prompt(query, schema_info, plan)

llm_service = LLMService()
