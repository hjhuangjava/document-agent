"""BaseNode – abstract base for all workflow node implementations.

Subclasses implement ``_run_async()`` with the node's business logic
(yielding domain events such as ``NodeRunSucceededEvent``).  The standard
lifecycle (started/failed) is emitted by ``run_async()`` in this base class
so subclasses never duplicate that boilerplate.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

from app.engine.workflow.events import (
    GraphEngineEvent,
    NodeRunFailedEvent,
    NodeRunStartedEvent,
)
from app.engine.workflow.runtime_state import GraphRuntimeState


class BaseNode(ABC):
    def __init__(self, node_data: dict, runtime_state: GraphRuntimeState):
        self.id: str = node_data["id"]
        self.node_data: dict = node_data
        self.name: str = node_data.get("name", self.id)
        self.runtime_state: GraphRuntimeState = runtime_state

    @abstractmethod
    async def _run_async(self) -> AsyncGenerator[GraphEngineEvent, None]:
        """Subclass business logic.

        Must yield at least one ``NodeRunSucceededEvent`` on success.  May
        also yield streaming chunks, tool events, etc.  Exceptions raised
        here are caught by ``run_async()`` and converted to
        ``NodeRunFailedEvent``.
        """
        ...
        # The following yield is unreachable but tells the type checker this
        # is an async generator (required for AsyncGenerator return typing).
        if False:  # pragma: no cover
            yield  # type: ignore[unreachable]

    async def run_async(self) -> AsyncGenerator[GraphEngineEvent, None]:
        """Standard lifecycle wrapper – the only entry point the engine calls."""
        yield NodeRunStartedEvent(node_id=self.id, node_name=self.name)
        try:
            async for event in self._run_async():
                yield event
        except Exception as e:
            yield NodeRunFailedEvent(
                node_id=self.id,
                node_name=self.name,
                error=str(e),
            )
