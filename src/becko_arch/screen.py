from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from .process import run_command


async def capture_screen() -> bytes:
    with tempfile.TemporaryDirectory(prefix="becko-screen-") as directory:
        path = Path(directory) / "screen.png"
        if os.getenv("WAYLAND_DISPLAY"):
            if not shutil.which("grim"):
                raise RuntimeError(
                    "Install grim for wlroots/Hyprland screen capture. Other Wayland desktops can block capture; text and voice still work."
                )
            await run_command("grim", str(path))
        elif os.getenv("DISPLAY"):
            await run_command("maim", str(path))
        else:
            raise RuntimeError("No graphical desktop session was detected.")
        if not path.exists():
            raise RuntimeError("Desktop did not produce a screenshot.")
        if path.stat().st_size > 15_000_000:
            raise RuntimeError(
                "Screenshot is larger than 15 MB. Reduce display resolution before sharing."
            )
        return path.read_bytes()
