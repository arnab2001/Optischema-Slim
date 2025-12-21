import logging
import re
from typing import Dict, Any, List, Optional
from connection_manager import connection_manager

logger = logging.getLogger(__name__)

class ExtensionService:
    def _detect_provider(self, host: str) -> str:
        """Identify the PostgreSQL provider based on the hostname."""
        if not host:
            return "unknown"
        if ".rds.amazonaws.com" in host:
            return "aws_rds"
        if ".supabase.co" in host or ".supabase.net" in host:
            return "supabase"
        if ".neon.tech" in host:
            return "neon"
        if host in ("localhost", "127.0.0.1", "postgres-sandbox"):
            return "local"
        return "generic"

    async def get_extensions_status(self) -> List[Dict[str, Any]]:
        """Get highly detailed status of all relevant extensions."""
        pool = await connection_manager.get_pool()
        if not pool:
            return []

        config = connection_manager.get_connection_config() or {}
        host = config.get('host', '')
        provider = self._detect_provider(host)
        
        extensions = ["pg_stat_statements", "hypopg"]
        status_list = []

        async with pool.acquire() as conn:
            # 1. Get shared_preload_libraries
            preload_libs = await conn.fetchval("SHOW shared_preload_libraries")
            preload_list = [lib.strip() for lib in preload_libs.split(',')] if preload_libs else []

            # 2. Get available extensions info
            available = await conn.fetch(
                "SELECT name, default_version, installed_version, comment "
                "FROM pg_available_extensions WHERE name = ANY($1)",
                extensions
            )
            available_map = {r['name']: r for r in available}

            # 3. Get currently installed extensions
            installed = await conn.fetch(
                "SELECT extname, extversion FROM pg_extension WHERE extname = ANY($1)",
                extensions
            )
            installed_map = {r['extname']: r['extversion'] for r in installed}

            # 4. Check user permissions (can create extensions?)
            is_superuser = await conn.fetchval("SELECT usesuper FROM pg_user WHERE usename = CURRENT_USER")
            has_create_permissions = is_superuser
            
            # For non-superusers, they might still have permission via specific roles or if it's a managed db
            if not is_superuser:
                # Check if user is member of rds_superuser (AWS) or similar
                roles = await conn.fetch("SELECT rolname FROM pg_roles WHERE pg_has_role(CURRENT_USER, oid, 'member')")
                role_names = [r['rolname'] for r in roles]
                if "rds_superuser" in role_names or "postgres" in role_names:
                    has_create_permissions = True

            for name in extensions:
                is_available = name in available_map
                is_enabled = name in installed_map
                is_preloaded = name in preload_list
                
                # Special case: pg_stat_statements MUST be preloaded
                requires_preload = name == "pg_stat_statements"
                preload_missing = requires_preload and not is_preloaded

                remediation = None
                if not is_available:
                    if provider == "aws_rds":
                        remediation = f"Add '{name}' to the 'rds.extensions' parameter in your RDS Parameter Group."
                    else:
                        remediation = f"The extension '{name}' is not installed on the server OS."
                elif preload_missing:
                    if provider == "aws_rds":
                        remediation = f"Add 'pg_stat_statements' to 'shared_preload_libraries' in your RDS Parameter Group and RESTART the instance."
                    elif provider == "local":
                        remediation = "Add 'pg_stat_statements' to 'shared_preload_libraries' in postgresql.conf and restart Postgres."
                    else:
                        remediation = "Consult your provider docs for enabling 'shared_preload_libraries' for pg_stat_statements."
                elif not is_enabled and not has_create_permissions:
                    remediation = f"Ask your DBA to run: CREATE EXTENSION {name};"

                status_list.append({
                    "name": name,
                    "available": is_available,
                    "enabled": is_enabled,
                    "preloaded": is_preloaded,
                    "requires_preload": requires_preload,
                    "preload_missing": preload_missing,
                    "version": installed_map.get(name) or (available_map.get(name)['default_version'] if is_available else None),
                    "description": available_map.get(name)['comment'] if is_available else "Not available on this PostgreSQL instance",
                    "remediation": remediation,
                    "provider_detected": provider
                })

        return status_list

    async def enable_extension(self, name: str) -> Dict[str, Any]:
        """Attempt to enable a specific extension with smart error handling."""
        pool = await connection_manager.get_pool()
        if not pool:
            return {"success": False, "message": "No database connection"}

        async with pool.acquire() as conn:
            try:
                # 1. Availability check
                available = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM pg_available_extensions WHERE name = $1)",
                    name
                )
                if not available:
                    config = connection_manager.get_connection_config() or {}
                    provider = self._detect_provider(config.get('host', ''))
                    
                    msg = f"Extension '{name}' is not available on this server."
                    if provider == "aws_rds":
                        msg += " You must add it to the 'rds.extensions' parameter group first."
                    return {"success": False, "message": msg}

                # 2. Preload check for pg_stat_statements
                if name == "pg_stat_statements":
                    preload_libs = await conn.fetchval("SHOW shared_preload_libraries")
                    if "pg_stat_statements" not in (preload_libs or ""):
                        return {
                            "success": False,
                            "message": "pg_stat_statements must be loaded via 'shared_preload_libraries' in your server configuration before it can be enabled via SQL."
                        }

                # 3. Execution
                await conn.execute(f"CREATE EXTENSION IF NOT EXISTS {name}")
                return {"success": True, "message": f"Extension '{name}' enabled successfully"}
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Failed to enable extension {name}: {e}")
                
                if "permission denied" in error_msg.lower():
                    return {
                        "success": False,
                        "message": "Permission denied. Please ask a superuser/DBA to enable this extension for you."
                    }
                if "must be loaded via shared_preload_libraries" in error_msg:
                    return {
                        "success": False,
                        "message": f"Extension '{name}' requires preloading in the server's 'shared_preload_libraries' setting."
                    }
                
                return {"success": False, "message": error_msg}

extension_service = ExtensionService()
