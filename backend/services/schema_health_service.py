"""
Schema Health Service for OptiSchema Slim.
Detects schema-usage mismatches using pure catalog queries (no LLM needed).
Includes intelligent unused index detection with cost-benefit scoring
and staged decommissioning workflow.
"""

import logging
import math
from typing import Dict, Any, List
from connection_manager import connection_manager

logger = logging.getLogger(__name__)

class SchemaHealthService:
    """Detects schema design issues that impact performance."""

    async def analyze_database_schema(self) -> Dict[str, Any]:
        """
        Run comprehensive schema health checks across all user tables.
        Returns structured report with issues grouped by severity.
        """
        pool = await connection_manager.get_pool()
        if not pool:
            return {"error": "No database connection"}

        try:
            async with pool.acquire() as conn:
                # Get all user tables
                tables = await conn.fetch("""
                    SELECT schemaname, tablename,
                           pg_total_relation_size(schemaname||'.'||tablename) as total_bytes
                    FROM pg_tables
                    WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                """)

                issues = []
                summary = {
                    "total_tables": len(tables),
                    "tables_with_issues": 0,
                    "p0_count": 0,
                    "p1_count": 0,
                    "p2_count": 0
                }

                for table in tables:
                    table_name = f"{table['schemaname']}.{table['tablename']}"
                    table_issues = await self._analyze_table(conn, table_name, table['total_bytes'])

                    if table_issues:
                        summary["tables_with_issues"] += 1
                        for issue in table_issues:
                            if issue["severity"] == "P0":
                                summary["p0_count"] += 1
                            elif issue["severity"] == "P1":
                                summary["p1_count"] += 1
                            else:
                                summary["p2_count"] += 1
                        issues.extend(table_issues)

                return {
                    "success": True,
                    "summary": summary,
                    "issues": issues
                }

        except Exception as e:
            logger.error(f"Schema health analysis failed: {e}")
            return {"error": str(e)}

    async def _analyze_table(self, conn, table_name: str, table_bytes: int) -> List[Dict[str, Any]]:
        """Run all schema health checks for a single table."""
        issues = []

        # Check 1: Excessive indexes
        excessive = await self._check_excessive_indexes(conn, table_name, table_bytes)
        if excessive:
            issues.append(excessive)

        # Check 2: Low cardinality indexes
        low_card = await self._check_low_cardinality_indexes(conn, table_name)
        issues.extend(low_card)

        # Check 3: Redundant/duplicate indexes
        redundant = await self._check_redundant_indexes(conn, table_name)
        issues.extend(redundant)

        # Check 4: Missing foreign key constraints
        missing_fks = await self._check_missing_foreign_keys(conn, table_name)
        issues.extend(missing_fks)

        # Check 5: Partitioning candidates
        partition_candidate = await self._check_partitioning_candidate(conn, table_name, table_bytes)
        if partition_candidate:
            issues.append(partition_candidate)

        # Check 6: Wide table with unused columns (if we have column stats)
        wide_table = await self._check_wide_table(conn, table_name)
        if wide_table:
            issues.append(wide_table)

        return issues

    async def _check_excessive_indexes(self, conn, table_name: str, table_bytes: int) -> Dict[str, Any] | None:
        """Check if table has too many indexes (write penalty)."""
        try:
            index_count = await conn.fetchval("""
                SELECT COUNT(*)
                FROM pg_indexes
                WHERE schemaname || '.' || tablename = $1
            """, table_name)

            # Threshold: >10 indexes is excessive
            if index_count > 10:
                return {
                    "severity": "P1",
                    "type": "excessive_indexes",
                    "table": table_name,
                    "message": f"{index_count} indexes on {table_name}",
                    "impact": "High write penalty on INSERTs/UPDATEs",
                    "recommendation": "Audit for redundant or unused indexes. Consider composite indexes instead of multiple single-column indexes.",
                    "metadata": {
                        "index_count": index_count,
                        "table_size": table_bytes
                    }
                }
        except Exception as e:
            logger.error(f"Failed to check excessive indexes for {table_name}: {e}")
        return None

    async def _check_low_cardinality_indexes(self, conn, table_name: str) -> List[Dict[str, Any]]:
        """Check for indexes on low-cardinality columns (poor selectivity)."""
        issues = []
        try:
            # Query pg_stats for column cardinality
            low_card_cols = await conn.fetch("""
                SELECT
                    i.indexname,
                    s.attname,
                    s.n_distinct,
                    s.null_frac
                FROM pg_stats s
                JOIN pg_indexes i ON i.tablename = s.tablename
                WHERE s.schemaname || '.' || s.tablename = $1
                  AND s.n_distinct > 0
                  AND s.n_distinct < 100
                  AND s.attname = ANY(
                      SELECT unnest(string_to_array(
                          regexp_replace(i.indexdef, '.*\\((.*)\\)', '\\1'),
                          ', '
                      ))
                  )
            """, table_name)

            for col in low_card_cols:
                issues.append({
                    "severity": "P1",
                    "type": "low_selectivity_index",
                    "table": table_name,
                    "message": f"Index {col['indexname']} on low-cardinality column {col['attname']}",
                    "impact": f"Index has only ~{int(col['n_distinct'])} distinct values - poor selectivity",
                    "recommendation": "Consider partial index with WHERE clause, composite index, or remove if unused",
                    "metadata": {
                        "index_name": col['indexname'],
                        "column": col['attname'],
                        "distinct_values": int(col['n_distinct']),
                        "null_fraction": float(col['null_frac'])
                    }
                })
        except Exception as e:
            logger.error(f"Failed to check low cardinality indexes for {table_name}: {e}")

        return issues

    async def _check_redundant_indexes(self, conn, table_name: str) -> List[Dict[str, Any]]:
        """Check for duplicate or left-prefix redundant indexes."""
        issues = []
        try:
            # Parse schema.table
            parts = table_name.split(".", 1)
            if len(parts) != 2:
                return issues
            schema_name, tbl_name = parts

            # Use pg_index + pg_attribute (reliable, no regex parsing of indexdef)
            indexes = await conn.fetch("""
                SELECT
                    ic.relname AS indexname,
                    array_agg(a.attname ORDER BY array_position(ix.indkey::int[], a.attnum)) AS columns,
                    pg_relation_size(ic.oid) AS index_bytes
                FROM pg_index ix
                JOIN pg_class t ON t.oid = ix.indrelid
                JOIN pg_namespace n ON n.oid = t.relnamespace
                JOIN pg_class ic ON ic.oid = ix.indexrelid
                JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
                WHERE n.nspname = $1 AND t.relname = $2
                  AND ix.indexprs IS NULL  -- skip expression indexes (columns only)
                  AND a.attnum > 0         -- skip system columns
                GROUP BY ic.relname, ic.oid
                HAVING array_length(array_agg(a.attname ORDER BY array_position(ix.indkey::int[], a.attnum)), 1) > 0
            """, schema_name, tbl_name)

            # Check for duplicates and left-prefix redundancy
            for i, idx1 in enumerate(indexes):
                for idx2 in indexes[i+1:]:
                    cols1 = idx1['columns']
                    cols2 = idx2['columns']

                    # Exact duplicate
                    if cols1 == cols2:
                        issues.append({
                            "severity": "P0",
                            "type": "duplicate_index",
                            "table": table_name,
                            "message": f"Duplicate indexes: {idx1['indexname']} and {idx2['indexname']}",
                            "impact": "Wasted storage and write overhead",
                            "recommendation": f"DROP INDEX {idx2['indexname']}",
                            "metadata": {
                                "index1": idx1['indexname'],
                                "index2": idx2['indexname'],
                                "columns": cols1
                            }
                        })

                    # Left-prefix redundancy (idx1 is prefix of idx2)
                    elif len(cols1) < len(cols2) and cols2[:len(cols1)] == cols1:
                        issues.append({
                            "severity": "P1",
                            "type": "redundant_index_prefix",
                            "table": table_name,
                            "message": f"Index {idx1['indexname']} is redundant (left-prefix of {idx2['indexname']})",
                            "impact": f"Index on {cols1} is covered by {cols2}",
                            "recommendation": f"Consider dropping {idx1['indexname']} unless it's heavily used for specific queries",
                            "metadata": {
                                "redundant_index": idx1['indexname'],
                                "covering_index": idx2['indexname'],
                                "redundant_columns": cols1,
                                "covering_columns": cols2
                            }
                        })
        except Exception as e:
            logger.error(f"Failed to check redundant indexes for {table_name}: {e}")

        return issues

    async def _check_missing_foreign_keys(self, conn, table_name: str) -> List[Dict[str, Any]]:
        """Check for columns that look like foreign keys but have no constraint."""
        issues = []
        try:
            # Look for columns ending in _id that don't have FK constraints
            potential_fks = await conn.fetch("""
                SELECT c.column_name, c.data_type
                FROM information_schema.columns c
                WHERE c.table_schema || '.' || c.table_name = $1
                  AND (c.column_name LIKE '%_id' OR c.column_name LIKE '%_fk')
                  AND NOT EXISTS (
                      SELECT 1
                      FROM information_schema.table_constraints tc
                      JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                      WHERE tc.table_schema || '.' || tc.table_name = $1
                        AND tc.constraint_type = 'FOREIGN KEY'
                        AND kcu.column_name = c.column_name
                  )
            """, table_name)

            for col in potential_fks:
                issues.append({
                    "severity": "P2",
                    "type": "missing_foreign_key",
                    "table": table_name,
                    "message": f"Column {col['column_name']} looks like a foreign key but has no constraint",
                    "impact": "Query planner can't use FK information for optimization",
                    "recommendation": f"Add FK constraint if {col['column_name']} references another table",
                    "metadata": {
                        "column": col['column_name'],
                        "data_type": col['data_type']
                    }
                })
        except Exception as e:
            logger.error(f"Failed to check missing FKs for {table_name}: {e}")

        return issues

    async def _check_partitioning_candidate(self, conn, table_name: str, table_bytes: int) -> Dict[str, Any] | None:
        """Check if large table would benefit from partitioning."""
        try:
            # Only check tables >10GB
            if table_bytes < 10 * 1024 * 1024 * 1024:
                return None

            # Check for timestamp/date columns (common partition keys)
            time_cols = await conn.fetch("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema || '.' || table_name = $1
                  AND data_type IN ('timestamp', 'timestamptz', 'date', 'timestamp without time zone', 'timestamp with time zone')
            """, table_name)

            if time_cols:
                return {
                    "severity": "P1",
                    "type": "partitioning_candidate",
                    "table": table_name,
                    "message": f"Large table ({table_bytes // (1024**3)}GB) with time-based columns",
                    "impact": "Slow queries scanning entire table",
                    "recommendation": f"Consider partitioning on {time_cols[0]['column_name']} (range partitioning)",
                    "metadata": {
                        "table_size_bytes": table_bytes,
                        "time_columns": [c['column_name'] for c in time_cols]
                    }
                }
        except Exception as e:
            logger.error(f"Failed to check partitioning for {table_name}: {e}")

        return None

    async def _check_wide_table(self, conn, table_name: str) -> Dict[str, Any] | None:
        """Check for tables with excessive columns (SELECT * antipattern)."""
        try:
            col_count = await conn.fetchval("""
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_schema || '.' || table_name = $1
            """, table_name)

            # Threshold: >50 columns is suspiciously wide
            if col_count > 50:
                return {
                    "severity": "P2",
                    "type": "wide_table",
                    "table": table_name,
                    "message": f"Table has {col_count} columns",
                    "impact": "SELECT * queries fetch unnecessary data, high I/O overhead",
                    "recommendation": "Audit for unused columns or consider vertical partitioning (split into multiple tables)",
                    "metadata": {
                        "column_count": col_count
                    }
                }
        except Exception as e:
            logger.error(f"Failed to check wide table for {table_name}: {e}")

        return None


    # ── Unused Index Intelligence ──────────────────────────────────────────

    async def analyze_unused_indexes(self) -> Dict[str, Any]:
        """
        Comprehensive unused index analysis with cost-benefit scoring.

        Scoring formula (0-100 usefulness):
          - scan_score  (0-40): idx_scan normalized by stats age
          - cost_score  (0-30): read benefit vs write overhead ratio
          - size_score  (0-10): larger unused indexes = lower score
          - constraint_bonus (+20): PK, unique, or FK-backing indexes
          - freshness_penalty: if stats < 7 days old, reduce confidence

        Recommended stage:
          - score >= 70: "active" (healthy, no action)
          - score 40-69: "monitoring" (watch for 30 days)
          - score 10-39: "ready_to_disable" (safe to soft-disable)
          - score 0-9:  "ready_to_drop" (strong drop candidate)
        """
        pool = await connection_manager.get_pool()
        if not pool:
            return {"error": "No database connection"}

        try:
            async with pool.acquire() as conn:
                # 1. Get stats age (days since last reset)
                stats_age = await conn.fetchval("""
                    SELECT EXTRACT(EPOCH FROM (now() - stats_reset)) / 86400.0
                    FROM pg_stat_database
                    WHERE datname = current_database()
                """)
                stats_age_days = float(stats_age) if stats_age else 0

                # 2. Get all indexes with usage + table write stats
                indexes = await conn.fetch("""
                    SELECT
                        sui.schemaname,
                        sui.relname AS table_name,
                        sui.indexrelname AS index_name,
                        sui.idx_scan,
                        sui.idx_tup_read,
                        sui.idx_tup_fetch,
                        pg_relation_size(sui.indexrelid) AS size_bytes,
                        pg_size_pretty(pg_relation_size(sui.indexrelid)) AS size_pretty,
                        i.indisprimary,
                        i.indisunique,
                        -- Table write activity
                        sut.n_tup_ins,
                        sut.n_tup_upd,
                        sut.n_tup_del,
                        -- Check if index backs a FK constraint
                        EXISTS(
                            SELECT 1 FROM pg_constraint c
                            WHERE c.conindid = sui.indexrelid
                        ) AS backs_constraint
                    FROM pg_stat_user_indexes sui
                    JOIN pg_index i ON i.indexrelid = sui.indexrelid
                    JOIN pg_stat_user_tables sut ON sut.relid = sui.relid
                    ORDER BY sui.idx_scan ASC, pg_relation_size(sui.indexrelid) DESC
                """)

                scored_indexes = []
                for idx in indexes:
                    score_breakdown = self._compute_usefulness_score(idx, stats_age_days)
                    scored_indexes.append(score_breakdown)

                # Sort by usefulness score ascending (worst first)
                scored_indexes.sort(key=lambda x: x["usefulness_score"])

                # Summary stats
                total = len(scored_indexes)
                drop_candidates = [i for i in scored_indexes if i["recommended_stage"] == "ready_to_drop"]
                disable_candidates = [i for i in scored_indexes if i["recommended_stage"] == "ready_to_disable"]
                monitoring_candidates = [i for i in scored_indexes if i["recommended_stage"] == "monitoring"]
                total_reclaimable = sum(i["size_bytes"] for i in drop_candidates + disable_candidates)

                return {
                    "success": True,
                    "stats_age_days": round(stats_age_days, 1),
                    "stats_reliable": stats_age_days >= 7,
                    "total_indexes": total,
                    "summary": {
                        "drop_candidates": len(drop_candidates),
                        "disable_candidates": len(disable_candidates),
                        "monitoring": len(monitoring_candidates),
                        "healthy": total - len(drop_candidates) - len(disable_candidates) - len(monitoring_candidates),
                        "total_reclaimable_bytes": total_reclaimable,
                        "total_reclaimable_pretty": self._format_bytes(total_reclaimable)
                    },
                    "indexes": scored_indexes
                }

        except Exception as e:
            logger.error(f"Unused index analysis failed: {e}")
            return {"error": str(e)}

    def _compute_usefulness_score(self, idx: dict, stats_age_days: float) -> Dict[str, Any]:
        """
        Compute a 0-100 usefulness score for a single index.

        Components:
          scan_score (0-40): How often is this index scanned?
          cost_score (0-30): Is the read benefit worth the write cost?
          size_score (0-10): Larger indexes penalized more when unused
          constraint_bonus (+20): PKs, unique, FK constraints
        """
        idx_scan = idx["idx_scan"] or 0
        size_bytes = idx["size_bytes"] or 0
        is_pk = idx["indisprimary"]
        is_unique = idx["indisunique"]
        backs_constraint = idx["backs_constraint"]
        total_writes = (idx["n_tup_ins"] or 0) + (idx["n_tup_upd"] or 0) + (idx["n_tup_del"] or 0)

        # ── Scan Score (0-40) ──
        # Normalize scans by stats age to get daily scan rate
        if stats_age_days > 0:
            scan_rate = idx_scan / stats_age_days
        else:
            scan_rate = 0

        # Logarithmic scale: 0 scans/day=0, 1 scan/day=20, 10/day=30, 100/day=40
        if scan_rate <= 0:
            scan_score = 0
        else:
            scan_score = min(40, 10 * math.log10(scan_rate + 1) + 20)

        # ── Cost-Benefit Score (0-30) ──
        # Ratio of reads vs writes - how much does this index earn vs cost?
        if total_writes > 0:
            cost_benefit_ratio = idx_scan / total_writes
        else:
            # No writes = index is free to keep
            cost_benefit_ratio = float('inf')

        if cost_benefit_ratio == float('inf'):
            cost_score = 30  # No write overhead, free index
        elif cost_benefit_ratio >= 1.0:
            cost_score = 30  # More reads than writes
        elif cost_benefit_ratio >= 0.1:
            cost_score = 20  # Moderate usage relative to writes
        elif cost_benefit_ratio >= 0.01:
            cost_score = 10  # Low usage relative to writes
        elif cost_benefit_ratio > 0:
            cost_score = 5   # Rarely used but writes are heavy
        else:
            cost_score = 0   # Zero scans with writes = pure overhead

        # ── Size Score (0-10) ──
        # Larger unused indexes are worse (more cache pollution, more write cost)
        size_mb = size_bytes / (1024 * 1024)
        if size_mb < 1:
            size_score = 10      # Tiny index, harmless
        elif size_mb < 10:
            size_score = 8
        elif size_mb < 100:
            size_score = 5
        elif size_mb < 1000:
            size_score = 2
        else:
            size_score = 0       # >1GB unused index = major waste

        # ── Constraint Detection ──
        # PKs, unique indexes, and FK-backing indexes are structurally required.
        # idx_scan = 0 is NORMAL for these — Postgres uses them for constraint
        # enforcement (INSERT uniqueness checks, FK lookups, ON CONFLICT) which
        # do NOT increment idx_scan. They must ALWAYS be "active".
        constraint_bonus = 0
        constraint_type = None
        is_structural = False

        if is_pk:
            constraint_bonus = 20
            constraint_type = "PRIMARY KEY"
            is_structural = True
        elif is_unique:
            constraint_bonus = 20
            constraint_type = "UNIQUE"
            is_structural = True
        elif backs_constraint:
            constraint_bonus = 20
            constraint_type = "FK_BACKING"
            is_structural = True

        # ── Final Score ──
        total_score = min(100, scan_score + cost_score + size_score + constraint_bonus)

        # Force structural indexes to minimum score of 70
        if is_structural:
            total_score = max(70, total_score)

        # Freshness penalty: if stats are < 7 days old, reduce confidence
        confidence_note = None
        if is_structural:
            confidence_note = "Structural index — required for constraint enforcement (idx_scan=0 is normal)"
        elif stats_age_days < 7 and stats_age_days > 0:
            confidence_note = f"Stats only {stats_age_days:.1f} days old — scores may be unreliable"

        # Determine recommended stage
        if is_structural or total_score >= 70:
            recommended_stage = "active"
        elif total_score >= 40:
            recommended_stage = "monitoring"
        elif total_score >= 10:
            recommended_stage = "ready_to_disable"
        else:
            recommended_stage = "ready_to_drop"

        # Write overhead ratio for storage
        write_overhead_ratio = round(cost_benefit_ratio, 4) if cost_benefit_ratio != float('inf') else -1

        return {
            "schema_name": idx["schemaname"],
            "table_name": idx["table_name"],
            "index_name": idx["index_name"],
            "usefulness_score": round(total_score, 1),
            "recommended_stage": recommended_stage,
            "idx_scan": idx_scan,
            "scan_rate_per_day": round(scan_rate, 2),
            "size_bytes": size_bytes,
            "size_pretty": idx["size_pretty"],
            "total_writes": total_writes,
            "write_overhead_ratio": write_overhead_ratio,
            "is_primary_key": is_pk,
            "is_unique": is_unique,
            "backs_constraint": backs_constraint,
            "constraint_type": constraint_type,
            "score_breakdown": {
                "scan_score": round(scan_score, 1),
                "cost_score": cost_score,
                "size_score": size_score,
                "constraint_bonus": constraint_bonus
            },
            "confidence_note": confidence_note
        }

    async def start_decommission(self, indexes: List[Dict[str, Any]], database_name: str) -> Dict[str, Any]:
        """
        Begin monitoring selected indexes for decommissioning.
        Records initial scan counts and creates tracking entries.
        """
        from storage import save_decommission_entry

        tracked = 0
        skipped = 0

        for idx in indexes:
            # Safety: never decommission structural indexes (PK, unique, FK-backing)
            ctype = idx.get("constraint_type")
            if idx.get("is_primary_key") or idx.get("is_unique") or ctype in ("PRIMARY KEY", "UNIQUE", "FK_BACKING"):
                skipped += 1
                continue

            await save_decommission_entry({
                "database_name": database_name,
                "schema_name": idx["schema_name"],
                "table_name": idx["table_name"],
                "index_name": idx["index_name"],
                "stage": "monitoring",
                "usefulness_score": idx.get("usefulness_score", 0),
                "idx_scan_at_start": idx.get("idx_scan", 0),
                "idx_scan_latest": idx.get("idx_scan", 0),
                "size_bytes": idx.get("size_bytes", 0),
                "write_overhead_ratio": idx.get("write_overhead_ratio", 0),
                "scan_rate_per_day": idx.get("scan_rate_per_day", 0),
                "is_constraint": 1 if idx.get("backs_constraint") else 0,
                "notes": f"Started monitoring. Score: {idx.get('usefulness_score', 0)}"
            })
            tracked += 1

        return {"tracked": tracked, "skipped_constraints": skipped}

    async def refresh_decommission_snapshots(self) -> Dict[str, Any]:
        """
        Take a snapshot of current idx_scan for all monitored indexes.
        Call this periodically (e.g., daily) to build monitoring history.
        """
        from storage import get_decommission_entries, save_decommission_snapshot, update_decommission_stage

        pool = await connection_manager.get_pool()
        if not pool:
            return {"error": "No database connection"}

        entries = await get_decommission_entries()
        if not entries:
            return {"updated": 0}

        updated = 0
        escalated = 0

        async with pool.acquire() as conn:
            for entry in entries:
                if entry["stage"] in ("dropped", "active"):
                    continue

                try:
                    current_scan = await conn.fetchval("""
                        SELECT idx_scan FROM pg_stat_user_indexes
                        WHERE schemaname = $1 AND indexrelname = $2
                    """, entry["schema_name"], entry["index_name"])

                    if current_scan is not None:
                        await save_decommission_snapshot(entry["id"], current_scan)

                        # Check if index gained scans since monitoring started
                        scans_gained = current_scan - entry["idx_scan_at_start"]

                        # Auto-escalate if still zero scans after monitoring
                        if entry["stage"] == "monitoring" and scans_gained == 0:
                            # Check if monitoring duration > 14 days
                            from datetime import datetime
                            started = datetime.fromisoformat(entry["started_at"]) if isinstance(entry["started_at"], str) else entry["started_at"]
                            days_monitored = (datetime.now() - started).days

                            if days_monitored >= 14:
                                new_stage = "ready_to_disable" if entry["is_constraint"] == 0 else "monitoring"
                                if new_stage != entry["stage"]:
                                    await update_decommission_stage(
                                        entry["id"], new_stage,
                                        f"Auto-escalated after {days_monitored} days with 0 new scans"
                                    )
                                    escalated += 1

                        # De-escalate: if index gained significant scans, move back to active
                        elif scans_gained > 10:
                            await update_decommission_stage(
                                entry["id"], "active",
                                f"Index gained {scans_gained} scans since monitoring started — still in use"
                            )
                            escalated += 1

                        updated += 1
                except Exception as e:
                    logger.warning(f"Failed to snapshot index {entry['index_name']}: {e}")

        return {"updated": updated, "escalated": escalated}

    @staticmethod
    def _format_bytes(size_bytes: int) -> str:
        """Format bytes into human-readable string."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


# Singleton instance
schema_health_service = SchemaHealthService()
