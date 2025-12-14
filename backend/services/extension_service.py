import logging
from connection_manager import connection_manager

logger = logging.getLogger(__name__)

class ExtensionService:
    async def check_pg_stat_statements(self) -> bool:
        """Check if pg_stat_statements is installed and enabled."""
        pool = await connection_manager.get_pool()
        if not pool:
            return False

        async with pool.acquire() as conn:
            try:
                # Check if extension exists
                result = await conn.fetchval("SELECT count(*) FROM pg_extension WHERE extname = 'pg_stat_statements'")
                return result > 0
            except Exception as e:
                logger.error(f"Failed to check extension: {e}")
                return False

    async def enable_pg_stat_statements(self) -> bool:
        """Attempt to enable pg_stat_statements."""
        pool = await connection_manager.get_pool()
        if not pool:
            return False

        async with pool.acquire() as conn:
            try:
                await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements")
                return True
            except Exception as e:
                logger.error(f"Failed to enable extension: {e}")
                return False

extension_service = ExtensionService()
