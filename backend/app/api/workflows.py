"""Workflow management API – CRUD + run (SSE)."""

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.db.engine import get_db
from app.db.models import Workflow, WorkflowRun
from app.schemas.workflow import WorkflowCreate, WorkflowOut, WorkflowRunRequest, WorkflowUpdate
from app.engine.workflow import (
    Graph,
    GraphEngine,
    GraphRuntimeState,
    VariablePool,
    node_factory,
    translate_stream,
)
from app.engine.tools import get_vfs, release_vfs

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


@router.put("/{wf_id}", response_model=WorkflowOut)
def update_workflow(wf_id: int, payload: WorkflowUpdate, db: Session = Depends(get_db)):
    wf = db.query(Workflow).filter(Workflow.id == wf_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if payload.name is not None:
        wf.name = payload.name
    if payload.description is not None:
        wf.description = payload.description
    if payload.nodes is not None:
        wf.nodes = json.dumps([n.model_dump() for n in payload.nodes], ensure_ascii=False)
    if payload.edges is not None:
        wf.edges = json.dumps([e.model_dump() for e in payload.edges], ensure_ascii=False)
    if payload.is_published is not None:
        wf.is_published = payload.is_published

    wf.version += 1
    db.commit()
    db.refresh(wf)
    return wf


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
      #print("Workflow topology loaded:", topology)

      session_id = uuid.uuid4().hex

      # --- Build runtime state with system variables ---
      pool = VariablePool()
      pool.set_system("business_context", payload.business_context)
      pool.set_system("_vfs_session_id", session_id)
      pool.set_system("_meta", {})
      pool.set_system("_messages", [])

      runtime_state = GraphRuntimeState(variable_pool=pool)

      # --- Build graph from topology ---
      graph = Graph.from_topology(topology, node_factory, runtime_state)

      # --- Create engine ---
      engine = GraphEngine(graph, runtime_state)

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

