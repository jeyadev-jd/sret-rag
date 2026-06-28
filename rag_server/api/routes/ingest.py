from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Request
from pathlib import Path
import uuid
from core.config import get_settings
from core.database import get_db
from core.auth import get_current_user
from workers.ingest_worker import IngestWorker

router = APIRouter()


@router.post("/api/v1/ingest/file")
async def ingest_file(
    file: UploadFile = File(...),
    request: Request = None,
    background_tasks: BackgroundTasks = None
):
    """Upload file → background ingest."""
    settings = get_settings()
    db = await get_db(settings)

    try:
        user = await get_current_user(request, db)

        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")

        file_id = str(uuid.uuid4())
        file_path = settings.uploads_dir / file.filename

        file_path.parent.mkdir(parents=True, exist_ok=True)

        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        worker = IngestWorker(settings)
        await worker.init()

        if background_tasks:
            background_tasks.add_task(worker.ingest_file, file_path)

        return {
            "file_id": file_id,
            "filename": file.filename,
            "status": "queued",
            "message": "File queued for ingestion"
        }
    finally:
        await db.close()


@router.post("/api/v1/ingest/url")
async def ingest_url(
    url: str,
    request: Request = None,
    background_tasks: BackgroundTasks = None
):
    """Fetch URL → ingest."""
    settings = get_settings()
    db = await get_db(settings)
    import httpx

    try:
        user = await get_current_user(request, db)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, timeout=30)
                response.raise_for_status()
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {str(e)}")

        file_id = str(uuid.uuid4())
        filename = url.split("/")[-1] or "document.html"
        file_path = settings.uploads_dir / filename

        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(response.content)

        worker = IngestWorker(settings)
        await worker.init()

        if background_tasks:
            background_tasks.add_task(worker.ingest_file, file_path)

        return {
            "file_id": file_id,
            "url": url,
            "status": "queued",
            "message": "URL queued for ingestion"
        }
    finally:
        await db.close()
