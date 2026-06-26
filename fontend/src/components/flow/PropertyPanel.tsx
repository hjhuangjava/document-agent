"use client";

import { useState, useEffect } from "react";
import { X, Plus, Trash2 } from "lucide-react";
import { listTools } from "@/lib/api";
import type { NodeDef, Tool, ToolConfigInputBinding, ToolConfigOutputBinding, OutputBinding } from "@/lib/types";
import { isFlowTerminalNode } from "@/lib/flow-control";

interface PropertyPanelProps {
  nodeDef: NodeDef;
  onChange: (updated: NodeDef) => void;
  onClose: () => void;
  onDelete: () => void;
  readOnly?: boolean;
}

export function PropertyPanel({ nodeDef, onChange, onClose, onDelete, readOnly = false }: PropertyPanelProps) {
  const isAgent = nodeDef.execution_mode === "agent";
  const isTerminal = isFlowTerminalNode(nodeDef);
  const [toolsMeta, setToolsMeta] = useState<Tool[]>([]);

  useEffect(() => {
    listTools().then(setToolsMeta).catch(console.error);
  }, []);

  const currentToolMeta = !isAgent && nodeDef.tool_config
    ? toolsMeta.find((t) => t.component_type === nodeDef.tool_config!.tool_name)
    : undefined;

  const update = (patch: Partial<NodeDef>) => {
    if (readOnly) return;
    onChange({ ...nodeDef, ...patch });
  };

  const updateAgentConfig = (patch: Partial<NonNullable<NodeDef["agent_config"]>>) => {
    if (readOnly) return;
    update({ agent_config: { ...nodeDef.agent_config!, ...patch } });
  };

  // --- Input binding (works for both agent and tool) ---
  const getInputBindings = (): ToolConfigInputBinding[] => {
    if (isAgent) return nodeDef.input_bindings || [];
    return nodeDef.tool_config?.input_bindings || [];
  };

  const addInputBinding = () => {
    if (readOnly) return;
    const newBinding: ToolConfigInputBinding = {
      name: "",
      bind: { type: "static", value: "" },
      required: true,
    };
    if (isAgent) {
      update({ input_bindings: [...(nodeDef.input_bindings || []), newBinding] });
    } else {
      const tc = nodeDef.tool_config!;
      update({ tool_config: { ...tc, input_bindings: [...tc.input_bindings, newBinding] } });
    }
  };

  const updateInputBinding = (index: number, patch: Partial<ToolConfigInputBinding>) => {
    if (readOnly) return;
    if (isAgent) {
      const bs = [...(nodeDef.input_bindings || [])];
      bs[index] = { ...bs[index], ...patch };
      update({ input_bindings: bs });
    } else {
      const bs = [...nodeDef.tool_config!.input_bindings];
      bs[index] = { ...bs[index], ...patch };
      update({ tool_config: { ...nodeDef.tool_config!, input_bindings: bs } });
    }
  };

  const removeInputBinding = (index: number) => {
    if (readOnly) return;
    if (isAgent) {
      const bs = (nodeDef.input_bindings || []).filter((_, i) => i !== index);
      update({ input_bindings: bs });
    } else {
      const bs = nodeDef.tool_config!.input_bindings.filter((_, i) => i !== index);
      update({ tool_config: { ...nodeDef.tool_config!, input_bindings: bs } });
    }
  };

  // --- Output binding (tool) ---
  const addToolOutputBinding = () => {
    if (readOnly || !nodeDef.tool_config) return;
    const tc = nodeDef.tool_config;
    const newBinding: ToolConfigOutputBinding = { output_name: "", state_key: "" };
    update({ tool_config: { ...tc, output_bindings: [...tc.output_bindings, newBinding] } });
  };

  const updateToolOutputBinding = (index: number, patch: Partial<ToolConfigOutputBinding>) => {
    if (readOnly || !nodeDef.tool_config) return;
    const bs = [...nodeDef.tool_config.output_bindings];
    bs[index] = { ...bs[index], ...patch };
    update({ tool_config: { ...nodeDef.tool_config, output_bindings: bs } });
  };

  const removeToolOutputBinding = (index: number) => {
    if (readOnly || !nodeDef.tool_config) return;
    const bs = nodeDef.tool_config.output_bindings.filter((_, i) => i !== index);
    update({ tool_config: { ...nodeDef.tool_config, output_bindings: bs } });
  };

  // --- Output binding (agent) ---
  const addAgentOutputBinding = () => {
    if (readOnly) return;
    const newBinding: OutputBinding = { output_name: "", state_key: "" };
    update({ output_bindings: [...(nodeDef.output_bindings || []), newBinding] });
  };

  const updateAgentOutputBinding = (index: number, patch: Partial<OutputBinding>) => {
    if (readOnly) return;
    const bs = [...(nodeDef.output_bindings || [])];
    bs[index] = { ...bs[index], ...patch };
    update({ output_bindings: bs });
  };

  const removeAgentOutputBinding = (index: number) => {
    if (readOnly) return;
    const bs = (nodeDef.output_bindings || []).filter((_, i) => i !== index);
    update({ output_bindings: bs });
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

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* 名称 */}
        <label className="block text-xs text-gray-500">名称</label>
        <input
          className="w-full border rounded px-2 py-1 text-sm"
          value={nodeDef.name || ""}
          onChange={(e) => update({ name: e.target.value })}
          disabled={readOnly}
        />

        {/* 类型 */}
        <label className="block text-xs text-gray-500">类型</label>
        <div className="text-sm px-2 py-1 bg-gray-100 rounded">
          {isTerminal ? "流程控制" : isAgent ? "Agent (LLM 驱动)" : "Tool (确定性)"}
        </div>

        {isTerminal && (
          <p className="text-xs text-gray-500 leading-relaxed">
            {nodeDef.description ||
              (nodeDef.id === "__start__"
                ? "连接下游节点，标识工作流从何处开始执行。"
                : "连接上游节点，标识工作流在何处结束。")}
          </p>
        )}

        {/* Agent 专属 */}
        {!isTerminal && isAgent && nodeDef.agent_config && (
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

        {/* Tool 专属 */}
        {!isTerminal && !isAgent && nodeDef.tool_config && (
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

        {/* 人工确认 */}
        {!isTerminal && (
          <>
            <label className="block text-xs text-gray-500">需要人工确认</label>
            <input
              type="checkbox"
              checked={nodeDef.requires_approval ?? false}
              onChange={(e) => update({ requires_approval: e.target.checked })}
              disabled={readOnly}
            />
          </>
        )}

        {/* ====== 输入参数 / 输出参数 ====== */}
        {!isTerminal && (
        <>
        <div className="border-t pt-3 mt-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-gray-700">输入参数</span>
            <button
              onClick={addInputBinding}
              className="flex items-center text-xs text-blue-600 hover:text-blue-800"
              disabled={readOnly}
            >
              <Plus className="h-3 w-3" /> 添加
            </button>
          </div>

          {getInputBindings().map((ib, i) => (
            <div key={i} className="flex items-center gap-1 mb-1.5">
              <input
                className="flex-1 border rounded px-1.5 py-1 text-xs"
                placeholder="参数名"
                value={ib.name}
                onChange={(e) => updateInputBinding(i, { name: e.target.value })}
                disabled={readOnly}
              />
              <select
                className="border rounded px-1.5 py-1 text-xs bg-white"
                value={ib.bind.type}
                onChange={(e) => {
                  const t = e.target.value as "static" | "state";
                  updateInputBinding(i, {
                    bind: t === "static"
                      ? { type: "static", value: ib.bind.value ?? "" }
                      : { type: "state", state_key: ib.bind.state_key ?? "" },
                  });
                }}
                disabled={readOnly}
              >
                <option value="static">静态值</option>
                <option value="state">上游输出</option>
              </select>
              {ib.bind.type === "static" ? (
                <input
                  className="flex-1 border rounded px-1.5 py-1 text-xs"
                  placeholder="值"
                  value={String(ib.bind.value ?? "")}
                  onChange={(e) => updateInputBinding(i, { bind: { ...ib.bind, value: e.target.value } })}
                  disabled={readOnly}
                />
              ) : (
                <input
                  className="flex-1 border rounded px-1.5 py-1 text-xs"
                  placeholder="state_key"
                  value={ib.bind.state_key ?? ""}
                  onChange={(e) => updateInputBinding(i, { bind: { ...ib.bind, state_key: e.target.value } })}
                  disabled={readOnly}
                />
              )}
              <button onClick={() => removeInputBinding(i)} className="text-red-400 hover:text-red-600" disabled={readOnly}>
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>

        {/* ====== 输出参数 ====== */}
        <div className="border-t pt-3 mt-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-gray-700">输出参数</span>
            <button
              onClick={isAgent ? addAgentOutputBinding : addToolOutputBinding}
              className="flex items-center text-xs text-blue-600 hover:text-blue-800"
              disabled={readOnly}
            >
              <Plus className="h-3 w-3" /> 添加
            </button>
          </div>

          {/* Tool output bindings */}
          {!isAgent && nodeDef.tool_config?.output_bindings.map((ob, i) => (
            <div key={i} className="flex items-center gap-1 mb-1.5">
              <input
                className="flex-1 border rounded px-1.5 py-1 text-xs"
                placeholder="输出名"
                value={ob.output_name}
                onChange={(e) => updateToolOutputBinding(i, { output_name: e.target.value })}
                disabled={readOnly}
              />
              <span className="text-gray-400 text-xs">→</span>
              <input
                className="flex-1 border rounded px-1.5 py-1 text-xs"
                placeholder="state_key"
                value={ob.state_key}
                onChange={(e) => updateToolOutputBinding(i, { state_key: e.target.value })}
                disabled={readOnly}
              />
              <button onClick={() => removeToolOutputBinding(i)} className="text-red-400 hover:text-red-600" disabled={readOnly}>
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}

          {/* Agent output bindings */}
          {isAgent && (nodeDef.output_bindings || []).map((ob, i) => (
            <div key={i} className="flex items-center gap-1 mb-1.5">
              <input
                className="flex-1 border rounded px-1.5 py-1 text-xs"
                placeholder="输出名"
                value={ob.output_name}
                onChange={(e) => updateAgentOutputBinding(i, { output_name: e.target.value })}
                disabled={readOnly}
              />
              <span className="text-gray-400 text-xs">→</span>
              <input
                className="flex-1 border rounded px-1.5 py-1 text-xs"
                placeholder="state_key"
                value={ob.state_key}
                onChange={(e) => updateAgentOutputBinding(i, { state_key: e.target.value })}
                disabled={readOnly}
              />
              <button onClick={() => removeAgentOutputBinding(i)} className="text-red-400 hover:text-red-600" disabled={readOnly}>
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
        </>
        )}
      </div>

      {/* 删除按钮 */}
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
