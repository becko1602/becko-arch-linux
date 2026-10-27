"""Shared Becko voice settings; no GUI, audio device or API key required."""

DEFAULT_VOICE = "Charon"

VOICES = {
    "Achernar": "mayin (Soft)",
    "Achird": "do'stona (Friendly)",
    "Algenib": "bo'g'iq (Gravelly)",
    "Algieba": "silliq (Smooth)",
    "Alnilam": "qat'iy (Firm)",
    "Aoede": "engil ayol (Breezy)",
    "Autonoe": "yorqin (Bright)",
    "Callirrhoe": "erkin (Easy-going)",
    "Charon": "chuqur erkak (Informative)",
    "Despina": "silliq (Smooth)",
    "Enceladus": "nafasli (Breathy)",
    "Erinome": "aniq (Clear)",
    "Fenrir": "qattiq erkak (Excitable)",
    "Gacrux": "etuk (Mature)",
    "Iapetus": "aniq (Clear)",
    "Kore": "jonli ayol (Firm)",
    "Laomedeia": "quvnoq (Upbeat)",
    "Leda": "yoshlik (Youthful)",
    "Orus": "qat'iy erkak (Firm)",
    "Puck": "quvnoq erkak (Upbeat)",
    "Pulcherrima": "dadil (Forward)",
    "Rasalgethi": "ma'lumotli (Informative)",
    "Sadachbia": "jonli (Lively)",
    "Sadaltager": "bilimdon (Knowledgeable)",
    "Schedar": "tinch (Even)",
    "Sulafat": "iliq (Warm)",
    "Umbriel": "erkin (Easy-going)",
    "Vindemiatrix": "muloyim (Gentle)",
    "Zephyr": "yorqin ayol (Bright)",
    "Zubenelgenubi": "oddiy (Casual)",
}
VOICE_NAMES = list(VOICES)


def normalize_voice(text) -> str:
    """Map user wording to a canonical Gemini voice name, or '' if unknown."""
    v = str(text or "").strip().lower().replace("-", " ").replace("_", " ")
    aliases = {
        "default": DEFAULT_VOICE,
        "auto": DEFAULT_VOICE,
        "standart": DEFAULT_VOICE,
        "normal": DEFAULT_VOICE,
        "classic": DEFAULT_VOICE,
        "aoede": "Aoede",
        "charon": "Charon",
        "fenrir": "Fenrir",
        "kore": "Kore",
        "puck": "Puck",
        "zephyr": "Zephyr",
        "ayol": "Aoede",
        "erkak": "Charon",
        "male": "Charon",
        "man": "Charon",
    }
    v = aliases.get(v, v.title())
    return v if v in VOICE_NAMES else ""


def get_voice_from_memory(memory: dict | None) -> str:
    """Returns the saved Gemini voice name (defaults to Charon)."""
    prefs = memory.get("preferences", {}) if isinstance(memory, dict) else {}
    if not isinstance(prefs, dict):
        prefs = {}
    entry = prefs.get("assistant_voice")
    voice = entry.get("value") if isinstance(entry, dict) else entry
    voice = normalize_voice(voice)
    return voice or DEFAULT_VOICE
