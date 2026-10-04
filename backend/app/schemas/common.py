from typing import Annotated, Any, Optional

from pydantic import BaseModel, StringConstraints

# IDs are restricted to a safe charset; this also blocks operator-injection style input.
SafeId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,64}$")]


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorBody
