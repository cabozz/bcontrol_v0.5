# app/auth_session.py
import os, secrets
from datetime import datetime, timedelta, UTC
from fastapi import Depends, HTTPException, Request
from passlib.context import CryptContext

from .db import get_pool

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

SESSION_COOKIE = os.getenv("SESSION_COOKIE", "bcontrol_session")
SESSION_TTL_HOURS = int(os.getenv("SESSION_TTL_HOURS", "24"))

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)

async def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    expires = now + timedelta(hours=SESSION_TTL_HOURS)

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO sessions (user_id, token, expires_at)
            VALUES ($1, $2, $3);
            """,
            user_id, token, expires
        )
    return token

async def delete_session(token: str):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM sessions WHERE token = $1;", token)

async def get_current_user(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT u.id, u.username, u.role
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token = $1
              AND s.expires_at > NOW()
              AND u.active = TRUE;
            """,
            token
        )

    if not row:
        raise HTTPException(status_code=401, detail="Invalid/expired session")

    return {"id": row["id"], "username": row["username"], "role": row["role"]}

def require_role(*roles: str):
    async def _guard(user=Depends(get_current_user)):
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return user
    return _guard
