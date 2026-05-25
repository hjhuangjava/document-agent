"use client";

import { useState, useEffect } from "react";
import { Bot, Wrench, Search, Database, Shield, Pen, BookOpen } from "lucide-react";
import { listTools } from "@/lib/api";
import type { Tool as APITool, NodeDef } from "@/lib/types";

const ICON_MAP: Record<string, React.ReactNode> = {
  data_source: <Database className="h-4 w-4" />,
  knowledge: <BookOpen className="h-4 w-4" />,
  executor: <Pen className="h-4 w-4" />,
  validator: <Shield className="h-4 w-4" />,
  interactor: <Bot className="h-4 w-4" />,
};

const LABEL_MAP: Record<string, string> = {
  data_source: "数据源",
  knowledge: "知识库",
  executor: "执行器",
  validator: "校验器",
  interactor: "交互",
};

interface ComponentPaletteProps {
  onAddNode: (def: NodeDef) => void;
}

export function ComponentPalette({ onAddNode }: ComponentPaletteProps) {
  const [tools, setTools] = useState<APITool[]>([]);
  const [search, setSearch] = useState("");

  useEffect(() => {
    listTools().then(setTools).catch(console.error);
  }, []);

  const filtered = tools.filter(
    (t) =>
      t.enabled &&
      (t.name.includes(search) || t.description.includes(search) || t.category.includes(search))
  );

  const groups = filtered.reduce<Record<string, APITool[]>>((acc, t) => {
    const cat = t.category || "general";
    acc[cat] = acc[cat] || [];
    acc[cat].push(t);
    return acc;
  }, {});

  return (
    <div className="w-56 border-r bg-gray-50 flex flex-col">
      <div className="p-2 border-b">
        <div className="relative">
          <Search className="absolute left-2 top-2 h-4 w-4 text-gray-400" />
          <input
            className="w-full pl-8 pr-2 py-1.5 text-sm border rounded-md"
            placeholder="搜索组件..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-3">
        {/* Agent template (always available) */}
        <div>
          <div className="text-xs font-semibold text-gray-500 mb-1 flex items-center gap-1">
            <Bot className="h-3 w-3" /> Agent 节点
          </div>
          <button
            draggable
            onDragStart={(e) => {
              e.dataTransfer.setData(
                "application/json",
                JSON.stringify({
                  id: `agent_${Date.now()}`,
                  execution_mode: "agent" as const,
                  name: "新 Agent",
                  category: "general",
                  agent_config: {
                    system_prompt: "",
                    tool_names: [],
                    llm_params: { temperature: 0.7 },
                  },
                })
              );
            }}
            onClick={() =>
              onAddNode({
                id: `agent_${Date.now()}`,
                execution_mode: "agent",
                name: "新 Agent",
                category: "general",
                agent_config: {
                  system_prompt: "",
                  tool_names: [],
                  llm_params: { temperature: 0.7 },
                },
              })
            }
            className="w-full text-left px-2 py-1.5 text-sm rounded hover:bg-blue-50 border border-blue-200 flex items-center gap-2"
          >
            <Bot className="h-4 w-4 text-blue-500" />
            + 新建 Agent
          </button>
        </div>

        {/* Tool nodes from backend */}
        {Object.entries(groups).map(([cat, items]) => (
          <div key={cat}>
            <div className="text-xs font-semibold text-gray-500 mb-1 flex items-center gap-1">
              {ICON_MAP[cat] || <Wrench className="h-3 w-3" />}
              {LABEL_MAP[cat] || cat}
            </div>
            {items.map((t) => (
              <button
                key={t.name}
                draggable
                onDragStart={(e) => {
                  e.dataTransfer.setData(
                    "application/json",
                    JSON.stringify({
                      id: `tool_${t.component_type}_${Date.now()}`,
                      execution_mode: "tool",
                      name: t.name,
                      category: t.category,
                      tool_config: {
                        tool_name: t.component_type,
                        input_bindings: [],
                        output_bindings: [],
                      },
                    })
                  );
                }}
                onClick={() =>
                  onAddNode({
                    id: `tool_${t.component_type}_${Date.now()}`,
                    execution_mode: "tool",
                    name: t.name,
                    category: t.category,
                    tool_config: {
                      tool_name: t.component_type,
                      input_bindings: [],
                      output_bindings: [],
                    },
                  })
                }
                className="w-full text-left px-2 py-1.5 text-sm rounded hover:bg-emerald-50 border border-emerald-200 flex items-center gap-2 mb-1"
              >
                <Wrench className="h-4 w-4 text-emerald-500" />
                {t.name}
              </button>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
