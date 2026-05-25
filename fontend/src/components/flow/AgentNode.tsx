"use client";

import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { NodeDef } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Bot, Wrench } from "lucide-react";

interface CustomNodeData extends Record<string, unknown> {
  nodeDef: NodeDef;
  isActive?: boolean;
  isCompleted?: boolean;
}

export function AgentNode({ data, selected }: NodeProps) {
  const d = data as unknown as CustomNodeData;
  const def = d.nodeDef;
  const isAgent = def.execution_mode === "agent";

  return (
    <div
      className={cn(
        "rounded-lg border-2 bg-white shadow-sm min-w-[180px]",
        selected && "ring-2 ring-blue-400",
        d.isActive && "border-amber-400 animate-pulse",
        d.isCompleted && "border-green-400",
        !d.isActive && !d.isCompleted && "border-gray-300",
        isAgent ? "border-l-4 border-l-blue-500" : "border-l-4 border-l-emerald-500"
      )}
    >
      <Handle type="target" position={Position.Left} className="!bg-gray-400 !w-2 !h-2" />

      <div className="px-3 py-2">
        <div className="flex items-center gap-2">
          {isAgent ? (
            <Bot className="h-4 w-4 text-blue-500 shrink-0" />
          ) : (
            <Wrench className="h-4 w-4 text-emerald-500 shrink-0" />
          )}
          <span className="font-medium text-sm truncate">{def.name || def.id}</span>
        </div>
        <div className="text-xs text-gray-500 mt-1">
          {isAgent ? "Agent" : "Tool"} · {def.category || "general"}
        </div>
        {isAgent && def.agent_config && (
          <div className="text-xs text-gray-400 mt-1 truncate">
            {def.agent_config.tool_names.join(", ")}
          </div>
        )}
        {!isAgent && def.tool_config && (
          <div className="text-xs text-gray-400 mt-1 truncate">
            {def.tool_config.tool_name}
          </div>
        )}
      </div>

      <Handle type="source" position={Position.Right} className="!bg-gray-400 !w-2 !h-2" />
    </div>
  );
}

export const nodeTypes = {
  custom: AgentNode,
};
