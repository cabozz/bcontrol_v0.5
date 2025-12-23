from __future__ import annotations

import asyncio
from datetime import datetime, UTC
from typing import Dict

from .config import settings
from .db import get_pool, is_client_id_allowed, insert_system_message, get_client_description

# In-memory registry of connected clients
clients: Dict[str, asyncio.StreamWriter] = {}   # {client_id: writer}


def get_online_clients() -> list[dict]:
    """Expose online clients to API layer."""
    return [{"client_id": cid, "status": "connected"} for cid in clients.keys()]


async def send_to_client(client_id: str, payload: bytes) -> None:
    """Used by API routes to send data to a connected TCP client."""
    if client_id not in clients:
        raise ValueError(f"Client {client_id} not connected")

    writer = clients[client_id]
    writer.write(payload)
    await writer.drain()

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO messages (client_id, timestamp, direction, message)
            VALUES ($1, $2, 'outgoing', $3);
            """,
            client_id,
            datetime.now(UTC),
            payload.decode(errors="replace"),
        )

    print(f"[{datetime.now(UTC).strftime('%H:%M:%S')}] Sent to {client_id}: {payload}")


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """Handle one TCP connection. First message = client_id."""
    pool = get_pool()
    addr = writer.get_extra_info("peername")
    ip, port = addr[0], addr[1]
    now_str = datetime.now(UTC).strftime("%H:%M:%S")

    print(f"[{now_str}] New TCP connection from {addr}")

    # 1) First message as client_id
    try:
        first_data = await reader.read(1024)
        if not first_data:
            print(f"[{now_str}] Connection closed before ID received: {addr}")
            writer.close()
            await writer.wait_closed()
            return

        client_id = first_data.decode(errors="replace").strip()

        if not client_id:
            print(f"[{now_str}] Empty client_id from {addr}, kicking client")
            writer.close()
            await writer.wait_closed()
            return

        if not await is_client_id_allowed(client_id):
            print(f"[{now_str}] UNAUTHORIZED client_id '{client_id}' from {addr}, kicking")
            await insert_system_message(
                client_id,
                "UNAUTHORIZED_CLIENT_ID",
                remote_ip=ip,
                remote_port=port,
            )
            writer.close()
            await writer.wait_closed()
            return

    except Exception as e:
        print(f"[{now_str}] Error receiving client_id from {addr}: {e}")
        writer.close()
        await writer.wait_closed()
        return

    # Fetch description for this connection
    description = await get_client_description(client_id)
    desc_label = f" - {description}" if description else ""
    print(f"[{datetime.now(UTC).strftime('%H:%M:%S')}] Client identified & allowed: {client_id}{desc_label}")

    # 2) Register client in memory and in DB
    clients[client_id] = writer

    async with pool.acquire() as conn:
        now = datetime.now(UTC)
        await conn.execute(
            """
            INSERT INTO clients (client_id, ip, port, status, connected_at, last_seen)
            VALUES ($1, $2, $3, 'connected', $4, $4)
            ON CONFLICT (client_id) DO UPDATE
            SET ip = EXCLUDED.ip,
                port = EXCLUDED.port,
                status = 'connected',
                connected_at = EXCLUDED.connected_at,
                last_seen = EXCLUDED.last_seen;
            """,
            client_id,
            ip,
            port,
            now,
        )

    # 3) Main message loop
    try:
        while True:
            data = await reader.read(1024)
            if not data:
                break
            
            data = data.replace(b'\x00', b'')  # Remove null bytes
            data = data.replace(b'\x07', b'\x53\x49\x52\x45\x4E\x41\x53\x20\x41\x43\x54\x49\x56\x41\x44\x41\x53')  # Remove null bytes
            message = data.decode(errors="replace").strip()
            if not message:
                continue                
            
            async with pool.acquire() as conn:
                expected = await conn.fetchval(
                    """
                    SELECT alive_expected_response
                    FROM allowed_clients
                    WHERE client_id = $1 AND alive_enabled = TRUE
                    """,
                    client_id,
                )

            if message.strip() == expected:
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        UPDATE clients
                        SET alive_status = 'connected'
                        WHERE client_id = $1
                        """,
                        client_id,
                    )
            else:
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO messages (client_id, timestamp, direction, message)
                        VALUES ($1, $2, 'incoming', $3);
                        """,
                        client_id,
                        datetime.now(UTC),
                        message,
                    )
            
            
                    

    except ConnectionResetError:
        print(f"[{datetime.now(UTC).strftime('%H:%M:%S')}] {client_id} disconnected forcibly")
    except Exception as e:
        print(f"[{datetime.now(UTC).strftime('%H:%M:%S')}] Error in client loop {client_id}: {e}")
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass

        clients.pop(client_id, None)

        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE clients
                SET status = 'disconnected',
                    last_seen = $2
                    alive_status = NULL
                WHERE client_id = $1;
                """,
                client_id,
                datetime.now(UTC),
            )

        print(f"[{datetime.now(UTC).strftime('%H:%M:%S')}] Client {client_id} connection closed")


async def start_tcp_server():
    server = await asyncio.start_server(
        handle_client,
        settings.TCP_HOST,
        settings.TCP_PORT,
    )
    print(
        f"[{datetime.now(UTC).strftime('%H:%M:%S')}] "
        f"TCP Server running on {settings.TCP_HOST}:{settings.TCP_PORT}"
    )
    async with server:
        await server.serve_forever()


