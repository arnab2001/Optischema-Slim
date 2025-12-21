
import logging
from typing import Dict, Any, List
from datetime import datetime
from connection_manager import connection_manager
from services.llm_service import llm_service
from storage import save_health_result

logger = logging.getLogger(__name__)

class HealthScanService:
    async def run_scan(self, limit: int = 50) -> Dict[str, Any]:
        """
        Orchestrate the health scan and return unified structured data.
        Satisfies both HealthScanWidget (summary/bloat) and HealthPanel (issues).
        """
        vitals = await self.collect_vitals(limit)
        if 'error' in vitals:
             return {"error": vitals['error']}
             
        # 1. Process Rule-based Vitals (for the widget)
        report = self.process_vitals_rules(vitals)
        
        # 2. Calculate Deterministic Score
        score, deductions = self.calculate_deterministic_score(vitals, report)
        report['score_breakdown'] = deductions
        
        # 3. Add AI Triage (using the deterministic score)
        ai_report = await self.triage_with_ai(vitals, score, deductions)
        
        # 4. Merge
        report['health_score'] = score
        report['issues'] = ai_report.get('issues', [])
        
        # 5. Persist & Enforce Retention
        try:
            from storage import save_health_result, enforce_health_retention
            await save_health_result(report)
            await enforce_health_retention(keep_n=10) # Default to 10 for now
        except Exception as e:
            logger.error(f"Failed to persist health result: {e}")
            
        return report

    async def collect_vitals(self, limit: int = 50) -> Dict[str, Any]:
        """
        Run the 4 data collection queries.
        """
        pool = await connection_manager.get_pool()
        if not pool:
            return {"error": "No database connection"}
        
        vitals = {}
        
        try:
            async with pool.acquire() as conn:
                # 1. Global Workload Baseline
                vitals['total_db_time'] = await conn.fetchval("SELECT SUM(total_exec_time)::float FROM pg_stat_statements") or 0.0

                # 2. Top Queries (Filtered for system noise)
                vitals['top_queries'] = await conn.fetch(f"""
                    SELECT queryid, query, total_exec_time::float, calls, mean_exec_time::float 
                    FROM pg_stat_statements 
                    WHERE query NOT ILIKE '%%pg_switch_wal%%'
                      AND query NOT ILIKE '%%pg_version%%'
                      AND query NOT ILIKE '%%pg_catalog.%%'
                      AND query NOT ILIKE '%%COMMIT%%'
                      AND query NOT ILIKE '%%BEGIN%%'
                      AND query NOT ILIKE '%%SET %%'
                      AND query NOT ILIKE '%%VACUUM%%'
                      AND query NOT ILIKE '%%ANALYZE%%'
                      AND query NOT ILIKE '%%SHOW %%'
                    ORDER BY total_exec_time DESC 
                    LIMIT {limit};
                """)
                
                # 3. Bloat
                vitals['bloat'] = await conn.fetch(f"""
                    SELECT schemaname, relname as table, n_live_tup as live_tuples, n_dead_tup as dead_tuples,
                        round((n_dead_tup::numeric / nullif(n_live_tup, 0)) * 100, 2)::float as dead_ratio,
                        last_autovacuum
                    FROM pg_stat_user_tables 
                    WHERE n_dead_tup > 50 
                    ORDER BY dead_ratio DESC LIMIT {limit};
                """)
                
                # 4. Unused Indexes
                vitals['unused_indexes'] = await conn.fetch(f"""
                    SELECT 
                        s.schemaname as schema, 
                        s.relname as table, 
                        s.indexrelname as index,
                        s.idx_scan as scans,
                        s.idx_tup_read as tuples_read,
                        s.idx_tup_fetch as tuples_fetched,
                        pg_size_pretty(pg_relation_size(s.indexrelid)) as size,
                        pg_relation_size(s.indexrelid) as size_bytes
                    FROM pg_stat_user_indexes s
                    JOIN pg_index i ON s.indexrelid = i.indexrelid
                    WHERE s.idx_scan = 0 
                    AND i.indisunique = false
                    ORDER BY pg_relation_size(s.indexrelid) DESC
                    LIMIT {limit};
                """)
                
                # 5. Config
                vitals['config'] = await conn.fetch("""
                    SELECT name as setting, setting as current_value, unit 
                    FROM pg_settings 
                    WHERE name IN ('shared_buffers', 'work_mem', 'maintenance_work_mem', 'effective_cache_size', 'max_connections', 'autovacuum_vacuum_scale_factor');
                """)
                
        except Exception as e:
            logger.error(f"Failed to collect vitals: {e}")
            vitals['error'] = str(e)
            
        return vitals

    def process_vitals_rules(self, vitals: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process raw vitals into the HealthScanWidget generic structure (Rule-based).
        """
        # Process Bloat
        bloat_issues = []
        for row in vitals.get('bloat', []):
            r = dict(row)
            if r['dead_ratio'] and r['dead_ratio'] > 20:
                bloat_issues.append({
                    "schema": r['schemaname'],
                    "table": r['table'],
                    "dead_ratio": r['dead_ratio'],
                    "live_tuples": r['live_tuples'],
                    "dead_tuples": r['dead_tuples'],
                    "last_autovacuum": str(r['last_autovacuum']) if r['last_autovacuum'] else None,
                    "vacuum_overdue": True,
                    "severity": "high" if r['dead_ratio'] > 50 else "medium",
                    "recommendation": f"Run VACUUM FULL {r['schemaname']}.{r['table']}"
                })

        # Process Unused Indexes
        index_issues = []
        for row in vitals.get('unused_indexes', []):
            r = dict(row)
            index_issues.append({
                "schema": r['schema'],
                "table": r['table'],
                "index": r['index'],
                "scans": r['scans'],
                "tuples_read": r['tuples_read'],
                "tuples_fetched": r['tuples_fetched'],
                "size": r['size'],
                "size_bytes": r['size_bytes'],
                "severity": "medium",
                "recommendation": f"DROP INDEX CONCURRENTLY {r['schema']}.{r['index']}"
            })

        # Process Config
        config_issues = []
        
        for row in vitals.get('config', []):
            r = dict(row)
            name = r['setting']
            val = r['current_value']
            unit = r['unit']
            
            # Helper: Convert everything to MB for comparison
            def to_mb(value, unit_str):
                try:
                    v = float(value)
                    if not unit_str: return v # No unit, return as is (e.g. max_connections)
                    if unit_str == 'kB': return v / 1024
                    if unit_str == '8kB': return (v * 8) / 1024
                    if unit_str == 'MB': return v
                    if unit_str == 'GB': return v * 1024
                    return v
                except:
                    return 0

            # 1. work_mem (Aim for > 4MB)
            if name == 'work_mem':
                mb = to_mb(val, unit)
                if mb <= 4:
                    config_issues.append({
                         "setting": "work_mem",
                         "current_value": f"{val}{unit}",
                         "severity": "low",
                         "issue": "Low work_mem (4MB)",
                         "recommendation": "Increase to 16MB+ for complex queries."
                     })

            # 2. shared_buffers (Warn if < 128MB for typical workloads)
            elif name == 'shared_buffers':
                mb = to_mb(val, unit)
                if mb < 128:
                    config_issues.append({
                         "setting": "shared_buffers",
                         "current_value": f"{int(mb)}MB",
                         "severity": "medium",
                         "issue": "Low shared_buffers",
                         "recommendation": f"Increase to 25-40% of RAM (current: {int(mb)}MB)."
                     })
            
            # 3. autovacuum_vacuum_scale_factor (Default 0.2 is often too high for big tables)
            elif name == 'autovacuum_vacuum_scale_factor':
                try:
                    factor = float(val)
                    if factor >= 0.2:
                        config_issues.append({
                             "setting": "autovacuum_vacuum_scale_factor",
                             "current_value": str(factor),
                             "severity": "low",
                             "issue": "Autovacuum scale factor is default (20%)",
                             "recommendation": "Lower to 0.05 (5%) for frequent updates."
                         })
                except:
                   pass
             
        return {
            "scan_timestamp": datetime.utcnow().isoformat(),
            "health_score": 100, # Will be overridden by AI
            "table_bloat": {
                "checked": True,
                "issues": bloat_issues,
                "total_tables_checked": len(vitals.get('bloat', []))
            },
            "index_bloat": {
                "checked": True,
                "unused_indexes": index_issues,
                "total_unused": len(index_issues)
            },
            "config_issues": {
                "checked": True,
                "issues": config_issues,
                "total_settings_checked": len(configs)
            },
            "summary": {
                "total_bloated_tables": len(bloat_issues),
                "total_unused_indexes": len(index_issues),
                "total_config_issues": len(config_issues)
            }
        }

    def calculate_deterministic_score(self, vitals: Dict[str, Any], rule_report: Dict[str, Any]) -> tuple[int, List[str]]:
        """
        Calculate a health score based on strict rules rather than AI hallucination.
        Returns (score, explanation_points).
        """
        score = 100
        deductions = []

        # 1. Performance Deductions (Latency & Workload)
        queries = vitals.get('top_queries', [])
        total_db_time = vitals.get('total_db_time', 0.0)
        
        slow_queries_count = 0
        workload_heavy_count = 0
        perf_penalty = 0
        
        for q in queries:
            qty = dict(q)
            mean_time = qty.get('mean_exec_time', 0)
            total_time = qty.get('total_exec_time', 0)
            
            # Latency Penalty
            if mean_time > 1000: # 1s
                perf_penalty += 10
                slow_queries_count += 1
            elif mean_time > 100: # 100ms
                perf_penalty += 3
                slow_queries_count += 1
                
            # Workload Penalty (Contribution to total DB time)
            if total_db_time > 0:
                workload_percent = (total_time / total_db_time) * 100
                if workload_percent > 25:
                    perf_penalty += 15
                    workload_heavy_count += 1
                    deductions.append(f"-15 pts: Query {qty['queryid']} impacts >25% of DB time")
                elif workload_percent > 10:
                    perf_penalty += 5
                    workload_heavy_count += 1
                    deductions.append(f"-5 pts: Query {qty['queryid']} impacts >10% of DB time")
        
        # Base latency deduction summary
        if slow_queries_count > 0:
            lat_deduction = min(perf_penalty, 30) # Latency portion capped
            deductions.append(f"-{lat_deduction} pts: {slow_queries_count} Slow Queries (>100ms) detected")

        # Total perf penalty cap
        score -= min(perf_penalty, 50)

        # 2. Bloat Deductions
        bloat_issues = rule_report.get('table_bloat', {}).get('issues', [])
        for issue in bloat_issues:
            if issue['severity'] == 'high':
                score -= 15
                deductions.append(f"-15 pts: Critical bloat in {issue['schema']}.{issue['table']}")
            else:
                score -= 5
                deductions.append(f"-5 pts: Moderate bloat in {issue['schema']}.{issue['table']}")

        # 3. Unused Indexes
        unused_indexes = rule_report.get('index_bloat', {}).get('unused_indexes', [])
        if unused_indexes:
            # -2 points per unused index, capped at -20
            points = min(len(unused_indexes) * 2, 20)
            score -= points
            deductions.append(f"-{points} pts: {len(unused_indexes)} unused indexes found")

        # 4. Config Issues
        config_issues = rule_report.get('config_issues', {}).get('issues', [])
        for issue in config_issues:
            score -= 5
            deductions.append(f"-5 pts: Configuration issue: {issue['setting']}")

        return max(0, score), deductions

    async def triage_with_ai(self, vitals: Dict[str, Any], deterministic_score: int, deductions: List[str]) -> Dict[str, Any]:
        """
        Send vitals to LLM for prioritization, using the pre-calculated score.
        """
        # Formulate query summaries for AI to see calls and total time
        q_summary = []
        total_db_time = vitals.get('total_db_time', 1)
        for q in vitals.get('top_queries', []):
            qty = dict(q)
            pct = (qty['total_exec_time'] / total_db_time) * 100
            q_summary.append(f"Query {qty['queryid']} ({qty['calls']} calls, {pct:.1f}% DB Load): {qty['query'][:200]}...")

        prompt = f"""
ROLE: Senior Database Performance Architect.
TASK: Analyze this database health snapshot and the calculated score.

SCORING POLICY:
Calculated Score: {deterministic_score}/100
Deductions:
{chr(10).join(deductions) if deductions else "None"}

INPUT DATA:
1. WORKLOAD SUMMARY:
{chr(10).join(q_summary)}

2. BLOAT: {vitals.get('bloat')}
3. CONFIG: {vitals.get('config')}
4. UNUSED INDEXES: {vitals.get('unused_indexes')}

YOUR GOAL: 
Explain the score and prioritize the issues. 
If a query has high 'DB Load %' (even if low latency), it is a CRITICAL optimization target. 
Demand specific fixes (like "Add index for join") in your explanation.

OUTPUT JSON FORMAT:
{{
  "health_score": {deterministic_score},
  "issues": [
    {{
      "type": "QUERY" | "CONFIG" | "SCHEMA",
      "severity": "CRITICAL" | "WARNING" | "INFO",
      "title": "Title",
      "description": "Explain WHY this matters based on stats.",
      "action_payload": "Context"
    }}
  ]
}}

STRICT RULES FOR 'type' AND 'action_payload':
1. type="QUERY": Use ONLY for specific slow/heavy queries from the WORKLOAD SUMMARY.
   - action_payload MUST be the 'queryid' (e.g., "123456789"). DO NOT put SQL here.
2. type="SCHEMA": Use for Bloat, Vacuum, or Missing Index issues.
   - action_payload MUST be the generic SQL command to fix it (e.g., "VACUUM FULL public.users;", "CREATE INDEX ON...").
3. type="CONFIG": Use for Postgres settings (work_mem, etc).
   - action_payload MUST be the SQL command to change it (e.g., "ALTER SYSTEM SET work_mem = '64MB';").
}}
"""
        try:
            result = await llm_service.get_completion(prompt, json_mode=True)
            result = self._validate_ai_response(result)
            
            # Fallback: If AI returned no issues but we have deductions, use deterministic generator
            if not result.get('issues') and deductions:
                 result['issues'] = self._synthesize_fallback_issues(deductions)
                 
            return result
        except Exception as e:
            logger.error(f"AI Triage failed: {e}")
            # Fallback on failure
            return {
                "health_score": deterministic_score, 
                "issues": self._synthesize_fallback_issues(deductions)
            }

    def _synthesize_fallback_issues(self, deductions: List[str]) -> List[Dict[str, Any]]:
        """
        Generate strict issues from deterministic deductions if AI fails.
        """
        issues = []
        import re
        
        for d in deductions:
            # Parse deduction string: "-15 pts: Query 123... impacts..."
            # Regex to capture: pts, description
            match = re.search(r'-\d+ pts: (.*)', d)
            if not match: continue
            
            desc = match.group(1)
            
            # 1. Slow Query
            if "Query" in desc:
                # Extract ID
                id_match = re.search(r'Query (-?\d+)', desc)
                if id_match:
                    qid = id_match.group(1)
                    issues.append({
                        "type": "QUERY",
                        "severity": "WARNING",
                        "title": "High Impact Query",
                        "description": desc,
                        "action_payload": qid
                    })
            
            # 2. Bloat
            elif "bloat" in desc.lower():
                # Extract table name if possible
                tbl_match = re.search(r'in ([\w\.]+)', desc)
                tbl = tbl_match.group(1) if tbl_match else "table"
                issues.append({
                    "type": "SCHEMA",
                    "severity": "WARNING",
                    "title": "Table Bloat Detected",
                    "description": desc,
                    "action_payload": f"VACUUM FULL {tbl};"
                })
                
            # 3. Unused Indexes
            elif "unused indexes" in desc.lower():
                issues.append({
                    "type": "SCHEMA",
                    "severity": "INFO",
                    "title": "Unused Indexes",
                    "description": desc,
                    "action_payload": "-- Check Unused Indexes section"
                })
                
            # 4. Config
            elif "Configuration" in desc:
                issues.append({
                    "type": "CONFIG",
                    "severity": "INFO",
                    "title": "Config Issue",
                    "description": desc,
                    "action_payload": "-- Check Config section"
                })
                
        return issues

    def _validate_ai_response(self, ai_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize AI output to prevent frontend crashes or broken links.
        """
        issues = ai_data.get('issues', [])
        sanitized_issues = []
        import re
        
        for issue in issues:
            try:
                # Normalize keys
                itype = issue.get('type', 'INFO').upper()
                payload = str(issue.get('action_payload', '')).strip()
                
                # RULE 1: QUERY type must have a numeric-looking ID (positive or negative int64)
                if itype == 'QUERY':
                    # Check if payload contains only digits (allowing for negative sign)
                    if not re.match(r'^-?\d+$', payload):
                        # If the payload is text (e.g. "Optimize...", "VACUUM..."), 
                        # this is a hallucination. Downgrade to INFO or SCHEMA.
                        if "VACUUM" in payload.upper() or "INDEX" in payload.upper():
                            itype = 'SCHEMA' # Fallback for misclassified schema actions
                        else:
                            itype = 'INFO' # Just advisory text
                            payload = ""   # Clear payload so no button is shown
                
                issue['type'] = itype
                issue['action_payload'] = payload
                sanitized_issues.append(issue)
            except Exception as e:
                logger.warning(f"Skipping malformed issue from AI: {e}")
                continue
            
        ai_data['issues'] = sanitized_issues
        return ai_data

health_scan_service = HealthScanService()
