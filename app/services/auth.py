import hashlib
import uuid
from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.config import settings
from app.database.sql.db import get_db
from app.database.sql.models.refresh_token import RefreshToken
from app.database.sql.models.user import User as UserModel
from app.exceptions.auth import (
    InvalidCredentialsException,
    UserAlreadyExistException,
    UserNotFoundException,
)
from app.schemas.auth import LoginRequestPayload, RegisterRequestPayload


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(user_id: int, email: str) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "user_id": user_id,
        "email": email,
        "iat": now,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> tuple[str, str, datetime]:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    jti = str(uuid.uuid4())
    payload = {
        "user_id": user_id,
        "jti": jti,
        "iat": now,
        "exp": expire,
        "type": "refresh",
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti, expire


async def revoke_refresh_token(db: AsyncSession, token: str) -> bool:
    token_hash = hash_token(token)
    stmt = select(RefreshToken).where(
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked_at.is_(None),
    )
    result = await db.execute(stmt)
    db_token = result.scalar_one_or_none()
    if db_token:
        db_token.revoked_at = datetime.now(timezone.utc)
        await db.commit()
        return True
    return False


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, payload: RegisterRequestPayload) -> UserModel:
        stmt = select(UserModel).where(UserModel.email == payload.email)
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none() is not None:
            raise UserAlreadyExistException()

        hashed_password = hash_password(payload.password)
        new_user = UserModel(
            username=payload.username,
            email=payload.email,
            password=hashed_password,
        )

        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)
        return new_user

    async def login(self, payload: LoginRequestPayload) -> tuple[str, str, UserModel]:
        stmt = select(UserModel).where(UserModel.email == payload.email)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            raise InvalidCredentialsException()

        if not verify_password(payload.password, user.password):
            raise InvalidCredentialsException()

        access_token = create_access_token(user_id=user.id, email=user.email)
        refresh_token, jti, expires_at = create_refresh_token(user_id=user.id)

        token_hash = hash_token(refresh_token)
        db_refresh_token = RefreshToken(
            user_id=user.id,
            jti=jti,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(db_refresh_token)
        await self.db.commit()

        return access_token, refresh_token, user

    async def refresh_tokens(self, refresh_token: str | None) -> tuple[str, str, UserModel]:
        if not refresh_token:
            raise InvalidCredentialsException(message="Missing refresh token")

        try:
            payload = jwt.decode(
                refresh_token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            if payload.get("type") != "refresh":
                raise InvalidCredentialsException(message="Invalid token type")
            user_id = payload.get("user_id")
            if not user_id:
                raise InvalidCredentialsException(message="Invalid token payload")
        except jwt.PyJWTError:
            raise InvalidCredentialsException(message="Invalid or expired refresh token")

        token_hash = hash_token(refresh_token)
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
        )
        result = await self.db.execute(stmt)
        db_token = result.scalar_one_or_none()
        if db_token is None:
            raise InvalidCredentialsException(message="Refresh token revoked or not found")

        expires_at = db_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise InvalidCredentialsException(message="Refresh token expired")

        user_stmt = select(UserModel).where(UserModel.id == user_id)
        user_result = await self.db.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        if user is None:
            raise UserNotFoundException(message="User not found")

        # Token rotation: revoke old token and issue new pair
        db_token.revoked_at = datetime.now(timezone.utc)

        new_access_token = create_access_token(user_id=user.id, email=user.email)
        new_refresh_token, new_jti, new_expires_at = create_refresh_token(user_id=user.id)

        new_db_token = RefreshToken(
            user_id=user.id,
            jti=new_jti,
            token_hash=hash_token(new_refresh_token),
            expires_at=new_expires_at,
        )
        self.db.add(new_db_token)
        await self.db.commit()

        return new_access_token, new_refresh_token, user

    async def logout(self, refresh_token: str | None) -> bool:
        if refresh_token:
            return await revoke_refresh_token(self.db, refresh_token)
        return False


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> UserModel:
    auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise InvalidCredentialsException(message="Missing or invalid Authorization header")

    token = auth_header[7:].strip()
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != "access":
            raise InvalidCredentialsException(message="Invalid token type")
        user_id = payload.get("user_id")
        if not user_id:
            raise InvalidCredentialsException(message="Invalid token payload")
    except jwt.PyJWTError:
        raise InvalidCredentialsException(message="Invalid or expired access token")

    stmt = select(UserModel).where(UserModel.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise UserNotFoundException(message="User not found")
    return user