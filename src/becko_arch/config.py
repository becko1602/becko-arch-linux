"""XDG configuration. Credentials never live inside the source checkout."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from platformdirs import user_config_path, user_state_path

from .voices import DEFAULT_VOICE, VOICE_NAMES


class ConfigurationError(ValueError):
    pass


def config_dir() -> Path:
    override = os.getenv("BECKO_CONFIG_HOME")
    return Path(override).expanduser() if override else user_config_path("becko")


def state_dir() -> Path:
    override = os.getenv("BECKO_STATE_HOME")
    return Path(override).expanduser() if override else user_state_path("becko")


def private_write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=".becko-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@dataclass
class Settings:
    api_key: str = ""
    text_model: str = "gemini-3.8-flash"
    live_model: str = "gemini-3.8-live"
    voice: str = DEFAULT_VOICE
    language: str = "auto"
    input_device: int | None = None
    output_device: int | None = None
    save_history: bool = True

    def validate(self) -> None:
        if any(
            not isinstance(getattr(self, name), str)
            for name in ("api_key", "text_model", "live_model", "voice", "language")
        ):
            raise ConfigurationError("Configuration text fields must be strings.")
        if self.voice not in VOICE_NAMES:
            raise ConfigurationError("Unknown voice. Use becko voices to list supported names.")
        if not self.text_model.strip() or not self.live_model.strip():
            raise ConfigurationError("Both model names are required.")
        for name in ("input_device", "output_device"):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 0):
                raise ConfigurationError(f"{name} must be a non-negative device index or null.")
        if type(self.save_history) is not bool:
            raise ConfigurationError("save_history must be true or false.")
        self.api_key = self.api_key.strip()

    @property
    def effective_key(self) -> str:
        return next(
            (
                os.getenv(name, "").strip()
                for name in ("BECKO_GEMINI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")
                if os.getenv(name, "").strip()
            ),
            self.api_key.strip(),
        )

    @classmethod
    def load(cls) -> Settings:
        path = config_dir() / "config.json"
        if not path.exists():
            return cls()
        try:
            raw = json.loads(path.read_text())
            if not isinstance(raw, dict):
                raise ConfigurationError("Configuration must be a JSON object.")
            allowed = {field.name for field in fields(cls)}
            result = cls(**{key: value for key, value in raw.items() if key in allowed})
            result.validate()
            return result
        except (OSError, ValueError, TypeError) as exc:
            raise ConfigurationError(
                f"Could not read {path}. Fix or rename it, then retry."
            ) from exc

    def save(self) -> None:
        self.validate()
        private_write(config_dir() / "config.json", asdict(self))

    def public(self) -> dict:
        values = asdict(self)
        values["api_key"] = "configured" if self.effective_key else "not configured"
        return values
