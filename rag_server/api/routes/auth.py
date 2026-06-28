from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
import aiosqlite
from core.auth import hash_password, verify_password, create_session_token, get_current_user
from core.config import get_settings
from core.database import get_db

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/auth/login")
async def login(req: LoginRequest):
    settings = get_settings()
    db = await get_db(settings)

    try:
        cursor = await db.execute(
            "SELECT id, password_hash, role FROM users WHERE username = ? AND is_active = 1",
            (req.username,)
        )
        user = await cursor.fetchone()

        if not user or not await verify_password(req.password, user[1]):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        user_id, _, role = user
        token = await create_session_token(user_id, db, settings.session_ttl_days)

        response = Response(
            content='{"token": "' + token + '", "username": "' + req.username + '", "role": "' + role + '"}',
            media_type="application/json"
        )
        response.set_cookie("session_token", token, httponly=True, max_age=settings.session_ttl_days*86400)
        return response
    finally:
        await db.close()


@router.post("/auth/logout")
async def logout(request: Request):
    settings = get_settings()
    db = await get_db(settings)

    try:
        user = await get_current_user(request, db)
        await db.execute("DELETE FROM sessions WHERE token = ?", (user["token"],))
        await db.commit()

        response = Response(content='{"message": "Logged out"}', media_type="application/json")
        response.delete_cookie("session_token")
        return response
    finally:
        await db.close()


@router.get("/auth/me")
async def get_me(request: Request):
    settings = get_settings()
    db = await get_db(settings)

    try:
        user = await get_current_user(request, db)
        return {"id": user["id"], "username": user["username"], "role": user["role"]}
    finally:
        await db.close()
