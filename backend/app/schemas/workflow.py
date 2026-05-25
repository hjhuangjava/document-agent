"""Pydantic schemas for workflow API (v3 Node Schema)."""

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Node schemas – mirrors the v3 Node Schema
# ---------------------------------------------------------------------------

class AgentConfig(BaseModel):
    system_prompt: str
    tool_names: list[str]
    llm_params: dict | None = None
    max_iterations: int = 10


class ToolConfigInputBinding(BaseModel):
    name: str
    bind: dict  # {"type": "state", "state_key": "..."} or {"type": "static", "value": ...}
    required: bool = True
    default: object = None


class ToolConfigOutputBinding(BaseModel):
    output_name: str
    state_key: str


class ToolConfig(BaseModel):
    tool_name: str
    input_bindings: list[ToolConfigInputBinding]
    output_bindings: list[ToolConfigOutputBinding] = []


class OutputBinding(BaseModel):
    output_name: str
    state_key: str


class NodeDef(BaseModel):
    id: str
    execution_mode: str  # "agent" | "tool"
    name: str = ""
    description: str = ""
    category: str = "general"
    icon: str = ""
    version: str = "1.0.0"
    agent_config: AgentConfig | None = None
    tool_config: ToolConfig | None = None
    output_bindings: list[OutputBinding] = []
    requires_approval: bool = False


# ---------------------------------------------------------------------------
# Edge schemas
# ---------------------------------------------------------------------------

class Condition(BaseModel):
    field: str
    operator: str  # eq, ne, gt, lt, gte, lte, in, contains
    value: object


class EdgeDef(BaseModel):
    id: str = ""
    source: str
    target: str
    sourceHandle: str | None = None
    targetHandle: str | None = None
    condition: Condition | None = None
    max_retries: int = 3


# ---------------------------------------------------------------------------
# Workflow top-level
# ---------------------------------------------------------------------------

class WorkflowCreate(BaseModel):
    name: str
    description: str = ""
    nodes: list[NodeDef]
    edges: list[EdgeDef]
    is_published: bool = False


class WorkflowOut(BaseModel):
    id: int
    name: str
    description: str
    nodes: str  # JSON (stored as-is from DB)
    edges: str  # JSON
    is_published: bool
    version: int

    model_config = {"from_attributes": True}


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    nodes: list[NodeDef] | None = None
    edges: list[EdgeDef] | None = None
    is_published: bool | None = None


class WorkflowRunRequest(BaseModel):
    business_context: dict
