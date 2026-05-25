"use client";

import { useEffect, useState } from "react";
import { listTools, patchTool } from "@/lib/api";
import type { Tool } from "@/lib/types";
import { ToggleLeft, ToggleRight, RefreshCw } from "lucide-react";

export default function SkillsPage() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      setTools(await listTools());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const toggle = async (name: string, enabled: boolean) => {
    try {
      await patchTool(name, { enabled: !enabled });
      setTools((ts) => ts.map((t) => (t.name === name ? { ...t, enabled: !enabled } : t)));
    } catch (e) {
      console.error(e);
    }
  };

  if (loading) {
    return <div className="p-8 text-gray-500">加载中...</div>;
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">技能仓</h1>
        <button
          onClick={load}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
        >
          <RefreshCw className="h-4 w-4" /> 刷新
        </button>
      </div>

      <div className="space-y-3">
        {tools.map((t) => (
          <div
            key={t.name}
            className="border rounded-lg p-4 flex items-center justify-between"
          >
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-medium">{t.name}</span>
                <span className="text-xs px-2 py-0.5 bg-gray-100 rounded">{t.category}</span>
              </div>
              <p className="text-sm text-gray-500 mt-1">{t.description}</p>
            </div>
            <button
              onClick={() => toggle(t.name, t.enabled)}
              className="ml-4"
              title={t.enabled ? "点击禁用" : "点击启用"}
            >
              {t.enabled ? (
                <ToggleRight className="h-8 w-8 text-emerald-500" />
              ) : (
                <ToggleLeft className="h-8 w-8 text-gray-400" />
              )}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
