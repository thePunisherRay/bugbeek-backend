from typing import Any
from pydantic import BaseModel, HttpUrl, Field

class ImportRequest(BaseModel):
    url: HttpUrl | None = None
    specification: dict[str, Any] | None = None
    content: str | None = None

class TestGenerationRequest(BaseModel):
    specification: dict[str, Any]

class ExecuteRequest(BaseModel):
    base_url: HttpUrl
    tests: list[dict[str, Any]] = Field(default_factory=list)

class SingleExecuteRequest(BaseModel):
    base_url: HttpUrl
    test: dict[str, Any]
