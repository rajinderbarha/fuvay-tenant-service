"""MODULE-L5-34 — staff-app mobile chat called a nonexistent endpoint family
and modeled fields the real staff chat backend doesn't have.

Continuation of MODULE-L5-00-004 (staff_app_mobile least-certified surface)
investigation, following MODULE-L5-33 (earnings). Found
mobile/staff-app/src/lib/api.ts's chatApi called /v1/chat/rooms* -- the real
chat engine only exposes /v1/chat/conversations*, and the real staff chat
surface built in MODULE-L5-19 lives entirely at a different prefix,
/v1/staff/chat/threads*, which the app never called. ChatRoom also modeled
participant_name, a last_message preview, and unread_count -- none of which
exist on the real ChatThread (record_type/record_id/status/last_message_at
only; no per-thread unread count anywhere in the backend).

Fix: rewired to /v1/staff/chat/threads*, corrected ChatThread/ChatMessage
interfaces to the real to_dict() shapes, and rewrote ChatListScreen/
ChatRoomScreen to only reference real fields.
"""
from __future__ import annotations

from pathlib import Path

API_TS = Path("mobile/staff-app/src/lib/api.ts")
LIST_SCREEN = Path("mobile/staff-app/src/screens/ChatListScreen.tsx")
ROOM_SCREEN = Path("mobile/staff-app/src/screens/ChatRoomScreen.tsx")
NAVIGATOR = Path("mobile/staff-app/src/navigation/AppNavigator.tsx")


def test_chat_api_targets_the_real_staff_chat_prefix():
    src = API_TS.read_text(encoding="utf-8")
    block = src.split("export const chatApi")[1]
    assert "/v1/staff/chat/threads" in block
    assert "/v1/chat/rooms" not in block


def test_chat_screens_no_longer_reference_fictional_fields():
    for path in (LIST_SCREEN, ROOM_SCREEN):
        live = [l for l in path.read_text(encoding="utf-8").splitlines()
                if not l.strip().startswith("//") and not l.strip().startswith("*")]
        src = "\n".join(live)
        for fictional in ("participant_name", "unread_count", "room_id", "sender_id", ".content", ".sent_at"):
            assert fictional not in src, f"{path}: {fictional} is not a real ChatThread/ChatMessage field"


def test_navigator_uses_the_real_route_params():
    src = NAVIGATOR.read_text(encoding="utf-8")
    assert "route.params as { title:string }" in src
