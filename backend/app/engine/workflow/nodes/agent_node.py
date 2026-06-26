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
        input_bindings = self.node_data.get("input_bindings", [])

        pool = self.runtime_state.variable_pool
        state = pool.to_state_dict()

        # Resolve input bindings and inject into system prompt
        from app.engine.executors import _resolve_value
        resolved_inputs: dict = {}
        for b in input_bindings:
            resolved_inputs[b["name"]] = _resolve_value(state, b)

        # Append resolved input context to system prompt
        system_prompt = agent_cfg["system_prompt"]
        if resolved_inputs:
            context_lines = [f"- {k}: {v}" for k, v in resolved_inputs.items() if v is not None]
            if context_lines:
                system_prompt += "\n\n以下是上游节点提供的输入数据：\n" + "\n".join(context_lines)

        result = await execute_agent_node(
            state,
            system_prompt=system_prompt,
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
