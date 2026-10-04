from datetime import datetime

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=5, max_length=200)
    organization: str = Field(default="", max_length=200)
    password: str = Field(min_length=8, max_length=200)


class LoginRequest(BaseModel):
    email: str = Field(max_length=200)
    password: str = Field(max_length=200)


class UserOut(BaseModel):
    user_id: str
    full_name: str
    email: str
    organization: str = ""
    role: str
    created_at: datetime
    updated_at: datetime


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
