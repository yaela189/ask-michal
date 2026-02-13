# -*- coding: utf-8 -*-
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from server.auth.jwt import create_access_token, decode_token


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
