from fastapi import FastAPI
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.database.sql.db import engine,get_db
from sqlalchemy import text


@asynccontextmanager
async def lifespan(app:FastAPI):
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        print("Connection established")
        yield
        
        await engine.dispose
 
app = FastAPI(title="Qual-go.dev",lifespan=lifespan)

@app.get("/")
def home():
    return  JSONResponse(content="Welcome to Qual-go")