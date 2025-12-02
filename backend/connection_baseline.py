"""Tenant-aware connection baseline service backed by Postgres."""

from __future__ import annotations

import json
import uuid
import asyncio
import asyncpg
import ssl
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

from connection_manager import connection_manager
from tenant_context import TenantContext

logger = logging.getLogger(__name__)


class ConnectionBaselineService:
    """Manage connection latency baselines with tenant isolation."""

    @staticmethod
    async def _get_pool():
        pool = await connection_manager.get_pool()
        if not pool:
            raise RuntimeError("No database connection available for baselines")
        return pool

    @staticmethod
    def _resolve_tenant(tenant_id: Optional[str] = None) -> str:
        return tenant_id or TenantContext.get_tenant_id_or_default()

    @staticmethod
    async def measure_connection_latency(connection_config: Dict[str, Any]) -> float:
        """Measure round-trip latency to the provided database."""
        start_time = datetime.utcnow()
        config = connection_config.copy()

        ssl_mode = config.get('ssl')
        if ssl_mode is None:
            ssl_mode = 'require'

        if ssl_mode == 'require':
            config['ssl'] = True
        elif ssl_mode == 'prefer':
            config['ssl'] = True
        elif ssl_mode == 'disable':
            config['ssl'] = False

        if config.get('ssl') and config['ssl'] is not False:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            config['ssl'] = context

        conn = await asyncpg.connect(**config)
        try:
            await conn.execute('SELECT 1')
        finally:
            await conn.close()

        latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        logger.info("Connection latency measured: %.2f ms", latency_ms)
        return latency_ms

    @staticmethod
    async def store_baseline(
        connection_id: str,
        connection_name: str,
        baseline_latency_ms: float,
        connection_config: Dict[str, Any],
        *,
        tenant_id: Optional[str] = None,
    ) -> str:
        tenant = ConnectionBaselineService._resolve_tenant(tenant_id)
        pool = await ConnectionBaselineService._get_pool()
        measured_at = datetime.utcnow()
        config_json = json.dumps(connection_config)
        new_id = str(uuid.uuid4())

        async with pool.acquire() as conn:
            baseline_id = await conn.fetchval(
                """
                INSERT INTO optischema.connection_baselines (
                    id,
                    tenant_id,
                    connection_id,
                    connection_name,
                    baseline_latency_ms,
                    measured_at,
                    connection_config,
                    is_active
                ) VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, TRUE)
                ON CONFLICT (tenant_id, connection_id)
                DO UPDATE SET
                    connection_name = EXCLUDED.connection_name,
                    baseline_latency_ms = EXCLUDED.baseline_latency_ms,
                    measured_at = EXCLUDED.measured_at,
                    connection_config = EXCLUDED.connection_config,
                    is_active = TRUE
                RETURNING id
                """,
                new_id,
                tenant,
                connection_id,
                connection_name,
                baseline_latency_ms,
                measured_at,
                config_json,
            )
        logger.info("Stored baseline %s for tenant %s connection %s", baseline_id, tenant, connection_id)
        return baseline_id

    @staticmethod
    async def get_baseline(connection_id: str, tenant_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        tenant = ConnectionBaselineService._resolve_tenant(tenant_id)
        pool = await ConnectionBaselineService._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT *
                FROM optischema.connection_baselines
                WHERE tenant_id = $1 AND connection_id = $2 AND is_active = TRUE
                ORDER BY measured_at DESC
                LIMIT 1
                """,
                tenant,
                connection_id,
            )
        if not row:
            return None
        record = dict(row)
        record['connection_config'] = json.loads(record['connection_config']) if record.get('connection_config') else {}
        return record

    @staticmethod
    async def get_all_baselines(tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        tenant = ConnectionBaselineService._resolve_tenant(tenant_id)
        pool = await ConnectionBaselineService._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT *
                FROM optischema.connection_baselines
                WHERE tenant_id = $1 AND is_active = TRUE
                ORDER BY measured_at DESC
                """,
                tenant,
            )
        baselines: List[Dict[str, Any]] = []
        for row in rows:
            record = dict(row)
            record['connection_config'] = json.loads(record['connection_config']) if record.get('connection_config') else {}
            baselines.append(record)
        return baselines

    @staticmethod
    async def update_baseline(
        connection_id: str,
        baseline_latency_ms: float,
        *,
        tenant_id: Optional[str] = None,
    ) -> bool:
        tenant = ConnectionBaselineService._resolve_tenant(tenant_id)
        pool = await ConnectionBaselineService._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE optischema.connection_baselines
                SET baseline_latency_ms = $1,
                    measured_at = $2
                WHERE tenant_id = $3
                  AND connection_id = $4
                  AND is_active = TRUE
                """,
                baseline_latency_ms,
                datetime.utcnow(),
                tenant,
                connection_id,
            )
        return result.startswith("UPDATE") and result.split()[-1] != "0"

    @staticmethod
    async def deactivate_baseline(connection_id: str, *, tenant_id: Optional[str] = None) -> bool:
        tenant = ConnectionBaselineService._resolve_tenant(tenant_id)
        pool = await ConnectionBaselineService._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE optischema.connection_baselines
                SET is_active = FALSE
                WHERE tenant_id = $1 AND connection_id = $2 AND is_active = TRUE
                """,
                tenant,
                connection_id,
            )
        return result.startswith("UPDATE") and result.split()[-1] != "0"

    @staticmethod
    async def get_baseline_summary(tenant_id: Optional[str] = None) -> Dict[str, Any]:
        tenant = ConnectionBaselineService._resolve_tenant(tenant_id)
        pool = await ConnectionBaselineService._get_pool()
        async with pool.acquire() as conn:
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM optischema.connection_baselines WHERE tenant_id = $1 AND is_active = TRUE",
                tenant,
            )
            recent = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM optischema.connection_baselines
                WHERE tenant_id = $1 AND measured_at >= NOW() - INTERVAL '1 day'
                """,
                tenant,
            )
            avg_latency = await conn.fetchval(
                """
                SELECT AVG(baseline_latency_ms)
                FROM optischema.connection_baselines
                WHERE tenant_id = $1 AND is_active = TRUE
                """,
                tenant,
            )
            min_max = await conn.fetchrow(
                """
                SELECT MIN(baseline_latency_ms), MAX(baseline_latency_ms)
                FROM optischema.connection_baselines
                WHERE tenant_id = $1 AND is_active = TRUE
                """,
                tenant,
            )
        min_latency, max_latency = (min_max[0] or 0, min_max[1] or 0) if min_max else (0, 0)
        return {
            "total_active_baselines": total or 0,
            "recent_measurements_24h": recent or 0,
            "average_latency_ms": round(avg_latency or 0, 2),
            "min_latency_ms": round(min_latency, 2) if min_latency else 0,
            "max_latency_ms": round(max_latency, 2) if max_latency else 0,
        }

    @staticmethod
    async def measure_and_store_baseline(
        connection_config: Dict[str, Any],
        connection_name: str,
        *,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Measure latency and persist the resulting baseline."""
        try:
            latency_ms = await ConnectionBaselineService.measure_connection_latency(connection_config)
            connection_id = connection_config.get('connection_id') or f"{connection_name}_{uuid.uuid4()}"
            baseline_id = await ConnectionBaselineService.store_baseline(
                connection_id,
                connection_name,
                latency_ms,
                connection_config,
                tenant_id=tenant_id,
            )
            return {
                "success": True,
                "baseline_id": baseline_id,
                "connection_id": connection_id,
                "connection_name": connection_name,
                "latency_ms": latency_ms,
                "measured_at": datetime.utcnow().isoformat(),
            }
        except Exception as exc:
            logger.error("Failed to measure/store baseline: %s", exc)
            raise
