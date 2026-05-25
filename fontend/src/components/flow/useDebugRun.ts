"use client";

import { useState, useCallback, useRef } from "react";
import { runWorkflowPost } from "@/lib/api";
import type { DebugState, NodeResult } from "@/lib/types";

const INITIAL_STATE: DebugState = {
  isRunning: false,
  businessContext: '{"query": "test"}',
  nodeResults: {},
  status: "idle",
  errorMessage: undefined,
  finalOutput: "",
  activeNodeId: null,
  completedNodeIds: [],
};

export function useDebugRun() {
  const [debugState, setDebugState] = useState<DebugState>(INITIAL_STATE);
  const abortRef = useRef<AbortController | null>(null);

  const startDebug = useCallback(async (workflowId: number) => {
    // Parse business context
    let context: Record<string, unknown>;
    try {
      context = JSON.parse(debugState.businessContext);
    } catch {
      setDebugState((prev) => ({
        ...prev,
        status: "error",
        errorMessage: "Business Context JSON 格式错误",
      }));
      return;
    }

    // Abort any previous run
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setDebugState((prev) => ({
      ...prev,
      isRunning: true,
      status: "running",
      errorMessage: undefined,
      finalOutput: "",
      nodeResults: {},
      activeNodeId: null,
      completedNodeIds: [],
    }));

    try {
      await runWorkflowPost(
        workflowId,
        context,
        (eventName: string, data: unknown) => {
          if (controller.signal.aborted) return;

          if (eventName === "node_started") {
            const d = data as { node_id: string; node_name: string };
            const result: NodeResult = {
              nodeId: d.node_id,
              nodeName: d.node_name,
              success: false,
              output: "",
              startedAt: new Date().toISOString(),
            };
            setDebugState((prev) => ({
              ...prev,
              activeNodeId: d.node_id,
              nodeResults: { ...prev.nodeResults, [d.node_id]: result },
            }));
          } else if (eventName === "text_delta") {
            const d = data as { content: string };
            setDebugState((prev) => {
              const activeId = prev.activeNodeId;
              if (!activeId) {
                return { ...prev, finalOutput: prev.finalOutput + d.content };
              }
              const existing = prev.nodeResults[activeId];
              return {
                ...prev,
                finalOutput: prev.finalOutput + d.content,
                nodeResults: {
                  ...prev.nodeResults,
                  [activeId]: {
                    ...existing,
                    output: (existing?.output ?? "") + d.content,
                  },
                },
              };
            });
          } else if (eventName === "node_completed") {
            const d = data as { node_id: string; node_name: string; output?: string };
            setDebugState((prev) => {
              const existing = prev.nodeResults[d.node_id];
              const completedResult: NodeResult = {
                ...existing,
                nodeId: d.node_id,
                nodeName: d.node_name,
                success: true,
                output: d.output ?? existing?.output ?? "",
                completedAt: new Date().toISOString(),
              };
              return {
                ...prev,
                activeNodeId: null,
                completedNodeIds: [...prev.completedNodeIds, d.node_id],
                nodeResults: { ...prev.nodeResults, [d.node_id]: completedResult },
              };
            });
          } else if (eventName === "error") {
            const d = data as { message: string };
            setDebugState((prev) => {
              // If we have an active node, mark it as failed
              if (prev.activeNodeId) {
                const existing = prev.nodeResults[prev.activeNodeId];
                return {
                  ...prev,
                  isRunning: false,
                  status: "error",
                  errorMessage: d.message,
                  activeNodeId: null,
                  nodeResults: {
                    ...prev.nodeResults,
                    [prev.activeNodeId]: {
                      ...existing,
                      success: false,
                      error: d.message,
                      completedAt: new Date().toISOString(),
                    },
                  },
                };
              }
              return {
                ...prev,
                isRunning: false,
                status: "error",
                errorMessage: d.message,
              };
            });
          }
        },
        (err: Error) => {
          if (controller.signal.aborted) return;
          setDebugState((prev) => ({
            ...prev,
            isRunning: false,
            status: "error",
            errorMessage: err.message,
            activeNodeId: null,
          }));
        },
        controller.signal,
      );

      // Stream completed
      if (!controller.signal.aborted) {
        setDebugState((prev) => ({
          ...prev,
          isRunning: false,
          status: "done",
          activeNodeId: null,
        }));
      }
    } catch (e) {
      if (controller.signal.aborted) return;
      setDebugState((prev) => ({
        ...prev,
        isRunning: false,
        status: "error",
        errorMessage: e instanceof Error ? e.message : String(e),
        activeNodeId: null,
      }));
    }
  }, [debugState.businessContext]);

  const resetDebug = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setDebugState((prev) => ({
      ...INITIAL_STATE,
      businessContext: prev.businessContext,
    }));
  }, []);

  const setBusinessContext = useCallback((value: string) => {
    setDebugState((prev) => ({ ...prev, businessContext: value }));
  }, []);

  return { debugState, startDebug, resetDebug, setBusinessContext };
}
