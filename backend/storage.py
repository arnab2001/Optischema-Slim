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

DB_PATH = os.path.join(os.path.dirname(__file__), 'optischema.db')

async def init_db():
    """Initialize the SQLite database with required tables."""
    async with aiosqlite.connect(DB_PATH) as db:
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
        await db.commit()
    logger.info(f"Initialized SQLite database at {DB_PATH}")

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

