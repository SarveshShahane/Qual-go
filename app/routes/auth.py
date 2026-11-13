from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.config import settings
from app.database.sql.db import get_db
from app.database.sql.models.user import User as UserModel
from app.schemas.auth import LoginRequestPayload, RegisterRequestPayload
from app.services.auth import AuthService, get_current_user
from app.services.csrf import generate_csrf_token

router = APIRouter(prefix="/auth", tags=["Auth", "auth"])


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db)


@router.get("/csrf-token", status_code=status.HTTP_200_OK)
async def get_csrf_token():
    token = generate_csrf_token()
    cookie_max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "csrf_token": token,
        },
    )
    response.set_cookie(
        key="csrf_token",
        value=token,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=cookie_max_age,
        expires=cookie_max_age,
        path="/",
    )
    response.headers["X-CSRF-Token"] = token
    return response


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequestPayload,
    auth_service: AuthService = Depends(get_auth_service),
):
    new_user = await auth_service.register(payload)
    csrf_token = generate_csrf_token()
    cookie_max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

    response = JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "success": True,
            "csrf_token": csrf_token,
            "user": {
                "id": new_user.id,
                "username": new_user.username,
                "email": new_user.email,
            },
        },
    )
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=cookie_max_age,
        expires=cookie_max_age,
        path="/",
    )
    response.headers["X-CSRF-Token"] = csrf_token
    return response


@router.post("/login", status_code=status.HTTP_200_OK)
async def login(
    payload: LoginRequestPayload,
    auth_service: AuthService = Depends(get_auth_service),
):
    access_token, refresh_token, user = await auth_service.login(payload)
    csrf_token = generate_csrf_token()

    cookie_max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "access_token": access_token,
            "token_type": "bearer",
            "csrf_token": csrf_token,
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
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=cookie_max_age,
        expires=cookie_max_age,
        path="/",
    )
    response.headers["X-CSRF-Token"] = csrf_token
    return response


async def handle_logout(
    request: Request,
    auth_service: AuthService,
) -> JSONResponse:
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
    response.delete_cookie(
        key="csrf_token",
        path="/",
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
    )
    return response


@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh_tokens(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            refresh_token = auth_header[7:].strip()

    access_token, new_refresh_token, user = await auth_service.refresh_tokens(refresh_token)
    csrf_token = generate_csrf_token()

    cookie_max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "access_token": access_token,
            "token_type": "bearer",
            "csrf_token": csrf_token,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            },
        },
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=cookie_max_age,
        expires=cookie_max_age,
        path="/",
    )
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=cookie_max_age,
        expires=cookie_max_age,
        path="/",
    )
    response.headers["X-CSRF-Token"] = csrf_token
    return response


@router.get("/me", status_code=status.HTTP_200_OK)
async def get_current_user_profile(
    current_user: UserModel = Depends(get_current_user),
):
    csrf_token = generate_csrf_token()
    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "user": {
                "id": current_user.id,
                "username": current_user.username,
                "email": current_user.email,
            },
            "csrf_token": csrf_token,
        },
    )
    response.headers["X-CSRF-Token"] = csrf_token
    return response


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout_post(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    return await handle_logout(request, auth_service)


@router.get("/logout", status_code=status.HTTP_200_OK)
async def logout_get(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    return await handle_logout(request, auth_service)