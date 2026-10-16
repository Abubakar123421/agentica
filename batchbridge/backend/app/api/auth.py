from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import current_user
from app.models import User
from app.schemas import LoginRequest, UserView
from app.security import create_session, delete_session, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=UserView)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(func.lower(User.email) == payload.email.lower()))
    if not user or not user.active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    raw_token = create_session(db, user)
    response.set_cookie(
        "bb_session",
        raw_token,
        max_age=get_settings().session_hours * 3600,
        httponly=True,
        secure=get_settings().cookie_secure,
        samesite="lax",
        path="/",
    )
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    delete_session(db, request.cookies.get("bb_session"))
    response.delete_cookie("bb_session", path="/")


@router.get("/me", response_model=UserView)
def me(user: User = Depends(current_user)):
    return user
