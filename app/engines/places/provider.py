"""Address lookup through Google Places.

Proxied, deliberately: the key stays on the SERVER and the app calls our endpoint.
A key shipped inside a mobile bundle is extractable by anyone who downloads the app,
and Places is billed per request -- so an embedded key is someone else's free
geocoding service and your invoice. It also means the key can be rotated without an
app release.

Uses the LEGACY Places endpoints (`maps.googleapis.com/maps/api/place/...`) because
that is what the supplied key is authorised for. Verified live: Places (New) at
`places.googleapis.com` answers 403 PERMISSION_DENIED for this key, and the
Geocoding and Timezone APIs answer REQUEST_DENIED. If the newer API is enabled later,
this is the one module to change.

`NullPlacesProvider` is the default with no key: the app then falls back to typing
the address by hand, which is what it did before this existed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger("places.provider")

BASE_URL = "https://maps.googleapis.com/maps/api/place"
TIMEOUT_S = 6.0

# India only. The platform is single-country today, and restricting the query keeps
# the suggestion list relevant instead of offering the customer a street in Ohio.
REGION_CODE = "in"

# Exactly the fields the address form needs. Requested explicitly because Places
# bills by field group -- asking for everything would pay for data nobody reads.
DETAIL_FIELDS = "address_component,formatted_address,geometry,name"


@dataclass(frozen=True)
class PlaceSuggestion:
    place_id: str
    description: str

    def to_dict(self) -> dict:
        return {"place_id": self.place_id, "description": self.description}


@dataclass(frozen=True)
class PlaceAddress:
    """A resolved address, in the shape the customer address form stores.

    Every field is nullable because Google genuinely omits them: a rural locality
    often has no postal_code, and a landmark may have no street number. The form
    keeps whatever came back and lets the customer fill the rest -- it never invents
    a PIN code, which would silently misroute serviceability.
    """
    formatted_address: str | None
    line1: str | None
    city: str | None
    state: str | None
    zipcode: str | None
    latitude: float | None
    longitude: float | None

    def to_dict(self) -> dict:
        return {
            "formatted_address": self.formatted_address,
            "line1": self.line1,
            "city": self.city,
            "state": self.state,
            "zipcode": self.zipcode,
            "latitude": self.latitude,
            "longitude": self.longitude,
        }


class PlacesProvider(Protocol):
    @property
    def configured(self) -> bool: ...

    async def suggest(self, *, query: str, session_token: str | None) -> list[PlaceSuggestion]: ...

    async def detail(self, *, place_id: str, session_token: str | None) -> PlaceAddress | None: ...


class NullPlacesProvider:
    """No Places key. Suggests nothing, resolves nothing.

    The address form then behaves exactly as it did before autocomplete existed --
    fully typed by hand. It does NOT fall back to guessing a city from a PIN.
    """

    @property
    def configured(self) -> bool:
        return False

    async def suggest(self, *, query: str, session_token: str | None) -> list[PlaceSuggestion]:
        return []

    async def detail(self, *, place_id: str, session_token: str | None) -> PlaceAddress | None:
        return None


class GooglePlacesProvider:
    def __init__(self, api_key: str):
        self._api_key = api_key

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    async def _get(self, path: str, params: dict) -> dict | None:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
                response = await client.get(
                    f"{BASE_URL}{path}", params={"key": self._api_key, **params},
                )
            if response.status_code != 200:
                logger.warning("places.http_error", status=response.status_code, path=path)
                return None
            body = response.json()
        except Exception as exc:  # noqa: BLE001 -- a lookup must never break the form
            logger.warning("places.request_failed", error=str(exc), path=path)
            return None

        status = body.get("status")
        # ZERO_RESULTS is a real answer, not a failure. Everything else with a
        # non-OK status is logged with Google's own message, because these are
        # almost always key/authorisation problems and the message says which.
        if status not in ("OK", "ZERO_RESULTS"):
            logger.warning(
                "places.api_status", status=status, path=path,
                message=(body.get("error_message") or "")[:200],
            )
            return None
        return body

    async def suggest(self, *, query: str, session_token: str | None) -> list[PlaceSuggestion]:
        params = {"input": query, "components": f"country:{REGION_CODE}"}
        # Google bills an autocomplete SESSION rather than each keystroke, provided
        # the token is passed on every call and again on the details request.
        if session_token:
            params["sessiontoken"] = session_token
        body = await self._get("/autocomplete/json", params)
        if not body:
            return []
        return [
            PlaceSuggestion(place_id=p["place_id"], description=p.get("description") or "")
            for p in body.get("predictions", [])
            if p.get("place_id")
        ]

    async def detail(self, *, place_id: str, session_token: str | None) -> PlaceAddress | None:
        params = {"place_id": place_id, "fields": DETAIL_FIELDS}
        if session_token:
            params["sessiontoken"] = session_token
        body = await self._get("/details/json", params)
        if not body:
            return None
        result = body.get("result") or {}
        return _to_address(result)


def _component(components: list[dict], *types: str) -> str | None:
    """First component matching any of `types`, in the order given.

    Order matters, and it is why this takes several: an Indian address's "city" is
    `locality` in a town but only `administrative_area_level_3` or `_2` in a rural
    area, so the list is a preference order rather than alternatives.
    """
    for wanted in types:
        for comp in components:
            if wanted in (comp.get("types") or []):
                name = (comp.get("long_name") or "").strip()
                if name:
                    return name
    return None


def _to_address(result: dict) -> PlaceAddress:
    components = result.get("address_components") or []
    location = (result.get("geometry") or {}).get("location") or {}

    street = _component(components, "route", "neighborhood", "sublocality_level_1", "sublocality")
    number = _component(components, "street_number", "premise")
    line1 = " ".join(part for part in (number, street) if part) or result.get("name") or None

    return PlaceAddress(
        formatted_address=result.get("formatted_address"),
        line1=line1,
        city=_component(
            components, "locality", "administrative_area_level_3", "administrative_area_level_2",
        ),
        state=_component(components, "administrative_area_level_1"),
        # Often absent on Indian rural addresses. Left as None rather than guessed:
        # a wrong PIN silently misroutes serviceability, which decides whether a
        # provider is even offered.
        zipcode=_component(components, "postal_code"),
        latitude=float(location["lat"]) if location.get("lat") is not None else None,
        longitude=float(location["lng"]) if location.get("lng") is not None else None,
    )


def resolve_places_provider() -> PlacesProvider:
    key = (getattr(get_settings(), "GOOGLE_PLACES_API_KEY", "") or "").strip()
    return GooglePlacesProvider(key) if key else NullPlacesProvider()
