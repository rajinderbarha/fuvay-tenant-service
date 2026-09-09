"""Reusable Instagram artwork and labels for admin-authored service problems."""
from __future__ import annotations

# Public, non-sensitive project assets. Keeping this unversioned means an art
# correction can be published without changing the booking service; Cloudinary
# invalidation controls the cache when that happens.
ASSET_BASE_URL = (
    "https://res.cloudinary.com/dr1b4ezct/image/upload/"
    "serviceos/social-problem-cards"
)

_FAMILIES = (
    (("cool", "cold", "temperature", "freez"), "cooling", "❄️"),
    (("leak", "water", "drip", "drain"), "leak", "💧"),
    (("noise", "sound", "vibrat", "rattl"), "noise", "🔊"),
    (("power", "electric", "start", "turn on", "dead"), "power", "⚡"),
    (("smell", "odor", "smoke", "burn"), "smell", "〰️"),
    (("clean", "dust", "dirty", "filter"), "clean", "✨"),
    (("install", "replace", "new"), "install", "🛠️"),
)


def problem_card_family(name: str) -> tuple[str, str]:
    """Return ``(asset key, symbol)`` inferred from customer-facing wording."""
    value = str(name or "").casefold()
    return next(
        ((key, symbol) for words, key, symbol in _FAMILIES
         if any(word in value for word in words)),
        ("other", "🔧"),
    )


def problem_card_image(name: str) -> str:
    key, _ = problem_card_family(name)
    return f"{ASSET_BASE_URL}/{key}.png"


def problem_card_symbol(name: str) -> str:
    _, symbol = problem_card_family(name)
    return symbol
