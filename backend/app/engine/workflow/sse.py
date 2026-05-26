"""SSE event translator – GraphEngine events → business SSE dicts.

Replaces the LangGraph ``astream_events`` translator.

Yields dicts with ``{"event": str, "data": str}`` where *data* is a
JSON-encoded string.  ``sse_starlette.EventSourceResponse`` will pass
the string through verbatim, ensuring the client receives valid JSON
(not Python repr with single-quotes).
"""

from __future__ import annotations

import json

from app.engine.workflow.events import (
    GraphRunFailedEvent,
    GraphRunStartedEvent,
    GraphRunSucceededEvent,
    NodeRunFailedEvent,
    NodeRunStartedEvent,
    NodeRunStreamChunkEvent,
    NodeRunSucceededEvent,
    ToolInvokedEvent,
    ToolResultEvent,
)


def _sse(event: str, data: dict) -> dict:
    """Build an SSE frame with JSON-serialised data string."""
    return {"event": event, "data": json.dumps(data, ensure_ascii=False)}


async def translate_stream(engine):
    """Consume ``engine.run()`` events and yield SSE-ready dicts."""
    async for event in engine.run():

        if isinstance(event, GraphRunStartedEvent):
            continue

        elif isinstance(event, NodeRunStartedEvent):
            yield _sse("node_started", {
                "node_id": event.node_id,
                "node_name": event.node_name,
            })

        elif isinstance(event, NodeRunStreamChunkEvent):
            yield _sse("text_delta", {"content": event.content})

        elif isinstance(event, NodeRunSucceededEvent):
            output_str = json.dumps(event.outputs, ensure_ascii=False)
            yield _sse("node_completed", {
                "node_id": event.node_id,
                "node_name": event.node_name,
                "output": output_str[:500],
            })

        elif isinstance(event, ToolInvokedEvent):
            yield _sse("tool_invoked", {"tool_name": event.tool_name})

        elif isinstance(event, ToolResultEvent):
            yield _sse("tool_result", {
                "tool_name": event.tool_name,
                "summary": event.summary[:200],
            })

        elif isinstance(event, NodeRunFailedEvent):
            yield _sse("node_failed", {
                "node_id": event.node_id,
                "node_name": event.node_name,
                "error": event.error,
            })

        elif isinstance(event, GraphRunSucceededEvent):
            yield _sse("workflow_completed", {"outputs": event.outputs})

        elif isinstance(event, GraphRunFailedEvent):
            yield _sse("error", {"message": event.error})
