"use client";

import { useEffect, useState } from "react";
import { FlowCanvas } from "@/components/flow/FlowCanvas";
import { listWorkflows, createWorkflow, updateWorkflow } from "@/lib/api";
import type { NodeDef, EdgeDef, Workflow } from "@/lib/types";

export default function CanvasPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [workflowName, setWorkflowName] = useState("");
  const [nodes, setNodes] = useState<NodeDef[]>([]);
  const [edges, setEdges] = useState<EdgeDef[]>([]);
  const [editMode, setEditMode] = useState(false);
  const [isPublished, setIsPublished] = useState(false);
  const [canvasKey, setCanvasKey] = useState(0);

  const loadWorkflows = async () => {
    const wfs = await listWorkflows();
    setWorkflows(wfs);
    return wfs;
  };

  useEffect(() => {
    loadWorkflows();
  }, []);

  useEffect(() => {
    if (selectedId === null) {
      setWorkflowName("");
      setNodes([]);
      setEdges([]);
      setEditMode(false);
      setIsPublished(false);
      setCanvasKey((k) => k + 1);
      return;
    }
    const wf = workflows.find((w) => w.id === selectedId);
    if (!wf) return;
    setWorkflowName(wf.name);
    setIsPublished(wf.is_published);
    setEditMode(false);
    try {
      setNodes(JSON.parse(wf.nodes));
      setEdges(JSON.parse(wf.edges));
    } catch {
      setNodes([]);
      setEdges([]);
    }
    setCanvasKey((k) => k + 1);
  }, [selectedId, workflows]);

  const handleEnterEdit = () => {
    setEditMode(true);
  };

  const handleSave = async (newNodes: NodeDef[], newEdges: EdgeDef[]) => {
    try {
      if (selectedId === null) {
        // New workflow – create as draft
        const wf = await createWorkflow({
          name: workflowName.trim() || `工作流_${Date.now()}`,
          nodes: newNodes,
          edges: newEdges,
          is_published: false,
        });
        setSelectedId(wf.id);
        setIsPublished(false);
        // Refresh list
        const wfs = await loadWorkflows();
        setWorkflows(wfs);
      } else {
        // Existing workflow – update nodes/edges only
        await updateWorkflow(selectedId, {
          name: workflowName.trim() || undefined,
          nodes: newNodes,
          edges: newEdges,
        });
        // Refresh list to pick up latest version
        const wfs = await loadWorkflows();
        setWorkflows(wfs);
      }
      // Stay in edit mode after saving
    } catch (e) {
      alert(`保存失败: ${e}`);
    }
  };

  const handlePublish = async () => {
    if (selectedId === null) return;
    try {
      await updateWorkflow(selectedId, { is_published: true });
      setIsPublished(true);
      setEditMode(false);
      const wfs = await loadWorkflows();
      setWorkflows(wfs);
    } catch (e) {
      alert(`发布失败: ${e}`);
    }
  };

  return (
    <div className="h-screen flex flex-col">
      {/* Top bar */}
      <div className="h-12 border-b flex items-center px-4 gap-4 bg-white">
        <h1 className="font-bold">编排画布</h1>
        <button
          onClick={() => setSelectedId(null)}
          className="bg-blue-600 text-white px-3 py-1 rounded text-sm font-medium hover:bg-blue-700"
        >
          新建工作流
        </button>
        <select
          className="border rounded px-2 py-1 text-sm"
          value={selectedId ?? ""}
          onChange={(e) => {
            const val = e.target.value;
            if (val === "") {
              setSelectedId(null);
            } else {
              setSelectedId(Number(val));
            }
          }}
        >
          <option value="">选择工作流...</option>
          {workflows.map((wf) => (
            <option key={wf.id} value={wf.id}>
              {wf.name} (v{wf.version}) {wf.is_published ? "" : "[草稿]"}
            </option>
          ))}
        </select>
      </div>

      {/* Canvas */}
      <div className="flex-1">
        <FlowCanvas
          key={canvasKey}
          initialNodes={nodes}
          initialEdges={edges}
          editable={editMode}
          workflowId={selectedId}
          workflowName={workflowName}
          isPublished={isPublished}
          onSave={handleSave}
          onPublish={handlePublish}
          onEnterEdit={handleEnterEdit}
          onNameChange={setWorkflowName}
        />
      </div>
    </div>
  );
}
