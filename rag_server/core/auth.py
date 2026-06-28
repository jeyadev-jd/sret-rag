import bcrypt
import secrets
import aiosqlite
from datetime import datetime, timedelta
from fastapi import HTTPException, Request
from core.config import Settings


async def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


async def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


async def create_session_token(user_id: int, db: aiosqlite.Connection, ttl_days: int = 7) -> str:
    token = secrets.token_hex(32)
    expires_at = (datetime.utcnow() + timedelta(days=ttl_days)).isoformat()
    await db.execute(
        "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, user_id, expires_at)
    )
    await db.commit()
    return token


async def get_current_user(request: Request, db: aiosqlite.Connection) -> dict:
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        token = request.cookies.get("session_token")

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    cursor = await db.execute(
        "SELECT u.id, u.username, u.role, s.expires_at FROM users u "
        "JOIN sessions s ON u.id = s.user_id WHERE s.token = ? AND s.expires_at > ?",
        (token, datetime.utcnow().isoformat())
    )
    row = await cursor.fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return {"id": row[0], "username": row[1], "role": row[2], "token": token}


async def require_admin(request: Request, db: aiosqlite.Connection) -> dict:
    user = await get_current_user(request, db)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
