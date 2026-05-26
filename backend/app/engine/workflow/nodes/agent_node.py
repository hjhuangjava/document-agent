"""AgentNode – LLM-driven node that wraps execute_agent_node."""

from collections.abc import Generator

from app.engine.executors import execute_agent_node
from app.engine.workflow.events import (
    GraphEngineEvent,
    NodeRunSucceededEvent,
)
from app.engine.workflow.node_base import BaseNode


class AgentNode(BaseNode):
    """Wraps ``execute_agent_node`` using VariablePool for input/output."""

    def _run(self) -> Generator[GraphEngineEvent, None, None]:
        agent_cfg = self.node_data["agent_config"]
        output_bindings = self.node_data.get("output_bindings", [])

        # Build executor-compatible state dict from VariablePool
        pool = self.runtime_state.variable_pool
        state = pool.to_state_dict()

        # Run the existing executor (synchronous in terms of generator — but
        # execute_agent_node is async; we need to await it)
        # We use a trampoline pattern: the caller (GraphEngine) handles async.
        # Since BaseNode._run() is synchronous Generator, we store the coroutine
        # for the engine to await.
        pass  # see below — this class must be used differently

    # ------------------------------------------------------------------
    # Override: return a coroutine for the engine to await
    # ------------------------------------------------------------------

    async def run_async(self):
        """Async entry point for the agent node."""
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

        # Extract outputs: strip "messages" (internal) and any None values
        outputs = {k: v for k, v in result.items() if k != "messages"}
        yield NodeRunSucceededEvent(
            node_id=self.id,
            node_name=self.name,
            outputs=outputs,
        )
