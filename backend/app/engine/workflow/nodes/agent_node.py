"""AgentNode – LLM-driven node that wraps execute_agent_node."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from app.engine.executors import execute_agent_node
from app.engine.workflow.events import GraphEngineEvent, NodeRunSucceededEvent
from app.engine.workflow.node_base import BaseNode


class AgentNode(BaseNode):
    """Wraps ``execute_agent_node`` using VariablePool for input/output."""

    async def _run_async(self) -> AsyncGenerator[GraphEngineEvent, None]:
        agent_cfg = self.node_data["agent_config"]
        output_bindings = self.node_data.get("output_bindings", [])

        pool = self.runtime_state.variable_pool
        state = pool.to_state_dict()

        result = await execute_agent_node(
            state,
            system_prompt=agent_cfg["system_prompt"],
            tool_names=agent_cfg["tool_names"],
            vfs_session_id=pool.get_system("_vfs_session_id", ""),
            llm_params=agent_cfg.get("llm_params"),
            output_bindings=output_bindings,
        )

        # Strip internal "messages" key
        outputs = {k: v for k, v in result.items() if k != "messages"}
        yield NodeRunSucceededEvent(
            node_id=self.id,
            node_name=self.name,
            outputs=outputs,
        )
