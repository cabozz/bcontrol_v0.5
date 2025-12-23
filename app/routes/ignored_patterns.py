# app/routes/ignored_patterns.py

from fastapi import APIRouter, HTTPException, Depends
from ..db import get_pool
from ..schemas import IgnorePatternModel
from ..auth_session import get_current_user
router = APIRouter(prefix="/ignored-patterns", tags=["ignored-patterns"])


@router.get("", dependencies=[Depends(get_current_user)])
async def list_ignored_patterns():
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, pattern_type, pattern, description, active
            FROM ignored_patterns
            ORDER BY id;
            """
        )
    return [
        {
            "id": r["id"],
            "pattern_type": r["pattern_type"],
            "pattern": r["pattern"],
            "description": r["description"],
            "active": r["active"],
        }
        for r in rows
    ]


@router.post("",dependencies=[Depends(get_current_user)])
async def add_ignored_pattern(data: IgnorePatternModel):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO ignored_patterns (pattern_type, pattern, description)
            VALUES ($1, $2, $3)
            RETURNING id;
            """,
            data.pattern_type,
            data.pattern,
            data.description,
        )
    return {"status": "added", "id": row["id"]}


@router.delete("/{pattern_id}", dependencies=[Depends(get_current_user)])
async def deactivate_ignored_pattern(pattern_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE ignored_patterns
            SET active = FALSE
            WHERE id = $1;
            """,
            pattern_id,
        )
        updated = int(result.split()[-1])
        if updated == 0:
            raise HTTPException(404, "pattern_id not found")
    return {"status": "deactivated", "id": pattern_id}
