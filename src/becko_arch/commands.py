"""Conservative shortcuts for explicit browser commands, without a cloud round trip."""

from __future__ import annotations

import re


def quick_command(text: str) -> tuple[str, dict] | None:
    text = text.strip().rstrip(".!?")
    text = text.translate(str.maketrans({"‘": "'", "’": "'", "ʻ": "'", "ʼ": "'"}))
    flags = re.IGNORECASE
    if re.fullmatch(r"(?:open youtube|youtube(?:ga|\s+ga)?\s+(?:kir|och))", text, flags):
        return "open_url", {"url": "https://www.youtube.com"}
    patterns = (
        r"(?:search(?:\s+for)?\s+|find\s+)(.+?)\s+on\s+youtube",
        r"(?:search\s+youtube\s+for|youtube\s+search)\s+(.+)",
        r"youtube(?:ga|\s+ga)?\s+kir\s*[,;]?\s+(.+?)\s+(?:deb\s+)?qidir",
        r"youtube(?:dan|da|\s+dan|\s+da)\s+(.+?)\s+(?:deb\s+)?(?:qidir|izla|top)",
    )
    for pattern in patterns:
        match = re.fullmatch(pattern, text, flags)
        if match:
            query = match.group(1).strip().strip('"')
            if query:
                return "youtube_search", {"query": query}
    return None
