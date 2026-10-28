import json
import stat

import pytest

from becko_arch.config import ConfigurationError, Settings, config_dir, state_dir
from becko_arch.history import History


def test_no_key_default_is_usable():
    settings = Settings.load()
    assert settings.voice == "Charon"
    assert settings.effective_key == ""
    assert settings.public()["api_key"] == "not configured"


def test_config_private_atomic_roundtrip():
    settings = Settings(api_key="  example-not-a-real-key  ", input_device=2)
    settings.save()
    assert Settings.load().api_key == "example-not-a-real-key"
    assert Settings.load().input_device == 2
    assert stat.S_IMODE((config_dir() / "config.json").stat().st_mode) == 0o600
    assert stat.S_IMODE(config_dir().stat().st_mode) == 0o700
    assert "example-not-a-real-key" not in json.dumps(settings.public())


def test_environment_priority(monkeypatch):
    settings = Settings(api_key="saved")
    monkeypatch.setenv("GOOGLE_API_KEY", "google")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini")
    monkeypatch.setenv("BECKO_GEMINI_API_KEY", " becko-env ")
    assert settings.effective_key == "becko-env"


@pytest.mark.parametrize(
    "raw",
    [
        [],
        None,
        {"voice": "not-real"},
        {"input_device": True},
        {"output_device": -1},
        {"save_history": "false"},
        {"api_key": 123},
    ],
)
def test_invalid_config_is_not_silently_overwritten(raw):
    config_dir().mkdir()
    path = config_dir() / "config.json"
    path.write_text(json.dumps(raw))
    with pytest.raises(ConfigurationError):
        Settings.load()
    assert json.loads(path.read_text()) == raw


def test_history_caps_and_clears():
    history = History()
    for i in range(105):
        history.add("user", str(i))
    assert len(History().turns) == 100
    assert History().turns[0]["text"] == "5"
    history.clear()
    assert History().turns == []
    assert stat.S_IMODE((state_dir() / "history.json").stat().st_mode) == 0o600


def test_history_off_has_no_disk_writes():
    history = History(False)
    history.add("user", "private")
    assert not (state_dir() / "history.json").exists()


def test_corrupt_history_is_retained():
    state_dir().mkdir()
    path = state_dir() / "history.json"
    path.write_text("broken JSON")
    history = History()
    history.add("user", "hello")
    assert history.warning
    assert path.read_text() == "broken JSON"


@pytest.mark.parametrize("role", [[], {}, None, 42])
def test_history_ignores_invalid_roles(role):
    state_dir().mkdir()
    path = state_dir() / "history.json"
    path.write_text(
        json.dumps(
            [
                {"role": role, "text": "invalid"},
                {"role": "user", "text": "hello"},
            ]
        )
    )

    history = History()

    assert history.turns == [{"role": "user", "text": "hello"}]
    assert not history.warning
