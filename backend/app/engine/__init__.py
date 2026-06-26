"""Engine package – re-export key symbols."""

from app.engine.state import AgentState, ConsistencyResult
from app.engine.vfs import VirtualFileSystem
from app.engine.tools import TOOL_REGISTRY, get_vfs, release_vfs

# ---------------------------------------------------------------------------
# Legacy (deprecated — retained for backward-compat reference)
# ---------------------------------------------------------------------------
from app.engine.sse import translate_stream  # noqa: F401

# ---------------------------------------------------------------------------
# New workflow engine (preferred)
# ---------------------------------------------------------------------------
from app.engine.workflow import (  # noqa: F401
    Graph,
    GraphEngine,
    GraphRuntimeState,
    VariablePool,
    node_factory,
)
from app.engine.workflow.sse import translate_stream as translate_stream_v2  # noqa: F401
