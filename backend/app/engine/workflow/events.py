"""Graph engine event types.

Events are yielded by nodes and processed by EventHandler / SSE translator.
"""

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Graph-level events
# ---------------------------------------------------------------------------

@dataclass
class GraphRunStartedEvent:
    pass


@dataclass
class GraphRunSucceededEvent:
    outputs: dict = field(default_factory=dict)


@dataclass
class GraphRunFailedEvent:
    error: str


@dataclass
class GraphRunPartialSucceededEvent:
    exceptions_count: int
    outputs: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Node-level events
# ---------------------------------------------------------------------------

@dataclass
class NodeRunStartedEvent:
    node_id: str
    node_name: str


@dataclass
class NodeRunSucceededEvent:
    node_id: str
    node_name: str
    outputs: dict = field(default_factory=dict)


@dataclass
class NodeRunFailedEvent:
    node_id: str
    node_name: str
    error: str


@dataclass
class NodeRunExceptionEvent:
    node_id: str
    node_name: str
    error: str
    outputs: dict = field(default_factory=dict)


@dataclass
class NodeRunStreamChunkEvent:
    node_id: str
    content: str


@dataclass
class NodeRunRetryEvent:
    node_id: str
    node_name: str


# ---------------------------------------------------------------------------
# Tool-level events
# ---------------------------------------------------------------------------

@dataclass
class ToolInvokedEvent:
    tool_name: str


@dataclass
class ToolResultEvent:
    tool_name: str
    summary: str


# ---------------------------------------------------------------------------
# Union type for dispatching
# ---------------------------------------------------------------------------

GraphEngineEvent = (
    GraphRunStartedEvent
    | GraphRunSucceededEvent
    | GraphRunFailedEvent
    | GraphRunPartialSucceededEvent
    | NodeRunStartedEvent
    | NodeRunSucceededEvent
    | NodeRunFailedEvent
    | NodeRunExceptionEvent
    | NodeRunStreamChunkEvent
    | NodeRunRetryEvent
    | ToolInvokedEvent
    | ToolResultEvent
)
