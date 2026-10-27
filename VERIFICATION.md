# Local verification

Verified on the target Arch Linux machine with Wayland, Python 3.11.16, google-genai 2.33.0, Textual 8.2.8 and sounddevice 0.5.6.

- Ruff checks and formatting; **42 automated tests passed**.
- Automated configuration, filesystem-permission, CLI, Linux-tool, subprocess-timeout, audio-buffer, fake-SDK lifecycle and headless terminal interaction tests.
- Source distribution and wheel build; wheel includes the terminal stylesheet and `becko` console entry point.
- Real PortAudio microphone and speaker streams opened, briefly sampled locally, then closed; no samples saved or transmitted.
- Installed launcher at `~/.local/bin/becko` and desktop application entry.
- Actual PTY session opened via `becko`, accepted `/status` and exited successfully with Ctrl+Q.
- `becko doctor --json` reported Linux, Wayland, audio readiness and Charon as the default voice.

No Gemini API key was configured during verification. A cloud conversation, speech understanding and live AI response still require the user's own valid key/model access. Tests use fake SDK responses and do not pretend to verify paid network calls. Optional playerctl was absent on the target machine; that tool reports a missing-utility error until installed. Lock/suspend and other disruptive desktop actions were mocked, not executed on the user's session.
