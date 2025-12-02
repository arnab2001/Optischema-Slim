"""Tenant-aware audit logging service backed by Postgres."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from connection_manager import connection_manager
from tenant_context import TenantContext

logger = logging.getLogger(__name__)


class AuditService:
    """Async audit logging utilities that scope all data by tenant."""

    @staticmethod
    async def _get_pool():
        pool = await connection_manager.get_pool()
        if not pool:
            raise RuntimeError("No database connection available for audit service")
        return pool

    @staticmethod
    def _resolve_tenant(tenant_id: Optional[str] = None) -> str:
        return tenant_id or TenantContext.get_tenant_id_or_default()

    @staticmethod
    async def log_action(
        *,
        action_type: str,
        user_id: Optional[str] = None,
        recommendation_id: Optional[str] = None,
        query_hash: Optional[str] = None,
        before_metrics: Optional[Dict[str, Any]] = None,
        after_metrics: Optional[Dict[str, Any]] = None,
        improvement_percent: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
        risk_level: Optional[str] = None,
        status: str = "completed",
        tenant_id: Optional[str] = None,
    ) -> str:
        """Persist an audit record for the active tenant."""

        tenant = AuditService._resolve_tenant(tenant_id)
        pool = await AuditService._get_pool()
        audit_id = str(uuid.uuid4())
        created_at = datetime.utcnow()

        async with pool.acquire() as conn:
            # Basic dedupe for rapid repeated apply actions
            if action_type == "recommendation_applied" and recommendation_id:
                existing = await conn.fetchval(
                    """
                    SELECT id
                    FROM optischema.audit_logs
                    WHERE tenant_id = $1
                      AND recommendation_id = $2
                      AND action_type = $3
                      AND created_at >= NOW() - INTERVAL '5 minutes'
                    LIMIT 1
                    """,
                    tenant,
                    recommendation_id,
                    action_type,
                )
                if existing:
                    logger.info(
                        "Skipping duplicate audit log for tenant %s recommendation %s",
                        tenant,
                        recommendation_id,
                    )
                    return existing

            await conn.execute(
                """
                INSERT INTO optischema.audit_logs (
                    id,
                    tenant_id,
                    action_type,
                    user_id,
                    recommendation_id,
                    query_hash,
                    before_metrics,
                    after_metrics,
                    improvement_percent,
                    details,
                    risk_level,
                    status,
                    created_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7::jsonb, $8::jsonb, $9, $10::jsonb, $11, $12, $13
                )
                """,
                audit_id,
                tenant,
                action_type,
                user_id,
                recommendation_id,
                query_hash,
                json.dumps(before_metrics) if before_metrics else None,
                json.dumps(after_metrics) if after_metrics else None,
                improvement_percent,
                json.dumps(details) if details else None,
                risk_level,
                status,
                created_at,
            )

        logger.info("Audit log created for tenant %s action %s", tenant, action_type)
        return audit_id

    @staticmethod
    async def get_audit_logs(
        *,
        action_type: Optional[str] = None,
        user_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        tenant_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        tenant = AuditService._resolve_tenant(tenant_id)
        pool = await AuditService._get_pool()

        query = [
            "SELECT id, tenant_id, action_type, user_id, recommendation_id, query_hash,",
            "       before_metrics, after_metrics, improvement_percent, details,",
            "       risk_level, status, created_at",
            "FROM optischema.audit_logs",
            "WHERE tenant_id = $1",
        ]
        params: List[Any] = [tenant]

        if action_type:
            params.append(action_type)
            query.append(f"AND action_type = ${len(params)}")
        if user_id:
            params.append(user_id)
            query.append(f"AND user_id = ${len(params)}")
        if start_date:
            params.append(start_date)
            query.append(f"AND created_at >= ${len(params)}")
        if end_date:
            params.append(end_date)
            query.append(f"AND created_at <= ${len(params)}")

        params.extend([limit, offset])
        query.append("ORDER BY created_at DESC LIMIT ${} OFFSET ${}".format(len(params) - 1, len(params)))

        async with pool.acquire() as conn:
            rows = await conn.fetch("\n".join(query), *params)

        logs: List[Dict[str, Any]] = []
        for row in rows:
            record = dict(row)
            for field in ("before_metrics", "after_metrics", "details"):
                if record.get(field):
                    record[field] = json.loads(record[field])
            logs.append(record)
        return logs

    @staticmethod
    async def get_audit_summary(tenant_id: Optional[str] = None) -> Dict[str, Any]:
        tenant = AuditService._resolve_tenant(tenant_id)
        pool = await AuditService._get_pool()

        async with pool.acquire() as conn:
            total_logs = await conn.fetchval(
                "SELECT COUNT(*) FROM optischema.audit_logs WHERE tenant_id = $1",
                tenant,
            )
            action_rows = await conn.fetch(
                """
                SELECT action_type, COUNT(*)
                FROM optischema.audit_logs
                WHERE tenant_id = $1
                GROUP BY action_type
                ORDER BY COUNT(*) DESC
                """,
                tenant,
            )
            status_rows = await conn.fetch(
                """
                SELECT status, COUNT(*)
                FROM optischema.audit_logs
                WHERE tenant_id = $1
                GROUP BY status
                ORDER BY COUNT(*) DESC
                """,
                tenant,
            )
            recent = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM optischema.audit_logs
                WHERE tenant_id = $1 AND created_at >= NOW() - INTERVAL '1 day'
                """,
                tenant,
            )
            avg_improvement = await conn.fetchval(
                """
                SELECT AVG(improvement_percent)
                FROM optischema.audit_logs
                WHERE tenant_id = $1 AND improvement_percent IS NOT NULL
                """,
                tenant,
            )

        return {
            "total_logs": total_logs or 0,
            "action_type_counts": {row[0]: row[1] for row in action_rows},
            "status_counts": {row[0]: row[1] for row in status_rows},
            "recent_activity_24h": recent or 0,
            "average_improvement_percent": round(avg_improvement or 0, 2),
        }

    @staticmethod
    async def get_distinct_action_types(tenant_id: Optional[str] = None) -> List[str]:
        tenant = AuditService._resolve_tenant(tenant_id)
        pool = await AuditService._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT DISTINCT action_type FROM optischema.audit_logs WHERE tenant_id = $1",
                tenant,
            )
        return sorted(row[0] for row in rows if row[0])

    @staticmethod
    async def get_distinct_users(tenant_id: Optional[str] = None) -> List[str]:
        tenant = AuditService._resolve_tenant(tenant_id)
        pool = await AuditService._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT DISTINCT user_id FROM optischema.audit_logs WHERE tenant_id = $1 AND user_id IS NOT NULL",
                tenant,
            )
        return sorted(row[0] for row in rows if row[0])

    @staticmethod
    async def clear_logs(tenant_id: Optional[str] = None) -> int:
        tenant = AuditService._resolve_tenant(tenant_id)
        pool = await AuditService._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM optischema.audit_logs WHERE tenant_id = $1",
                tenant,
            )
        return int(result.split()[-1]) if result.startswith("DELETE") else 0
