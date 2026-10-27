from __future__ import annotations

import os
import platform
import shutil

from .config import Settings, config_dir, state_dir


def audio_devices() -> list[dict]:
    import sounddevice as sd

    return [
        {
            "index": i,
            "name": device["name"],
            "inputs": device["max_input_channels"],
            "outputs": device["max_output_channels"],
            "default_sample_rate": device["default_samplerate"],
        }
        for i, device in enumerate(sd.query_devices())
    ]


def diagnose(settings: Settings) -> dict:
    result: dict = {
        "platform": platform.system(),
        "python": platform.python_version(),
        "session": os.getenv("XDG_SESSION_TYPE", "unknown"),
        "config": str(config_dir() / "config.json"),
        "state": str(state_dir()),
        "api_key_configured": bool(settings.effective_key),
        "text_model": settings.text_model,
        "live_model": settings.live_model,
        "voice": settings.voice,
        "utilities": {
            name: bool(shutil.which(name))
            for name in (
                "xdg-open",
                "wpctl",
                "pactl",
                "notify-send",
                "playerctl",
                "brightnessctl",
                "grim",
                "maim",
                "wl-copy",
                "xclip",
            )
        },
    }
    try:
        import sounddevice as sd

        devices = audio_devices()
        sd.check_input_settings(
            device=settings.input_device, channels=1, dtype="int16", samplerate=16000
        )
        sd.check_output_settings(
            device=settings.output_device, channels=1, dtype="int16", samplerate=24000
        )
        result.update(audio_ready=True, audio_devices=devices, audio_error=None)
    except Exception as exc:
        result.update(audio_ready=False, audio_error=str(exc)[:500])
    return result
