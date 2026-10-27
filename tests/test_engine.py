import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from google.genai import types

from becko_arch.audio import AudioIO
from becko_arch.config import Settings
from becko_arch.engine import LiveAssistant, TextAssistant, friendly_error, live_config
from becko_arch.history import History
from becko_arch.tools import ToolRouter


async def test_missing_key_never_calls_api(monkeypatch):
    constructor = AsyncMock()
    monkeypatch.setattr("becko_arch.engine.genai.Client", constructor)
    assistant = TextAssistant(Settings(), ToolRouter(AsyncMock(), lambda _: None), History(False))
    with pytest.raises(ValueError, match="No Gemini API key"):
        await assistant.ask("hello")
    constructor.assert_not_called()


def test_live_config_has_real_sdk_fields_and_voice():
    config = live_config(Settings())
    assert config.response_modalities == [types.Modality.AUDIO]
    assert config.speech_config.voice_config.prebuilt_voice_config.voice_name == "Charon"
    assert config.input_audio_transcription is not None
    assert config.tools[0].function_declarations


def test_errors_redact_keys():
    settings = Settings(api_key="do-not-print-this-secret")
    assert "do-not-print" not in friendly_error(
        RuntimeError("failed do-not-print-this-secret"), settings
    )
    assert "quota" in friendly_error(RuntimeError("429"), settings)


def text_response(text):
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(content=types.Content(role="model", parts=[types.Part(text=text)]))
        ]
    )


async def test_text_tool_loop_returns_real_result(monkeypatch):
    call = types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(
                                id="call-17", name="system_status", args={}
                            )
                        )
                    ],
                )
            )
        ]
    )
    generate = AsyncMock(side_effect=[call, text_response("Linux status retrieved.")])
    close = AsyncMock()
    client = SimpleNamespace(
        aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate), aclose=close)
    )
    monkeypatch.setattr("becko_arch.engine.genai.Client", lambda **kwargs: client)
    router = ToolRouter(AsyncMock(), lambda _: None)
    router.execute = AsyncMock(return_value={"result": "Linux RAM 20%"})
    history = History(False)
    answer = await TextAssistant(Settings(api_key="test-key"), router, history).ask("status")
    assert answer == "Linux status retrieved."
    router.execute.assert_awaited_once_with("system_status", {})
    assert generate.await_count == 2
    assert generate.await_args.kwargs["contents"][-1].parts[0].function_response.id == "call-17"
    assert generate.await_args.kwargs["contents"][-1].parts[0].function_response.response == {
        "result": "Linux RAM 20%"
    }
    assert [turn["role"] for turn in history.turns] == ["user", "model"]
    close.assert_awaited_once()


async def test_audio_queue_is_bounded_and_muting_drops_frames():
    audio = AudioIO()
    audio._closed = False
    for _ in range(50):
        audio._enqueue(b"00")
    assert audio.incoming.qsize() == 12
    assert audio.input_overflows == 38
    audio.muted = True
    audio._enqueue(b"11")
    assert audio.incoming.qsize() == 12
    audio.queue_output(b"a" * (audio.MAX_OUTPUT + 1000))
    assert len(audio._output) == audio.MAX_OUTPUT
    audio.close()
    assert not audio._output
    assert audio.incoming.empty()


async def test_live_stop_closes_audio_and_connection(monkeypatch):
    events = []
    audio = SimpleNamespace(
        incoming=asyncio.Queue(),
        start=lambda: events.append("audio-start"),
        close=lambda: events.append("audio-close"),
        muted=False,
    )

    async def receive():
        await asyncio.Future()
        yield None

    session = SimpleNamespace(receive=receive)

    @asynccontextmanager
    async def connect(**kwargs):
        events.append("socket-open")
        try:
            yield session
        finally:
            events.append("socket-close")

    close = AsyncMock()
    monkeypatch.setattr(
        "becko_arch.engine.genai.Client",
        lambda **kwargs: SimpleNamespace(
            aio=SimpleNamespace(live=SimpleNamespace(connect=connect), aclose=close)
        ),
    )
    live = LiveAssistant(
        Settings(api_key="test-key"),
        ToolRouter(AsyncMock(), lambda _: None),
        lambda kind, text: events.append(kind),
    )
    live.audio = audio
    task = asyncio.create_task(live.run())
    for _ in range(100):
        if live.connected:
            break
        await asyncio.sleep(0.01)
    assert live.connected
    live.stop()
    await asyncio.wait_for(task, 1)
    assert not live.connected
    assert "audio-close" in events
    assert "socket-close" in events
    close.assert_awaited_once()
