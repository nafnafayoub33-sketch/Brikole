"""Shapes shared by every endpoint."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ErrorOut(BaseModel):
    """The only error shape this API returns.

    `code` is machine-readable and the web app owns the wording, in all three
    languages. There is deliberately no `message` field for a human to read.
    """

    code: str
    details: dict[str, Any] | None = None


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int = Field(ge=1)
    per_page: int = Field(ge=1, le=100)

    @property
    def pages(self) -> int:
        return max(1, -(-self.total // self.per_page))
