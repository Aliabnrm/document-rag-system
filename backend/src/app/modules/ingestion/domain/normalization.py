import re
import unicodedata

NORMALIZER_VERSION = "fa-en-normalizer-v1"

_ARABIC_TO_PERSIAN = str.maketrans(
    {
        "\u064a": "\u06cc",
        "\u0649": "\u06cc",
        "\u0643": "\u06a9",
        "\u06c0": "\u0647\u0654",
        "\u0629": "\u0647",
        "\u0624": "\u0648\u0654",
    }
)
_ARABIC_DIACRITICS = re.compile(r"[\u064b-\u065f\u0670\u06d6-\u06ed]")
_HORIZONTAL_WHITESPACE = re.compile(r"[^\S\r\n\u200c]+")
_AROUND_HALF_SPACE = re.compile(r"[ \t]*\u200c[ \t]*")
_EXCESS_BLANK_LINES = re.compile(r"\n{3,}")


def normalize_for_retrieval(value: str) -> str:
    """Normalize a retrieval copy without modifying citation source text."""
    normalized = unicodedata.normalize("NFC", value).translate(_ARABIC_TO_PERSIAN)
    normalized = normalized.replace("\u0640", "")
    normalized = _ARABIC_DIACRITICS.sub("", normalized)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _AROUND_HALF_SPACE.sub("\u200c", normalized)
    normalized = _HORIZONTAL_WHITESPACE.sub(" ", normalized)
    normalized = "\n".join(line.strip() for line in normalized.split("\n"))
    return _EXCESS_BLANK_LINES.sub("\n\n", normalized).strip()
