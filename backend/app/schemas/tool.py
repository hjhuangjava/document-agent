"""Pydantic schemas for tool API."""

from pydantic import BaseModel


class ToolOut(BaseModel):
    name: str
    description: str
    category: str
    component_type: str
    inputs: str  # JSON string (stored as-is from DB)
    outputs: str  # JSON string
    enabled: bool

    model_config = {"from_attributes": True}


class ToolPatch(BaseModel):
    """Only mutable fields – description and enabled flag."""
    description: str | None = None
    enabled: bool | None = None
