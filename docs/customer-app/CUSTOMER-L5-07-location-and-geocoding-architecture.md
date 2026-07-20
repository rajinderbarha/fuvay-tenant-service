# CUSTOMER-L5-07 — Location and Geocoding Architecture

## No Backend Geocoding Exists

Confirmed by an exhaustive grep across the entire backend
(`app/engines/`) for any geocoding capability — zero results. This is not
a gap this sprint failed to close; it is a genuine, structural absence.
Every "location" capability in this sprint is therefore either (a) a real
backend lookup keyed by explicit text fields (city/state/zipcode, as the
real `AddressCreate` schema requires), or (b) a device-local, OS-provided
capability with no backend involvement at all.

## Permission Strategy

`expo-location`'s `requestForegroundPermissionsAsync()` is called only at
the point of use — the "Use current location" button on
`AddressFormScreen` — never at app startup. `app.json` already declares
the iOS `NSLocationWhenInUseUsageDescription` and Android
`ACCESS_FINE_LOCATION` permission (configured in an earlier sprint,
unused until now).

## Approximate vs. Precise Location

This sprint requests `Location.Accuracy.Balanced` (not the highest
precision tier) — sufficient for reverse-geocoding to a street-level
address, without requesting GPS-grade precision the address-entry use
case does not need.

## Current Location Flow

```
customer taps "Use current location"
  → requestForegroundPermissionsAsync()
      → denied → show a customer-friendly notice, manual entry remains fully available
      → granted → getCurrentPositionAsync()
          → reverseGeocodeAsync({latitude, longitude})
              → no result → "couldn't determine your location" notice, manual entry remains available
              → result → prefill address_line_1/city/district/state/zipcode fields
                  → customer reviews and can edit every field before saving
                  → nothing is ever auto-submitted
```

Coordinates are only ever sent to the backend as part of an explicit
`create`/`update` address call the customer themselves initiates by
tapping "Save" — never transmitted anywhere else, never logged.

## Reverse Geocoding — Client-Only, OS-Provided

`expo-location#reverseGeocodeAsync` uses the device's own native geocoder
(Apple's on iOS, Google's on Android via Play Services) — no third-party
API key is configured or required, and no request leaves the device to any
service this app or its backend controls. This is a real, disclosed
architectural choice, not a limitation of this sprint's implementation:
since the backend has no geocoding capability to normalize or validate
against, the OS-level result is presented as an editable prefill and nothing
more.

## Forward Geocoding

Not implemented — no product need was identified (nothing in this
sprint's real scope consumes address-text-to-coordinates), and no backend
endpoint exists to validate the result against even if it were built.

## Structured Location Picker (`location_engine`)

A real, public, unauthenticated set of cascading lookup endpoints exists
(`GET /v1/public/locations/states|districts|cities|zones`) — genuine
admin-managed master data with real `city_tier` values. **Deliberately not
used this sprint** — see known-gaps.md for the reasoning (keeping this
already-large sprint's scope bounded to free-text entry, which the real
`AddressCreate` schema already fully supports and requires regardless).

## Privacy

- Coordinates are never logged (verified by grep — see security-review.md).
- Coordinates are never included in analytics.
- No third-party geocoding provider receives any data — the geocoder is
  the OS itself, not a network call this app makes.
- The customer always retains a fully-functional manual-entry path; no
  screen requires location permission to proceed.
