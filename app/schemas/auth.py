from pydantic import BaseModel, Field, EmailStr


class RegisterRequestPayload(BaseModel):
    username: str = Field(..., examples=["John", "Marko"], min_length=3, max_length=20)
    email: EmailStr = Field(..., examples=["john@example.com"])
    password: str = Field(..., min_length=8, max_length=72)


class LoginRequestPayload(BaseModel):
    email: EmailStr = Field(..., examples=["john@example.com"])
    password: str = Field(..., min_length=8, max_length=72)
