"""MODULE-L5-61 — address lookup: fill what Google said, invent nothing.

Two rules this engine is built around:

1. With no key, the lookup must resolve NOTHING and say so (`configured=False`), so the
   app hides the affordance instead of offering a search that can never answer. It must
   never fall back to guessing a city from a PIN.
2. A field Google omitted stays `None`. The PIN in particular decides serviceability --
   whether a provider is even offered for an address -- and a plausible-looking guess
   would silently misroute a real booking.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.engines.places.provider import (
    GooglePlacesProvider, NullPlacesProvider, _component, _to_address,
    resolve_places_provider,
)


def _component_dict(long_name: str, types: list[str]) -> dict:
    return {"long_name": long_name, "types": types}


class TestNullProvider:
    @pytest.mark.asyncio
    async def test_suggests_nothing_and_resolves_nothing(self):
        provider = NullPlacesProvider()
        assert provider.configured is False
        assert await provider.suggest(query="Bassi Pathana", session_token=None) == []
        assert await provider.detail(place_id="p-1", session_token=None) is None


class TestProviderResolution:
    def test_null_provider_without_a_key(self):
        settings = type("S", (), {"GOOGLE_PLACES_API_KEY": ""})()
        with patch("app.engines.places.provider.get_settings", return_value=settings):
            assert isinstance(resolve_places_provider(), NullPlacesProvider)

    def test_google_provider_with_a_key(self):
        settings = type("S", (), {"GOOGLE_PLACES_API_KEY": "test-key"})()
        with patch("app.engines.places.provider.get_settings", return_value=settings):
            provider = resolve_places_provider()
        assert isinstance(provider, GooglePlacesProvider)
        assert provider.configured is True


class TestComponentPreference:
    def test_prefers_locality_for_a_towns_city(self):
        components = [
            _component_dict("Ludhiana", ["locality"]),
            _component_dict("Ludhiana District", ["administrative_area_level_2"]),
        ]
        assert _component(components, "locality", "administrative_area_level_2") == "Ludhiana"

    def test_falls_back_down_the_hierarchy_for_a_rural_address(self):
        # An Indian rural address often carries no `locality` at all -- the tehsil or
        # district is the closest thing to a city, and skipping it would leave the
        # customer's city field empty for no reason.
        components = [_component_dict("Bassi Pathana", ["administrative_area_level_3"])]
        assert _component(
            components, "locality", "administrative_area_level_3",
        ) == "Bassi Pathana"

    def test_returns_none_when_nothing_matches(self):
        assert _component([_component_dict("India", ["country"])], "locality") is None

    def test_ignores_a_blank_long_name(self):
        components = [
            _component_dict("   ", ["locality"]),
            _component_dict("Morinda", ["administrative_area_level_3"]),
        ]
        assert _component(components, "locality", "administrative_area_level_3") == "Morinda"


class TestAddressMapping:
    def test_maps_a_complete_result(self):
        address = _to_address({
            "formatted_address": "24, Model Town Rd, Ludhiana, Punjab 141002, India",
            "geometry": {"location": {"lat": 30.9009, "lng": 75.8573}},
            "address_components": [
                _component_dict("24", ["street_number"]),
                _component_dict("Model Town Road", ["route"]),
                _component_dict("Ludhiana", ["locality"]),
                _component_dict("Punjab", ["administrative_area_level_1"]),
                _component_dict("141002", ["postal_code"]),
            ],
        })
        assert address.line1 == "24 Model Town Road"
        assert address.city == "Ludhiana"
        assert address.state == "Punjab"
        assert address.zipcode == "141002"
        assert address.latitude == pytest.approx(30.9009)
        assert address.longitude == pytest.approx(75.8573)

    def test_leaves_a_missing_pin_as_none_rather_than_guessing(self):
        address = _to_address({
            "formatted_address": "Bassi Pathana, Punjab, India",
            "geometry": {"location": {"lat": 30.6861187, "lng": 76.4042404}},
            "address_components": [
                _component_dict("Bassi Pathana", ["locality"]),
                _component_dict("Punjab", ["administrative_area_level_1"]),
                _component_dict("India", ["country"]),
            ],
        })
        assert address.zipcode is None
        # The rest of the address is still usable -- absence of one field does not
        # discard the ones that were returned.
        assert address.city == "Bassi Pathana"
        assert address.state == "Punjab"

    def test_falls_back_to_the_place_name_when_there_is_no_street(self):
        address = _to_address({
            "name": "Fortis Hospital",
            "formatted_address": "Fortis Hospital, Ludhiana, Punjab, India",
            "address_components": [_component_dict("Ludhiana", ["locality"])],
        })
        assert address.line1 == "Fortis Hospital"

    def test_omits_coordinates_entirely_when_geometry_is_absent(self):
        address = _to_address({"formatted_address": "Somewhere", "address_components": []})
        assert address.latitude is None
        assert address.longitude is None
        assert address.line1 is None


class TestRouterBehaviour:
    """The router is a thin proxy, but two of its decisions are load-bearing."""

    @staticmethod
    def _request():
        return type("R", (), {"state": type("S", (), {"request_id": "req-1"})()})()

    @pytest.mark.asyncio
    async def test_short_queries_never_reach_google(self):
        # Each call is billed, and a two-letter query returns the biggest places in
        # the country rather than anything the customer meant.
        from app.engines.places import router as places_router

        provider = GooglePlacesProvider("test-key")
        with patch.object(provider, "suggest") as suggest, \
             patch.object(places_router, "resolve_places_provider", return_value=provider):
            response = await places_router.autocomplete(
                q="Ba", r=self._request(), session_token=None, user=None,
            )
        suggest.assert_not_called()
        assert response.data == {"configured": True, "suggestions": []}

    @pytest.mark.asyncio
    async def test_reports_unconfigured_so_the_app_can_hide_the_affordance(self):
        from app.engines.places import router as places_router

        with patch.object(
            places_router, "resolve_places_provider", return_value=NullPlacesProvider(),
        ):
            response = await places_router.autocomplete(
                q="Bassi Pathana", r=self._request(), session_token=None, user=None,
            )
        assert response.data == {"configured": False, "suggestions": []}

    @pytest.mark.asyncio
    async def test_an_unresolvable_place_is_not_an_error(self):
        # A 404 here would surface as a failure over an optional convenience; the form
        # simply keeps what the customer typed.
        from app.engines.places import router as places_router

        with patch.object(
            places_router, "resolve_places_provider", return_value=NullPlacesProvider(),
        ):
            response = await places_router.place_detail(
                place_id="p-1", r=self._request(), session_token=None, user=None,
            )
        assert response.data == {"resolved": False, "address": None}


class TestGoogleProviderCalls:
    @pytest.mark.asyncio
    async def test_passes_the_session_token_on_both_calls(self):
        # Google bills an autocomplete SESSION, so the token must travel with the
        # keystroke queries AND the final details call, or one address entry is
        # charged as a dozen separate lookups.
        provider = GooglePlacesProvider("test-key")
        seen: list[dict] = []

        async def fake_get(path, params):
            seen.append({"path": path, **params})
            return {"predictions": [], "result": {"address_components": []}}

        with patch.object(provider, "_get", side_effect=fake_get):
            await provider.suggest(query="Bassi", session_token="tok-1")
            await provider.detail(place_id="p-1", session_token="tok-1")

        assert [call["sessiontoken"] for call in seen] == ["tok-1", "tok-1"]

    @pytest.mark.asyncio
    async def test_restricts_suggestions_to_india(self):
        provider = GooglePlacesProvider("test-key")
        seen: list[dict] = []

        async def fake_get(path, params):
            seen.append(params)
            return {"predictions": []}

        with patch.object(provider, "_get", side_effect=fake_get):
            await provider.suggest(query="Main Street", session_token=None)

        assert seen[0]["components"] == "country:in"

    @pytest.mark.asyncio
    async def test_a_failed_lookup_yields_nothing_instead_of_raising(self):
        # The typed address form is the fallback; a Places outage must never be able
        # to break address entry.
        provider = GooglePlacesProvider("test-key")
        with patch.object(provider, "_get", return_value=None):
            assert await provider.suggest(query="Bassi", session_token=None) == []
            assert await provider.detail(place_id="p-1", session_token=None) is None

    @pytest.mark.asyncio
    async def test_drops_predictions_without_a_place_id(self):
        provider = GooglePlacesProvider("test-key")
        body = {"predictions": [
            {"description": "usable", "place_id": "p-1"},
            {"description": "unusable -- cannot be resolved"},
        ]}
        with patch.object(provider, "_get", return_value=body):
            suggestions = await provider.suggest(query="Bassi", session_token=None)
        assert [s.place_id for s in suggestions] == ["p-1"]
