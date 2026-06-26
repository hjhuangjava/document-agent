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
import { flowNodeType } from "./TerminalNode";
import { PropertyPanel } from "./PropertyPanel";
import { ComponentPalette } from "./ComponentPalette";
import { DebugPanel } from "./DebugPanel";
import { useDebugRun } from "./useDebugRun";
import type { NodeDef, EdgeDef } from "@/lib/types";
import {
  END_NODE_ID,
  START_NODE_ID,
  injectTerminalNodes,
  isFlowTerminalNode,
  stripTerminalNodes,
} from "@/lib/flow-control";
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

/** Layered layout constants */
const H_SPACING = 320;
const V_SPACING = 170;
const LAYOUT_OFFSET_X = 80;
const LAYOUT_OFFSET_Y = 80;

/**
 * Compute positions using a layered (Sugiyama-style) layout:
 *  - Each node is assigned a layer (column) by its longest path from the roots,
 *    so the flow reads left → right.
 *  - Sibling nodes in the same layer are stacked vertically (multiple rows),
 *    which keeps parallel branches from overlapping.
 *  - A barycenter pass orders nodes within a layer to reduce edge crossings.
 */
function computeLayout(defs: NodeDef[], allEdges: EdgeDef[]): Map<string, { x: number; y: number }> {
  const positions = new Map<string, { x: number; y: number }>();
  const regularDefs = defs.filter((d) => !isFlowTerminalNode(d));
  const hasStart = defs.some((d) => d.id === START_NODE_ID);
  const hasEnd = defs.some((d) => d.id === END_NODE_ID);

  if (regularDefs.length === 0) {
    if (hasStart) positions.set(START_NODE_ID, { x: LAYOUT_OFFSET_X, y: LAYOUT_OFFSET_Y });
    if (hasEnd) positions.set(END_NODE_ID, { x: LAYOUT_OFFSET_X + H_SPACING, y: LAYOUT_OFFSET_Y });
    return positions;
  }

  const nodeIds = new Set(regularDefs.map((d) => d.id));
  const adjacency = new Map<string, string[]>();
  const incoming = new Map<string, string[]>();
  for (const d of regularDefs) {
    adjacency.set(d.id, []);
    incoming.set(d.id, []);
  }
  for (const e of allEdges) {
    if (nodeIds.has(e.source) && nodeIds.has(e.target)) {
      adjacency.get(e.source)!.push(e.target);
      incoming.get(e.target)!.push(e.source);
    }
  }

  // Roots: targets of __start__ edges, else nodes without incoming edges
  const startEdges = allEdges.filter((e) => e.source === START_NODE_ID && nodeIds.has(e.target));
  let rootNodes: string[];
  if (startEdges.length > 0) {
    rootNodes = startEdges.map((e) => e.target);
  } else {
    rootNodes = regularDefs.filter((d) => incoming.get(d.id)!.length === 0).map((d) => d.id);
  }
  if (rootNodes.length === 0) rootNodes = [regularDefs[0].id];

  // Detect back-edges (retry loops) via DFS so cycles don't break layering
  const backEdges = new Set<string>();
  const visited = new Set<string>();
  const onStack = new Set<string>();
  const dfs = (n: string) => {
    visited.add(n);
    onStack.add(n);
    for (const t of adjacency.get(n) || []) {
      if (onStack.has(t)) backEdges.add(`${n}->${t}`);
      else if (!visited.has(t)) dfs(t);
    }
    onStack.delete(n);
  };
  for (const r of rootNodes) if (!visited.has(r)) dfs(r);
  for (const d of regularDefs) if (!visited.has(d.id)) dfs(d.id);

  // Longest-path layering over forward edges only
  const level = new Map<string, number>(regularDefs.map((d) => [d.id, 0]));
  const fwdAdj = new Map<string, string[]>(regularDefs.map((d) => [d.id, []]));
  const indeg = new Map<string, number>(regularDefs.map((d) => [d.id, 0]));
  for (const e of allEdges) {
    if (!nodeIds.has(e.source) || !nodeIds.has(e.target)) continue;
    if (backEdges.has(`${e.source}->${e.target}`)) continue;
    fwdAdj.get(e.source)!.push(e.target);
    indeg.set(e.target, indeg.get(e.target)! + 1);
  }
  const queue = regularDefs.filter((d) => indeg.get(d.id) === 0).map((d) => d.id);
  const seen = new Set(queue);
  const bfsOrder: string[] = [];
  while (queue.length > 0) {
    const n = queue.shift()!;
    bfsOrder.push(n);
    for (const t of fwdAdj.get(n)!) {
      level.set(t, Math.max(level.get(t)!, level.get(n)! + 1));
      indeg.set(t, indeg.get(t)! - 1);
      if (indeg.get(t) === 0 && !seen.has(t)) {
        seen.add(t);
        queue.push(t);
      }
    }
  }
  for (const d of regularDefs) if (!bfsOrder.includes(d.id)) bfsOrder.push(d.id);

  // Group by layer, keeping BFS order within each layer
  const levelGroups = new Map<number, string[]>();
  for (const id of bfsOrder) {
    const lvl = level.get(id) ?? 0;
    if (!levelGroups.has(lvl)) levelGroups.set(lvl, []);
    levelGroups.get(lvl)!.push(id);
  }

  // Barycenter ordering (top-down) to reduce edge crossings
  const rowIndex = new Map<string, number>();
  const sortedLevels = [...levelGroups.keys()].sort((a, b) => a - b);
  const bary = (id: string): number => {
    const parents = incoming.get(id)!.filter((p) => (level.get(p) ?? 0) < (level.get(id) ?? 0));
    if (parents.length === 0) return rowIndex.get(id) ?? 0;
    const sum = parents.reduce((acc, p) => acc + (rowIndex.get(p) ?? 0), 0);
    return sum / parents.length;
  };
  for (const lvl of sortedLevels) {
    const ids = levelGroups.get(lvl)!;
    if (lvl > 0) ids.sort((a, b) => bary(a) - bary(b));
    ids.forEach((id, idx) => rowIndex.set(id, idx));
  }

  // Assign coordinates – each layer vertically centred for a balanced look
  const baseX = LAYOUT_OFFSET_X + (hasStart ? H_SPACING : 0);
  const maxCount = Math.max(...[...levelGroups.values()].map((g) => g.length));
  for (const lvl of sortedLevels) {
    const ids = levelGroups.get(lvl)!;
    const offset = ((maxCount - ids.length) * V_SPACING) / 2;
    ids.forEach((id, idx) => {
      positions.set(id, {
        x: baseX + lvl * H_SPACING,
        y: LAYOUT_OFFSET_Y + offset + idx * V_SPACING,
      });
    });
  }

  const centerY = LAYOUT_OFFSET_Y + ((maxCount - 1) * V_SPACING) / 2;

  if (hasStart) {
    const ys = rootNodes.map((r) => positions.get(r)?.y).filter((y): y is number => y != null);
    const y = ys.length ? ys.reduce((a, b) => a + b, 0) / ys.length : centerY;
    positions.set(START_NODE_ID, { x: LAYOUT_OFFSET_X, y });
  }

  if (hasEnd) {
    const endSources = allEdges
      .filter((e) => e.target === END_NODE_ID && nodeIds.has(e.source))
      .map((e) => e.source);
    const ys = endSources.map((s) => positions.get(s)?.y).filter((y): y is number => y != null);
    const maxLevel = sortedLevels.length ? Math.max(...sortedLevels) : 0;
    const y = ys.length ? ys.reduce((a, b) => a + b, 0) / ys.length : centerY;
    positions.set(END_NODE_ID, { x: baseX + (maxLevel + 1) * H_SPACING, y });
  }

  return positions;
}

/** Convert NodeDef[] to React Flow Node[], placing nodes on a grid by topological order */
function toFlowNodes(defs: NodeDef[], allEdges: EdgeDef[]): Node[] {
  const positions = computeLayout(defs, allEdges);
  const fallback = { x: 100, y: 200 };
  return defs.map((d) => ({
    id: d.id,
    type: flowNodeType(d.id),
    position: positions.get(d.id) || fallback,
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
    type: "straight",
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
  const hydratedNodes = useMemo(
    () => injectTerminalNodes(initialNodes, initialEdges),
    [initialNodes, initialEdges]
  );
  const [nodes, setNodes, onNodesChange] = useNodesState(toFlowNodes(hydratedNodes, initialEdges));
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
            type: "straight",
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
      if (isFlowTerminalNode(def) && nodes.some((n) => n.id === newId)) {
        return;
      }
      const flowNode: Node = {
        id: newId,
        type: flowNodeType(newId),
        position: { x: 100 + Math.random() * 400, y: 100 + Math.random() * 300 },
        data: { nodeDef: { ...def, id: newId } },
      };
      setNodes((nds) => [...nds, flowNode]);
    },
    [editable, setNodes, nodes]
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
    const nodeDefs: NodeDef[] = stripTerminalNodes(
      nodes.map((n) => {
        const d = (n.data as { nodeDef: NodeDef }).nodeDef;
        return { ...d, id: n.id };
      })
    );
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
