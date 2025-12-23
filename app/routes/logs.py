from fastapi import APIRouter, Depends

from ..db import get_pool, should_ignore_message
from ..auth_session import get_current_user

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("", dependencies=[Depends(get_current_user)])
async def get_logs(limit: int = 10):
    """
    Return up to `limit` messages that are NOT matched by ignored_patterns.
    All messages are still stored in DB; filtering is only for the dashboard.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        # Fetch more than we need, because some will be ignored
        inner_limit = max(limit * 5, 100)
        rows = await conn.fetch(
            """
            SELECT
                m.client_id,
                a.description,
                m.direction,
                m.message,
                m.timestamp,
                m.remote_ip,
                m.remote_port
            FROM messages m
            LEFT JOIN allowed_clients a
                ON m.client_id = a.client_id
            WHERE m.direction = 'incoming' AND m.message NOT IN ('#NFS640.027.001', 'SERIAL NUMBER = 0010365116','- ')
            ORDER BY m.timestamp DESC
            LIMIT $1;
            """,
            inner_limit,
        )

    result = []
    for r in rows:
        msg = r["message"] or ""
        # 🔥 Filter only for dashboard
        if await should_ignore_message(msg):
            continue

        result.append(
            {
                "client_id": r["client_id"],
                "description": r["description"],
                "direction": r["direction"],
                "message": r["message"],
                "timestamp": r["timestamp"],
                "remote_ip": r["remote_ip"],
                "remote_port": r["remote_port"],
            }
        )
        if len(result) >= limit:
            break

    return result
