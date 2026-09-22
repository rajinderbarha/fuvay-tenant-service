"""The one line shown under each service's name in the chat service list.

Every live service had an empty `MasterService.description`, so the Instagram
cards had nothing to say under the name and showed a card counter instead. An
admin-written description still wins. The lines below fill the gap with what
each service actually covers, taken from its live customer-visible problem
list (2026-09-22). A service added later gets a plain line rather than nothing.
"""
from __future__ import annotations

import re

from app.engines.messaging_gateway.constants import WA_ROW_DESCRIPTION_CHARS

# The same row feeds a WhatsApp list (72 chars) and an Instagram card
# subtitle (80). Meta rejects the whole message when a field runs long, so
# every line has to fit the smaller of the two.
MAX_BLURB_CHARS = WA_ROW_DESCRIPTION_CHARS

SERVICE_BLURBS: dict[str, str] = {
    "air-conditioner":
        "Cooling problems, gas refill, servicing, cleaning and new installation",
    "cctv-camera":
        "No video, recording or night-vision faults, plus new CCTV setup",
    "desktop-computer":
        "Won't start, crashes, slow PC, virus removal, Windows and upgrades",
    "fan-light":
        "Fans and lights not working or flickering, plus new fittings",
    "furniture-repair-assembly":
        "Hinges, drawers, wobbly joints, and flat-pack or modular assembly",
    "geyser-water-heater":
        "No hot water, leaks, tripping, descaling and new geyser installation",
    "kitchen-chimney":
        "Low suction, motor or light faults, deep cleaning and installation",
    "laptop":
        "Won't start, charging, screen, keyboard, overheating and software",
    "mcb-electrical-panel":
        "MCB tripping, main switch faults, overheating and panel upgrades",
    "microwave-oven":
        "Not heating, sparking, door, display or turntable faults, and setup",
    "pest-control":
        "Cockroaches, ants, mosquitoes, bed bugs, rodents and termites",
    "plumbing":
        "Leaking taps and pipes, blocked drains, flush issues, tank cleaning",
    "printer":
        "Not printing, paper jams, poor print quality and Wi-Fi setup",
    "refrigerator":
        "Not cooling, frost build-up, door seal, noise and water leakage",
    "ro-water-purifier":
        "No water, leaks, bad taste, filter change and new RO installation",
    "switch-socket-wiring":
        "Faulty switches and sockets, sparking, tripping and new points",
    "television":
        "No picture or sound, screen lines, smart apps and wall mounting",
    "video-door-bell-smart-lock":
        "Smart lock and video doorbell setup, app, power and lock problems",
    "wall-painting":
        "Interior, exterior and ceiling painting, with crack and seepage prep",
    "washing-machine":
        "Not spinning or draining, leaks, noise, drum cleaning, installation",
    "waterproofing":
        "Terrace, roof and bathroom leakage, and wall seepage treatment",
    "wifi-router-networking":
        "No internet, weak Wi-Fi, drop-outs, and new router or extender setup",
}

_SENTENCE_END = re.compile(r"(?<=[.!?])\s")


def _fit(text: str) -> str:
    """Shorten at a word boundary, so a line never ends mid-word."""
    if len(text) <= MAX_BLURB_CHARS:
        return text
    cut = text[:MAX_BLURB_CHARS - 1].rsplit(" ", 1)[0].rstrip(" ,;:-")
    return f"{cut}…"


def _first_sentence(description: object) -> str:
    """The admin's opening sentence. A full paragraph is written for the app."""
    lines = str(description or "").strip().splitlines()
    first_line = " ".join(lines[0].split()) if lines else ""
    return _SENTENCE_END.split(first_line, 1)[0]


def service_blurb(slug: object, name: object, description: object = None) -> str:
    """What this service covers, in one line that fits under its name."""
    admin = _first_sentence(description)
    if admin:
        return _fit(admin)
    known = SERVICE_BLURBS.get(str(slug or "").strip().lower())
    if known:
        return known
    label = " ".join(str(name or "").split())
    return _fit(f"Book a professional for {label}") if label else "Tap below to choose this service."
