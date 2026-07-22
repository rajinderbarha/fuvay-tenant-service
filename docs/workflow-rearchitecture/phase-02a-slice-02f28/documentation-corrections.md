# Documentation Corrections - Slice 2F-28

1. **Security-observation count.** Earlier slices referred to "37 static
   security observations". The machine-readable registry carried forward
   contains 9 explicit rows plus an aggregate carry-forward line; the remainder
   live in prose in the 2F-26H/2F-27 markdown registries. This slice maps the
   explicit rows and records the carry-forward honestly rather than inventing
   37 structured entries.

2. **API-key subsystems.** `/v1/auth/api-keys` and `/v1/security/api-keys` are
   NOT the same capability. Auth uses `ApiKey` -> `api_keys`; security uses
   `APIKey` -> `tenant_api_keys`. Any earlier wording implying one API-key
   surface is corrected here.

3. No prior numeric coverage claim is corrected. 214/259 with 45 unprotected is
   re-verified from the live inventory.
