/**
 * Shared TypeScript types – mirrors v3 Node Schema & backend models.
 */

// ---------------------------------------------------------------------------
// Tool (from backend /api/v1/tools)
// ---------------------------------------------------------------------------

export interface ToolInput {
  name: string;
  type: string;
  required?: boolean;
  default?: unknown;
  description?: string;
}

export interface ToolOutput {
  name: string;
  type: string;
  description?: string;
}

export interface Tool {
  name: string;
  description: string;
  category: string;
  component_type: string;
  inputs: string; // JSON string – parse at runtime
  outputs: string;
  enabled: boolean;
}

// ---------------------------------------------------------------------------
// Workflow / Node / Edge (v3 Schema)
// ---------------------------------------------------------------------------

export interface AgentConfig {
  system_prompt: string;
  tool_names: string[];
  llm_params?: Record<string, unknown>;
  max_iterations?: number;
}

export interface ToolConfigInputBinding {
  name: string;
  bind: { type: "state" | "static"; state_key?: string; value?: unknown };
  required?: boolean;
  default?: unknown;
}

export interface ToolConfigOutputBinding {
  output_name: string;
  state_key: string;
}

export interface ToolConfig {
  tool_name: string;
  input_bindings: ToolConfigInputBinding[];
  output_bindings: ToolConfigOutputBinding[];
}

export interface OutputBinding {
  output_name: string;
  state_key: string;
}

export interface NodeDef {
  id: string;
  execution_mode: "agent" | "tool";
  name?: string;
  description?: string;
  category?: string;
  icon?: string;
  version?: string;
  agent_config?: AgentConfig;
  tool_config?: ToolConfig;
  output_bindings?: OutputBinding[];
  requires_approval?: boolean;
}

export interface Condition {
  field: string;
  operator: "eq" | "ne" | "gt" | "lt" | "gte" | "lte" | "in" | "contains";
  value: unknown;
}

export interface EdgeDef {
  id?: string;
  source: string;
  target: string;
  sourceHandle?: string | null;
  targetHandle?: string | null;
  condition?: Condition | null;
  max_retries?: number;
}

export interface Workflow {
  id: number;
  name: string;
  description: string;
  nodes: string; // JSON – parse at runtime
  edges: string; // JSON
  is_published: boolean;
  version: number;
}

// ---------------------------------------------------------------------------
// Debug (workflow test run)
// ---------------------------------------------------------------------------

export interface NodeResult {
  nodeId: string;
  nodeName: string;
  success: boolean;
  output: string;
  error?: string;
  startedAt?: string;
  completedAt?: string;
}

export interface DebugState {
  isRunning: boolean;
  businessContext: string;
  nodeResults: Record<string, NodeResult>;
  status: "idle" | "running" | "done" | "error";
  errorMessage?: string;
  finalOutput: string;
  activeNodeId: string | null;
  completedNodeIds: string[];
}

// ---------------------------------------------------------------------------
// SSE events (from backend translate_stream)
// ---------------------------------------------------------------------------

export type SSEEvent =
  | { event: "node_started"; data: { node_id: string; node_name: string } }
  | { event: "node_completed"; data: { node_id: string; node_name: string; output?: string } }
  | { event: "tool_invoked"; data: { tool_name: string } }
  | { event: "tool_result"; data: { tool_name: string; summary: string } }
  | { event: "text_delta"; data: { content: string } }
  | { event: "error"; data: { message: string } };
