# -*- coding: utf-8 -*-
import os
import time
import secrets

# Suppress oauthlib scope change warning (Google returns scopes in different format)
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google_auth_oauthlib.flow import Flow
from sqlalchemy.orm import Session

from server.config import Settings
from server.database import get_db
from server.models import User
from server.auth.jwt import create_access_token

router = APIRouter(prefix="/auth", tags=["authentication"])
settings = Settings()

# CSRF state store: state -> (timestamp, redirect_port)
_pending_states: dict[str, tuple[float, int | None]] = {}
_STATE_TTL = 300  # 5 minutes


def _cleanup_stale_states():
    now = time.time()
    expired = [s for s, (ts, _) in _pending_states.items() if now - ts > _STATE_TTL]
    for s in expired:
        del _pending_states[s]


def _create_flow(redirect_uri: str | None = None) -> Flow:
    return Flow.from_client_config(
        client_config={
            "web": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=["openid", "email", "profile"],
        redirect_uri=redirect_uri or settings.google_redirect_uri,
    )


@router.get("/login")
async def login(redirect_port: int | None = None):
    """Initiate Google OAuth flow. Optional redirect_port for CLI callback."""
    _cleanup_stale_states()

    state = secrets.token_urlsafe(32)
    _pending_states[state] = (time.time(), redirect_port)

    flow = _create_flow()
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        state=state,
        prompt="consent",
    )
    return RedirectResponse(url=authorization_url)


@router.get("/callback")
async def callback(request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth callback."""
    state = request.query_params.get("state")
    if not state or state not in _pending_states:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    timestamp, redirect_port = _pending_states.pop(state)

    if time.time() - timestamp > _STATE_TTL:
        raise HTTPException(status_code=400, detail="State expired")

    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    flow = _create_flow()
    flow.fetch_token(code=code)

    credentials = flow.credentials
    id_info = id_token.verify_oauth2_token(
        credentials.id_token,
        google_requests.Request(),
        settings.google_client_id,
    )

    google_id = id_info["sub"]
    email = id_info["email"]
    name = id_info.get("name", email)

    # Upsert user
    user = db.query(User).filter(User.google_id == google_id).first()
    if not user:
        user = User(
            google_id=google_id,
            email=email,
            name=name,
            queries_remaining=settings.default_query_quota,
        )
        db.add(user)
    else:
        user.name = name
        user.email = email
    db.commit()
    db.refresh(user)

    token = create_access_token(
        user_id=user.id, email=user.email, is_admin=user.is_admin
    )

    # If CLI provided a redirect_port, redirect there with the token
    if redirect_port:
        return RedirectResponse(
            url=f"http://localhost:{redirect_port}/?token={token}"
        )

    # Otherwise show HTML page (for browser-only flow)
    html = f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head><meta charset="utf-8"><title>Ask Michal - Login</title></head>
<body style="font-family: sans-serif; text-align: center; padding: 50px; background: #f5f5f5;">
    <div style="max-width: 400px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
        <h1 style="color: #2e7d32;">&#x2705; ההתחברות הצליחה!</h1>
        <p>שלום <strong>{name}</strong></p>
        <p>ניתן לחזור לטרמינל.</p>
        <p style="font-size: 11px; color: #999; word-break: break-all; margin-top: 30px;">
            Token: <code>{token[:20]}...{token[-10:]}</code>
        </p>
    </div>
</body>
</html>"""
    return HTMLResponse(content=html)
