"use client";

import { X, Play, Loader2, CheckCircle, XCircle as XCircleIcon } from "lucide-react";
import type { DebugState, NodeResult } from "@/lib/types";

interface DebugPanelProps {
  debugState: DebugState;
  selectedNodeId?: string | null;
  onBusinessContextChange: (value: string) => void;
  onStartDebug: () => void;
  onClose: () => void;
}

export function DebugPanel({
  debugState,
  selectedNodeId,
  onBusinessContextChange,
  onStartDebug,
  onClose,
}: DebugPanelProps) {
  const { isRunning, businessContext, nodeResults, status, errorMessage, finalOutput } = debugState;
  const results = Object.values(nodeResults);
  const hasResults = results.length > 0;

  const selectedResult: NodeResult | undefined =
    selectedNodeId && nodeResults[selectedNodeId] ? nodeResults[selectedNodeId] : undefined;

  return (
    <div className="w-80 border-l bg-white flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b">
        <h3 className="font-medium text-sm">调试面板</h3>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Business Context */}
      <div className="p-3 border-b">
        <label className="block text-xs text-gray-500 mb-1">Business Context (JSON)</label>
        <textarea
          className="w-full border rounded px-2 py-1 text-xs font-mono h-20 resize-none"
          value={businessContext}
          onChange={(e) => onBusinessContextChange(e.target.value)}
          disabled={isRunning}
        />
      </div>

      {/* Run Button */}
      <div className="p-3 border-b">
        <button
          onClick={onStartDebug}
          disabled={isRunning}
          className={`w-full py-2 text-sm font-medium rounded flex items-center justify-center gap-2 ${
            isRunning
              ? "bg-gray-300 text-gray-500 cursor-not-allowed"
              : "bg-green-600 text-white hover:bg-green-700"
          }`}
        >
          {isRunning ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              执行中...
            </>
          ) : status === "done" || status === "error" ? (
            <>
              <Play className="h-4 w-4" />
              重新执行
            </>
          ) : (
            <>
              <Play className="h-4 w-4" />
              开始执行
            </>
          )}
        </button>
      </div>

      {/* Node Results */}
      <div className="flex-1 overflow-y-auto p-3">
        <label className="block text-xs text-gray-500 mb-2">
          节点结果 {hasResults && `(${results.filter((r) => r.success).length}/${results.length} 成功)`}
        </label>

        {!hasResults && (
          <div className="text-xs text-gray-400 text-center py-8">
            {isRunning ? "执行中，等待结果..." : "点击「开始执行」运行工作流"}
          </div>
        )}

        {hasResults &&
          results.map((r) => (
            <div
              key={r.nodeId}
              className={`flex items-start gap-2 text-xs py-2 border-b border-gray-50 cursor-pointer rounded px-1 ${
                selectedNodeId === r.nodeId ? "bg-blue-50 ring-1 ring-blue-200" : "hover:bg-gray-50"
              } ${r.success ? "text-green-700" : "text-red-700"}`}
            >
              {r.success ? (
                <CheckCircle className="h-3.5 w-3.5 text-green-500 shrink-0 mt-0.5" />
              ) : (
                <XCircleIcon className="h-3.5 w-3.5 text-red-500 shrink-0 mt-0.5" />
              )}
              <div className="min-w-0">
                <div className="font-medium truncate">{r.nodeName || r.nodeId}</div>
                {r.error && <div className="text-red-500 mt-0.5 break-all">{r.error}</div>}
              </div>
            </div>
          ))}
      </div>

      {/* Selected Node Detail */}
      {selectedResult && (
        <div className="p-3 border-t">
          <label className="block text-xs text-gray-500 mb-1">
            节点详情: {selectedResult.nodeName || selectedResult.nodeId}
          </label>
          <div className="text-xs bg-gray-50 rounded p-2 max-h-40 overflow-y-auto whitespace-pre-wrap break-all">
            {selectedResult.output || "(无输出)"}
          </div>
          {selectedResult.startedAt && (
            <div className="text-xs text-gray-400 mt-1">
              开始: {new Date(selectedResult.startedAt).toLocaleTimeString()}
            </div>
          )}
          {selectedResult.completedAt && (
            <div className="text-xs text-gray-400">
              完成: {new Date(selectedResult.completedAt).toLocaleTimeString()}
            </div>
          )}
        </div>
      )}

      {/* Final Output */}
      {finalOutput && (
        <div className="p-3 border-t">
          <label className="block text-xs text-gray-500 mb-1">最终输出</label>
          <div className="text-xs bg-gray-50 rounded p-2 max-h-24 overflow-y-auto whitespace-pre-wrap break-all">
            {finalOutput}
          </div>
        </div>
      )}

      {/* Status Bar */}
      <div className="p-3 border-t text-xs">
        {status === "running" && (
          <div className="flex items-center gap-2 text-blue-600">
            <Loader2 className="h-3 w-3 animate-spin" />
            执行中...
          </div>
        )}
        {status === "done" && <div className="text-green-600">完成</div>}
        {status === "error" && <div className="text-red-600">错误: {errorMessage}</div>}
        {status === "idle" && <div className="text-gray-400">就绪</div>}
      </div>
    </div>
  );
}
