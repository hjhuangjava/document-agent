import type { NodeDef, EdgeDef } from "./types";

export const START_NODE_ID = "__start__";
export const END_NODE_ID = "__end__";

export const FLOW_TERMINAL_IDS = [START_NODE_ID, END_NODE_ID] as const;

export function isFlowTerminalNode(def: Pick<NodeDef, "id">): boolean {
  return (FLOW_TERMINAL_IDS as readonly string[]).includes(def.id);
}

export function createStartNodeDef(): NodeDef {
  return {
    id: START_NODE_ID,
    execution_mode: "tool",
    name: "开始节点",
    description: "标识工作流的入口",
    category: "flow_control",
    icon: "play",
    tool_config: {
      tool_name: "workflow_start",
      input_bindings: [],
      output_bindings: [],
    },
  };
}

export function createEndNodeDef(): NodeDef {
  return {
    id: END_NODE_ID,
    execution_mode: "tool",
    name: "结束节点",
    description: "标识工作流的出口",
    category: "flow_control",
    icon: "square",
    tool_config: {
      tool_name: "workflow_end",
      input_bindings: [],
      output_bindings: [],
    },
  };
}

/** Inject visual start/end nodes when edges reference them. */
export function injectTerminalNodes(nodes: NodeDef[], edges: EdgeDef[]): NodeDef[] {
  const ids = new Set(nodes.map((n) => n.id));
  const result = [...nodes];

  const hasStart =
    ids.has(START_NODE_ID) || edges.some((e) => e.source === START_NODE_ID);
  const hasEnd =
    ids.has(END_NODE_ID) || edges.some((e) => e.target === END_NODE_ID);

  if (hasStart && !ids.has(START_NODE_ID)) {
    result.unshift(createStartNodeDef());
  }
  if (hasEnd && !ids.has(END_NODE_ID)) {
    result.push(createEndNodeDef());
  }

  return result;
}

/** Remove start/end markers before persisting – backend uses edge endpoints only. */
export function stripTerminalNodes(nodes: NodeDef[]): NodeDef[] {
  return nodes.filter((n) => !isFlowTerminalNode(n));
}
