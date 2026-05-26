"""User-facing generate endpoint – selects default published workflow and runs it."""

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.db.engine import get_db
from app.db.models import Workflow, WorkflowRun
from app.engine.tools import get_vfs, release_vfs
from app.engine.workflow import (
    Graph,
    GraphEngine,
    GraphRuntimeState,
    VariablePool,
    node_factory,
    translate_stream,
)

router = APIRouter(prefix="/generate", tags=["generate"])


class GenerateRequest(BaseModel):
    business_context: dict


@router.post("")
async def generate(request: GenerateRequest, db: Session = Depends(get_db)):
    """Pick the first published workflow and execute it via SSE."""
    wf = db.query(Workflow).filter(Workflow.is_published == True).first()
    if not wf:
        raise HTTPException(status_code=404, detail="No published workflow found")

    topology = {
        "nodes": json.loads(wf.nodes),
        "edges": json.loads(wf.edges),
    }

    session_id = uuid.uuid4().hex

    # --- Build runtime state with system variables ---
    pool = VariablePool()
    pool.set_system("business_context", request.business_context)
    pool.set_system("_vfs_session_id", session_id)
    pool.set_system("_meta", {})
    pool.set_system("_messages", [])

    runtime_state = GraphRuntimeState(variable_pool=pool)

    # --- Build graph from topology ---
    graph = Graph.from_topology(topology, node_factory, runtime_state)

    # --- Create engine ---
    engine = GraphEngine(graph, runtime_state)

    # --- DB run record ---
    run_id = uuid.uuid4().hex
    run_record = WorkflowRun(
        id=run_id,
        workflow_id=wf.id,
        status="running",
        business_context=json.dumps(request.business_context, ensure_ascii=False),
    )
    db.add(run_record)
    db.commit()

    async def event_generator():
        try:
            async for evt in translate_stream(engine):
                yield evt
            run_record.status = "completed"
            db.commit()
        except Exception as e:
            run_record.status = "failed"
            run_record.error_message = str(e)
            db.commit()
            yield {"event": "error", "data": {"message": str(e)}}
        finally:
            release_vfs(session_id)

    return EventSourceResponse(event_generator())
