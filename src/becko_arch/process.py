"""Run argument arrays only; never interpolate model content into a shell."""

from __future__ import annotations

import asyncio
import shutil


async def run_command(*args: str, timeout: float = 10) -> str:
    if not args or not shutil.which(args[0]):
        raise RuntimeError(f"Missing Linux utility: {args[0] if args else 'unknown'}")
    process = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout)
    except (TimeoutError, asyncio.CancelledError):
        if process.returncode is None:
            process.kill()
        await process.communicate()
        raise
    if process.returncode:
        raise RuntimeError(
            stderr.decode(errors="replace").strip()[:500]
            or f"{args[0]} exited with {process.returncode}"
        )
    return stdout.decode(errors="replace").strip()[:20000]
