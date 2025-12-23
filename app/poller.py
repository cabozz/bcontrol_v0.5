import asyncio
from datetime import datetime, UTC, timedelta

from app.db import get_pool
from app.protocol.encoder import build_payload
from app.tcp_server import send_to_client, clients  # adjust import to your layout

POLL_LOOP_SECONDS = 30  # how often we scan DB for probe targets


async def alive_poller():
    pool = get_pool()
    await asyncio.sleep(3)

    while True:
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT
                        ac.client_id,
                        ac.alive_command_id,
                        ac.alive_expected_response,
                        ac.alive_interval_seconds,
                        ac.alive_timeout_seconds,
                        c.alive_status
                    FROM allowed_clients ac
                    JOIN clients c ON c.client_id = ac.client_id
                    WHERE ac.alive_enabled = TRUE
                      AND ac.alive_command_id IS NOT NULL
                    """
                )

            now = datetime.now(UTC)

            for r in rows:
                client_id = r["client_id"]

                # Load command definition from DB
                async with pool.acquire() as conn:
                    cmd = await conn.fetchrow(
                        """
                        SELECT id, name, payload, encoding, append_null, append_cr, append_lf, admin_only, enabled
                        FROM tcp_commands
                        WHERE id = $1 AND enabled = TRUE
                        """,
                        r["alive_command_id"],
                    )

                if not cmd:
                    continue

                payload_bytes = build_payload(dict(cmd))

                # Try sending probe
                try:
                    await send_to_client(client_id, payload_bytes)

                    async with pool.acquire() as conn:
                        await conn.execute(
                            """
                            UPDATE clients
                            SET alive_status = 'pending'
                            WHERE client_id = $1
                            """,
                            client_id,
                        )

                except Exception as e:
                    async with pool.acquire() as conn:
                        await conn.execute(
                            """
                            UPDATE clients
                            SET alive_status = 'disconnected'
                            WHERE client_id = $1
                            """,
                            client_id,

                        )

        except Exception as outer:
            print(f"[ALIVE POLLER] loop error: {outer}")

        await asyncio.sleep(POLL_LOOP_SECONDS)
