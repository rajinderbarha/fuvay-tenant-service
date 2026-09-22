"""Reusable Instagram artwork and labels for admin-authored service problems."""
from __future__ import annotations

import ipaddress
from functools import lru_cache
from urllib.parse import urlsplit, urlunsplit

import structlog

from app.config import get_settings

logger = structlog.get_logger("messaging_gateway.problem_cards")

# Where Meta fetches the fallback card art. The PNGs in
# assets/social-problem-cards are hosted here byte-for-byte (checked
# 2026-09-22); a changed PNG must be re-uploaded under the same public id.
# Meta fetches from its own servers, so this must be public HTTPS: the API
# itself is plain HTTP on the VPS, and api.fuvay.in is not routed to it.
DEFAULT_CARD_BASE_URL = (
    "https://res.cloudinary.com/dr1b4ezct/image/upload/"
    "serviceos/social-problem-cards"
)
_OLD_ASSET_PATH = "/serviceos/social-problem-cards/"
_CARD_KEYS = frozenset({"cooling", "leak", "noise", "power", "smell", "clean", "install", "other"})

# Keep the entire uploaded picture visible inside Instagram's square card.
# c_fill cropped the edges of portrait photos and wide logos.
INSTAGRAM_CARD_TRANSFORMATION = "c_pad,b_white,h_960,w_960,q_auto:good,f_jpg"
_LEGACY_CARD_TRANSFORMATION = "c_fill,g_auto,h_960,w_960,q_auto:good,f_jpg"

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


@lru_cache(maxsize=8)
def _card_base(configured: str) -> str:
    """The configured card host, or the hosted copy if Meta could not reach it."""
    base = configured.strip().rstrip("/")
    if _public_https_url(base):
        return base
    # A localhost, LAN or plain-http override blanks every card with no error
    # anywhere. Keep the cards working and leave one line in the log.
    logger.warning("messaging_gateway.card_base_not_public", configured=configured)
    return DEFAULT_CARD_BASE_URL


def _card_asset_url(key: str) -> str:
    return f"{_card_base(str(get_settings().INSTAGRAM_CARD_PUBLIC_BASE_URL or ''))}/{key}.png"


def problem_card_image(name: str) -> str:
    key, _ = problem_card_family(name)
    return _card_asset_url(key)


def problem_card_symbol(name: str) -> str:
    _, symbol = problem_card_family(name)
    return symbol


def _public_https_url(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        if (parsed.scheme != "https" or not host or parsed.username or parsed.password
                or any(char.isspace() or ord(char) < 32 for char in value)):
            return False
        parsed.port  # Reject malformed port values.
        try:
            return ipaddress.ip_address(host).is_global
        except ValueError:
            return host not in {"localhost", "localhost.localdomain"}
    except ValueError:
        return False


def instagram_card_image_url(value: object, *, fallback_name: str = "") -> str:
    """Return small, square artwork that Meta can fetch reliably."""
    raw = str(value or "").strip()
    if not _public_https_url(raw):
        raw = problem_card_image(fallback_name)
    else:
        parsed = urlsplit(raw)
        if parsed.hostname == "res.cloudinary.com" and _OLD_ASSET_PATH in parsed.path:
            # A saved picker/booking context can still carry a bundled card
            # URL with an old crop in front of the asset id. Rebuild it from
            # the key, so it gets the current host and the padding below.
            asset_key = parsed.path.rsplit("/", 1)[-1].removesuffix(".png")
            if asset_key in _CARD_KEYS:
                raw = _card_asset_url(asset_key)
    parsed = urlsplit(raw)
    if (
        (parsed.hostname or "").lower() == "res.cloudinary.com"
        and "/image/upload/" in parsed.path
        and f"/{INSTAGRAM_CARD_TRANSFORMATION}/" not in parsed.path
    ):
        if f"/{_LEGACY_CARD_TRANSFORMATION}/" in parsed.path:
            path = parsed.path.replace(
                f"/{_LEGACY_CARD_TRANSFORMATION}/",
                f"/{INSTAGRAM_CARD_TRANSFORMATION}/", 1,
            )
        else:
            path = parsed.path.replace(
                "/image/upload/",
                f"/image/upload/{INSTAGRAM_CARD_TRANSFORMATION}/", 1,
            )
        return urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment))
    return raw
