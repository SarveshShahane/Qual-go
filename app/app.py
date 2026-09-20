from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.database.sql.db import engine
from app.exceptions.base_exception import (
    BaseAppException,
    base_exception_handler,
    global_exception_handler,
)
from app.exceptions.auth import (
    BaseAuthException,
    auth_exception_handler,
)
from app.routes.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    print("Connection established")
    yield

    await engine.dispose()


app = FastAPI(title="Qual-go.dev", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(BaseAuthException, auth_exception_handler)
app.add_exception_handler(BaseAppException, base_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

app.include_router(auth_router)


@app.get("/")
def home():
    return JSONResponse(content="Welcome to Qual-go")