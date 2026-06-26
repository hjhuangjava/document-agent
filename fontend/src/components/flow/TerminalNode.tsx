"use client";

import { Handle, Position, type NodeProps } from "@xyflow/react";
import { Play, Square } from "lucide-react";
import { cn } from "@/lib/utils";
import type { NodeDef } from "@/lib/types";
import { END_NODE_ID, START_NODE_ID } from "@/lib/flow-control";

interface TerminalNodeData extends Record<string, unknown> {
  nodeDef: NodeDef;
  isActive?: boolean;
  isCompleted?: boolean;
}

function TerminalNodeShell({
  data,
  selected,
  variant,
}: NodeProps & { variant: "start" | "end" }) {
  const d = data as unknown as TerminalNodeData;
  const def = d.nodeDef;
  const isStart = variant === "start";

  return (
    <div
      className={cn(
        "rounded-full border-2 bg-white shadow-sm min-w-[120px] px-4 py-3 text-center",
        selected && "ring-2 ring-blue-400",
        d.isActive && "border-amber-400 animate-pulse",
        d.isCompleted && "border-green-400",
        !d.isActive && !d.isCompleted && (isStart ? "border-green-500" : "border-rose-500")
      )}
    >
      {!isStart && (
        <Handle type="target" position={Position.Left} className="!bg-gray-400 !w-2 !h-2" />
      )}

      <div className="flex flex-col items-center gap-1">
        {isStart ? (
          <Play className="h-5 w-5 text-green-600" />
        ) : (
          <Square className="h-5 w-5 text-rose-600" />
        )}
        <span className="font-medium text-sm">{def.name || (isStart ? "开始节点" : "结束节点")}</span>
        <span className="text-xs text-gray-500">{isStart ? "工作流入口" : "工作流出口"}</span>
      </div>

      {isStart && (
        <Handle type="source" position={Position.Right} className="!bg-gray-400 !w-2 !h-2" />
      )}
    </div>
  );
}

export function StartNode(props: NodeProps) {
  return <TerminalNodeShell {...props} variant="start" />;
}

export function EndNode(props: NodeProps) {
  return <TerminalNodeShell {...props} variant="end" />;
}

export function flowNodeType(nodeId: string): "start" | "end" | "custom" {
  if (nodeId === START_NODE_ID) return "start";
  if (nodeId === END_NODE_ID) return "end";
  return "custom";
}
