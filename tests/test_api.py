# -*- coding: utf-8 -*-
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from pydantic import ValidationError

from server.auth.jwt import create_access_token, decode_token
from server.api.schemas import RateRequest, AskResponse


class TestJWT:
    def test_create_and_decode_token(self):
        token = create_access_token(user_id=1, email="test@example.com", is_admin=False)
        payload = decode_token(token)

        assert payload["sub"] == "1"
        assert payload["email"] == "test@example.com"
        assert payload["is_admin"] is False

    def test_admin_flag_in_token(self):
        token = create_access_token(user_id=2, email="admin@example.com", is_admin=True)
        payload = decode_token(token)

        assert payload["is_admin"] is True

    def test_invalid_token_raises(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            decode_token("invalid.token.here")
        assert exc_info.value.status_code == 401


class TestRateRequest:
    def test_valid_rating(self):
        req = RateRequest(query_id=1, rating=3)
        assert req.rating == 3
        assert req.comment is None

    def test_valid_rating_with_comment(self):
        req = RateRequest(query_id=1, rating=5, comment="Great answer!")
        assert req.rating == 5
        assert req.comment == "Great answer!"

    def test_rating_below_range(self):
        with pytest.raises(ValidationError):
            RateRequest(query_id=1, rating=0)

    def test_rating_above_range(self):
        with pytest.raises(ValidationError):
            RateRequest(query_id=1, rating=6)

    def test_optional_comment_is_none(self):
        req = RateRequest(query_id=1, rating=2)
        assert req.comment is None


class TestAskResponse:
    def test_includes_query_id(self):
        resp = AskResponse(
            answer="test",
            sources=["src1"],
            queries_remaining=10,
            query_id=42,
        )
        assert resp.query_id == 42
