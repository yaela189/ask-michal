# -*- coding: utf-8 -*-
from datetime import datetime

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=2000)


class AskResponse(BaseModel):
    answer: str
    sources: list[str]
    queries_remaining: int


class QuotaResponse(BaseModel):
    queries_remaining: int
    queries_used: int
    total_quota: int


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    queries_remaining: int
    is_admin: bool
    created_at: datetime | None
    last_login: datetime | None

    model_config = {"from_attributes": True}


class ReloadQuotaRequest(BaseModel):
    amount: int = Field(..., gt=0, le=1000)
