"""Google OAuth (ID-token flow) + app JWT sessions.

Flow: the frontend's "Sign in with Google" button yields a Google ID token
(credential). We verify it server-side against our GOOGLE_CLIENT_ID, upsert the
user, and issue our OWN short-lived JWT that the SPA sends as a Bearer token on
subsequent requests. No client secret needed for this flow.
"""

from __future__ import annotations

import os
import time

import jwt  # PyJWT
from fastapi import Depends, Header, HTTPException
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy.orm import Session

from database import get_db
import models

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
JWT_SECRET = os.getenv("SECRET_KEY", "dev-insecure-change-me")
JWT_ALG = "HS256"
JWT_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days


def verify_google_credential(credential: str) -> dict:
    """Verify a Google ID token and return its claims (sub, email, name, picture)."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="GOOGLE_CLIENT_ID not configured on the server")
    try:
        info = google_id_token.verify_oauth2_token(
            credential, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {e}")
    if info.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise HTTPException(status_code=401, detail="Wrong token issuer")
    return info


def upsert_user(db: Session, claims: dict) -> models.User:
    """Find or create the user for these Google claims."""
    sub = claims["sub"]
    user = db.query(models.User).filter(models.User.google_sub == sub).first()
    if user is None:
        user = models.User(
            google_sub=sub, email=claims.get("email"),
            name=claims.get("name"), picture=claims.get("picture"),
        )
        db.add(user)
    else:  # keep profile fresh
        user.email = claims.get("email", user.email)
        user.name = claims.get("name", user.name)
        user.picture = claims.get("picture", user.picture)
    db.commit()
    db.refresh(user)
    return user


def create_app_token(user: models.User) -> str:
    payload = {"sub": str(user.id), "email": user.email, "exp": int(time.time()) + JWT_TTL_SECONDS}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def _user_from_bearer(authorization: str | None, db: Session) -> models.User | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except Exception:  # noqa: BLE001 — expired/invalid
        return None
    return db.query(models.User).filter(models.User.id == int(payload["sub"])).first()


def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)) -> models.User:
    """Dependency for protected routes — 401 if not a valid session."""
    user = _user_from_bearer(authorization, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def get_optional_user(authorization: str = Header(None), db: Session = Depends(get_db)) -> models.User | None:
    """Dependency for routes that work anonymously but personalise when logged in."""
    return _user_from_bearer(authorization, db)
