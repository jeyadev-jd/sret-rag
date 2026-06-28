from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from core.auth import hash_password, require_admin
from core.config import get_settings
from core.database import get_db

router = APIRouter()


class UserCreateRequest(BaseModel):
    username: str
    password: str
    role: str = "user"


class UserUpdateRequest(BaseModel):
    username: str = None
    password: str = None
    role: str = None
    is_active: bool = None


@router.get("/admin/users")
async def list_users(request: Request):
    settings = get_settings()
    db = await get_db(settings)

    try:
        await require_admin(request, db)

        cursor = await db.execute(
            "SELECT id, username, role, is_active, created_at FROM users"
        )
        users = await cursor.fetchall()
        return [
            {
                "id": u[0],
                "username": u[1],
                "role": u[2],
                "is_active": bool(u[3]),
                "created_at": u[4]
            }
            for u in users
        ]
    finally:
        await db.close()


@router.post("/admin/users")
async def create_user(req: UserCreateRequest, request: Request):
    settings = get_settings()
    db = await get_db(settings)

    try:
        await require_admin(request, db)

        pwd_hash = await hash_password(req.password)
        await db.execute(
            "INSERT INTO users (username, password_hash, role, is_active) VALUES (?, ?, ?, 1)",
            (req.username, pwd_hash, req.role)
        )
        await db.commit()

        cursor = await db.execute(
            "SELECT id FROM users WHERE username = ?",
            (req.username,)
        )
        user_id = (await cursor.fetchone())[0]
        return {"id": user_id, "username": req.username, "role": req.role}
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            raise HTTPException(status_code=400, detail="Username already exists")
        raise
    finally:
        await db.close()


@router.put("/admin/users/{user_id}")
async def update_user(user_id: int, req: UserUpdateRequest, request: Request):
    settings = get_settings()
    db = await get_db(settings)

    try:
        await require_admin(request, db)

        updates = []
        params = []

        if req.username:
            updates.append("username = ?")
            params.append(req.username)
        if req.password:
            pwd_hash = await hash_password(req.password)
            updates.append("password_hash = ?")
            params.append(pwd_hash)
        if req.role:
            updates.append("role = ?")
            params.append(req.role)
        if req.is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if req.is_active else 0)

        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        params.append(user_id)
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        await db.execute(query, params)
        await db.commit()

        return {"id": user_id, "message": "Updated"}
    finally:
        await db.close()


@router.delete("/admin/users/{user_id}")
async def deactivate_user(user_id: int, request: Request):
    settings = get_settings()
    db = await get_db(settings)

    try:
        await require_admin(request, db)

        await db.execute(
            "UPDATE users SET is_active = 0 WHERE id = ?",
            (user_id,)
        )
        await db.commit()

        return {"id": user_id, "message": "Deactivated"}
    finally:
        await db.close()
