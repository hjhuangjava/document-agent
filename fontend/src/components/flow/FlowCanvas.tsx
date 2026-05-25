"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
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
import { DebugPanel } from "./DebugPanel";
import { useDebugRun } from "./useDebugRun";
import type { NodeDef, EdgeDef } from "@/lib/types";
import { Play, Loader2 } from "lucide-react";

interface FlowCanvasProps {
  initialNodes?: NodeDef[];
  initialEdges?: EdgeDef[];
  editable: boolean;
  workflowId: number | null;
  workflowName: string;
  isPublished: boolean;
  onSave: (nodes: NodeDef[], edges: EdgeDef[]) => Promise<void>;
  onPublish: () => Promise<void>;
  onEnterEdit: () => void;
  onNameChange: (name: string) => void;
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

export function FlowCanvas({
  initialNodes = [],
  initialEdges = [],
  editable,
  workflowId,
  workflowName,
  isPublished,
  onSave,
  onPublish,
  onEnterEdit,
  onNameChange,
}: FlowCanvasProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState(toFlowNodes(initialNodes));
  const [edges, setEdges, onEdgesChange] = useEdgesState(toFlowEdges(initialEdges));
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [isDebugMode, setIsDebugMode] = useState(false);

  const { debugState, startDebug, resetDebug, setBusinessContext } = useDebugRun();

  const onConnect = useCallback(
    (connection: Connection) => {
      if (!editable) return;
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
    [editable, setEdges]
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
      if (!editable) return;
      const newId = def.id || `node_${Date.now()}`;
      const flowNode: Node = {
        id: newId,
        type: "custom",
        position: { x: 100 + Math.random() * 400, y: 100 + Math.random() * 300 },
        data: { nodeDef: { ...def, id: newId } },
      };
      setNodes((nds) => [...nds, flowNode]);
    },
    [editable, setNodes]
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

  /** Serialize current canvas to NodeDef[] + EdgeDef[] and save */
  const handleLocalSave = useCallback(async () => {
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
    await onSave(nodeDefs, edgeDefs);
  }, [nodes, edges, onSave]);

  /** Start debug: run directly without saving/publishing */
  const handleStartDebug = useCallback(async () => {
    if (!workflowId) return;
    setIsDebugMode(true);
    await startDebug(workflowId);
  }, [workflowId, startDebug]);

  /** Close debug panel and reset */
  const handleCloseDebug = useCallback(() => {
    resetDebug();
    setIsDebugMode(false);
  }, [resetDebug]);

  /** Update node visuals based on debug state */
  useEffect(() => {
    if (!isDebugMode) return;

    setNodes((nds) =>
      nds.map((n) => {
        const isActive = debugState.activeNodeId === n.id;
        const isCompleted = debugState.completedNodeIds.includes(n.id);
        return {
          ...n,
          data: { ...n.data, isActive, isCompleted },
        };
      })
    );
  }, [isDebugMode, debugState.activeNodeId, debugState.completedNodeIds, setNodes]);

  /** Clear node visuals when exiting debug mode */
  useEffect(() => {
    if (isDebugMode) return;

    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        data: { ...n.data, isActive: false, isCompleted: false },
      }))
    );
  }, [isDebugMode, setNodes]);

  return (
    <div className="flex h-full w-full">
      {/* Left: Component Palette – only in edit mode */}
      {editable && <ComponentPalette onAddNode={handleAddNode} />}

      {/* Center: Canvas */}
      <div className="flex-1">
        <div className="h-full relative">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={editable ? onNodesChange : undefined}
            onEdgesChange={editable ? onEdgesChange : undefined}
            onConnect={editable ? onConnect : undefined}
            onNodeClick={(_, n) => setSelectedNodeId(n.id)}
            deleteKeyCode={editable ? "Backspace" : null}
            nodesDraggable={editable}
            nodesConnectable={editable}
            elementsSelectable={true}
            onNodesDelete={editable ? (deleted) => {
              const ids = new Set(deleted.map((n) => n.id));
              setEdges((eds) => eds.filter((e) => !ids.has(e.source) && !ids.has(e.target)));
              if (selectedNodeId && ids.has(selectedNodeId)) setSelectedNodeId(null);
            } : undefined}
            nodeTypes={nodeTypes}
            fitView
          >
            <Background />
            <Controls />
            <MiniMap />
          </ReactFlow>

          {/* Toolbar buttons */}
          <div className="absolute top-4 right-4 flex gap-2">
            {editable ? (
              <button
                onClick={handleLocalSave}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 shadow"
              >
                保存
              </button>
            ) : (
              <>
                <button
                  onClick={onEnterEdit}
                  className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 shadow"
                >
                  编辑
                </button>
                {workflowId !== null && (
                  <>
                    <button
                      onClick={handleStartDebug}
                      disabled={debugState.isRunning}
                      className={`px-4 py-2 rounded-lg text-sm font-medium shadow flex items-center gap-2 ${
                        debugState.isRunning
                          ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                          : "bg-green-600 text-white hover:bg-green-700"
                      }`}
                    >
                      {debugState.isRunning ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          执行中...
                        </>
                      ) : (
                        <>
                          <Play className="h-4 w-4" />
                          测试
                        </>
                      )}
                    </button>
                    {!isPublished && (
                      <button
                        onClick={onPublish}
                        className="bg-emerald-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-emerald-700 shadow"
                      >
                        发布
                      </button>
                    )}
                  </>
                )}
              </>
            )}
          </div>

          {/* Workflow name */}
          <div className="absolute top-4 left-4">
            <input
              className="border rounded px-2 py-2 text-sm w-48 shadow bg-white"
              type="text"
              placeholder="工作流名称"
              value={workflowName}
              disabled={!editable}
              onChange={(e) => onNameChange(e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* Right Panel: Debug or Property */}
      {isDebugMode ? (
        <DebugPanel
          debugState={debugState}
          selectedNodeId={selectedNodeId}
          onBusinessContextChange={setBusinessContext}
          onStartDebug={() => {
            if (workflowId) startDebug(workflowId);
          }}
          onClose={handleCloseDebug}
        />
      ) : (
        selectedNodeDef && (
          <PropertyPanel
            nodeDef={selectedNodeDef}
            readOnly={!editable}
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
        )
      )}
    </div>
  );
}
