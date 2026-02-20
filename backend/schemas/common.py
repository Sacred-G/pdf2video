"""Shared Pydantic schemas."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict | None = None


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
