"""EventHandler – dispatches events to update state, store outputs, and trigger
edge processing."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from app.engine.workflow.events import (
    GraphEngineEvent,
    NodeRunFailedEvent,
    NodeRunSucceededEvent,
    NodeRunStartedEvent,
)

if TYPE_CHECKING:
    from app.engine.workflow.edge_processor import EdgeProcessor
    from app.engine.workflow.state_manager import GraphStateManager
    from app.engine.workflow.variable_pool import VariablePool
    from app.engine.workflow.runtime_state import GraphRuntimeState


class EventHandler:
    def __init__(
        self,
        state_manager: GraphStateManager,
        variable_pool: VariablePool,
        runtime_state: GraphRuntimeState,
        edge_processor: EdgeProcessor,
    ):
        self._sm = state_manager
        self._pool = variable_pool
        self._runtime = runtime_state
        self._edge_processor = edge_processor

    def handle(self, event: GraphEngineEvent) -> None:
        """Dispatch event to the appropriate handler."""
        if isinstance(event, NodeRunStartedEvent):
            self._sm.mark_executing(event.node_id)
            self._sm.mark_node_taken(event.node_id)

        elif isinstance(event, NodeRunSucceededEvent):
            self._sm.mark_completed(event.node_id)
            # Persist outputs to VariablePool
            for key, value in event.outputs.items():
                self._pool.add(event.node_id, key, value)
            # Process outgoing edges
            self._edge_processor.process_node_success(event.node_id)

        elif isinstance(event, NodeRunFailedEvent):
            self._sm.mark_completed(event.node_id)
            self._runtime.exception_count += 1
            self._runtime.failed_node_ids.append(event.node_id)
