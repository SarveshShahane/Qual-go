from fastapi import Request, status
from fastapi.responses import JSONResponse


class BaseException(Exception):
    def __init__(
        self,
        message: str = "An error occurred",
        status: int = status.HTTP_400_BAD_REQUEST,
        detail: any = None,
    ):
        self.message = message
        self.status = status
        self.status_code = status
        self.detail = detail
        super().__init__(self.message)


BaseAppException = BaseException


from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError


async def base_exception_handler(request: Request, exc: BaseException) -> JSONResponse:
    content = {
        "success": False,
        "error": exc.message,
        "message": exc.message,
    }
    if exc.detail is not None:
        content["detail"] = jsonable_encoder(exc.detail)
    status_code = getattr(exc, "status", getattr(exc, "status_code", status.HTTP_400_BAD_REQUEST))
    return JSONResponse(status_code=status_code, content=content)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "error": "Invalid request payload",
            "message": "Invalid request payload",
            "detail": jsonable_encoder(exc.errors()),
        },
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Internal server error",
            "message": "Internal server error",
            "detail": str(exc),
        },
    )