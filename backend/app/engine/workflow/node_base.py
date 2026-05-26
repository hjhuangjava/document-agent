"""BaseNode – abstract base for all workflow node implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Generator

from app.engine.workflow.events import (
    NodeRunFailedEvent,
    NodeRunStartedEvent,
    GraphEngineEvent,
)
from app.engine.workflow.runtime_state import GraphRuntimeState


class BaseNode(ABC):
    def __init__(self, node_data: dict, runtime_state: GraphRuntimeState):
        self.id: str = node_data["id"]
        self.node_data: dict = node_data
        self.name: str = node_data.get("name", self.id)
        self.runtime_state: GraphRuntimeState = runtime_state

    @abstractmethod
    def _run(self) -> Generator[GraphEngineEvent, None, None]:
        """Yields node-level events during execution.

        Subclasses must implement this to yield:
        - ``NodeRunStreamChunkEvent`` for streamed text
        - ``NodeRunSucceededEvent`` with outputs on success
        """
        ...

    def run(self) -> Generator[GraphEngineEvent, None, None]:
        """Execute the node with standard lifecycle events."""
        yield NodeRunStartedEvent(node_id=self.id, node_name=self.name)
        try:
            yield from self._run()
        except Exception as e:
            yield NodeRunFailedEvent(
                node_id=self.id,
                node_name=self.name,
                error=str(e),
            )
