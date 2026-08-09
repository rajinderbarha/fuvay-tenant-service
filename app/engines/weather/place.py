"""Turning an address into something a weather API can resolve.

Both of the obvious choices are wrong, and both were found live:

* An Indian PIN code is NOT resolvable. `q=140412` answers
  `1006 No matching location found` -- postcode lookup covers US/UK/Canada, not
  India.
* A bare city name is worse than useless, because it fails SILENTLY.
  `q=Bassi Pathana` resolved to Pathana in **Uva, Sri Lanka** -- a real 200
  response with real weather from the wrong country, which would have shown a
  Punjab customer a Sri Lankan temperature and nothing would have looked broken.

So: coordinates when the address has them (exact, unambiguous), otherwise the city
qualified with its state and country, and never a bare PIN or bare city. The
provider then verifies the country it actually resolved to, because a qualified
query still only reduces the chance of a mismatch -- it does not remove it.
"""
from __future__ import annotations

# The platform is single-country today. Kept as a constant because the provider
# checks its answer against it, so widening the platform means changing one thing.
COUNTRY = "India"


def resolve_place(
    *,
    city: str | None = None,
    state: str | None = None,
    zipcode: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> str | None:
    """A query string the provider can resolve, or None.

    None when there is nothing usable: a PIN on its own is not a location as far as
    this API is concerned, and guessing from it would just produce the wrong city's
    weather with full confidence.
    """
    if latitude is not None and longitude is not None:
        # Exact, and immune to the wrong-country problem entirely.
        return f"{float(latitude)},{float(longitude)}"

    parts = [p.strip() for p in (city, state) if p and p.strip()]
    if not parts:
        return None
    return ",".join([*parts, COUNTRY])
