# Becko for Arch Linux

A native Linux voice and desktop assistant that opens when you type **`becko`**. It provides a full-screen terminal UI, real Gemini Live speech conversations with the Charon voice, text chat, and Linux desktop tools. Works in Wayland and X11 sessions; standard terminal chat also works without a graphical display.

## Install on Arch Linux

```bash
sudo pacman -S --needed uv portaudio pipewire pipewire-pulse wireplumber xdg-utils libnotify
git clone https://github.com/becko1602/becko-arch-linux.git
cd becko-arch-linux
bash install.sh
becko
```

The installer creates an isolated `uv` tool environment with Python 3.11 and the `becko` launcher in `~/.local/bin`. It also adds a **Becko** desktop application entry. The source directory must remain available because the install is editable. It does not modify the Windows Becko repo or your shell configuration. Existing PulseAudio installations can also use PortAudio; switching your audio server is not required if sound already works.

If `~/.local/bin` is absent from PATH, add `export PATH="$HOME/.local/bin:$PATH"` to your shell configuration and open a new terminal. If `becko` is already another installed application, inspect it before replacing it; `uv` does not overwrite conflicting executables by default.

Optional desktop utilities:

```bash
sudo pacman -S --needed playerctl brightnessctl grim wl-clipboard
# For X11 screenshots, install maim instead of grim.
```

Hardware brightness requires your normal user to have permission to access the backlight. Screenshots use `grim` on wlroots/Hyprland/Sway and `maim` on X11. Other Wayland compositors may reject capture; voice and text continue to work.

## First-time API setup

```bash
becko setup
becko doctor
becko
```

Get your own key from https://aistudio.google.com/apikey. `becko setup` uses a hidden prompt; it never accepts a key as a shell argument. You can also press **F3** inside Becko and paste the key into the password field. Without a key the UI, local commands and explicit typed YouTube shortcuts work; other AI requests show a setup message.

Environment variables take priority over the saved key: `BECKO_GEMINI_API_KEY`, then `GEMINI_API_KEY`, then `GOOGLE_API_KEY`. Set them securely in your environment; do not paste actual credentials into commands saved in shell history or commit them.

The default model identifiers are `gemini-3.8-live` and `gemini-3.8-flash`, following the Google model documentation checked during development. Model availability, region access and quotas depend on your Google account. Change models at any time in F3 Settings or with `becko config --live-model MODEL --text-model MODEL`. Quota/authentication/model errors are shown honestly; no AI answers or grades are fabricated.

## Uzbek / English voice and quick tasks

Run `becko setup` once to save your own Gemini API key, then run `becko`.
Voice connects automatically; F4 mutes and F2 disconnects. `becko --text` starts without voice.
The assistant follows the language you speak, including Uzbek and English. You can set a preference with `becko config --language Uzbek` (or `English` / `auto`).

Try saying:

- “YouTubega kir, o‘zbek qo‘shiqlari deb qidir.”
- “Search YouTube for Arch Linux tutorials.”
- “Firefoxni och.” / “Open Firefox.”
- “Ovozni 40 foiz qil.” / “Set volume to 40 percent.”

YouTube search opens the actual results page directly in one tool call. It does not automatically select or play a video. Explicit typed YouTube requests also work without an API key, skipping the cloud round trip. Voice and general AI requests require internet and Gemini access; response time depends on the network and service.

## Controls

| Control | Action |
| --- | --- |
| Enter | Send typed text or a local slash command |
| F1 | Local command help |
| F2 | Connect/disconnect live voice |
| F3 | API key, voice, models, language, audio devices and history settings |
| F4 | Mute/unmute the microphone during a live session |
| F6 | Confirm sharing one screenshot with Gemini |
| Ctrl+Q | Disconnect audio, cancel session reminders and exit |

Running `becko` automatically connects live voice and opens the microphone when an API key is configured. Use `becko --text` to launch with the microphone off. Without a key, the microphone stays off; configure it with `becko setup` or F3. During a live session microphone PCM is sent to Gemini. Disconnect releases the audio streams. Audio is never saved to disk. Echo gating pauses mic input during speaker playback; headphones improve conversation quality. A continuous live session has model-specific duration limits; reconnect using F2 after an expiry or network failure.

Recommended terminal size: 80×24 or larger. The sidebar is hidden in narrow terminals. Every action is available by keyboard; confirmation dialogs focus Cancel by default.

## Local commands (no API key required)

```text
/help
/status
/devices
/open firefox
/open terminal
/search Arch Linux PipeWire documentation
/volume 40
/mute
/unmute
/media play-pause
/brightness 60
/remind 10m Take a break
/reminders
/cancel 1
/voice Charon
/settings
/connect
/disconnect
/clear
/quit
```

App launching is restricted to a built-in list (`/help` shows it). Typed/model text never becomes a shell command. Gemini may call the same tools with structured arguments, and lock/suspend operations require a separate local confirmation. Browser search opens a real search page; the model is not supplied with scraped search results. Screen sharing requires an explicit local confirmation and sends only one temporary screenshot; images are not written to history. Reminders run while the app stays open and are cancelled when it exits.

## Command-line utilities

```bash
becko --version
becko --help
becko doctor --json
becko devices
becko voices
becko config                 # Redacted config; never prints keys
becko config --voice Charon
becko config --input-device 3 --output-device 4
becko config --no-history
becko config --clear-key
becko ask "Explain the difference between Wayland and X11"
```

`becko ask` is a one-shot text client; short-lived CLI sessions cancel any in-process reminders when they end. Use the interactive app for reminders and live voice. A selected numeric audio device index may change after reconnecting USB/Bluetooth devices. Leave device fields blank in Settings to use the default devices.

## Data locations

- Config and API key: `$XDG_CONFIG_HOME/becko/config.json` (default `~/.config/becko/config.json`). Atomic writes create files with mode **0600** inside a newly-created **0700** directory.
- Optional conversation history: `$XDG_STATE_HOME/becko/history.json` (default `~/.local/state/becko/history.json`). Stores text transcripts locally, capped at 100 entries; up to 20 recent turns are supplied as conversation context to Gemini.
- `BECKO_CONFIG_HOME` / `BECKO_STATE_HOME` override those directories, useful for isolated testing.

Keys are not logged or included in public configuration output. `.gitignore` excludes runtime credentials, transcripts, environments and recordings. Chat/history travels to Gemini when used as model context; this is a cloud AI application with local desktop control, not an offline language model. Disabling history stops disk writes; `/clear` asks before removing stored conversation text. Reconnect voice to clear its active server context.

## Development and verification

```bash
uv venv --python 3.11
uv pip install --python .venv/bin/python -e '.[dev]'
.venv/bin/ruff check src tests
.venv/bin/pytest
.venv/bin/python -m compileall -q src
uv build
```

Tests isolate XDG paths and mock the network/system actions. Headless Textual tests exercise typing, settings, keyboard controls and confirmation dialogs; engine tests use the actual SDK types with fake sessions, not a paid API call. Device diagnostics and local stream smoke tests can verify real Linux hardware separately. A successful cloud conversation additionally requires your own valid Gemini key and model access.

## Architecture

`src/becko_arch/`: `ui.py` (Textual), `cli.py` (installed entry point), `engine.py` (Gemini Live and text), `audio.py` (bounded raw PCM callbacks), `tools.py` (Linux actions), `process.py` (argument-array subprocesses), `config.py` / `history.py` (XDG storage), `diagnostics.py`, `screen.py`, and shared `voices.py`.

PCM input is 16-bit little-endian mono at 16 kHz; output is mono at 24 kHz. Bounded queues/buffers prevent audio from growing without limit; cancelling a session closes the WebSocket and audio devices. API key setup and diagnostics do not contact Google.

References: [Gemini Live SDK](https://ai.google.dev/gemini-api/docs/live-api/get-started-sdk), [Live tools](https://ai.google.dev/gemini-api/docs/live-api/tools), [Textual testing](https://textual.textualize.io/guide/testing/).

MIT licensed. Based on Becko / Kaizumi by Musayev Doniyor (Kaizo), with original attribution preserved. See [NOTICE.md](NOTICE.md) and [LICENSE](LICENSE).
