# -*- coding: utf-8 -*-
import os
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from sqlalchemy.orm import Session

from server.auth.jwt import require_admin
from server.database import get_db
from server.models import User
from server.api.schemas import UserResponse, ReloadQuotaRequest

logger = logging.getLogger("ask-michal")

router = APIRouter(prefix="/admin", tags=["admin"])

MSG_USER_NOT_FOUND = "משתמש לא נמצא"
MSG_CANNOT_CHANGE_SELF = "לא ניתן לשנות הרשאות עצמיות"


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return db.query(User).all()


@router.post("/users/{user_id}/reload")
async def reload_quota(
    user_id: int,
    body: ReloadQuotaRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=MSG_USER_NOT_FOUND)

    user.queries_remaining += body.amount
    db.commit()

    return {
        "message": f"נטענו {body.amount} שאילתות למשתמש {user.email}",
        "new_balance": user.queries_remaining,
    }


@router.post("/users/{user_id}/set-admin")
async def toggle_admin(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=MSG_USER_NOT_FOUND)

    if user.id == admin.id:
        raise HTTPException(status_code=400, detail=MSG_CANNOT_CHANGE_SELF)

    user.is_admin = not user.is_admin
    db.commit()

    return {
        "message": f"הרשאת מנהל עודכנה ל-{user.is_admin}",
        "is_admin": user.is_admin,
    }


@router.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    admin: User = Depends(require_admin),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    kb_dir = "./knowledge_base"
    os.makedirs(kb_dir, exist_ok=True)
    path = os.path.join(kb_dir, file.filename)

    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)

    return {"message": f"Uploaded {file.filename}", "size_bytes": len(content)}


@router.post("/ingest")
async def ingest_knowledge_base(
    request: Request,
    admin: User = Depends(require_admin),
):
    from server.rag.ingest import PDFIngestor
    from server.config import Settings

    settings = Settings()
    kb_dir = "./knowledge_base"

    pdfs = [f for f in os.listdir(kb_dir) if f.lower().endswith(".pdf")] if os.path.isdir(kb_dir) else []
    if not pdfs:
        raise HTTPException(status_code=404, detail="No PDF files found in knowledge_base/")

    logger.info(f"Ingesting {len(pdfs)} PDFs...")
    ingestor = PDFIngestor(settings)
    results = ingestor.ingest_directory(kb_dir)

    # Reload the engine's retriever with the new index
    request.app.state.engine.retriever._load_index()

    total = sum(results.values())
    return {
        "message": f"Ingested {total} new chunks from {len(results)} files",
        "files": results,
        "total_chunks": len(ingestor.metadata["chunks"]),
    }
