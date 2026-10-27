import asyncio

from textual.widgets import Input, RichLog

from becko_arch.config import Settings
from becko_arch.ui import BeckoApp, ConfirmScreen, SettingsScreen


async def test_local_commands_work_without_key_and_quit():
    app = BeckoApp(Settings(save_history=False))
    async with app.run_test(size=(110, 36)) as pilot:
        await pilot.press(*"/status", "enter")
        await app.workers.wait_for_complete()
        text = "\n".join(line.text for line in app.query_one("#chat", RichLog).lines)
        assert "Linux" in text
        assert app.live is None
        await pilot.press("ctrl+q")


async def test_voice_without_key_opens_settings_without_microphone():
    app = BeckoApp(Settings(save_history=False))
    async with app.run_test(size=(110, 36)) as pilot:
        await pilot.press("f2")
        await pilot.pause()
        assert isinstance(app.screen, SettingsScreen)
        assert app.screen.query_one("#api-key", Input).password
        assert app.live is None
        await pilot.press("escape")
        assert not isinstance(app.screen, SettingsScreen)


async def test_settings_save_private_file():
    app = BeckoApp(Settings(save_history=False))
    async with app.run_test(size=(110, 40)) as pilot:
        await pilot.press("f3")
        await pilot.pause()
        app.screen.query_one("#api-key", Input).value = "test-not-real-key"
        app.screen.query_one("#language", Input).value = "Uzbek"
        await pilot.click("#settings-save")
        await pilot.pause()
        assert Settings.load().language == "Uzbek"
        assert Settings.load().api_key == "test-not-real-key"


async def test_narrow_terminal_hides_sidebar():
    app = BeckoApp(Settings(save_history=False))
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        assert not app.query_one("#sidebar").display
        assert app.query_one("#prompt", Input).region.width <= 80
        await pilot.press(*"/help", "enter")
        await app.workers.wait_for_complete()
        assert app.query_one("#prompt", Input).value == ""


async def test_confirmation_defaults_to_cancel():
    app = BeckoApp(Settings(save_history=False))
    async with app.run_test(size=(100, 35)) as pilot:
        task = asyncio.create_task(app.confirm("Suspend?"))
        await pilot.pause()
        assert isinstance(app.screen, ConfirmScreen)
        assert app.screen.focused.id == "deny"
        await pilot.press("escape")
        assert await task is False


async def test_screen_share_with_no_key_does_not_capture(monkeypatch):
    from unittest.mock import AsyncMock

    capture = AsyncMock()
    monkeypatch.setattr("becko_arch.ui.capture_screen", capture)
    app = BeckoApp(Settings(save_history=False))
    async with app.run_test(size=(100, 35)) as pilot:
        await pilot.press("f6")
        await app.workers.wait_for_complete()
        capture.assert_not_called()
