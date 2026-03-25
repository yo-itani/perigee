from pydantic import BaseModel


class PaginatedResponse[T](BaseModel):
    """Generic paginated response schema for list endpoints."""

    items: list[T]
    total_count: int
    offset: int
    limit: int
