from fastapi import Request, status
from fastapi.responses import JSONResponse
from app.exceptions.base_exception import BaseException, BaseAppException


class BaseAuthException(BaseException):
    def __init__(
        self,
        message: str = "Authentication error",
        status: int = status.HTTP_400_BAD_REQUEST,
        detail: any = None,
    ):
        super().__init__(message=message, status=status, detail=detail)


class UserAlreadyExistException(BaseAuthException):
    def __init__(
        self,
        message: str = "User with this email already exists",
        detail: any = None,
    ):
        super().__init__(
            message=message,
            status=status.HTTP_409_CONFLICT,
            detail=detail,
        )


class InvalidCredentialsException(BaseAuthException):
    def __init__(
        self,
        message: str = "Invalid email or password",
        detail: any = None,
    ):
        super().__init__(
            message=message,
            status=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )


class UserNotFoundException(BaseAuthException):
    def __init__(
        self,
        message: str = "User not found",
        detail: any = None,
    ):
        super().__init__(
            message=message,
            status=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


class CSRFValidationException(BaseAuthException):
    def __init__(
        self,
        message: str = "Invalid or missing CSRF token",
        detail: any = None,
    ):
        super().__init__(
            message=message,
            status=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


async def auth_exception_handler(request: Request, exc: BaseAuthException) -> JSONResponse:
    content = {
        "success": False,
        "error": exc.message,
        "message": exc.message,
    }
    if exc.detail is not None:
        content["detail"] = exc.detail
    status_code = getattr(exc, "status", getattr(exc, "status_code", status.HTTP_400_BAD_REQUEST))
    return JSONResponse(status_code=status_code, content=content)