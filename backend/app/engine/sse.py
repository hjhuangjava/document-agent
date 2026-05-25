"""SSE event translator – LangGraph astream_events v2 → business events."""

from app.engine.state import AgentState


async def translate_stream(app, inputs: dict, config: dict, node_names: dict[str, str]):
    """Yield business-level SSE dicts from LangGraph internal events.

    ``node_names`` maps node_id → display name (loaded from topology).
    """
    async for event in app.astream_events(inputs, config=config, version="v2"):
        kind = event["event"]
        node = event.get("name", "")

        if kind == "on_chain_start" and node in node_names:
            yield {
                "event": "node_started",
                "data": {"node_id": node, "node_name": node_names[node]},
            }

        elif kind == "on_chain_end" and node in node_names:
            output_str = str(event.get("data", {}).get("output", ""))
            yield {
                "event": "node_completed",
                "data": {
                    "node_id": node,
                    "node_name": node_names[node],
                    "output": output_str[:500],
                },
            }

        elif kind == "on_tool_start":
            yield {
                "event": "tool_invoked",
                "data": {"tool_name": event["name"]},
            }

        elif kind == "on_tool_end":
            output = str(event["data"].get("output", ""))
            yield {
                "event": "tool_result",
                "data": {"tool_name": event["name"], "summary": output[:200]},
            }

        elif kind == "on_chat_model_stream":
            chunk = event["data"].get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                yield {
                    "event": "text_delta",
                    "data": {"content": chunk.content},
                }
