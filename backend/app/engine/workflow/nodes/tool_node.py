"""ToolNode – deterministic node that wraps execute_tool_node."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from app.engine.executors import execute_tool_node
from app.engine.workflow.events import GraphEngineEvent, NodeRunSucceededEvent
from app.engine.workflow.node_base import BaseNode


class ToolNode(BaseNode):
    """Wraps ``execute_tool_node`` using VariablePool for input/output."""

    async def _run_async(self) -> AsyncGenerator[GraphEngineEvent, None]:
        tool_cfg = self.node_data["tool_config"]
        output_bindings = tool_cfg.get("output_bindings", [])
        input_bindings = tool_cfg["input_bindings"]

        pool = self.runtime_state.variable_pool
        state = pool.to_state_dict()

        # Resolve and print parameters for debugging
        from app.engine.executors import _resolve_value
        resolved_debug: dict = {}
        for b in input_bindings:
            resolved_debug[b["name"]] = _resolve_value(state, b)
        print(f"[ToolNode] node={self.id} name={self.name} tool={tool_cfg['tool_name']} resolved_params={resolved_debug}")

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
