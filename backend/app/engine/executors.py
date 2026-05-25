"""Node executors – Agent nodes (LLM-driven) and Tool nodes (deterministic)."""

from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI

from app.config import settings
from app.engine.state import AgentState
from app.engine.tools import TOOL_REGISTRY


# ---------------------------------------------------------------------------
# Helper: state path resolution
# ---------------------------------------------------------------------------

def _get_state_path(state: dict, path: str):
    keys = path.split(".")
    cur = state
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur


def _set_state_path(updates: dict, path: str, value):
    keys = path.split(".")
    cur = updates
    for k in keys[:-1]:
        cur = cur.setdefault(k, {})
    cur[keys[-1]] = value


def _resolve_value(state: AgentState, binding: dict):
    bind = binding.get("bind", {})
    if bind.get("type") == "state":
        return _get_state_path(state, bind["state_key"])
    return bind.get("value", binding.get("default"))


# ---------------------------------------------------------------------------
# Agent-node executor
# ---------------------------------------------------------------------------

async def execute_agent_node(
    state: AgentState,
    *,
    system_prompt: str,
    tool_names: list[str],
    vfs_session_id: str,
    llm_params: dict | None = None,
    output_bindings: list[dict] | None = None,
) -> dict:
    """LLM-driven node: model decides which tools to call, loops until no tool calls."""

    tools = [TOOL_REGISTRY[n] for n in tool_names if n in TOOL_REGISTRY]
    if not tools:
        raise ValueError(f"No registered tools found for: {tool_names}")

    params = {**_base_llm_params(), **(llm_params or {})}
    model = ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=params.pop("model", settings.llm_model_name),
        streaming=True,
        **params,
    )
    model_with_tools = model.bind_tools(tools)
    tool_node = ToolNode(tools)

    # Inject vfs_session_id into tool calls by adding it to system_prompt hint
    augmented_prompt = f"{system_prompt}\n\n当前会话 VFS ID: {vfs_session_id}，调用需要 vfs_session_id 参数的工具时请传入此值。"

    response = await model_with_tools.ainvoke(
        [("system", augmented_prompt)] + state["messages"]
    )
    messages = [response]

    iterations = 0
    max_iterations = 10
    while response.tool_calls and iterations < max_iterations:
        tool_result = await tool_node.ainvoke({"messages": messages})
        messages.append(tool_result["messages"][-1])
        response = await model_with_tools.ainvoke(
            [("system", augmented_prompt)] + state["messages"] + messages
        )
        messages.append(response)
        iterations += 1

    # Map final text to state fields
    state_updates: dict = {"messages": messages}
    final_content = response.content
    for ob in (output_bindings or []):
        _set_state_path(state_updates, ob["state_key"], final_content)

    return state_updates


# ---------------------------------------------------------------------------
# Tool-node executor (deterministic)
# ---------------------------------------------------------------------------

async def execute_tool_node(
    state: AgentState,
    *,
    tool_name: str,
    input_bindings: list[dict],
    output_bindings: list[dict] | None = None,
) -> dict:
    """Deterministic node: call a single tool with resolved inputs, write outputs to state."""

    tool_fn = TOOL_REGISTRY.get(tool_name)
    if not tool_fn:
        raise ValueError(f"Unregistered tool: {tool_name}")

    resolved: dict = {}
    for b in input_bindings:
        resolved[b["name"]] = _resolve_value(state, b)

    result = await tool_fn.ainvoke(resolved)

    state_updates: dict = {}
    for ob in (output_bindings or []):
        value = result.get(ob["output_name"]) if isinstance(result, dict) else result
        _set_state_path(state_updates, ob["state_key"], value)

    return state_updates


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _base_llm_params() -> dict:
    return {
        "temperature": 0,
    }
