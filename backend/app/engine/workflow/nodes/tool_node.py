"""ToolNode – deterministic node that wraps execute_tool_node."""

from collections.abc import Generator

from app.engine.executors import execute_tool_node
from app.engine.workflow.events import (
    GraphEngineEvent,
    NodeRunSucceededEvent,
)
from app.engine.workflow.node_base import BaseNode


class ToolNode(BaseNode):
    """Wraps ``execute_tool_node`` using VariablePool for input/output."""

    def _run(self) -> Generator[GraphEngineEvent, None, None]:
        # Synchronous stub — real execution is async, handled by the engine
        pass

    async def run_async(self):
        from app.engine.workflow.events import NodeRunStartedEvent, NodeRunFailedEvent

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

    async def _run_async(self):
        tool_cfg = self.node_data["tool_config"]
        output_bindings = tool_cfg.get("output_bindings", [])
        input_bindings = tool_cfg["input_bindings"]

        pool = self.runtime_state.variable_pool
        state = pool.to_state_dict()

        result = await execute_tool_node(
            state,
            tool_name=tool_cfg["tool_name"],
            input_bindings=input_bindings,
            output_bindings=output_bindings,
        )

        yield NodeRunSucceededEvent(
            node_id=self.id,
            node_name=self.name,
            outputs=result,
        )
