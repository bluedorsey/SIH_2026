from __future__ import annotations
from typing import Generic, TypeVar
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int
    
    model_config = ConfigDict(from_attributes=True)

class ErrorResponse(BaseModel):
    error: str
    detail: str
    request_id: str | None = None
