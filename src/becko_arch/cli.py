"""Installed `becko` entry point; no virtualenv activation required."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import sys

from rich.console import Console
from rich.table import Table

from . import __version__
from .config import ConfigurationError, Settings, config_dir
from .diagnostics import audio_devices, diagnose
from .voices import VOICES

console = Console()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="becko", description="Becko — native Arch Linux voice and desktop assistant"
    )
    parser.add_argument("--version", action="version", version=f"Becko Arch Linux {__version__}")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("setup", help="Save your API key securely using a hidden prompt")
    doctor = sub.add_parser(
        "doctor", help="Check Linux/audio/key configuration without contacting Gemini"
    )
    doctor.add_argument("--json", action="store_true")
    sub.add_parser("devices", help="List microphone and speaker device indices")
    sub.add_parser("voices", help="List supported Gemini voices")
    ask = sub.add_parser("ask", help="Ask Gemini from a plain terminal (text only)")
    ask.add_argument("prompt", nargs="+")
    config = sub.add_parser(
        "config", help="Show redacted configuration or update model/voice settings"
    )
    config.add_argument("--text-model")
    config.add_argument("--live-model")
    config.add_argument("--voice", choices=list(VOICES))
    config.add_argument("--input-device", type=int)
    config.add_argument("--output-device", type=int)
    config.add_argument("--no-history", action="store_true")
    config.add_argument("--clear-key", action="store_true")
    return parser


async def ask(settings: Settings, prompt: str) -> None:
    from .engine import TextAssistant
    from .history import History
    from .tools import ToolRouter

    async def confirm(message: str) -> bool:
        if not sys.stdin.isatty():
            return False
        return (await asyncio.to_thread(input, f"{message} [y/N] ")).strip().lower() == "y"

    router = ToolRouter(confirm, lambda message: console.print(message, markup=False))
    try:
        result = await TextAssistant(settings, router, History(settings.save_history)).ask(prompt)
        console.print(result, markup=False)
    finally:
        await router.close()


def main() -> None:
    args = build_parser().parse_args()
    try:
        settings = Settings.load()
        if args.command == "setup":
            if not sys.stdin.isatty():
                raise ValueError(
                    "Run becko setup in an interactive terminal; API keys are never accepted as command arguments."
                )
            console.print("Get a Gemini key from https://aistudio.google.com/apikey", markup=False)
            key = getpass.getpass("Gemini API key (hidden; blank cancels): ").strip()
            if not key:
                console.print("Cancelled. No settings changed.")
                return
            settings.api_key = key
            settings.save()
            console.print(
                f"Saved privately: {config_dir() / 'config.json'}\nRun becko to open the assistant.",
                markup=False,
            )
        elif args.command == "doctor":
            report = diagnose(settings)
            if args.json:
                print(json.dumps(report, ensure_ascii=False, indent=2))
            else:
                table = Table(title="Becko / Arch Linux diagnostics", show_lines=False)
                table.add_column("Check", style="cyan")
                table.add_column("Result")
                for name in (
                    "platform",
                    "python",
                    "session",
                    "audio_ready",
                    "api_key_configured",
                    "voice",
                    "live_model",
                    "config",
                    "state",
                ):
                    table.add_row(name, str(report.get(name)))
                console.print(table)
                if report.get("audio_error"):
                    console.print(str(report["audio_error"]), markup=False)
                if not report["api_key_configured"]:
                    console.print(
                        "Voice AI needs your Gemini key. Run: becko setup", style="yellow"
                    )
        elif args.command == "devices":
            print(json.dumps(audio_devices(), ensure_ascii=False, indent=2))
        elif args.command == "voices":
            for name, description in VOICES.items():
                console.print(f"{name:16} {description}", markup=False)
        elif args.command == "config":
            changed = False
            for field in ("text_model", "live_model", "voice", "input_device", "output_device"):
                if getattr(args, field) is not None:
                    setattr(settings, field, getattr(args, field))
                    changed = True
            if args.no_history:
                settings.save_history = False
                changed = True
            if args.clear_key:
                settings.api_key = ""
                changed = True
            if changed:
                settings.save()
            print(json.dumps(settings.public(), ensure_ascii=False, indent=2))
        elif args.command == "ask":
            asyncio.run(ask(settings, " ".join(args.prompt)))
        else:
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                raise ValueError(
                    "Open becko in an interactive terminal. For scripts use becko ask, becko doctor --json or becko --help."
                )
            from .ui import BeckoApp

            BeckoApp(settings).run()
    except KeyboardInterrupt:
        return
    except Exception as exc:
        if isinstance(exc, ConfigurationError):
            message = str(exc)
        else:
            from .engine import friendly_error

            message = friendly_error(exc, settings if "settings" in locals() else Settings())
        console.print(f"Becko: {message}", style="red", markup=False)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
