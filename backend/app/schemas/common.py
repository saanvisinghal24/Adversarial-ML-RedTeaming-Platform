from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Every non-2xx response from this API has this shape."""

    detail: str = Field(..., examples=["model not found"])


class HealthResponse(BaseModel):
    status: str = Field(..., examples=["ok"])
    environment: str
    database: str = Field(..., description="'up' or 'down' — result of a SELECT 1")
    version: str
