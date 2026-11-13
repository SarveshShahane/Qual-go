from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config.config import settings
from app.database.sql.db import engine
from app.exceptions.base_exception import (
    BaseAppException,
    base_exception_handler,
    global_exception_handler,
    validation_exception_handler,
)
from app.exceptions.auth import (
    BaseAuthException,
    auth_exception_handler,
)
from app.routes.auth import get_csrf_token, router as auth_router
from app.routes.course import router as course_router
from app.routes.quantum import router as quantum_router
from app.routes.ai_tutor import router as ai_tutor_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        print("Database connection established")
    except Exception as e:
        print(f"Warning: Database connection could not be established on startup: {e}")
    yield

    await engine.dispose()


app = FastAPI(title="Qual-go.dev", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-CSRF-Token", "x-csrf-token"],
)

app.add_exception_handler(BaseAuthException, auth_exception_handler)
app.add_exception_handler(BaseAppException, base_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# Include routers with /api/v1 prefix (per API Documentation.docx)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(course_router, prefix="/api/v1")
app.include_router(quantum_router, prefix="/api/v1")
app.include_router(ai_tutor_router, prefix="/api/v1")

# Also include at root for direct path access & backward compatibility
app.include_router(auth_router)
app.include_router(course_router)
app.include_router(quantum_router)
app.include_router(ai_tutor_router)


@app.get("/csrf-token", status_code=200, tags=["CSRF"])
@app.get("/api/v1/csrf-token", status_code=200, tags=["CSRF"])
async def csrf_token_endpoint():
    return await get_csrf_token()


@app.get("/")
def home():
    return JSONResponse(content={"message": "Welcome to Qual-go"})