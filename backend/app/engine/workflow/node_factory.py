"""NodeFactory – create node instances from topology NodeDef dicts."""

from __future__ import annotations

from app.engine.workflow.nodes.agent_node import AgentNode
from app.engine.workflow.nodes.tool_node import ToolNode
from app.engine.workflow.node_base import BaseNode
from app.engine.workflow.runtime_state import GraphRuntimeState


def node_factory(node_cfg: dict, runtime_state: GraphRuntimeState) -> BaseNode:
    mode = node_cfg["execution_mode"]

    if mode == "agent":
        return AgentNode(node_cfg, runtime_state)

    elif mode == "tool":
        return ToolNode(node_cfg, runtime_state)

    raise ValueError(f"Unknown execution_mode '{mode}' for node {node_cfg['id']}")
