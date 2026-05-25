"use client";

import { useCallback, useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  type Connection,
  type Edge,
  type Node,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { nodeTypes } from "./AgentNode";
import { PropertyPanel } from "./PropertyPanel";
import { ComponentPalette } from "./ComponentPalette";
import type { NodeDef, EdgeDef } from "@/lib/types";

interface FlowCanvasProps {
  initialNodes?: NodeDef[];
  initialEdges?: EdgeDef[];
  onPublish?: (nodes: NodeDef[], edges: EdgeDef[]) => void;
}

/** Convert NodeDef[] to React Flow Node[] */
function toFlowNodes(defs: NodeDef[]): Node[] {
  return defs.map((d, i) => ({
    id: d.id,
    type: "custom",
    position: { x: 100 + i * 250, y: 200 },
    data: { nodeDef: d },
  }));
}

/** Convert EdgeDef[] to React Flow Edge[] */
function toFlowEdges(defs: EdgeDef[]): Edge[] {
  return defs.map((e) => ({
    id: e.id || `${e.source}-${e.target}`,
    source: e.source,
    target: e.target,
    sourceHandle: e.sourceHandle ?? undefined,
    targetHandle: e.targetHandle ?? undefined,
    label: e.condition ? `${e.condition.operator} ${String(e.condition.value)}` : undefined,
    animated: !!e.condition,
    markerEnd: { type: MarkerType.ArrowClosed },
    data: { condition: e.condition, max_retries: e.max_retries },
  }));
}

export function FlowCanvas({ initialNodes = [], initialEdges = [], onPublish }: FlowCanvasProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState(toFlowNodes(initialNodes));
  const [edges, setEdges, onEdgesChange] = useEdgesState(toFlowEdges(initialEdges));
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) =>
        addEdge(
          {
            ...connection,
            markerEnd: { type: MarkerType.ArrowClosed },
          },
          eds
        )
      );
    },
    [setEdges]
  );

  const selectedNode = useMemo(
    () => nodes.find((n) => n.id === selectedNodeId),
    [nodes, selectedNodeId]
  );

  const selectedNodeDef = useMemo(
    () => (selectedNode?.data as { nodeDef?: NodeDef })?.nodeDef ?? null,
    [selectedNode]
  );

  /** Add a new node from palette drag */
  const handleAddNode = useCallback(
    (def: NodeDef) => {
      const newId = def.id || `node_${Date.now()}`;
      const flowNode: Node = {
        id: newId,
        type: "custom",
        position: { x: 100 + Math.random() * 400, y: 100 + Math.random() * 300 },
        data: { nodeDef: { ...def, id: newId } },
      };
      setNodes((nds) => [...nds, flowNode]);
    },
    [setNodes]
  );

  /** Delete a node and its connected edges */
  const handleDeleteNode = useCallback(
    (nodeId: string) => {
      setNodes((nds) => nds.filter((n) => n.id !== nodeId));
      setEdges((eds) => eds.filter((e) => e.source !== nodeId && e.target !== nodeId));
      if (selectedNodeId === nodeId) setSelectedNodeId(null);
    },
    [setNodes, setEdges, selectedNodeId]
  );

  /** Export current canvas back to NodeDef[] + EdgeDef[] */
  const handlePublish = useCallback(() => {
    const nodeDefs: NodeDef[] = nodes.map((n) => {
      const d = (n.data as { nodeDef: NodeDef }).nodeDef;
      return { ...d, id: n.id };
    });
    const edgeDefs: EdgeDef[] = edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      sourceHandle: e.sourceHandle ?? null,
      targetHandle: e.targetHandle ?? null,
      condition: (e.data as { condition?: EdgeDef["condition"] })?.condition ?? null,
      max_retries: (e.data as { max_retries?: number })?.max_retries ?? 3,
    }));
    onPublish?.(nodeDefs, edgeDefs);
  }, [nodes, edges, onPublish]);

  return (
    <div className="flex h-full w-full">
      {/* Left: Component Palette */}
      <ComponentPalette onAddNode={handleAddNode} />

      {/* Center: Canvas */}
      <div className="flex-1">
        <div className="h-full relative">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={(_, n) => setSelectedNodeId(n.id)}
            deleteKeyCode="Backspace"
            onNodesDelete={(deleted) => {
              const ids = new Set(deleted.map((n) => n.id));
              setEdges((eds) => eds.filter((e) => !ids.has(e.source) && !ids.has(e.target)));
              if (selectedNodeId && ids.has(selectedNodeId)) setSelectedNodeId(null);
            }}
            nodeTypes={nodeTypes}
            fitView
          >
            <Background />
            <Controls />
            <MiniMap />
          </ReactFlow>

          {/* Publish button */}
          <button
            onClick={handlePublish}
            className="absolute top-4 right-4 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 shadow"
          >
            保存并发布
          </button>
        </div>
      </div>

      {/* Right: Property Panel */}
      {selectedNodeDef && (
        <PropertyPanel
          nodeDef={selectedNodeDef}
          onChange={(updated) => {
            setNodes((nds) =>
              nds.map((n) =>
                n.id === selectedNodeId ? { ...n, data: { nodeDef: updated } } : n
              )
            );
          }}
          onClose={() => setSelectedNodeId(null)}
          onDelete={() => handleDeleteNode(selectedNodeId!)}
        />
      )}
    </div>
  );
}
