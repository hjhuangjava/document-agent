"""Virtual File System – session-isolated final-artifact storage."""

import shutil
import uuid
from pathlib import Path

from backend.app.config import settings


class VirtualFileSystem:
    """Session-scoped file store. Only for final artifacts (charts, full docs).
    Intermediate data flows through AgentState, NOT through files."""

    def __init__(self, session_id: str | None = None, base_dir: str | None = None):
        self.session_id = session_id or uuid.uuid4().hex[:8]
        self.root = Path(base_dir or settings.vfs_base_dir) / self.session_id
        self.root.mkdir(parents=True, exist_ok=True)

    def write(self, filename: str, content: str | bytes) -> str:
        filepath = self.root / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            filepath.write_bytes(content)
        else:
            filepath.write_text(content, encoding="utf-8")
        return str(filepath)

    def read(self, filename: str) -> str:
        return (self.root / filename).read_text(encoding="utf-8")

    def read_bytes(self, filename: str) -> bytes:
        return (self.root / filename).read_bytes()

    def list_artifacts(self) -> list[str]:
        return [str(p) for p in self.root.rglob("*") if p.is_file()]

    def cleanup(self):
        shutil.rmtree(self.root, ignore_errors=True)
