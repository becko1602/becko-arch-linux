#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v uv >/dev/null 2>&1; then
  echo "Install the Arch packages first: sudo pacman -S --needed uv portaudio pipewire pipewire-pulse wireplumber xdg-utils libnotify"
  exit 1
fi
uv tool install --python 3.11 --editable "$project_dir"
becko_bin="${UV_TOOL_BIN_DIR:-$HOME/.local/bin}/becko"
if [[ ! -x "$becko_bin" ]]; then
  echo "uv installed the tool. Run 'uv tool dir --bin' to locate becko, then add that directory to PATH."
  exit 1
fi
mkdir -p "${XDG_DATA_HOME:-$HOME/.local/share}/applications"
python3 - "$project_dir" "$becko_bin" <<'DESKTOP'
import os,sys
from pathlib import Path
source,executable=sys.argv[1:]
destination=Path(os.getenv("XDG_DATA_HOME",str(Path.home()/".local/share")))/"applications/becko.desktop"
escaped=executable.replace("\\","\\\\").replace('"','\\"').replace('`','\\`').replace('$','\\$').replace('%','%%')
destination.write_text(f'[Desktop Entry]\nType=Application\nName=Becko\nComment=Arch Linux voice assistant\nExec="{escaped}"\nIcon={source}/assets/becko-arch.svg\nTerminal=true\nCategories=Utility;\nKeywords=AI;Voice;Assistant;\n')
DESKTOP
printf '\nBecko installed. Run: becko\nFirst-time setup: becko setup\nDiagnostics: becko doctor\n'
case ":$PATH:" in
  *":$(dirname "$becko_bin"):"*) ;;
  *) echo "Add $(dirname "$becko_bin") to your shell PATH, then open a new terminal." ;;
esac
