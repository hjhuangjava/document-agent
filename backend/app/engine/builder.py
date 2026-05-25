"""Workflow builder – translate topology JSON → LangGraph StateGraph."""

from langgraph.graph import StateGraph, START, END

from app.engine.state import AgentState
from app.engine.executors import (
    execute_agent_node,
    execute_tool_node,
    _get_state_path,
    _set_state_path,
)


def build_workflow(topology: dict) -> StateGraph:
    """Build a StateGraph from a topology dict (v3 Node Schema).

    Each node declares ``execution_mode``: "agent" or "tool".
    Agent nodes delegate to ``execute_agent_node``; tool nodes to ``execute_tool_node``.
    """
    workflow = StateGraph(AgentState)

    # --- Register nodes ---
    for node_cfg in topology["nodes"]:
        nid = node_cfg["id"]
        mode = node_cfg["execution_mode"]

        if mode == "agent":
            agent_cfg = node_cfg["agent_config"]
            out_bindings = node_cfg.get("output_bindings", [])

            async def _agent_fn(state, _cfg=node_cfg, _ac=agent_cfg, _ob=out_bindings):
                return await execute_agent_node(
                    state,
                    system_prompt=_ac["system_prompt"],
                    tool_names=_ac["tool_names"],
                    vfs_session_id=state.get("_vfs_session_id", ""),
                    llm_params=_ac.get("llm_params"),
                    output_bindings=_ob,
                )

            workflow.add_node(nid, _agent_fn)

        elif mode == "tool":
            tool_cfg = node_cfg["tool_config"]
            in_bindings = tool_cfg["input_bindings"]
            out_bindings = tool_cfg.get("output_bindings", [])

            async def _tool_fn(state, _tc=tool_cfg, _ib=in_bindings, _ob=out_bindings):
                return await execute_tool_node(
                    state,
                    tool_name=_tc["tool_name"],
                    input_bindings=_ib,
                    output_bindings=_ob,
                )

            workflow.add_node(nid, _tool_fn)

        else:
            raise ValueError(f"Unknown execution_mode '{mode}' for node {nid}")

    # --- Register edges ---
    _register_edges(workflow, topology.get("edges", []))

    return workflow


# ---------------------------------------------------------------------------
# Edge registration helpers
# ---------------------------------------------------------------------------

def _register_edges(workflow: StateGraph, edges: list[dict]):
    plain = [e for e in edges if not e.get("condition")]
    conditional = [e for e in edges if e.get("condition")]

    for edge in plain:
        src = START if edge["source"] == "__start__" else edge["source"]
        tgt = END if edge["target"] == "__end__" else edge["target"]
        workflow.add_edge(src, tgt)

    # Group conditional edges by source
    groups: dict[str, list] = {}
    for edge in conditional:
        groups.setdefault(edge["source"], []).append(edge)

    for src, group in groups.items():
        max_retries = max((e.get("max_retries", 3) for e in group), default=3)

        def _make_router(edges_list, src_node=src, _max=max_retries):
            def router(state: AgentState) -> str:
                meta = state.get("_meta", {})
                count = meta.get(src_node, 0)
                for e in edges_list:
                    cond = e["condition"]
                    actual = _get_state_path(state, cond["field"])
                    if _eval_condition(actual, cond["operator"], cond["value"]):
                        # Back-edge guard: prevent infinite retries
                        if e["target"] != "__end__" and count >= _max:
                            return END
                        # Increment retry counter for back-edges
                        if e["target"] != "__end__":
                            meta[src_node] = count + 1
                        return e["target"] if e["target"] != "__end__" else END
                return END
            return router

        workflow.add_conditional_edges(src, _make_router(group))


def _eval_condition(actual, operator: str, expected) -> bool:
    ops = {
        "eq": lambda a, b: a == b,
        "ne": lambda a, b: a != b,
        "gt": lambda a, b: a is not None and b is not None and a > b,
        "lt": lambda a, b: a is not None and b is not None and a < b,
        "gte": lambda a, b: a is not None and b is not None and a >= b,
        "lte": lambda a, b: a is not None and b is not None and a <= b,
        "in": lambda a, b: a in b if isinstance(b, list) else False,
        "contains": lambda a, b: b in a if isinstance(a, str) else False,
    }
    return ops.get(operator, lambda a, b: False)(actual, expected)
