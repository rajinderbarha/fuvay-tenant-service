"""Reusable Instagram artwork and labels for admin-authored service problems."""
from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

# Public, non-sensitive project assets. Keeping this unversioned means an art
# correction can be published without changing the booking service; Cloudinary
# invalidation controls the cache when that happens.
ASSET_BASE_URL = (
    "https://res.cloudinary.com/dr1b4ezct/image/upload/"
    "serviceos/social-problem-cards"
)

INSTAGRAM_CARD_TRANSFORMATION = "c_fill,g_auto,h_960,w_960,q_auto:good,f_jpg"

_FAMILIES = (
    (("cool", "cold", "temperature", "freez"), "cooling", "❄️"),
    (("leak", "water", "drip", "drain"), "leak", "💧"),
    (("noise", "sound", "vibrat", "rattl"), "noise", "🔊"),
    (("power", "electric", "start", "turn on", "dead"), "power", "⚡"),
    (("smell", "odor", "smoke", "burn"), "smell", "〰️"),
    (("clean", "dust", "dirty", "filter"), "clean", "✨"),
    (("install", "replace", "new"), "install", "🛠️"),
)

_PLUMBING_INSTALL_TERMS = (
    "change", "tap", "faucet", "basin", "sink", "commode",
    "toilet", "fixture", "plumb",
)


def problem_card_family(name: str) -> tuple[str, str]:
    """Return ``(asset key, symbol)`` inferred from customer-facing wording."""
    value = str(name or "").casefold()
    if any(word in value for word in _PLUMBING_INSTALL_TERMS):
        # Plumbing type rows commonly have no uploaded artwork yet. Use the
        # public install card rather than the generic/unknown placeholder.
        install = next((item for item in _FAMILIES if item[1] == "install"), None)
        if install:
            return install[1], install[2]
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


def instagram_card_image_url(value: object, *, fallback_name: str = "") -> str:
    """Return small, square artwork that Meta can fetch reliably."""
    raw = str(value or "").strip()
    if not raw.startswith("https://"):
        raw = problem_card_image(fallback_name)
    parsed = urlsplit(raw)
    if (
        (parsed.hostname or "").lower() == "res.cloudinary.com"
        and "/image/upload/" in parsed.path
        and f"/{INSTAGRAM_CARD_TRANSFORMATION}/" not in parsed.path
    ):
        path = parsed.path.replace(
            "/image/upload/",
            f"/image/upload/{INSTAGRAM_CARD_TRANSFORMATION}/",
            1,
        )
        return urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment))
    return raw
