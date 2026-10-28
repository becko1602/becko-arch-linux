from __future__ import annotations

import json
from datetime import UTC, datetime

from .config import private_write, state_dir


class History:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.turns: list[dict[str, str]] = []
        self.warning = ""
        if enabled:
            path = state_dir() / "history.json"
            if path.exists():
                try:
                    raw = json.loads(path.read_text())
                    if not isinstance(raw, list):
                        raise ValueError("Not a list")
                    self.turns = [
                        item
                        for item in raw[-100:]
                        if isinstance(item, dict)
                        and item.get("role") in ("user", "model")
                        and isinstance(item.get("text"), str)
                    ]
                except (OSError, ValueError):
                    self.warning = (
                        "Saved conversation could not be read. It has not been overwritten."
                    )

    def add(self, role: str, text: str) -> None:
        if not text.strip():
            return
        self.turns.append(
            {"role": role, "text": text[:20000], "time": datetime.now(UTC).isoformat()}
        )
        self.turns = self.turns[-100:]
        if self.enabled and not self.warning:
            private_write(state_dir() / "history.json", self.turns)

    def clear(self) -> None:
        self.turns = []
        self.warning = ""
        if self.enabled:
            private_write(state_dir() / "history.json", [])
