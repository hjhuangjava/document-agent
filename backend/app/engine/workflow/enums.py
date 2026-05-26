"""Workflow engine enums."""

from enum import StrEnum


class NodeState(StrEnum):
    UNKNOWN = "unknown"
    TAKEN = "taken"
    SKIPPED = "skipped"


class NodeExecutionType(StrEnum):
    EXECUTABLE = "executable"  # agent / tool nodes
    BRANCH = "branch"          # nodes with conditional outgoing edges


class ErrorStrategy(StrEnum):
    FAIL_BRANCH = "fail-branch"
    DEFAULT_VALUE = "default-value"
