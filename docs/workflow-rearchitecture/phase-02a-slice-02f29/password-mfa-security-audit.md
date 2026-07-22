# Password and MFA Security Audit - Slice 2F-29

Routes: `PUT /v1/auth/password/change`,
`POST /v1/auth/change-password-required`, `POST /v1/auth/mfa/confirm`,
`POST /v1/auth/mfa/disable`, `PUT /v1/auth/me`.

## Persona

All five are **self-service**: the subject is the authenticated principal.
There is no tenant authority and no target other than self.

## Evidence

- Every route passes `uuid.UUID(user.user_id)` taken from the token. No route
  accepts a user id, email or tenant from the request body - asserted by test
  (`body.user_id` absent from all five).
- `change_password` requires `current_password`; `change_password_required`
  requires the current (possibly temporary) password; `disable_mfa` requires
  **both** the current password and a TOTP code; `confirm_mfa` requires a TOTP
  code against pending setup.
- `disable_mfa` additionally refuses for `super_admin` (MFA mandatory) -
  pre-existing policy, preserved.
- Cross-tenant credential mutation is structurally impossible: the identity
  is never taken from input, so one principal cannot address another.
- No account-existence oracle: there is no foreign target to probe.
- Secrets: no password hash, MFA secret or recovery material is returned or
  logged by these paths.

## Conclusion

These five are `FULLY_PROTECTED`. No product redesign of the MFA flow was
performed and no credential verification was weakened.
