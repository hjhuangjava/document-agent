"""Workflow engine state definition (v3)."""

from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class ConsistencyResult(TypedDict):
    status: Literal["pass", "fail"]
    violations: list[str]


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    business_context: dict
    data_query_result: str
    draft_content: str
    consistency_report: ConsistencyResult
    vfs_artifacts: list[str]
    _vfs_session_id: str
    _meta: dict  # dynamic metadata e.g. retry counters
