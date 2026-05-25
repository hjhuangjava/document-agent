"""Workflow management API – CRUD + run (SSE)."""

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.db.engine import get_db
from app.db.models import Workflow, WorkflowRun
from app.schemas.workflow import WorkflowCreate, WorkflowOut, WorkflowRunRequest
from app.engine.builder import build_workflow
from app.engine.sse import translate_stream
from app.engine.tools import get_vfs, release_vfs
from app.config import settings

router = APIRouter(prefix="/workflows", tags=["workflows"])


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@router.post("", response_model=WorkflowOut, status_code=201)
def create_workflow(payload: WorkflowCreate, db: Session = Depends(get_db)):
    wf = Workflow(
        name=payload.name,
        description=payload.description,
        nodes=json.dumps([n.model_dump() for n in payload.nodes], ensure_ascii=False),
        edges=json.dumps([e.model_dump() for e in payload.edges], ensure_ascii=False),
        is_published=payload.is_published,
    )
    db.add(wf)
    db.commit()
    db.refresh(wf)
    return wf


@router.get("", response_model=list[WorkflowOut])
def list_workflows(db: Session = Depends(get_db)):
    return db.query(Workflow).all()


@router.get("/{wf_id}", response_model=WorkflowOut)
def get_workflow(wf_id: int, db: Session = Depends(get_db)):
    wf = db.query(Workflow).filter(Workflow.id == wf_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@router.delete("/{wf_id}", status_code=204)
def delete_workflow(wf_id: int, db: Session = Depends(get_db)):
    wf = db.query(Workflow).filter(Workflow.id == wf_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    db.delete(wf)
    db.commit()


# ---------------------------------------------------------------------------
# Run (SSE)
# ---------------------------------------------------------------------------

@router.post("/{wf_id}/run")
async def run_workflow(wf_id: int, payload: WorkflowRunRequest, db: Session = Depends(get_db)):
    wf = db.query(Workflow).filter(Workflow.id == wf_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    topology = {
        "nodes": json.loads(wf.nodes),
        "edges": json.loads(wf.edges),
    }

    graph = build_workflow(topology)

    # Use SQLite checkpointer per run
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    checkpointer = AsyncSqliteSaver.from_conn_string("./data/checkpoints.db")
    app = graph.compile(checkpointer=checkpointer)

    session_id = uuid.uuid4().hex
    config = {"configurable": {"thread_id": session_id}}

    # Build node display-name map for SSE translator
    node_names = {n["id"]: n.get("name", n["id"]) for n in topology["nodes"]}

    # Initial state
    inputs = {
        "business_context": payload.business_context,
        "data_query_result": "",
        "draft_content": "",
        "consistency_report": {"status": "pass", "violations": []},
        "vfs_artifacts": [],
        "_vfs_session_id": session_id,
    }

    # Record run in DB
    run_id = uuid.uuid4().hex
    run_record = WorkflowRun(
        id=run_id,
        workflow_id=wf_id,
        status="running",
        business_context=json.dumps(payload.business_context, ensure_ascii=False),
    )
    db.add(run_record)
    db.commit()

    async def event_generator():
        try:
            async for evt in translate_stream(app, inputs, config, node_names):
                yield evt
            # Mark completed
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
