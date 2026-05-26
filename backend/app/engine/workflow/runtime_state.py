"""GraphRuntimeState – execution-scoped state wrapper around VariablePool."""

from __future__ import annotations

from app.engine.workflow.variable_pool import VariablePool


class GraphRuntimeState:
    """Holds a VariablePool + per-run metadata.

    One instance per workflow execution.
    """

    def __init__(
        self,
        variable_pool: VariablePool | None = None,
    ):
        self.variable_pool = variable_pool or VariablePool()
        self.exception_count: int = 0
        self.failed_node_ids: list[str] = []
