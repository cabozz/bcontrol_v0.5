from pydantic import BaseModel
from typing import Literal

class MessageModel(BaseModel):
    client_id: str
    message: str


class AllowedClientModel(BaseModel):
    client_id: str
    description: str | None = None


class IgnorePatternModel(BaseModel):
    pattern_type: Literal["exact", "startswith", "contains", "regex"]
    pattern: str
    description: str | None = None