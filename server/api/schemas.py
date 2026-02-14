# -*- coding: utf-8 -*-
from datetime import datetime

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=2000)


class AskResponse(BaseModel):
    answer: str
    sources: list[str]
    queries_remaining: int
    query_id: int


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


class RateRequest(BaseModel):
    query_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = None


class RateResponse(BaseModel):
    message: str
    queries_remaining: int


class RatingItem(BaseModel):
    query_id: int
    user_email: str
    user_name: str
    rating: int
    comment: str | None
    rated_at: datetime | None
    created_at: datetime | None

    model_config = {"from_attributes": True}


class RatingsListResponse(BaseModel):
    ratings: list[RatingItem]
    total: int


class ReloadQuotaRequest(BaseModel):
    amount: int = Field(..., gt=0, le=1000)
