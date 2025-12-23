from datetime import datetime, timedelta, UTC
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from pydantic import BaseModel

from ..db import get_pool
from ..audit import write_audit
from ..auth_session import (
    SESSION_COOKIE, create_session,
    verify_password, get_current_user, delete_session
)

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginModel(BaseModel):
    username: str
    password: str

@router.post("/login")
async def login(data: LoginModel, response: Response, request: Request):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, username, role, password_hash FROM users WHERE username=$1 AND active=TRUE;",
            data.username
        )

    if not row or not verify_password(data.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = await create_session(row["id"])

    # cookie-based session
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,          # LAN-only HTTP; when you move to HTTPS set True
        max_age=60 * 60 * 24
    )

    await write_audit(
        request=request,
        action="LOGIN_SUCCESS",
        user={"id": row["id"], "username": data.username, "role": row["role"]},
        success=True,
    )
    return {"ok": True}

@router.post("/logout")
async def logout(request: Request, response: Response, user=Depends(get_current_user)):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        await delete_session(token)

    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
        samesite="lax",
    )

    return {"ok": True}

@router.get("/me")
async def me(user=Depends(get_current_user)):
    return user
