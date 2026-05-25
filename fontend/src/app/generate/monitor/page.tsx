"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { ProgressMonitor } from "@/components/monitor/ProgressMonitor";
import { TiptapEditor } from "@/components/editor/TiptapEditor";

function MonitorContent() {
  const params = useSearchParams();
  const contextStr = params.get("context") ?? "{}";
  const [context] = useState(() => {
    try { return JSON.parse(contextStr); } catch { return {}; }
  });
  const [fullText, setFullText] = useState<string | null>(null);

  // Default workflow ID = 1 (demo)
  const workflowId = 1;

  if (fullText) {
    return (
      <div className="h-screen flex flex-col">
        <div className="h-12 border-b flex items-center px-4 gap-4">
          <h1 className="font-bold">方案工作台</h1>
          <button
            onClick={() => setFullText(null)}
            className="text-sm text-gray-500 hover:underline"
          >
            重新生成
          </button>
        </div>
        <div className="flex-1">
          <TiptapEditor initialContent={fullText} />
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col">
      <div className="h-12 border-b flex items-center px-4">
        <h1 className="font-bold">生成进度</h1>
      </div>
      <div className="flex-1">
        <ProgressMonitor
          workflowId={workflowId}
          businessContext={context}
          onComplete={setFullText}
        />
      </div>
    </div>
  );
}

export default function MonitorPage() {
  return (
    <Suspense fallback={<div className="p-8 text-gray-500">加载中...</div>}>
      <MonitorContent />
    </Suspense>
  );
}
