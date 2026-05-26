"use client";

import { useState } from "react";
import { X } from "lucide-react";
import type { NodeDef } from "@/lib/types";

interface PropertyPanelProps {
  nodeDef: NodeDef;
  onChange: (updated: NodeDef) => void;
  onClose: () => void;
  onDelete: () => void;
  readOnly?: boolean;
}

export function PropertyPanel({ nodeDef, onChange, onClose, onDelete, readOnly = false }: PropertyPanelProps) {
  const isAgent = nodeDef.execution_mode === "agent";
  const [tab, setTab] = useState<"basic" | "io">("basic");

  const update = (patch: Partial<NodeDef>) => {
    if (readOnly) return;
    onChange({ ...nodeDef, ...patch });
  };

  const updateAgentConfig = (patch: Partial<NonNullable<NodeDef["agent_config"]>>) => {
    if (readOnly) return;
    update({ agent_config: { ...nodeDef.agent_config!, ...patch } });
  };

  return (
    <div className="w-72 border-l bg-white flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b">
        <h3 className="font-medium text-sm">{nodeDef.name || nodeDef.id}</h3>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b">
        <button
          className={`flex-1 py-2 text-xs font-medium ${tab === "basic" ? "border-b-2 border-blue-500 text-blue-600" : "text-gray-500"}`}
          onClick={() => setTab("basic")}
        >
          基本
        </button>
        <button
          className={`flex-1 py-2 text-xs font-medium ${tab === "io" ? "border-b-2 border-blue-500 text-blue-600" : "text-gray-500"}`}
          onClick={() => setTab("io")}
        >
          输入/输出
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {tab === "basic" && (
          <>
            <label className="block text-xs text-gray-500">名称</label>
            <input
              className="w-full border rounded px-2 py-1 text-sm"
              value={nodeDef.name || ""}
              onChange={(e) => update({ name: e.target.value })}
              disabled={readOnly}
            />

            <label className="block text-xs text-gray-500">类型</label>
            <div className="text-sm px-2 py-1 bg-gray-100 rounded">
              {isAgent ? "Agent (LLM 驱动)" : "Tool (确定性)"}
            </div>

            {isAgent && nodeDef.agent_config && (
              <>
                <label className="block text-xs text-gray-500">System Prompt</label>
                <textarea
                  className="w-full border rounded px-2 py-1 text-sm h-32"
                  value={nodeDef.agent_config.system_prompt}
                  onChange={(e) => updateAgentConfig({ system_prompt: e.target.value })}
                  disabled={readOnly}
                />

                <label className="block text-xs text-gray-500">Temperature</label>
                <input
                  type="number"
                  step={0.1}
                  min={0}
                  max={2}
                  className="w-full border rounded px-2 py-1 text-sm"
                  value={(nodeDef.agent_config.llm_params?.temperature as number) ?? 0.7}
                  onChange={(e) =>
                    updateAgentConfig({
                      llm_params: {
                        ...nodeDef.agent_config!.llm_params,
                        temperature: parseFloat(e.target.value),
                      },
                    })
                  }
                  disabled={readOnly}
                />

                <label className="block text-xs text-gray-500">绑定工具</label>
                <div className="text-sm text-gray-600">
                  {nodeDef.agent_config.tool_names.join(", ") || "无"}
                </div>
              </>
            )}

            {!isAgent && nodeDef.tool_config && (
              <>
                <label className="block text-xs text-gray-500">工具名称</label>
                <div className="text-sm px-2 py-1 bg-gray-100 rounded">
                  {nodeDef.tool_config.tool_name}
                </div>

                {nodeDef.tool_config.tool_name === "user_input" && (
                  <>
                    <label className="block text-xs text-gray-500 mt-2">用户输入内容</label>
                    <textarea
                      className="w-full border rounded px-2 py-1 text-sm h-32"
                      value={
                        nodeDef.tool_config.input_bindings[0]?.bind.type === "static"
                          ? (nodeDef.tool_config.input_bindings[0].bind.value as string) ?? ""
                          : ""
                      }
                      onChange={(e) => {
                        if (readOnly) return;
                        const newBindings = [...nodeDef.tool_config!.input_bindings];
                        if (newBindings[0]) {
                          newBindings[0] = {
                            ...newBindings[0],
                            bind: { ...newBindings[0].bind, value: e.target.value },
                          };
                        }
                        update({
                          tool_config: {
                            ...nodeDef.tool_config!,
                            input_bindings: newBindings,
                          },
                        });
                      }}
                      readOnly={readOnly}
                      placeholder="请输入内容..."
                    />
                  </>
                )}
              </>
            )}

            <label className="block text-xs text-gray-500">需要人工确认</label>
            <input
              type="checkbox"
              checked={nodeDef.requires_approval ?? false}
              onChange={(e) => update({ requires_approval: e.target.checked })}
              disabled={readOnly}
            />
          </>
        )}

        {tab === "io" && (
          <>
            <div className="text-xs font-semibold text-gray-500 mb-1">输出映射</div>
            {(nodeDef.output_bindings || []).map((ob, i) => (
              <div key={i} className="flex gap-1 text-sm">
                <span className="text-blue-600">{ob.output_name}</span>
                <span className="text-gray-400">→</span>
                <span className="text-emerald-600">{ob.state_key}</span>
              </div>
            ))}
            {(!nodeDef.output_bindings || nodeDef.output_bindings.length === 0) && (
              <div className="text-xs text-gray-400">暂无输出映射</div>
            )}

            {isAgent && nodeDef.agent_config && (
              <>
                <div className="text-xs font-semibold text-gray-500 mt-3 mb-1">可用工具</div>
                {nodeDef.agent_config.tool_names.map((tn) => (
                  <div key={tn} className="text-sm px-2 py-1 bg-blue-50 rounded mb-1">
                    {tn}
                  </div>
                ))}
              </>
            )}

            {!isAgent && nodeDef.tool_config && (
              <>
                <div className="text-xs font-semibold text-gray-500 mt-3 mb-1">输入绑定</div>
                {nodeDef.tool_config.input_bindings.map((ib, i) => (
                  <div key={i} className="text-sm mb-1">
                    <span className="font-medium">{ib.name}</span>
                    {ib.bind.type === "state" ? (
                      <span className="text-emerald-600 ml-1">← {ib.bind.state_key}</span>
                    ) : (
                      <span className="text-gray-500 ml-1">= {String(ib.bind.value)}</span>
                    )}
                  </div>
                ))}
              </>
            )}
          </>
        )}
      </div>

      {/* Delete button – only in edit mode */}
      {!readOnly && (
        <div className="p-3 border-t">
          <button
            onClick={onDelete}
            className="w-full py-2 text-sm text-red-600 border border-red-300 rounded hover:bg-red-50"
          >
            删除节点
          </button>
        </div>
      )}
    </div>
  );
}
