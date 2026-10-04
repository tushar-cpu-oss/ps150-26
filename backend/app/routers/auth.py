from fastapi import APIRouter, Depends

from app.database import get_db
from app.routers.deps import get_current_user
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest, UserOut
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201,
             responses={409: {"description": "EMAIL_EXISTS"}, 422: {"description": "Validation error"}})
def register(body: RegisterRequest, db=Depends(get_db)):
    """Create an investigator account. The role is always `investigator`."""
    return auth_service.register(db, body.full_name, body.email, body.organization, body.password)


@router.post("/login", response_model=LoginResponse, responses={401: {"description": "INVALID_CREDENTIALS"}})
def login(body: LoginRequest, db=Depends(get_db)):
    """Exchange email + password for a bearer JWT."""
    return auth_service.login(db, body.email, body.password)


@router.get("/me", response_model=UserOut, responses={401: {"description": "Not authenticated"}})
def me(user: dict = Depends(get_current_user)):
    return auth_service.public_user(user)
