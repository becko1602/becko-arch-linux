from unittest.mock import AsyncMock

import pytest

from becko_arch.commands import quick_command
from becko_arch.config import Settings
from becko_arch.engine import TextAssistant
from becko_arch.history import History


@pytest.mark.parametrize(
    "text,query",
    [
        ("YouTubega kir, o'zbek qo'shiqlari deb qidir", "o'zbek qo'shiqlari"),
        ("Youtubedan English lessons qidir", "English lessons"),
        ("Search for Arch Linux on YouTube", "Arch Linux"),
        ("search YouTube for Python & Linux", "Python & Linux"),
    ],
)
def test_bilingual_search_shortcuts(text, query):
    assert quick_command(text) == ("youtube_search", {"query": query})


@pytest.mark.parametrize(
    "text", ["do not open youtube", "What is YouTube?", "explain Linux", "YouTubedan"]
)
def test_conversation_is_not_executed(text):
    assert quick_command(text) is None


async def test_shortcut_does_not_need_api_key(monkeypatch):
    client = AsyncMock()
    monkeypatch.setattr("becko_arch.engine.genai.Client", client)
    router = AsyncMock()
    router.execute.return_value = {"result": "YouTube search opened: Linux"}
    answer = await TextAssistant(Settings(), router, History(False)).ask("search YouTube for Linux")
    assert "Linux" in answer
    router.execute.assert_awaited_once_with("youtube_search", {"query": "Linux"})
    client.assert_not_called()
