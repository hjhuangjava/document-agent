"""Tool management API – list / patch (enable-disable, update description)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.engine import get_db
from app.db.models import Tool
from app.schemas.tool import ToolOut, ToolPatch

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_model=list[ToolOut])
def list_tools(db: Session = Depends(get_db)):
    return db.query(Tool).all()


@router.patch("/{tool_name}", response_model=ToolOut)
def patch_tool(tool_name: str, patch: ToolPatch, db: Session = Depends(get_db)):
    tool = db.query(Tool).filter(Tool.component_type == tool_name).first()
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    if patch.description is not None:
        tool.description = patch.description
    if patch.enabled is not None:
        tool.enabled = patch.enabled
    db.commit()
    db.refresh(tool)
    return tool
