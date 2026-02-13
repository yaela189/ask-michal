# -*- coding: utf-8 -*-
import hashlib

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from server.auth.jwt import get_current_user
from server.database import get_db
from server.models import User, QueryLog
from server.api.schemas import AskRequest, AskResponse, QuotaResponse

router = APIRouter(prefix="/api", tags=["api"])

MSG_QUOTA_EXHAUSTED = "מכסת השאלות שלך נגמרה. פנה/י למנהל המערכת לטעינה מחדש."
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

        return AskResponse(
            answer=result["answer"],
            sources=result["sources"],
            queries_remaining=user.queries_remaining,
        )
    except Exception:
        # Restore quota on failure
        user.queries_remaining += 1
        db.commit()
        raise HTTPException(status_code=500, detail=MSG_INTERNAL_ERROR)


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
