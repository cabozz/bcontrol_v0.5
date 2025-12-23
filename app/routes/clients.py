# app/routes/clients.py

from fastapi import APIRouter, HTTPException, Request

from ..db import get_pool
from ..schemas import MessageModel
from ..tcp_server import send_to_client
from fastapi import APIRouter, Depends
from ..auth_session import require_role, get_current_user
from ..audit import write_audit
from ..protocol.encoder import build_payload
from pydantic import BaseModel

router = APIRouter(prefix="/clients", tags=["clients"])

class SendCommandModel(BaseModel):
    client_id: str
    command_id: int


@router.get("")
async def list_all_clients(depend=Depends(get_current_user)):
    """
    Return all known clients (connected or not) with their description
    (joined from allowed_clients if present).
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                c.client_id,
                c.ip,
                c.port,
                c.status,
                c.connected_at,
                c.last_seen,
                c.alive_status,
                a.description
            FROM clients c
            LEFT JOIN allowed_clients a
                ON c.client_id = a.client_id
            ORDER BY c.client_id;
            """
        )
    return [
        {
            "client_id": r["client_id"],
            "description": r["description"],
            "ip": str(r["ip"]) if r["ip"] is not None else None,
            "port": r["port"],
            "status": r["status"],
            "connected_at": r["connected_at"],
            "last_seen": r["last_seen"],
            "alive_status": r["alive_status"],
        }
        for r in rows
    ]


@router.get("/online")
async def online_clients():
    """
    Kept as-is (based on in-memory connections).
    Frontend will stop using this and derive online from /clients.
    """
    # If you still have get_online_clients in tcp_server, you can keep this using it,
    # but the frontend won't depend on this endpoint anymore.
    return []


@router.post("/send", dependencies=[Depends(require_role("admin","operator"))])
async def send_message_api(
    data: MessageModel,
    request: Request,
    user = Depends(require_role("admin", "operator"))
):
    # get description snapshot (optional but nice)
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT description FROM allowed_clients WHERE client_id = $1;",
            data.client_id
        )
    desc = row["description"] if row else None

    # classify action
    action = "SEND"
    if data.message == "~N":
        action = "RESET"
    elif data.message == "~L":
        action = "ACK"

    # admin-only RESET enforcement
    if action == "RESET" and user["role"] != "admin":
        await write_audit(
            request=request,
            action="DENIED_RESET",
            user=user,
            client_id=data.client_id,
            client_description=desc,
            message=data.message,
            success=False,
            reason="RESET is admin-only",
        )
        raise HTTPException(status_code=403, detail="RESET command is admin-only")

    # perform send
    try:
        await send_to_client(data.client_id, data.message)
        await write_audit(
            request=request,
            action=action,
            user=user,
            client_id=data.client_id,
            client_description=desc,
            message=data.message,
            success=True,
        )
        return {"status": "sent"}
    except Exception as e:
        await write_audit(
            request=request,
            action=action,
            user=user,
            client_id=data.client_id,
            client_description=desc,
            message=data.message,
            success=False,
            reason=str(e),
        )
        raise

@router.post("/send-command")
async def send_command_api(
    data: SendCommandModel,
    request: Request,
    user=Depends(require_role("admin", "operator")),
):
    pool = get_pool()

    # 1) Load command
    async with pool.acquire() as conn:
        cmd = await conn.fetchrow(
            """
            SELECT *
            FROM tcp_commands
            WHERE id = $1 AND enabled = TRUE
            """,
            data.command_id,
        )

    if not cmd:
        raise HTTPException(status_code=404, detail="Command not found or disabled")

    # 2) Permission check
    if cmd["admin_only"] and user["role"] != "admin":
        await write_audit(
            request=request,
            action="DENIED_COMMAND",
            user=user,
            client_id=data.client_id,
            message=cmd["name"],
            success=False,
            reason="admin_only",
        )
        raise HTTPException(status_code=403, detail="Admin-only command")
    
    # 2.5) Client ↔ command compatibility check
    async with pool.acquire() as conn:
        compatible = await conn.fetchval(
            """
            SELECT 1
            FROM client_commands
            WHERE client_id = $1
            AND command_id = $2
            AND enabled = TRUE
            """,
            data.client_id,
            data.command_id,
        )

    if not compatible:
        await write_audit(
            request=request,
            action="DENIED_COMMAND",
            user=user,
            client_id=data.client_id,
            message=cmd["name"],
            success=False,
            reason="command_not_supported_by_client",
        )
        raise HTTPException(
            status_code=403,
            detail="Command not supported by this client")

    # 3) Build payload bytes
    try:
        payload_bytes = build_payload(dict(cmd))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Payload error: {e}")

    # 4) Send over TCP
    try:
        await send_to_client(data.client_id, payload_bytes)
    except Exception as e:
        await write_audit(
            request=request,
            action="COMMAND_SEND_FAILED",
            user=user,
            client_id=data.client_id,
            message=cmd["name"],
            success=False,
            reason=str(e),
        )
        raise

    # 5) Audit success
    await write_audit(
        request=request,
        action="COMMAND_SENT",
        user=user,
        client_id=data.client_id,
        message=cmd["name"],
        success=True,
    )

    return {
        "status": "sent",
        "command": cmd["name"],
        "client_id": data.client_id,
    }

@router.get("/{client_id}/commands")
async def get_client_commands(
    client_id: str,
    user=Depends(require_role("admin", "operator")),
):
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT c.id, c.name, c.description, c.admin_only
            FROM tcp_commands c
            JOIN client_commands cc ON cc.command_id = c.id
            WHERE cc.client_id = $1
              AND cc.enabled = TRUE
              AND c.enabled = TRUE
              AND c.ui_visible = TRUE
            ORDER BY c.name
            """,
            client_id,
        )
    return [dict(r) for r in rows]

