import pytest


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("BECKO_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("BECKO_STATE_HOME", str(tmp_path / "state"))
    for name in ("BECKO_GEMINI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(name, raising=False)
