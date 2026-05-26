"""SSE event translator – GraphEngine events → business SSE dicts.

Replaces the LangGraph ``astream_events`` translator.
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


async def translate_stream(engine):
    """Consume ``engine.run()`` events and yield SSE-ready dicts.

    Each yielded dict has the shape ``{"event": str, "data": dict}``,
    compatible with the existing frontend SSE protocol.
    """
    async for event in engine.run():

        if isinstance(event, GraphRunStartedEvent):
            continue  # Implicit; nothing to broadcast

        elif isinstance(event, NodeRunStartedEvent):
            yield {
                "event": "node_started",
                "data": {
                    "node_id": event.node_id,
                    "node_name": event.node_name,
                },
            }

        elif isinstance(event, NodeRunStreamChunkEvent):
            yield {
                "event": "text_delta",
                "data": {"content": event.content},
            }

        elif isinstance(event, NodeRunSucceededEvent):
            output_str = json.dumps(event.outputs, ensure_ascii=False)
            yield {
                "event": "node_completed",
                "data": {
                    "node_id": event.node_id,
                    "node_name": event.node_name,
                    "output": output_str[:500],
                },
            }

        elif isinstance(event, ToolInvokedEvent):
            yield {
                "event": "tool_invoked",
                "data": {"tool_name": event.tool_name},
            }

        elif isinstance(event, ToolResultEvent):
            yield {
                "event": "tool_result",
                "data": {
                    "tool_name": event.tool_name,
                    "summary": event.summary[:200],
                },
            }

        elif isinstance(event, NodeRunFailedEvent):
            yield {
                "event": "node_failed",
                "data": {
                    "node_id": event.node_id,
                    "node_name": event.node_name,
                    "error": event.error,
                },
            }

        elif isinstance(event, GraphRunSucceededEvent):
            yield {
                "event": "workflow_completed",
                "data": {"outputs": event.outputs},
            }

        elif isinstance(event, GraphRunFailedEvent):
            yield {
                "event": "error",
                "data": {"message": event.error},
            }
