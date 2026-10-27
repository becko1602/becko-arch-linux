import json
import subprocess
import sys


def test_cli_version_and_redacted_config():
    result = subprocess.run(
        [sys.executable, "-m", "becko_arch.cli", "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Becko Arch Linux" in result.stdout
    result = subprocess.run(
        [sys.executable, "-m", "becko_arch.cli", "config"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout)["api_key"] == "not configured"


def test_cli_noninteractive_default_gives_guidance():
    result = subprocess.run(
        [sys.executable, "-m", "becko_arch.cli"], capture_output=True, text=True
    )
    assert result.returncode == 1
    assert "interactive terminal" in result.stdout
