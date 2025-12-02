"""Tenant-aware benchmark jobs storage backed by Postgres."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from connection_manager import connection_manager
from tenant_context import TenantContext

logger = logging.getLogger(__name__)


class BenchmarkJobsService:
    """CRUD helpers for optischema.benchmark_jobs with tenant scoping."""

    @staticmethod
    async def _get_pool():
        pool = await connection_manager.get_pool()
        if not pool:
            raise RuntimeError("No database connection available for benchmark jobs")
        return pool

    @staticmethod
    def _resolve_tenant(tenant_id: Optional[str] = None) -> str:
        return tenant_id or TenantContext.get_tenant_id_or_default()

    @staticmethod
    async def create_job(
        recommendation_id: str,
        job_type: str = "benchmark",
        *,
        tenant_id: Optional[str] = None,
    ) -> str:
        tenant = BenchmarkJobsService._resolve_tenant(tenant_id)
        pool = await BenchmarkJobsService._get_pool()
        job_id = str(uuid.uuid4())
        created_at = datetime.utcnow()

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO optischema.benchmark_jobs (
                    id,
                    tenant_id,
                    recommendation_id,
                    status,
                    job_type,
                    created_at
                ) VALUES ($1, $2, $3, 'pending', $4, $5)
                """,
                job_id,
                tenant,
                recommendation_id,
                job_type,
                created_at,
            )
        logger.info("Created benchmark job %s for tenant %s", job_id, tenant)
        return job_id

    @staticmethod
    async def get_job(job_id: str, *, tenant_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        tenant = BenchmarkJobsService._resolve_tenant(tenant_id)
        pool = await BenchmarkJobsService._get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT *
                FROM optischema.benchmark_jobs
                WHERE tenant_id = $1 AND id = $2
                """,
                tenant,
                job_id,
            )
        if not row:
            return None
        record = dict(row)
        if record.get("result_json"):
            record["result_json"] = json.loads(record["result_json"])
        return record

    @staticmethod
    async def update_job_status(
        job_id: str,
        status: str,
        *,
        tenant_id: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        tenant = BenchmarkJobsService._resolve_tenant(tenant_id)
        pool = await BenchmarkJobsService._get_pool()
        timestamp = datetime.utcnow()

        started_at = timestamp if status == "running" else None
        completed_at = timestamp if status in {"completed", "failed", "error", "cancelled"} else None

        async with pool.acquire() as conn:
            res = await conn.execute(
                """
                UPDATE optischema.benchmark_jobs
                SET status = $1,
                    started_at = COALESCE($2, started_at),
                    completed_at = COALESCE($3, completed_at),
                    result_json = $4,
                    error_message = $5
                WHERE tenant_id = $6 AND id = $7
                """,
                status,
                started_at,
                completed_at,
                json.dumps(result) if result is not None else None,
                error_message,
                tenant,
                job_id,
            )
        updated = res.startswith("UPDATE") and res.split()[-1] != "0"
        if updated:
            logger.info("Updated benchmark job %s status to %s", job_id, status)
        return updated

    @staticmethod
    async def list_jobs(
        *,
        status: Optional[str] = None,
        recommendation_id: Optional[str] = None,
        limit: int = 100,
        tenant_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        tenant = BenchmarkJobsService._resolve_tenant(tenant_id)
        pool = await BenchmarkJobsService._get_pool()
        query = [
            "SELECT * FROM optischema.benchmark_jobs WHERE tenant_id = $1",
        ]
        params: List[Any] = [tenant]

        if status:
            params.append(status)
            query.append(f"AND status = ${len(params)}")
        if recommendation_id:
            params.append(recommendation_id)
            query.append(f"AND recommendation_id = ${len(params)}")

        params.append(limit)
        query.append(f"ORDER BY created_at DESC LIMIT ${len(params)}")

        async with pool.acquire() as conn:
            rows = await conn.fetch("\n".join(query), *params)

        jobs: List[Dict[str, Any]] = []
        for row in rows:
            record = dict(row)
            if record.get("result_json"):
                record["result_json"] = json.loads(record["result_json"])
            jobs.append(record)
        return jobs

    @staticmethod
    async def get_jobs_by_recommendation(
        recommendation_id: str,
        *,
        tenant_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return await BenchmarkJobsService.list_jobs(
            recommendation_id=recommendation_id,
            tenant_id=tenant_id,
            limit=1000,
        )

    @staticmethod
    async def get_jobs_count(
        status: Optional[str] = None,
        *,
        tenant_id: Optional[str] = None,
    ) -> int:
        tenant = BenchmarkJobsService._resolve_tenant(tenant_id)
        pool = await BenchmarkJobsService._get_pool()
        query = "SELECT COUNT(*) FROM optischema.benchmark_jobs WHERE tenant_id = $1"
        params: List[Any] = [tenant]
        if status:
            query += " AND status = $2"
            params.append(status)
        async with pool.acquire() as conn:
            count = await conn.fetchval(query, *params)
        return count or 0

    @staticmethod
    async def cleanup_old_jobs(hours: int = 72, *, tenant_id: Optional[str] = None) -> int:
        tenant = BenchmarkJobsService._resolve_tenant(tenant_id)
        pool = await BenchmarkJobsService._get_pool()
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM optischema.benchmark_jobs
                WHERE tenant_id = $1 AND completed_at IS NOT NULL AND completed_at < $2
                """,
                tenant,
                cutoff,
            )
        return int(result.split()[-1]) if result.startswith("DELETE") else 0

    @staticmethod
    async def get_job_statistics(tenant_id: Optional[str] = None) -> Dict[str, Any]:
        tenant = BenchmarkJobsService._resolve_tenant(tenant_id)
        pool = await BenchmarkJobsService._get_pool()

        async with pool.acquire() as conn:
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM optischema.benchmark_jobs WHERE tenant_id = $1",
                tenant,
            )
            status_rows = await conn.fetch(
                """
                SELECT status, COUNT(*)
                FROM optischema.benchmark_jobs
                WHERE tenant_id = $1
                GROUP BY status
                """,
                tenant,
            )
            recent = await conn.fetchval(
                """
                SELECT MAX(completed_at)
                FROM optischema.benchmark_jobs
                WHERE tenant_id = $1 AND completed_at IS NOT NULL
                """,
                tenant,
            )

        return {
            "total_jobs": total or 0,
            "status_counts": {row[0]: row[1] for row in status_rows},
            "last_completed_at": recent.isoformat() if recent else None,
        }
