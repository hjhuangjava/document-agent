"""Lightweight, toggleable debug logging for the workflow engine.

Enabled by default; set environment variable ``WORKFLOW_DEBUG=0`` to silence.
Output goes straight to stdout with ``flush=True`` so it shows up reliably
under uvicorn / Windows.
"""

from __future__ import annotations

import os

_DISABLED_VALUES = {"0", "false", "False", "no", "off", ""}

DEBUG_ENABLED = os.environ.get("WORKFLOW_DEBUG", "1") not in _DISABLED_VALUES


def wflog(msg: str) -> None:
    """Print a workflow-engine debug line (no-op when disabled)."""
    if DEBUG_ENABLED:
        print(f"[workflow] {msg}", flush=True)
