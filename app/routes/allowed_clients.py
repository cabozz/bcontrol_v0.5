from fastapi import APIRouter, HTTPException, Depends

from ..db import get_pool
from ..schemas import AllowedClientModel
from ..auth_session import get_current_user

router = APIRouter(prefix="/allowed-clients", tags=["allowed-clients"])


@router.get("",dependencies=[Depends(get_current_user)])
async def list_allowed_clients():
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT client_id, description, created_at
            FROM allowed_clients
            ORDER BY client_id;
            """
        )
    return [
        {
            "client_id": r["client_id"],
            "description": r["description"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


@router.post("",dependencies=[Depends(get_current_user)])
async def add_allowed_client(data: AllowedClientModel):
    pool = get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT 1 FROM allowed_clients WHERE client_id = $1",
            data.client_id,
        )
        if existing:
            raise HTTPException(409, "client_id already allowed")

        await conn.execute(
            """
            INSERT INTO allowed_clients (client_id, description)
            VALUES ($1, $2);
            """,
            data.client_id,
            data.description,
        )

    return {"status": "added", "client_id": data.client_id}


@router.delete("/{client_id}" ,dependencies=[Depends(get_current_user)])
async def remove_allowed_client(client_id: str):
    pool = get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM allowed_clients WHERE client_id = $1",
            client_id,
        )
        deleted = int(result.split()[-1])
        if deleted == 0:
            raise HTTPException(404, "client_id not found")

    return {"status": "removed", "client_id": client_id}
