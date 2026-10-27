from unittest.mock import AsyncMock

import pytest

from becko_arch.tools import ToolRouter


@pytest.fixture
def router():
    return ToolRouter(AsyncMock(return_value=False), lambda message: None)


@pytest.mark.parametrize(
    "name,args",
    [
        ("open_app", {"app": "kitty; rm -rf /"}),
        ("open_url", {"url": "file:///etc/passwd"}),
        ("open_url", {"url": "https://user:secret@example.com"}),
        ("set_volume", {"percent": 101}),
        ("set_volume", {"percent": True}),
        ("set_brightness", {"percent": 0}),
        ("media_control", {"action": "next; reboot"}),
        ("power_action", {"action": "shutdown"}),
        ("shell", {"command": "id"}),
    ],
)
async def test_invalid_tool_arguments_do_not_run_processes(router, name, args, monkeypatch):
    run = AsyncMock()
    monkeypatch.setattr("becko_arch.tools.run_command", run)
    result = await router.execute(name, args)
    assert "error" in result
    run.assert_not_called()


async def test_volume_uses_argument_array(router, monkeypatch):
    run = AsyncMock(return_value="")
    monkeypatch.setattr("becko_arch.tools.run_command", run)
    monkeypatch.setattr("becko_arch.tools.shutil.which", lambda name: "/usr/bin/" + name)
    result = await router.execute("set_volume", {"percent": 40})
    assert "40%" in result["result"]
    run.assert_awaited_once_with("wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "40%")


async def test_power_refusal_does_nothing(router, monkeypatch):
    run = AsyncMock()
    monkeypatch.setattr("becko_arch.tools.run_command", run)
    result = await router.execute("power_action", {"action": "suspend"})
    assert "Cancelled" in result["result"]
    router.confirm.assert_awaited_once()
    run.assert_not_called()


async def test_confirmed_lock_uses_native_linux_command(monkeypatch):
    router = ToolRouter(AsyncMock(return_value=True), lambda _: None)
    run = AsyncMock(return_value="")
    monkeypatch.setattr("becko_arch.tools.run_command", run)
    await router.execute("power_action", {"action": "lock"})
    run.assert_awaited_once_with("loginctl", "lock-session")


async def test_reminders_list_cancel_and_cleanup(router):
    result = await router.execute("set_reminder", {"seconds": 60, "message": "break"})
    assert "#1" in result["result"]
    assert "break" in (await router.execute("list_reminders", {}))["result"]
    await router.execute("cancel_reminder", {"id": 1})
    assert not router.reminders
    await router.execute("set_reminder", {"seconds": 60, "message": "another"})
    await router.close()
    assert not router.reminders


async def test_real_system_status_is_reported(router):
    result = await router.execute("system_status", {})
    assert "Linux" in result["result"]
    assert "RAM" in result["result"]


async def test_subprocess_timeout_kills_child():
    import sys

    from becko_arch.process import run_command

    with pytest.raises(TimeoutError):
        await run_command(sys.executable, "-c", "import time;time.sleep(30)", timeout=0.05)
