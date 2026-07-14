from pydantic import BaseModel


class AcceptedResponse(BaseModel):
    accepted: int


class ErrorResponse(BaseModel):
    error: str
