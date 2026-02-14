"""
SQLite storage for OptiSchema Slim.
Handles persistence of settings, chat history, saved optimizations, and saved connections.
"""

import aiosqlite
import json
import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

# Database path configuration
# Use /app/data/optischema.db as default if data directory exists (for Docker persistence)
DEFAULT_DB_DIR = os.path.join(os.path.dirname(__file__), 'data')
if not os.path.exists(DEFAULT_DB_DIR) and os.access(os.path.dirname(__file__), os.W_OK):
    try:
        os.makedirs(DEFAULT_DB_DIR, exist_ok=True)
    except Exception:
        DEFAULT_DB_DIR = os.path.dirname(__file__)

DB_PATH = os.environ.get('DATABASE_PATH', os.path.join(DEFAULT_DB_DIR, 'optischema.db'))

async def init_db():
    """Initialize the SQLite database with required tables."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Enable WAL mode for better concurrency (allows concurrent reads during writes)
        await db.execute("PRAGMA journal_mode=WAL")
        
        # Set busy timeout to 5 seconds (prevents immediate SQLITE_BUSY errors)
        await db.execute("PRAGMA busy_timeout=5000")
        
        # Optimize for local development (faster writes, acceptable risk for local-only tool)
        await db.execute("PRAGMA synchronous=NORMAL")
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_text TEXT,
                response_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS saved_optimizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_cost FLOAT,
                new_cost FLOAT,
                query_text TEXT,
                optimization_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS saved_connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                host TEXT NOT NULL,
                port TEXT NOT NULL,
                database TEXT NOT NULL,
                username TEXT NOT NULL,
                password_encrypted TEXT NOT NULL,
                ssl BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMP
            )
        """)
        # Add unique constraint on connection credentials (host, port, database, username)
        # This prevents duplicate connections while allowing same DB with different users
        await db.execute("""
            CREATE TABLE IF NOT EXISTS benchmark_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scenario_id TEXT,
                query_text TEXT,
                prompt TEXT,
                raw_response TEXT,
                actual_category TEXT,
                expected_category TEXT,
                actual_sql TEXT,
                alignment_score FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS health_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt_tokens INTEGER NOT NULL,
                completion_tokens INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS index_decommission (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                database_name TEXT NOT NULL,
                schema_name TEXT NOT NULL,
                table_name TEXT NOT NULL,
                index_name TEXT NOT NULL,
                stage TEXT NOT NULL DEFAULT 'monitoring',
                usefulness_score FLOAT NOT NULL DEFAULT 0,
                idx_scan_at_start INTEGER NOT NULL DEFAULT 0,
                idx_scan_latest INTEGER NOT NULL DEFAULT 0,
                size_bytes INTEGER NOT NULL DEFAULT 0,
                write_overhead_ratio FLOAT NOT NULL DEFAULT 0,
                scan_rate_per_day FLOAT NOT NULL DEFAULT 0,
                is_constraint INTEGER NOT NULL DEFAULT 0,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                stage_changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                UNIQUE(database_name, schema_name, index_name)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS index_decommission_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decommission_id INTEGER NOT NULL,
                idx_scan INTEGER NOT NULL DEFAULT 0,
                snapshot_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (decommission_id) REFERENCES index_decommission(id) ON DELETE CASCADE
            )
        """)
        await db.commit()
    logger.info(f"Initialized SQLite database at {DB_PATH} with WAL mode enabled")

async def get_setting(key: str) -> Optional[Any]:
    """Get a setting value by key."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            if row:
                try:
                    return json.loads(row[0])
                except json.JSONDecodeError:
                    return row[0]
            return None

async def set_setting(key: str, value: Any):
    """Set a setting value."""
    json_value = json.dumps(value)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (key, json_value)
        )
        await db.commit()

async def save_chat_message(query: str, response: str):
    """Save a chat message."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO chat_history (query_text, response_text) VALUES (?, ?)",
            (query, response)
        )
        await db.commit()

async def get_chat_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Get chat history."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM chat_history ORDER BY created_at DESC LIMIT ?", (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def save_optimization(query: str, suggestion: str, sql: Optional[str] = None, tier: str = "advisory"):
    """Save an optimization."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO saved_optimizations (query_text, optimization_text, tier, suggested_sql) VALUES (?, ?, ?, ?)",
            (query, suggestion, tier, sql)
        )
        await db.commit()

async def get_saved_optimizations() -> List[Dict[str, Any]]:
    """Get all saved optimizations."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM saved_optimizations ORDER BY created_at DESC") as cursor:
            rows = await cursor.fetchall()
            return [
                {
                    "id": str(row["id"]),
                    "query": row["query_text"],
                    "suggestion": row["optimization_text"],
                    "sql": row.get("suggested_sql"),
                    "tier": row.get("tier", "advisory"),
                    "createdAt": row["created_at"]
                }
                for row in rows
            ]

async def delete_saved_optimization(opt_id: str):
    """Delete a saved optimization."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM saved_optimizations WHERE id = ?", (opt_id,))
        await db.commit()

async def get_all_settings() -> Dict[str, Any]:
    """Get all settings as a dictionary."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT key, value FROM settings") as cursor:
            rows = await cursor.fetchall()
            result = {}
            for row in rows:
                try:
                    result[row["key"]] = json.loads(row["value"])
                except json.JSONDecodeError:
                    result[row["key"]] = row["value"]
            return result

async def set_all_settings(settings: Dict[str, Any]):
    """Set multiple settings at once."""
    for key, value in settings.items():
        await set_setting(key, value)

# Password encryption helpers
async def _get_encryption_key() -> bytes:
    """Get or generate encryption key for password storage."""
    key_setting = await get_setting('connection_encryption_key')
    if key_setting:
        return key_setting.encode()
    
    # Generate new key
    key = Fernet.generate_key()
    await set_setting('connection_encryption_key', key.decode())
    return key

async def encrypt_password(password: str) -> str:
    """Encrypt a password for storage."""
    key = await _get_encryption_key()
    f = Fernet(key)
    return f.encrypt(password.encode()).decode()

async def decrypt_password(encrypted: str) -> str:
    """Decrypt a stored password."""
    key = await _get_encryption_key()
    f = Fernet(key)
    return f.decrypt(encrypted.encode()).decode()

# Saved connections CRUD
async def find_connection_by_credentials(host: str, port: str, database: str, username: str) -> Optional[Dict[str, Any]]:
    """Find an existing connection with the same credentials."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT id, name, host, port, database, username, ssl, created_at, last_used_at
            FROM saved_connections
            WHERE host = ? AND port = ? AND database = ? AND username = ?
        """, (host, port, database, username)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "name": row["name"],
                    "host": row["host"],
                    "port": row["port"],
                    "database": row["database"],
                    "username": row["username"],
                    "ssl": bool(row["ssl"]),
                    "created_at": row["created_at"],
                    "last_used_at": row["last_used_at"]
                }
            return None

class DuplicateConnectionError(Exception):
    """Raised when attempting to save a connection with credentials that already exist."""
    def __init__(self, existing_name: str, existing_id: int):
        self.existing_name = existing_name
        self.existing_id = existing_id
        super().__init__(f"A connection with these credentials already exists: '{existing_name}'")

async def save_connection(name: str, host: str, port: str, database: str, username: str, password: str, ssl: bool = False) -> int:
    """Save a connection with encrypted password. Returns connection ID.
    
    Raises:
        DuplicateConnectionError: If a connection with the same credentials already exists.
    """
    # Check for existing connection with same credentials
    existing = await find_connection_by_credentials(host, port, database, username)
    if existing and existing["name"] != name:
        # Different name but same credentials - this is a duplicate
        raise DuplicateConnectionError(existing["name"], existing["id"])
    
    encrypted_password = await encrypt_password(password)
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO saved_connections (name, host, port, database, username, password_encrypted, ssl)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                host = excluded.host,
                port = excluded.port,
                database = excluded.database,
                username = excluded.username,
                password_encrypted = excluded.password_encrypted,
                ssl = excluded.ssl
        """, (name, host, port, database, username, encrypted_password, ssl))
        await db.commit()
        return cursor.lastrowid

async def get_saved_connections() -> List[Dict[str, Any]]:
    """Get all saved connections without decrypted passwords."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT id, name, host, port, database, username, ssl, created_at, last_used_at
            FROM saved_connections
            ORDER BY last_used_at DESC NULLS LAST, created_at DESC
        """) as cursor:
            rows = await cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "host": row["host"],
                    "port": row["port"],
                    "database": row["database"],
                    "username": row["username"],
                    "ssl": bool(row["ssl"]),
                    "created_at": row["created_at"],
                    "last_used_at": row["last_used_at"]
                }
                for row in rows
            ]

async def get_connection_with_password(connection_id: int) -> Optional[Dict[str, Any]]:
    """Get a saved connection with decrypted password."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT id, name, host, port, database, username, password_encrypted, ssl
            FROM saved_connections
            WHERE id = ?
        """, (connection_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            
            try:
                password = await decrypt_password(row["password_encrypted"])
            except Exception as e:
                logger.error(f"Failed to decrypt password for connection {connection_id}: {e}")
                return None
            
            return {
                "id": row["id"],
                "name": row["name"],
                "host": row["host"],
                "port": row["port"],
                "database": row["database"],
                "username": row["username"],
                "password": password,
                "ssl": bool(row["ssl"])
            }

async def delete_saved_connection(connection_id: int):
    """Delete a saved connection."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM saved_connections WHERE id = ?", (connection_id,))
        await db.commit()

async def update_last_used(connection_id: int):
    """Update the last_used_at timestamp for a connection."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE saved_connections
            SET last_used_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (connection_id,))
        await db.commit()

async def save_health_result(data: Dict[str, Any]):
    """Save a health scan result."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO health_results (data) VALUES (?)",
            (json.dumps(data),)
        )
        await db.commit()

async def get_latest_health_result() -> Optional[Dict[str, Any]]:
    """Get the latest health scan result."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT data FROM health_results ORDER BY created_at DESC LIMIT 1") as cursor:
            row = await cursor.fetchone()
            if row:
                return json.loads(row["data"])
            return None

async def get_health_history(limit: int = 10) -> List[Dict[str, Any]]:
    """Get historical health scan results."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT id, data, created_at FROM health_results ORDER BY created_at DESC LIMIT ?", (limit,)) as cursor:
            rows = await cursor.fetchall()
            results = []
            for row in rows:
                try:
                    data = json.loads(row["data"])
                    data["id"] = row["id"]
                    data["created_at"] = row["created_at"]
                    results.append(data)
                except:
                    continue
            return results

async def enforce_health_retention(keep_n: int = 10):
    """Delete old health results, keeping only the latest N."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Get IDs to keep
        async with db.execute("SELECT id FROM health_results ORDER BY created_at DESC LIMIT ?", (keep_n,)) as cursor:
            rows = await cursor.fetchall()
            if not rows:
                return

            # The last ID we keep is the cutoff
            oldest_id_to_keep = rows[-1][0]

            # Delete anything older (smaller ID) than that, or simply NOT IN the list
            # A cleaner way is DELETE WHERE id NOT IN (SELECT id FROM ... LIMIT N)
            # but sqlite support for LIMIT in subqueries can be tricky in older versions.
            # We'll use the ID comparison assuming auto-increment.
            await db.execute("DELETE FROM health_results WHERE id < ?", (oldest_id_to_keep,))
            await db.commit()

# Token usage tracking
async def save_token_usage(provider: str, model: str, prompt_tokens: int, completion_tokens: int, total_tokens: int):
    """Save token usage from an LLM call."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO token_usage (provider, model, prompt_tokens, completion_tokens, total_tokens)
            VALUES (?, ?, ?, ?, ?)
        """, (provider, model, prompt_tokens, completion_tokens, total_tokens))
        await db.commit()

async def get_token_usage_stats() -> Dict[str, Any]:
    """Get cumulative token usage statistics."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Total stats
        async with db.execute("""
            SELECT
                SUM(prompt_tokens) as total_prompt,
                SUM(completion_tokens) as total_completion,
                SUM(total_tokens) as total,
                COUNT(*) as call_count
            FROM token_usage
        """) as cursor:
            row = await cursor.fetchone()
            stats = {
                "total_prompt_tokens": row["total_prompt"] or 0,
                "total_completion_tokens": row["total_completion"] or 0,
                "total_tokens": row["total"] or 0,
                "total_calls": row["call_count"] or 0
            }

        # Per-provider breakdown
        async with db.execute("""
            SELECT
                provider,
                SUM(total_tokens) as tokens,
                COUNT(*) as calls
            FROM token_usage
            GROUP BY provider
        """) as cursor:
            rows = await cursor.fetchall()
            stats["by_provider"] = {row["provider"]: {"tokens": row["tokens"], "calls": row["calls"]} for row in rows}

        # Recent calls (last 10)
        async with db.execute("""
            SELECT provider, model, prompt_tokens, completion_tokens, total_tokens, created_at
            FROM token_usage
            ORDER BY created_at DESC
            LIMIT 10
        """) as cursor:
            rows = await cursor.fetchall()
            stats["recent_calls"] = [dict(row) for row in rows]

        return stats

async def reset_token_usage():
    """Clear all token usage records."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM token_usage")
        await db.commit()


# ── Index Decommission Tracking ──────────────────────────────────────────────

async def save_decommission_entry(entry: Dict[str, Any]):
    """Create or update an index decommission tracking entry."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO index_decommission (
                database_name, schema_name, table_name, index_name,
                stage, usefulness_score, idx_scan_at_start, idx_scan_latest,
                size_bytes, write_overhead_ratio, scan_rate_per_day,
                is_constraint, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(database_name, schema_name, index_name) DO UPDATE SET
                usefulness_score = excluded.usefulness_score,
                idx_scan_latest = excluded.idx_scan_latest,
                size_bytes = excluded.size_bytes,
                write_overhead_ratio = excluded.write_overhead_ratio,
                scan_rate_per_day = excluded.scan_rate_per_day
        """, (
            entry['database_name'], entry['schema_name'], entry['table_name'],
            entry['index_name'], entry.get('stage', 'monitoring'),
            entry.get('usefulness_score', 0), entry.get('idx_scan_at_start', 0),
            entry.get('idx_scan_latest', 0), entry.get('size_bytes', 0),
            entry.get('write_overhead_ratio', 0), entry.get('scan_rate_per_day', 0),
            entry.get('is_constraint', 0), entry.get('notes', '')
        ))
        await db.commit()


async def update_decommission_stage(decommission_id: int, new_stage: str, notes: str = ""):
    """Advance or revert a decommission entry to a new stage."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE index_decommission
            SET stage = ?, stage_changed_at = CURRENT_TIMESTAMP, notes = COALESCE(NULLIF(?, ''), notes)
            WHERE id = ?
        """, (new_stage, notes, decommission_id))
        await db.commit()


async def save_decommission_snapshot(decommission_id: int, idx_scan: int):
    """Record a point-in-time scan count snapshot for monitoring."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO index_decommission_snapshots (decommission_id, idx_scan)
            VALUES (?, ?)
        """, (decommission_id, idx_scan))
        await db.commit()


async def get_decommission_entries(database_name: str = None) -> List[Dict[str, Any]]:
    """Get all decommission tracking entries, optionally filtered by database."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if database_name:
            async with db.execute(
                "SELECT * FROM index_decommission WHERE database_name = ? ORDER BY usefulness_score ASC",
                (database_name,)
            ) as cursor:
                rows = await cursor.fetchall()
        else:
            async with db.execute(
                "SELECT * FROM index_decommission ORDER BY usefulness_score ASC"
            ) as cursor:
                rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_decommission_snapshots(decommission_id: int) -> List[Dict[str, Any]]:
    """Get scan count snapshots for a decommission entry."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM index_decommission_snapshots WHERE decommission_id = ? ORDER BY snapshot_at ASC",
            (decommission_id,)
        ) as cursor:
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def delete_decommission_entry(decommission_id: int):
    """Remove a decommission entry and its snapshots."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM index_decommission_snapshots WHERE decommission_id = ?", (decommission_id,))
        await db.execute("DELETE FROM index_decommission WHERE id = ?", (decommission_id,))
        await db.commit()

