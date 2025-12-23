from typing import Optional
from fastapi import Request
from .db import get_pool

async def write_audit(
    *,
    request: Request,
    action: str,
    user: Optional[dict],
    client_id: Optional[str] = None,
    client_description: Optional[str] = None,
    message: Optional[str] = None,
    success: bool = True,
    reason: Optional[str] = None,
):
    pool = get_pool()
    remote_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO audit_log
              (user_id, username, role, action, client_id, client_description, message, success, reason, remote_ip, user_agent)
            VALUES
              ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11);
            """,
            user["id"] if user else None,
            user["username"] if user else None,
            user["role"] if user else None,
            action,
            client_id,
            client_description,
            message,
            success,
            reason,
            remote_ip,
            user_agent,
        )
