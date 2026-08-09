"""Address autocomplete for the customer app.

A PROXY, not a passthrough of the key. The app sends a query, we call Google, and the
key never leaves the server -- see provider.py for why that matters.

Authenticated: Places is billed per request, so an open endpoint is a way for anyone
to spend the platform's quota.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.dependencies.auth import get_current_user, UserContext
from app.engines.places.provider import resolve_places_provider
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/customer/places", tags=["Address Autocomplete"])

# Below this, suggestions are noise: a one- or two-letter query returns the largest
# places in the country rather than anything the customer meant, and each call costs.
MIN_QUERY_LENGTH = 3


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


@router.get("/autocomplete", response_model=ApiResponse[dict],
            summary="Suggest addresses for a partial query")
async def autocomplete(
    q: str,
    r: Request,
    session_token: str | None = None,
    user: UserContext = Depends(get_current_user),
):
    """`configured` tells the app whether autocomplete exists at all.

    Without it the app cannot distinguish "no matches for that query" from "this
    deployment has no Places key", and those need different UI: the first shows
    nothing, the second shows the plain typed form with no suggestion affordance at
    all.
    """
    provider = resolve_places_provider()
    query = (q or "").strip()
    if not provider.configured or len(query) < MIN_QUERY_LENGTH:
        return ok(
            {"configured": provider.configured, "suggestions": []},
            _rid(r), "places",
        )
    suggestions = await provider.suggest(query=query, session_token=session_token)
    return ok(
        {"configured": True, "suggestions": [s.to_dict() for s in suggestions]},
        _rid(r), "places",
    )


@router.get("/{place_id}", response_model=ApiResponse[dict],
            summary="Resolve a suggestion into city, state, PIN and coordinates")
async def place_detail(
    place_id: str,
    r: Request,
    session_token: str | None = None,
    user: UserContext = Depends(get_current_user),
):
    """The whole point of the feature: coordinates and a real city/state/PIN, so the
    address is exact, serviceability matches the right area, and the weather lookup
    has a precise point rather than a place name that can resolve to another country.
    """
    provider = resolve_places_provider()
    address = await provider.detail(place_id=place_id, session_token=session_token)
    if address is None:
        # Not a 404: the suggestion was real, the lookup simply did not come back. The
        # form keeps whatever the customer typed rather than clearing it.
        return ok({"resolved": False, "address": None}, _rid(r), "places")
    return ok({"resolved": True, "address": address.to_dict()}, _rid(r), "places")
