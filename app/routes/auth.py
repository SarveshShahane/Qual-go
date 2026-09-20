from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.config import settings
from app.database.sql.db import get_db
from app.schemas.auth import LoginRequestPayload, RegisterRequestPayload
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Auth", "auth"])


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db)


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequestPayload,
    auth_service: AuthService = Depends(get_auth_service),
):
    new_user = await auth_service.register(payload)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "success": True,
            "user": {
                "id": new_user.id,
                "username": new_user.username,
                "email": new_user.email,
            },
        },
    )


@router.post("/login", status_code=status.HTTP_200_OK)
async def login(
    payload: LoginRequestPayload,
    auth_service: AuthService = Depends(get_auth_service),
):
    access_token, refresh_token, user = await auth_service.login(payload)

    cookie_max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            },
        },
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=cookie_max_age,
        expires=cookie_max_age,
        path="/",
    )
    return response


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    refresh_token = request.cookies.get("refresh_token")
    await auth_service.logout(refresh_token)

    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "message": "Logged out successfully",
        },
    )
    response.delete_cookie(
        key="refresh_token",
        path="/",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
    )
    return response