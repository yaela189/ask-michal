# -*- coding: utf-8 -*-
import hashlib
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from sqlalchemy.orm import Session

from server.auth.jwt import get_current_user
from server.database import get_db
from server.models import User, QueryLog
from server.api.schemas import AskRequest, AskResponse, QuotaResponse, RateRequest, RateResponse

logger = logging.getLogger("ask-michal")
router = APIRouter(prefix="/api", tags=["api"])

MSG_QUOTA_EXHAUSTED = "מכסת השאלות שלך נגמרה. לקבלת שאלות נוספות פנה/י למנהל המערכת: bar@yae.la"
MSG_INTERNAL_ERROR = "שגיאה פנימית. נסה/י שנית."


@router.post("/ask", response_model=AskResponse)
async def ask_question(
    body: AskRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.queries_remaining <= 0:
        raise HTTPException(status_code=429, detail=MSG_QUOTA_EXHAUSTED)

    # Decrement quota optimistically
    user.queries_remaining -= 1
    db.commit()

    try:
        engine = request.app.state.engine
        result = engine.ask(body.question)

        # Log the query (hash only, not raw text)
        log = QueryLog(
            user_id=user.id,
            question_hash=hashlib.sha256(body.question.encode()).hexdigest(),
            tokens_used=result["tokens_used"],
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        return AskResponse(
            answer=result["answer"],
            sources=result["sources"],
            queries_remaining=user.queries_remaining,
            query_id=log.id,
        )
    except Exception:
        # Restore quota on failure
        user.queries_remaining += 1
        db.commit()
        raise HTTPException(status_code=500, detail=MSG_INTERNAL_ERROR)


@router.post("/upload-pdf")
async def upload_pdf(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="ניתן להעלות קבצי PDF בלבד")

    kb_dir = "./knowledge_base"
    os.makedirs(kb_dir, exist_ok=True)
    path = os.path.join(kb_dir, file.filename)

    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)

    # Ingest the new PDF
    try:
        from server.rag.ingest import PDFIngestor
        from server.config import Settings

        ingestor = PDFIngestor(Settings())
        chunks = ingestor.ingest_pdf(path)

        # Reload the retriever with updated index
        request.app.state.engine.retriever._load_index()

        logger.info(f"User {user.email} uploaded {file.filename}: {chunks} chunks")
        return {
            "message": f"הקובץ {file.filename} הועלה ועובד בהצלחה",
            "chunks": chunks,
        }
    except Exception as e:
        logger.error(f"Failed to ingest {file.filename}: {e}")
        raise HTTPException(status_code=500, detail="שגיאה בעיבוד הקובץ")


@router.get("/quota", response_model=QuotaResponse)
async def get_quota(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    queries_used = db.query(QueryLog).filter(QueryLog.user_id == user.id).count()
    return QuotaResponse(
        queries_remaining=user.queries_remaining,
        queries_used=queries_used,
        total_quota=queries_used + user.queries_remaining,
    )


@router.post("/rate", response_model=RateResponse)
async def rate_answer(
    body: RateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    log = db.query(QueryLog).filter(QueryLog.id == body.query_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="שאילתה לא נמצאה")

    if log.user_id != user.id:
        raise HTTPException(status_code=403, detail="אין הרשאה לדרג שאילתה זו")

    if log.rating is not None:
        raise HTTPException(status_code=409, detail="שאילתה זו כבר דורגה")

    log.rating = body.rating
    log.rating_comment = body.comment
    log.rated_at = datetime.now(timezone.utc)

    user.queries_remaining += 1
    db.commit()

    return RateResponse(
        message="תודה על הדירוג!",
        queries_remaining=user.queries_remaining,
    )
