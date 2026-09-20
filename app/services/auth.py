import hashlib
import uuid
from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.config import settings
from app.database.sql.models.refresh_token import RefreshToken
from app.database.sql.models.user import User as UserModel
from app.exceptions.auth import InvalidCredentialsException, UserAlreadyExistException
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

    async def logout(self, refresh_token: str | None) -> bool:
        if refresh_token:
            return await revoke_refresh_token(self.db, refresh_token)
        return False