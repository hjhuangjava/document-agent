"use client";

import { useEffect, useState } from "react";
import { FlowCanvas } from "@/components/flow/FlowCanvas";
import { listWorkflows, createWorkflow } from "@/lib/api";
import type { NodeDef, EdgeDef, Workflow } from "@/lib/types";

export default function CanvasPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [nodes, setNodes] = useState<NodeDef[]>([]);
  const [edges, setEdges] = useState<EdgeDef[]>([]);

  useEffect(() => {
    listWorkflows().then((wfs) => {
      setWorkflows(wfs);
      if (wfs.length > 0) {
        setSelectedId(wfs[0].id);
      }
    });
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    const wf = workflows.find((w) => w.id === selectedId);
    if (!wf) return;
    try {
      setNodes(JSON.parse(wf.nodes));
      setEdges(JSON.parse(wf.edges));
    } catch {
      setNodes([]);
      setEdges([]);
    }
  }, [selectedId, workflows]);

  const handlePublish = async (newNodes: NodeDef[], newEdges: EdgeDef[]) => {
    try {
      await createWorkflow({
        name: `工作流_${Date.now()}`,
        nodes: newNodes,
        edges: newEdges,
        is_published: true,
      });
      const wfs = await listWorkflows();
      setWorkflows(wfs);
      alert("发布成功");
    } catch (e) {
      alert(`发布失败: ${e}`);
    }
  };

  return (
    <div className="h-screen flex flex-col">
      {/* Top bar */}
      <div className="h-12 border-b flex items-center px-4 gap-4 bg-white">
        <h1 className="font-bold">编排画布</h1>
        <select
          className="border rounded px-2 py-1 text-sm"
          value={selectedId ?? ""}
          onChange={(e) => setSelectedId(Number(e.target.value))}
        >
          <option value="">选择工作流...</option>
          {workflows.map((wf) => (
            <option key={wf.id} value={wf.id}>
              {wf.name} (v{wf.version})
            </option>
          ))}
        </select>
      </div>

      {/* Canvas */}
      <div className="flex-1">
        <FlowCanvas
          initialNodes={nodes}
          initialEdges={edges}
          onPublish={handlePublish}
        />
      </div>
    </div>
  );
}
