from __future__ import annotations

import asyncpg
import re
from datetime import datetime, UTC

from .config import settings

db_pool: asyncpg.Pool | None = None


async def init_db_pool() -> None:
    """Create global pool and ensure tables exist."""
    global db_pool
    db_pool = await asyncpg.create_pool(settings.DATABASE_URL)
    await _init_db(db_pool)


def get_pool() -> asyncpg.Pool:
    if db_pool is None:
        raise RuntimeError("DB pool not initialized. Call init_db_pool() first.")
    return db_pool


async def _init_db(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        # Whitelist
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS allowed_clients (
                client_id   TEXT PRIMARY KEY,
                description TEXT,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )

        # Clients
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS clients (
                client_id    TEXT PRIMARY KEY,
                ip           INET,
                port         INTEGER,
                status       TEXT,
                connected_at TIMESTAMPTZ,
                last_seen    TIMESTAMPTZ
            );
            """
        )
                # Extra column for "Client Alive" status (for dashboard)
        await conn.execute(
            """
            ALTER TABLE clients
            ADD COLUMN IF NOT EXISTS alive_status TEXT;
            """
        )

        # Messages / events
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id          BIGSERIAL PRIMARY KEY,
                client_id   TEXT,
                timestamp   TIMESTAMPTZ NOT NULL DEFAULT now(),
                direction   TEXT NOT NULL,           -- 'incoming' / 'outgoing' / 'system'
                message     TEXT NOT NULL,
                remote_ip   INET,
                remote_port INTEGER
            );

            CREATE INDEX IF NOT EXISTS idx_messages_timestamp
                ON messages (timestamp DESC);
            """
        )

        # Ignored message patterns
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ignored_patterns (
                id           SERIAL PRIMARY KEY,
                pattern_type TEXT NOT NULL,  -- 'exact' | 'startswith' | 'contains' | 'regex'
                pattern      TEXT NOT NULL,
                description  TEXT,
                active       BOOLEAN NOT NULL DEFAULT TRUE
            );
            """
        )

        # Users and sessions
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('admin','operator')),
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token TEXT UNIQUE NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            expires_at TIMESTAMPTZ NOT NULL
            );
            """)
        
        # Audit logs
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
            id BIGSERIAL PRIMARY KEY,
            ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            username TEXT,
            role TEXT,

            action TEXT NOT NULL,            -- action
            client_id TEXT,                  -- target tcp client id
            client_description TEXT,         -- snapshot at time of action
            message TEXT,                    -- payload
            success BOOLEAN NOT NULL DEFAULT TRUE,
            reason TEXT,                     -- error/denied reason

            remote_ip TEXT,
            user_agent TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_audit_log_ts ON audit_log (ts DESC);
            """)
        
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS tcp_commands (
            id SERIAL PRIMARY KEY,

            name TEXT NOT NULL UNIQUE,        -- RESET, ACK, HEARTBEAT, POLL
            description TEXT,

            payload TEXT NOT NULL,            -- stored representation (ascii / hex / base64)
            encoding TEXT NOT NULL CHECK (
                encoding IN ('ascii', 'hex', 'base64')
            ),

            append_null BOOLEAN DEFAULT FALSE,
            append_cr BOOLEAN DEFAULT FALSE,
            append_lf BOOLEAN DEFAULT FALSE,

            admin_only BOOLEAN DEFAULT FALSE,
            enabled BOOLEAN DEFAULT TRUE,

            created_at TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_tcp_commands_enabled
                ON tcp_commands (enabled);
            """)
        
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS client_commands (
            client_id TEXT NOT NULL,
            command_id INTEGER NOT NULL,

            enabled BOOLEAN DEFAULT TRUE,

            PRIMARY KEY (client_id, command_id),

            FOREIGN KEY (client_id)
                REFERENCES allowed_clients (client_id)
                ON DELETE CASCADE,

            FOREIGN KEY (command_id)
                REFERENCES tcp_commands (id)
                ON DELETE CASCADE
            );""")

# ---- Shared helpers (can be reused in routes if needed) ----

async def is_client_id_allowed(client_id: str) -> bool:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT 1 FROM allowed_clients WHERE client_id = $1",
            client_id,
        )
        return row is not None


async def insert_system_message(
    client_id: str,
    message: str,
    remote_ip: str | None = None,
    remote_port: int | None = None,
) -> None:
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO messages (client_id, timestamp, direction, message, remote_ip, remote_port)
            VALUES ($1, $2, 'system', $3, $4, $5);
            """,
            client_id,
            datetime.now(UTC),
            message,
            remote_ip,
            remote_port,
        )

async def get_client_description(client_id: str) -> str | None:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT description FROM allowed_clients WHERE client_id = $1",
            client_id,
        )
        return row["description"] if row else None

async def should_ignore_message(message: str) -> bool:
    """
    Check if a message matches any active ignore pattern.
    pattern_type:
      - exact:       message == pattern
      - startswith:  message.startswith(pattern)
      - contains:    pattern in message
      - regex:       re.search(pattern, message) is not None
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT pattern_type, pattern
            FROM ignored_patterns
            WHERE active = TRUE;
            """
        )

    for r in rows:
        ptype = r["pattern_type"]
        pat = r["pattern"]

        if ptype == "exact" and message == pat:
            return True
        if ptype == "startswith" and message.startswith(pat):
            return True
        if ptype == "contains" and pat in message:
            return True
        if ptype == "regex" and re.search(pat, message):
            return True

    return False
