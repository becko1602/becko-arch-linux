"""Native Linux tools, shared by local commands and Gemini function calling."""

from __future__ import annotations

import asyncio
import os
import platform
import shutil
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus, urlparse

import psutil

from .process import run_command

Confirm = Callable[[str], Awaitable[bool]]
Notify = Callable[[str], None]
APPS = {
    "browser": ("xdg-open", "https://www.google.com"),
    "firefox": ("firefox",),
    "chromium": ("chromium",),
    "chrome": ("google-chrome-stable",),
    "kitty": ("kitty",),
    "foot": ("foot",),
    "terminal": ("kitty",),
    "files": ("xdg-open", str(Path.home())),
    "dolphin": ("dolphin",),
    "thunar": ("thunar",),
    "code": ("code",),
    "spotify": ("spotify",),
    "vlc": ("vlc",),
    "libreoffice": ("libreoffice",),
    "obsidian": ("obsidian",),
    "calculator": ("qalculate-gtk",),
}


class ToolError(ValueError):
    pass


def text_arg(args: dict, key: str, limit: int = 2000) -> str:
    value = args.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > limit or "\x00" in value:
        raise ToolError(f"{key} must be non-empty text (maximum {limit} characters).")
    return value.strip()


def number_arg(args: dict, key: str, low: int, high: int) -> int:
    value = args.get(key)
    if type(value) is not int or not low <= value <= high:
        raise ToolError(f"{key} must be an integer from {low} to {high}.")
    return value


def declaration(
    name: str, description: str, properties: dict | None = None, required: list[str] | None = None
) -> dict:
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "OBJECT",
            "properties": properties or {},
            "required": required or [],
        },
    }


DECLARATIONS = [
    declaration("system_status", "Read Linux CPU, memory, disk, battery, local time and uptime."),
    declaration(
        "open_app",
        "Open one supported Linux desktop app, never a command line.",
        {"app": {"type": "STRING", "enum": list(APPS)}},
        ["app"],
    ),
    declaration(
        "open_url",
        "Open a public HTTP or HTTPS URL in the browser.",
        {"url": {"type": "STRING"}},
        ["url"],
    ),
    declaration(
        "web_search",
        "Open a real search in the browser. This does not return search results.",
        {"query": {"type": "STRING"}},
        ["query"],
    ),
    declaration(
        "youtube_search",
        "Search YouTube directly for videos or music. Opens results in the browser; does not play or inspect videos.",
        {"query": {"type": "STRING"}},
        ["query"],
    ),
    declaration(
        "set_volume",
        "Set the PipeWire/PulseAudio output volume to 0–100 percent.",
        {"percent": {"type": "INTEGER"}},
        ["percent"],
    ),
    declaration(
        "set_mute", "Mute or unmute the system speakers.", {"muted": {"type": "BOOLEAN"}}, ["muted"]
    ),
    declaration(
        "media_control",
        "Control a running media player using MPRIS/playerctl.",
        {"action": {"type": "STRING", "enum": ["play-pause", "next", "previous", "stop"]}},
        ["action"],
    ),
    declaration(
        "set_brightness",
        "Set screen brightness using brightnessctl (requires device permission).",
        {"percent": {"type": "INTEGER"}},
        ["percent"],
    ),
    declaration(
        "notify",
        "Display a local desktop notification, not a message to another person.",
        {"message": {"type": "STRING"}},
        ["message"],
    ),
    declaration(
        "set_reminder",
        "Remind the user after a delay, while Becko stays open.",
        {"seconds": {"type": "INTEGER"}, "message": {"type": "STRING"}},
        ["seconds", "message"],
    ),
    declaration("list_reminders", "List active session reminders."),
    declaration(
        "cancel_reminder",
        "Cancel a session reminder by its number.",
        {"id": {"type": "INTEGER"}},
        ["id"],
    ),
    declaration(
        "power_action",
        "Ask the user to confirm locking the desktop or suspending Linux. Never shutdown or reboot.",
        {"action": {"type": "STRING", "enum": ["lock", "suspend"]}},
        ["action"],
    ),
]


class ToolRouter:
    def __init__(self, confirm: Confirm, notify: Notify):
        self.confirm = confirm
        self.notify = notify
        self.reminders: dict[int, tuple[str, asyncio.Task]] = {}
        self._next_id = 1
        self._children: list[asyncio.subprocess.Process] = []

    async def _launch(self, *args: str) -> str:
        if not shutil.which(args[0]):
            raise ToolError(
                f"{args[0]} is not installed. Install the app with pacman or choose another app."
            )
        if not os.getenv("DISPLAY") and not os.getenv("WAYLAND_DISPLAY"):
            raise ToolError(
                "No desktop session was detected. Open Becko in your graphical session."
            )
        process = await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            start_new_session=True,
        )
        self._children.append(process)
        await asyncio.sleep(0.15)
        if process.returncode not in (None, 0):
            raise ToolError(
                f"{args[0]} exited with {process.returncode}; check its desktop configuration."
            )
        return "Launch requested: " + args[0]

    async def execute(self, name: str, args: dict) -> dict:
        if not isinstance(args, dict):
            return {"error": "Tool arguments must be an object."}
        try:
            return {"result": await self._execute(name, args)}
        except (ToolError, RuntimeError, OSError, TimeoutError, ValueError) as exc:
            return {"error": str(exc)[:1000]}

    async def _execute(self, name: str, args: dict) -> str:
        if name == "system_status":
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage(str(Path.home()))
            battery = psutil.sensors_battery()
            return f"{platform.system()} {platform.release()} | {datetime.now().astimezone().isoformat(timespec='seconds')} | CPU {psutil.cpu_percent()}% | RAM {memory.percent}% ({memory.used // 2**20} MiB used) | Home disk {disk.percent}% | Battery {str(round(battery.percent)) + '%' if battery else 'not present'} | uptime {int((datetime.now().timestamp() - psutil.boot_time()) / 60)} min"
        if name == "open_app":
            app = text_arg(args, "app", 40)
            if app not in APPS:
                raise ToolError("Unsupported app. Choose: " + ", ".join(APPS))
            return await self._launch(*APPS[app])
        if name == "youtube_search":
            url = "https://www.youtube.com/results?search_query=" + quote_plus(
                text_arg(args, "query")
            )
            await self._launch("xdg-open", url)
            return "YouTube search opened: " + args["query"].strip()
        if name in {"open_url", "web_search"}:
            url = (
                "https://www.google.com/search?q=" + quote_plus(text_arg(args, "query"))
                if name == "web_search"
                else text_arg(args, "url")
            )
            parsed = urlparse(url)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
            ):
                raise ToolError("Only HTTP(S) URLs without embedded credentials can be opened.")
            return await self._launch("xdg-open", url)
        if name == "set_volume":
            percent = number_arg(args, "percent", 0, 100)
            if shutil.which("wpctl"):
                await run_command("wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{percent}%")
            else:
                await run_command("pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{percent}%")
            return f"Output volume set to {percent}%."
        if name == "set_mute":
            muted = args.get("muted")
            if type(muted) is not bool:
                raise ToolError("muted must be true or false.")
            if shutil.which("wpctl"):
                await run_command(
                    "wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "1" if muted else "0"
                )
            else:
                await run_command("pactl", "set-sink-mute", "@DEFAULT_SINK@", "1" if muted else "0")
            return "Speakers muted." if muted else "Speakers unmuted."
        if name == "media_control":
            action = text_arg(args, "action", 20)
            if action not in {"play-pause", "next", "previous", "stop"}:
                raise ToolError("Unknown media action.")
            await run_command("playerctl", action)
            return "Media action completed: " + action
        if name == "set_brightness":
            percent = number_arg(args, "percent", 1, 100)
            await run_command("brightnessctl", "set", f"{percent}%")
            return f"Brightness set to {percent}%."
        if name == "notify":
            message = text_arg(args, "message")
            await run_command("notify-send", "--app-name=Becko", "--", "Becko", message)
            return "Desktop notification sent."
        if name == "set_reminder":
            seconds = number_arg(args, "seconds", 1, 86400)
            message = text_arg(args, "message", 500)
            if len(self.reminders) >= 50:
                raise ToolError("There are already 50 active reminders.")
            reminder_id = self._next_id
            self._next_id += 1

            async def fire() -> None:
                try:
                    await asyncio.sleep(seconds)
                    self.notify("Reminder: " + message)
                    if shutil.which("notify-send"):
                        try:
                            await run_command(
                                "notify-send", "--app-name=Becko", "--", "Becko reminder", message
                            )
                        except (RuntimeError, OSError, TimeoutError):
                            pass
                finally:
                    self.reminders.pop(reminder_id, None)

            self.reminders[reminder_id] = (message, asyncio.create_task(fire()))
            return f"Reminder #{reminder_id} in {seconds} seconds. Keep Becko open."
        if name == "list_reminders":
            return (
                "\n".join(f"#{key}: {value[0]}" for key, value in self.reminders.items())
                or "No active reminders."
            )
        if name == "cancel_reminder":
            reminder_id = number_arg(args, "id", 1, 1000000)
            if reminder_id not in self.reminders:
                raise ToolError("Reminder not found.")
            self.reminders.pop(reminder_id)[1].cancel()
            return f"Reminder #{reminder_id} cancelled."
        if name == "power_action":
            action = text_arg(args, "action", 20)
            if action not in {"lock", "suspend"}:
                raise ToolError("Only lock and suspend are supported.")
            if not await self.confirm(f"Allow Becko to {action} your Linux session now?"):
                return "Cancelled by the user. No system action was taken."
            await run_command(
                "loginctl", "lock-session"
            ) if action == "lock" else await run_command("systemctl", "suspend")
            return "System action requested: " + action
        raise ToolError("Unknown or unsupported tool: " + name)

    async def close(self) -> None:
        tasks = [task for _, task in self.reminders.values()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self.reminders.clear()
        # Apps are independent desktop processes; never terminate them on exit.
        self._children.clear()
