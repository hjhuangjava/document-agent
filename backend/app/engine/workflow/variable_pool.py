"""VariablePool – typed data sharing across workflow nodes.

Structure::

    _outputs: dict[str, Any]         # flat namespace (state_key → value)
    _system: dict[str, Any]          # system variables (business_context, etc.)
    _node_outputs: dict[str, dict]   # per-node audit trail
"""

from __future__ import annotations


class VariablePool:
    def __init__(self):
        self._outputs: dict[str, Any] = {}
        self._system: dict[str, Any] = {}
        self._node_outputs: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def add(self, node_id: str, key: str, value: Any) -> None:
        """Write a node output value to the flat namespace + per-node store."""
        self._outputs[key] = value
        self._node_outputs.setdefault(node_id, {})[key] = value

    def set_system(self, key: str, value: Any) -> None:
        self._system[key] = value

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        return self._outputs.get(key, default)

    def get_system(self, key: str, default: Any = None) -> Any:
        return self._system.get(key, default)

    def get_node_outputs(self, node_id: str) -> dict[str, Any]:
        return self._node_outputs.get(node_id, {})

    # ------------------------------------------------------------------
    # Dotted-path resolution
    # ------------------------------------------------------------------

    def resolve_path(self, path: str, default: Any = None) -> Any:
        """Resolve a dotted path like ``"draft_content"`` or
        ``"consistency_report.status"``.

        The first segment is looked up in the flat output namespace first,
        then in system variables.  Subsequent segments traverse dict keys.
        """
        if not path:
            return default

        parts = path.split(".", 1)
        root_key = parts[0]
        rest = parts[1] if len(parts) > 1 else None

        # Look up root
        if root_key in self._outputs:
            cur = self._outputs[root_key]
        elif root_key in self._system:
            cur = self._system[root_key]
        else:
            return default

        # Traverse sub-keys
        if rest is not None:
            for k in rest.split("."):
                if isinstance(cur, dict) and k in cur:
                    cur = cur[k]
                else:
                    return default

        return cur

    # ------------------------------------------------------------------
    # Helpers for building executor-compatible state dicts
    # ------------------------------------------------------------------

    def to_state_dict(self) -> dict:
        """Build a dict mirroring AgentState fields + all dynamic outputs
        for existing executor functions.
        """
        state = {
            "messages": self.get_system("_messages", []),
            "business_context": self.get_system("business_context", {}),
            "data_query_result": self.get("data_query_result", ""),
            "draft_content": self.get("draft_content", ""),
            "consistency_report": self.get("consistency_report", {"status": "pass", "violations": []}),
            "vfs_artifacts": self.get("vfs_artifacts", []),
            "_vfs_session_id": self.get_system("_vfs_session_id", ""),
            "_meta": self.get_system("_meta", {}),
        }
        # Merge ALL dynamic outputs — downstream nodes may use arbitrary state_key names
        state.update(self._outputs)
        return state
