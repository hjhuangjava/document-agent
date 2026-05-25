"use client";

import { useState, useEffect, useRef } from "react";
import { runWorkflowPost } from "@/lib/api";
import type { SSEEvent } from "@/lib/types";

interface ProgressMonitorProps {
  /** Workflow ID to run */
  workflowId: number;
  /** Business context passed to backend */
  businessContext: Record<string, unknown>;
  /** Called when generation completes */
  onComplete?: (fullText: string) => void;
}

export function ProgressMonitor({ workflowId, businessContext, onComplete }: ProgressMonitorProps) {
  const [timeline, setTimeline] = useState<{ event: string; data: unknown; ts: number }[]>([]);
  const [text, setText] = useState("");
  const [status, setStatus] = useState<"idle" | "running" | "done" | "error">("idle");
  const textRef = useRef(text);
  textRef.current = text;

  const start = async () => {
    setStatus("running");
    setTimeline([]);
    setText("");

    await runWorkflowPost(
      workflowId,
      businessContext,
      (eventName, data) => {
        setTimeline((t) => [...t, { event: eventName, data, ts: Date.now() }]);

        if (eventName === "text_delta") {
          const d = data as { content?: string };
          if (d.content) {
            setText((prev) => prev + d.content);
          }
        }
      },
      (err) => {
        setStatus("error");
        setTimeline((t) => [...t, { event: "error", data: err.message, ts: Date.now() }]);
      }
    );

    setStatus("done");
    onComplete?.(textRef.current);
  };

  useEffect(() => {
    start();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex h-full">
      {/* Left: Timeline */}
      <div className="w-72 border-r overflow-y-auto p-4 space-y-2">
        <h3 className="font-semibold text-sm mb-3">执行进度</h3>
        {timeline.map((item, i) => (
          <div key={i} className="text-xs">
            <span className="text-gray-400">
              {new Date(item.ts).toLocaleTimeString()}
            </span>{" "}
            <span
              className={
                item.event === "node_started"
                  ? "text-amber-600"
                  : item.event === "node_completed"
                  ? "text-emerald-600"
                  : item.event === "tool_invoked"
                  ? "text-blue-600"
                  : item.event === "error"
                  ? "text-red-600"
                  : "text-gray-600"
              }
            >
              {item.event === "node_started" && `▶ ${(item.data as { node_name?: string }).node_name}`}
              {item.event === "node_completed" && `✓ ${(item.data as { node_name?: string }).node_name}`}
              {item.event === "tool_invoked" && `🔧 ${(item.data as { tool_name?: string }).tool_name}`}
              {item.event === "tool_result" && `↩ ${(item.data as { tool_name?: string }).tool_name}`}
              {item.event === "error" && `✗ ${item.data}`}
            </span>
          </div>
        ))}
        {status === "running" && (
          <div className="text-xs text-blue-500 animate-pulse">执行中...</div>
        )}
        {status === "done" && (
          <div className="text-xs text-emerald-600 font-medium">生成完成</div>
        )}
      </div>

      {/* Right: Text preview */}
      <div className="flex-1 overflow-y-auto p-6">
        <pre className="whitespace-pre-wrap font-mono text-sm leading-relaxed">
          {text}
          {status === "running" && <span className="animate-pulse">▌</span>}
        </pre>
      </div>
    </div>
  );
}
