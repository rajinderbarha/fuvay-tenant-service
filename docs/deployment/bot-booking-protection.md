# Bot-booking protection deployment gate

The application now enforces OTP cost limits, booking velocity limits,
active-draft caps, duplicate booking rejection, signed/replay-safe Meta
webhooks, Turnstile on public provider signup, and admin-visible abuse events.
The deployment must preserve these controls.

## Required production environment

```dotenv
APP_ENV=production
TRUSTED_PROXY_CIDRS=172.16.0.0/12
TURNSTILE_REQUIRED=true
TURNSTILE_SECRET_KEY=<Cloudflare secret key>
TURNSTILE_ALLOWED_HOSTNAMES=www.example.com,example.com
OTP_DAILY_GLOBAL_LIMIT=1000
OTP_DAILY_RECIPIENT_LIMIT=5
OTP_DAILY_IP_LIMIT=20
OTP_DAILY_SOURCE_LIMIT=20
BOOKING_MAX_ACTIVE_DRAFTS=3
BOOKING_MAX_CONFIRMATIONS_PER_DAY=5
```

Set `NEXT_PUBLIC_TURNSTILE_SITE_KEY` in the tenant-portal build environment.
The backend intentionally refuses to start in production when Turnstile or
trusted-proxy settings are missing.

`TRUSTED_PROXY_CIDRS` must describe only the network that directly connects to
the API container. Do not put public client ranges there. The API container has
no published host port in `docker-compose.prod.yml`, so requests must traverse
Nginx.

## Cloudflare / Bluehost edge rules

If Cloudflare proxies the public DNS record, enable Managed WAF rules and Bot
Fight Mode where the plan permits it. Add rate-limit rules in this order:

1. Managed Challenge after 5 POST requests/minute/IP to `/v1/auth/login`,
   `/v1/auth/otp/send`, or `/v1/auth/otp/verify`; block after 15/10 minutes.
2. Managed Challenge after 5 POST requests/minute/IP under
   `/v1/public/signup/`; block after 20/hour.
3. Managed Challenge after 60 requests/minute/IP under
   `/v1/customer/home-services/booking-drafts`; block after 300/10 minutes.
4. Do not challenge Meta webhook paths. They are HMAC-signed, replay-deduped,
   and sender-throttled in the application. A challenge would break delivery.

Lock the origin firewall to Cloudflare IP ranges if Cloudflare is enabled. If
it is not enabled, keep the API private behind the included Nginx service and
use the Nginx route limits in `nginx/nginx.conf`.

## Release checks

- A provider-signup request without a valid Turnstile token is rejected.
- A direct request cannot change its limit identity using `X-Forwarded-For`.
- The fourth OTP/hour to one recipient is rejected and no SMS is sent.
- Repeated social webhook message IDs are processed once.
- A social sender flood is acknowledged but creates no new draft or OTP.
- The fourth active draft is rejected.
- A duplicate active service/ZIP/date/time confirmation is rejected with the
  existing booking number; unscheduled and completed bookings do not collide.
- Blocked OTP and confirmation spikes appear under Admin > Security > Threats.
- Redis unavailability returns 503 for sensitive production actions rather
  than silently disabling protection.
