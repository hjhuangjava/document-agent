/**
 * API client – thin wrappers around fetch for the backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Tools
// ---------------------------------------------------------------------------

import type { Tool } from "./types";

export const listTools = () => request<Tool[]>("/tools");

export const patchTool = (name: string, body: { description?: string; enabled?: boolean }) =>
  request<Tool>(`/tools/${name}`, { method: "PATCH", body: JSON.stringify(body) });

// ---------------------------------------------------------------------------
// Knowledge
// ---------------------------------------------------------------------------

export interface KnowledgeSearchResult {
  id: string;
  title: string;
  content: string;
  score: number;
  source: string;
  category: string;
  updated_at: string;
}

export interface KnowledgeSearchResponse {
  query: string;
  results: KnowledgeSearchResult[];
  total: number;
}

export const searchKnowledge = (query: string, top_k = 5) =>
  request<KnowledgeSearchResponse>("/knowledge/search", {
    method: "POST",
    body: JSON.stringify({ query, top_k }),
  });

// ---------------------------------------------------------------------------
// Workflows
// ---------------------------------------------------------------------------

import type { Workflow, NodeDef, EdgeDef } from "./types";

export const listWorkflows = () => request<Workflow[]>("/workflows");

export const getWorkflow = (id: number) => request<Workflow>(`/workflows/${id}`);

export const createWorkflow = (body: {
  name: string;
  description?: string;
  nodes: NodeDef[];
  edges: EdgeDef[];
  is_published?: boolean;
}) => request<Workflow>("/workflows", { method: "POST", body: JSON.stringify(body) });

export const deleteWorkflow = (id: number) =>
  request<void>(`/workflows/${id}`, { method: "DELETE" });

// ---------------------------------------------------------------------------
// Run (SSE) – returns raw EventSource, not a promise
// ---------------------------------------------------------------------------

export function runWorkflow(
  workflowId: number,
  businessContext: Record<string, unknown>,
  onEvent: (evt: MessageEvent) => void,
): EventSource {
  // POST to SSE endpoint – but EventSource only supports GET.
  // We use fetch + ReadableStream for POST-based SSE.
  // Return a mock "close" handle instead.
  // For simplicity, use GET-style EventSource against /generate.

  const es = new EventSource(`${API_BASE}/generate?context=${encodeURIComponent(JSON.stringify(businessContext))}`);
  es.onmessage = onEvent;
  es.onerror = () => es.close();
  return es;
}

/**
 * POST-based SSE using fetch + ReadableStream.
 * Better for sending business_context in body.
 */
export async function runWorkflowPost(
  workflowId: number,
  businessContext: Record<string, unknown>,
  onEvent: (eventName: string, data: unknown) => void,
  onError?: (err: Error) => void,
) {
  const res = await fetch(`${API_BASE}/workflows/${workflowId}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({ business_context: businessContext }),
  });

  if (!res.ok || !res.body) {
    throw new Error(`Run failed: ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      let currentEvent = "message";
      for (const line of lines) {
        if (line.startsWith("event:")) {
          currentEvent = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          const raw = line.slice(5).trim();
          try {
            onEvent(currentEvent, JSON.parse(raw));
          } catch {
            onEvent(currentEvent, raw);
          }
          currentEvent = "message";
        }
      }
    }
  } catch (e) {
    onError?.(e instanceof Error ? e : new Error(String(e)));
  }
}
