"""Instagram booking-bot simulator — drives the real webhook without Meta.

Stands in for Meta. Signs an Instagram webhook payload with the configured app
secret, POSTs it into the FastAPI app in-process, and intercepts every outbound
Graph API call so nothing reaches Instagram. What the bot WOULD have sent is
printed as a transcript instead.

Every send path in `meta_client` funnels through `_post`, so patching that one
function captures plain text, quick replies, button templates and carousels
alike — no other app code is touched, and no server or tunnel is needed.

What this DOES exercise: signature verification, the real inbound parser, the
real flow engine, and real Postgres thread state.
What it does NOT: Meta's delivery, the tunnel, and the 24-hour messaging
window. Those need a real DM.

    python scripts/ig_sim.py --seed                     # one-time local setup
    python scripts/ig_sim.py "Book AC service" "560001" # scripted turns
    python scripts/ig_sim.py                            # interactive
    python scripts/ig_sim.py --reset                    # forget the thread

`--seed` writes a LOCAL DEV channel config carrying a dummy access token. It is
safe only because outbound never leaves this process — never run it against a
database that a real deployment reads.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import hmac
import json
import logging
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

#: The simulated customer. Any stable non-business id works; keeping it fixed
#: means repeat runs land on the same `messaging_threads` row, which is what
#: makes multi-turn state realistic.
SIM_IGSID = "sim-customer-0001"

SEED = {
    "instagram_account_id": "17841400000000000",
    "api_version": "v26.0",
    "app_secret": "ig-sim-local-app-secret",
    "verify_token": "ig-sim-local-verify-token-0123456789",
    "access_token": "ig-sim-local-dummy-token-never-sent",
}

WEBHOOK = "/v1/messaging/meta/webhook/instagram"

#: Outbound Graph payloads, captured in order, drained after every turn.
CAPTURED: list[dict] = []


async def _fake_post(url: str, token: str, payload: dict) -> dict:
    """Stand-in for `meta_client._post` — records instead of sending."""
    CAPTURED.append(payload)
    return {
        "sent": True,
        "status": 200,
        "response": {
            "message_id": f"sim-out-{uuid.uuid4().hex[:12]}",
            "recipient_id": str((payload.get("recipient") or {}).get("id") or ""),
        },
    }


async def boot(verbose: bool) -> None:
    """Bring up exactly the startup pieces a webhook request depends on."""
    # Bot replies contain em-dashes and rupee signs; the Windows console
    # defaults to cp1252 and would render them as question marks.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    from app.database import init_db
    from app.redis_client import init_redis, get_redis
    from app.core.events import EventBus, set_event_bus

    await init_db()
    await init_redis()
    set_event_bus(EventBus(get_redis()))

    if not verbose:
        # Two separate log streams have to be muted, or the transcript is
        # unreadable: SQLAlchemy's echo goes through stdlib logging, while the
        # app configures structlog to write straight to stdout, which ignores
        # `logging.disable` entirely. Mute both AFTER startup — doing it
        # earlier would hide a genuine DB or Redis connection failure.
        logging.disable(logging.WARNING)
        import structlog
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(logging.ERROR),
        )


async def seed() -> None:
    from sqlalchemy import update
    from app.database import get_db_session
    from app.engines.messaging_gateway.config_service import (
        messaging_channel_config_service,
    )
    from app.engines.messaging_gateway.constants import (
        CHANNEL_INSTAGRAM, CONFIG_CHANNEL_INSTAGRAM,
    )
    from app.engines.notification.models import NotificationChannelConfig
    from app.engines.platform_notifications.channel_config_service import (
        PLATFORM_CONFIG_TENANT_ID,
    )

    async with get_db_session() as db:
        await messaging_channel_config_service.save(db, CHANNEL_INSTAGRAM, dict(SEED), None)
        # `save` deliberately disables the channel until a connection test
        # passes, and that test calls Graph for real. Flip the flags directly
        # instead — the simulator never needs a live credential.
        await db.execute(
            update(NotificationChannelConfig)
            .where(
                NotificationChannelConfig.tenant_id == PLATFORM_CONFIG_TENANT_ID,
                NotificationChannelConfig.channel == CONFIG_CHANNEL_INSTAGRAM,
            )
            .values(is_enabled=True, last_test_status="passed",
                    last_test_message="Seeded by scripts/ig_sim.py")
        )
    print(f"seeded instagram channel  account_id={SEED['instagram_account_id']}  enabled=True")


async def reset() -> None:
    """Drop this simulated customer's thread so the next run starts cold."""
    from sqlalchemy import text
    from app.database import get_db_session

    async with get_db_session() as db:
        rows = await db.execute(
            text("DELETE FROM messaging_threads WHERE channel_user_id = :u RETURNING id"),
            {"u": SIM_IGSID},
        )
        killed = len(rows.fetchall())
        await db.execute(
            text("DELETE FROM messaging_inbound_messages WHERE from_id = :u"),
            {"u": SIM_IGSID},
        )
    print(f"reset: removed {killed} thread(s) for {SIM_IGSID}")


async def load_config() -> dict:
    from app.database import get_db_session
    from app.engines.messaging_gateway.config_service import (
        messaging_channel_config_service,
    )
    from app.engines.messaging_gateway.constants import CHANNEL_INSTAGRAM

    async with get_db_session() as db:
        return await messaging_channel_config_service.get(db, CHANNEL_INSTAGRAM) or {}


def build_event(biz: str, *, text: str | None, tap: str | None,
                kind: str, title: str | None) -> dict:
    """One `entry[].messaging[]` event in the shape Instagram actually sends."""
    mid = f"sim-in-{uuid.uuid4().hex[:14]}"
    base = {"sender": {"id": SIM_IGSID}, "recipient": {"id": biz},
            "timestamp": int(time.time() * 1000)}
    if tap and kind == "postback":
        base["postback"] = {"mid": mid, "title": title or tap, "payload": tap}
    elif tap:
        base["message"] = {"mid": mid, "text": title or tap,
                           "quick_reply": {"payload": tap}}
    else:
        base["message"] = {"mid": mid, "text": text or ""}
    return base


async def turn(client: httpx.AsyncClient, cfg: dict, **kw) -> tuple[int, list]:
    """Deliver one inbound event, then render everything the bot sent back."""
    biz = str(cfg.get("instagram_account_id") or "")
    body = {"object": "instagram",
            "entry": [{"id": biz, "time": int(time.time()),
                       "messaging": [build_event(biz, **kw)]}]}
    # Sign the EXACT bytes that go on the wire — re-serialising would change
    # whitespace and the HMAC would never match.
    raw = json.dumps(body, separators=(",", ":")).encode()
    signature = "sha256=" + hmac.new(
        str(cfg.get("app_secret") or "").encode(), raw, hashlib.sha256,
    ).hexdigest()

    CAPTURED.clear()
    resp = await client.post(
        WEBHOOK, content=raw,
        headers={"Content-Type": "application/json",
                 "X-Hub-Signature-256": signature},
    )
    if resp.status_code != 200:
        print(f"  !! webhook {resp.status_code}: {resp.text[:300]}")
        return resp.status_code, []

    options: list[tuple[str, str, str]] = []
    for payload in CAPTURED:
        options.extend(render(payload))
    if not CAPTURED:
        print("  (bot sent nothing)")
    return resp.status_code, options


async def play(client: httpx.AsyncClient, cfg: dict, entry: str,
               options: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    """Send one customer turn. A bare number taps that option from the last
    reply, exactly as a finger would; anything else is typed text.

    Prefix with `=` to force literal text. That matters because Instagram
    replies carry a numbered list AND tappable chips, and the two arrive as
    different inbound shapes — `=1` types "1" at the numbered fallback, while
    `1` taps the chip. Both paths are live, so both need to be reachable.
    """
    if entry.startswith("="):
        entry = entry[1:]
    elif entry.isdigit() and 1 <= int(entry) <= len(options):
        title, payload_id, kind = options[int(entry) - 1]
        print(f"       (tapped {title})")
        _, options = await turn(client, cfg, text=None, tap=payload_id,
                                kind=kind, title=title)
        return options
    _, options = await turn(client, cfg, text=entry, tap=None,
                            kind="text", title=None)
    return options


def render(payload: dict) -> list[tuple[str, str, str]]:
    """Print one outbound Graph payload; return its tappable options."""
    msg = payload.get("message") or {}
    attachment = (msg.get("attachment") or {}).get("payload") or {}
    options: list[tuple[str, str, str]] = []

    if msg.get("text"):
        for line in str(msg["text"]).splitlines():
            print(f"  bot | {line}")

    if attachment.get("template_type") == "button":
        for line in str(attachment.get("text") or "").splitlines():
            print(f"  bot | {line}")
        for button in attachment.get("buttons") or []:
            options.append((button.get("title", ""), button.get("payload", ""), "postback"))

    if attachment.get("template_type") == "generic":
        for element in attachment.get("elements") or []:
            subtitle = element.get("subtitle")
            suffix = f" — {subtitle}" if subtitle else ""
            print(f"  bot | [card] {element.get('title', '')}{suffix}")
            for button in element.get("buttons") or []:
                options.append((button.get("title", ""), button.get("payload", ""), "postback"))

    for chip in msg.get("quick_replies") or []:
        options.append((chip.get("title", ""), chip.get("payload", ""), "quick_reply"))

    for index, (title, payload_id, kind) in enumerate(options, start=1):
        marker = "chip" if kind == "quick_reply" else "btn "
        print(f"       [{index}] {marker} {title}   -> {payload_id}")
    return options


async def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("messages", nargs="*", help="turns to send, in order")
    parser.add_argument("--seed", action="store_true", help="create the local dev channel config")
    parser.add_argument("--reset", action="store_true", help="delete the simulated thread")
    parser.add_argument("--verbose", action="store_true", help="keep app logs")
    args = parser.parse_args()

    await boot(args.verbose)

    from app.database import close_db
    from app.engines.messaging_gateway import meta_client

    try:
        if args.seed:
            await seed()
        if args.reset:
            await reset()
        if (args.seed or args.reset) and not args.messages:
            return 0

        cfg = await load_config()
        if not cfg.get("instagram_account_id"):
            print("No Instagram channel configured. Run:  python scripts/ig_sim.py --seed")
            return 1

        meta_client._post = _fake_post  # every send path funnels through this

        from app.main import app
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport,
                                     base_url="http://sim", timeout=60.0) as client:
            options: list[tuple[str, str, str]] = []
            if args.messages:
                for message in args.messages:
                    print(f"  you | {message}")
                    options = await play(client, cfg, message, options)
                    print()
                return 0

            print("Instagram simulator — type a message, or a number to tap an option.")
            print("Ctrl-C to quit.\n")
            while True:
                try:
                    entry = input("  you | ").strip()
                except (EOFError, KeyboardInterrupt):
                    print()
                    return 0
                if not entry:
                    continue
                options = await play(client, cfg, entry, options)
                print()
    finally:
        await close_db()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
