"""Reusable Instagram artwork and labels for admin-authored service problems."""
from __future__ import annotations

import asyncio
import ipaddress
import time
from collections.abc import Sequence
from contextlib import AsyncExitStack
from functools import lru_cache
from urllib.parse import urlsplit, urlunsplit

import httpx
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


# ── Reachability ─────────────────────────────────────────────────────────────
#
# Everything above is URL *syntax*. Meta fetches card artwork from its own
# servers and, when that fetch fails, renders the card with a blank picture and
# tells us nothing — the send itself still returns 200. Syntax cannot separate
# the two cases: a deleted Cloudinary asset, an icon saved one extension short
# of the delivery id (`.../card.webp` where only `.../card.webp.webp`
# resolves), an SVG, a 20 MB photo and a host that refuses Meta's crawler are
# all perfectly well-formed public HTTPS.
#
# So each candidate is fetched once the way Meta would fetch it, the verdict is
# cached, and anything that does not come back as a renderable image falls back
# down a ladder: the admin's artwork, then the bundled card for that problem,
# then the hosted copy of it. If even that fails the element is sent with no
# `image_url` at all — a card with a title, a subtitle and a working button
# beats a card with a broken picture.

_VERIFY_UA = ("facebookexternalhit/1.1 "
              "(+http://www.facebook.com/externalhit_uatext.php)")
#: A good verdict is stable, so re-check rarely. A bad one is re-checked soon,
#: because the usual cause is an admin part-way through fixing the upload.
_VERIFY_OK_TTL_SECONDS = 6 * 60 * 60
_VERIFY_BAD_TTL_SECONDS = 10 * 60
_VERIFY_CACHE_MAX = 2048
#: Meta's ceiling for template artwork.
_MAX_CARD_BYTES = 8 * 1024 * 1024
#: Image types Meta will not render in a template, whatever the URL says.
_UNRENDERABLE_TYPES = ("image/svg", "image/heic", "image/heif", "image/avif",
                       "image/tiff", "image/x-icon", "image/vnd.microsoft.icon")

#: url -> (monotonic expiry, renderable)
_verdicts: dict[str, tuple[float, bool]] = {}


def _cached_verdict(url: str) -> bool | None:
    entry = _verdicts.get(url)
    if not entry:
        return None
    expires, renderable = entry
    if expires <= time.monotonic():
        _verdicts.pop(url, None)
        return None
    return renderable


def _remember_verdict(url: str, renderable: bool) -> None:
    if len(_verdicts) >= _VERIFY_CACHE_MAX:
        now = time.monotonic()
        for key, (expires, _) in list(_verdicts.items()):
            if expires <= now:
                _verdicts.pop(key, None)
        while len(_verdicts) >= _VERIFY_CACHE_MAX:
            _verdicts.pop(next(iter(_verdicts)))
    ttl = _VERIFY_OK_TTL_SECONDS if renderable else _VERIFY_BAD_TTL_SECONDS
    _verdicts[url] = (time.monotonic() + ttl, renderable)


def reset_artwork_cache() -> None:
    """Forget every cached verdict — for tests, and after an admin re-upload."""
    _verdicts.clear()


def _artwork_client(timeout: float) -> httpx.AsyncClient:
    """The HTTP client the checks run on — a seam the tests replace, so they
    never reach the network and never disturb the outbound Meta client."""
    return httpx.AsyncClient(follow_redirects=True, timeout=timeout,
                             headers={"User-Agent": _VERIFY_UA})


async def _fetchable(client: httpx.AsyncClient, url: str) -> bool:
    """True when Meta would get a renderable image back from `url`."""
    try:
        response = await client.get(url, headers={
            "Accept": "image/*,*/*;q=0.8",
            # The headers are all this needs; without a range a cold check
            # would pull the whole file for every card on every carousel.
            "Range": "bytes=0-2047",
        })
    except Exception as exc:  # noqa: BLE001 -- any failure means "use the card"
        logger.info("messaging_gateway.card.artwork_unreachable",
                    url=url, error=type(exc).__name__)
        return False

    content_type = (
        response.headers.get("content-type") or ""
    ).split(";")[0].strip().lower()
    total: int | None = None
    content_range = response.headers.get("content-range") or ""
    if "/" in content_range:
        declared = content_range.rsplit("/", 1)[-1].strip()
        total = int(declared) if declared.isdigit() else None
    elif response.status_code == 200:
        declared = (response.headers.get("content-length") or "").strip()
        total = int(declared) if declared.isdigit() else None

    renderable = (
        response.status_code in (200, 206)
        and content_type.startswith("image/")
        and not content_type.startswith(_UNRENDERABLE_TYPES)
        and (total is None or total <= _MAX_CARD_BYTES)
    )
    if not renderable:
        logger.warning("messaging_gateway.card.artwork_not_renderable",
                       url=url, status=response.status_code,
                       content_type=content_type or None, bytes=total)
    return renderable


async def _verify(open_client, urls: list[str]) -> dict[str, bool]:
    """Cached renderability per url; the unknown ones are checked together.

    `open_client` is awaited only when something actually has to be fetched:
    building an HTTPS client costs about as much as the request, and the
    steady state is every card already having a verdict.
    """
    verdicts: dict[str, bool] = {}
    unknown = []
    for url in urls:
        cached = _cached_verdict(url)
        if cached is None:
            unknown.append(url)
        else:
            verdicts[url] = cached
    if unknown:
        client = await open_client()
        checked = await asyncio.gather(
            *(_fetchable(client, url) for url in unknown), return_exceptions=True,
        )
        for url, outcome in zip(unknown, checked):
            renderable = outcome is True
            _remember_verdict(url, renderable)
            verdicts[url] = renderable
    return verdicts


def _artwork_ladder(value: object, fallback_name: str) -> list[str]:
    """The artwork to try for one card, best first."""
    ladder = [instagram_card_image_url(value, fallback_name=fallback_name)]
    key, _ = problem_card_family(fallback_name)
    for alternative in (problem_card_image(fallback_name),
                        f"{DEFAULT_CARD_BASE_URL}/{key}.png"):
        normalized = instagram_card_image_url(alternative, fallback_name=fallback_name)
        if normalized not in ladder:
            ladder.append(normalized)
    return ladder


async def resolve_card_image_urls(
    candidates: Sequence[tuple[object, str]],
) -> list[str | None]:
    """Artwork Meta can actually fetch, one entry per `(value, fallback name)`.

    `None` means send that element without a picture: every candidate for the
    card failed, and a blank image area is worse than none.
    """
    ladders = [_artwork_ladder(value, name) for value, name in candidates]
    timeout = float(
        getattr(get_settings(), "INSTAGRAM_CARD_VERIFY_TIMEOUT_SECONDS", 0) or 0
    )
    if timeout <= 0 or not ladders:
        # Verification switched off: the previous behaviour, exactly.
        return [ladder[0] for ladder in ladders]

    resolved: list[str | None] = [None] * len(ladders)
    pending = list(range(len(ladders)))

    async def run() -> None:
        nonlocal pending
        async with AsyncExitStack() as stack:
            client: httpx.AsyncClient | None = None

            async def open_client() -> httpx.AsyncClient:
                nonlocal client
                if client is None:
                    client = await stack.enter_async_context(_artwork_client(timeout))
                return client

            for depth in range(max(len(ladder) for ladder in ladders)):
                wanted = sorted({ladders[i][depth] for i in pending
                                 if depth < len(ladders[i])})
                if not wanted:
                    break
                verdicts = await _verify(open_client, wanted)
                still_pending = []
                for i in pending:
                    if depth >= len(ladders[i]):
                        continue
                    if verdicts.get(ladders[i][depth]):
                        resolved[i] = ladders[i][depth]
                    else:
                        still_pending.append(i)
                pending = still_pending
                if not pending:
                    break

    timed_out = False
    try:
        # ONE budget for the whole carousel, not one per request: the checks
        # already run concurrently, and a customer waiting on a reply must
        # never pay a rung of the ladder times a slow host.
        await asyncio.wait_for(run(), timeout)
    except asyncio.TimeoutError:
        timed_out = True
    except Exception as exc:  # noqa: BLE001 -- a check must never block a reply
        logger.warning("messaging_gateway.card.verification_failed", error=str(exc))
        return [ladder[0] for ladder in ladders]

    for i in pending:
        if timed_out:
            # Out of budget, so this card was never judged. Our own artwork is
            # the better guess than a URL nothing has confirmed.
            resolved[i] = ladders[i][-1]
            logger.warning("messaging_gateway.card.verification_timed_out",
                           url=ladders[i][0])
        else:
            # Judged, and nothing in the ladder answered.
            logger.warning("messaging_gateway.card.artwork_dropped",
                           url=ladders[i][0],
                           action="upload replacement artwork for this option")
    return resolved


async def resolve_card_image_url(value: object, *,
                                 fallback_name: str = "") -> str | None:
    """`resolve_card_image_urls` for a single card."""
    return (await resolve_card_image_urls([(value, fallback_name)]))[0]
