"""
Fuvay — Application Configuration
All settings loaded from environment / .env file via pydantic-settings.
Never import settings directly — always use get_settings() to allow DI in tests.
"""
from functools import lru_cache
import ipaddress
import json
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Current release version — bump for each release candidate
APP_RC_VERSION = "rc-1"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ────────────────────────────────────────────────────────
    APP_NAME: str = "Fuvay"
    APP_VERSION: str = "rc-1"
    APP_ENV: Literal["development", "staging", "production", "testing"] = "development"
    DEBUG: bool = False  # Must stay False; only override to True in dev via .env
    SECRET_KEY: str = "dev-secret-key-change-in-production"

    # ── API ────────────────────────────────────────────────────────
    API_V1_PREFIX: str = "/v1"
    # API-key issuance is intentionally unavailable until the integration
    # product, tenant controls, and operational support model are launched.
    # Keeping this server-side flag off removes the routes from both runtime
    # routing and OpenAPI rather than relying on frontend concealment.
    API_KEYS_ENABLED: bool = False
    ALLOWED_ORIGINS: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",   # Super Admin Portal
        "http://localhost:3001",   # Tenant Owner Portal
        "http://localhost:3002",   # Customer App
        "http://localhost:5173",   # Vite dev (if used)
        "http://localhost:19006",  # Expo web
    ]
    RATE_LIMIT_PER_MINUTE: int = 100
    # Run periodic schedulers in exactly one process. Production API workers
    # disable this and the dedicated worker service enables it.
    BACKGROUND_JOBS_ENABLED: bool = True

    # Public-edge abuse protection. Proxy headers are only trusted when the
    # socket peer belongs to one of these networks; otherwise clients could
    # rotate X-Forwarded-For values to evade every IP limit.
    TRUSTED_PROXY_CIDRS: Annotated[list[str], NoDecode] = ["127.0.0.1/32", "::1/128"]
    TURNSTILE_REQUIRED: bool = False
    TURNSTILE_SECRET_KEY: str = ""
    TURNSTILE_ALLOWED_HOSTNAMES: Annotated[list[str], NoDecode] = []
    OTP_DAILY_GLOBAL_LIMIT: int = Field(default=1000, ge=1)
    OTP_DAILY_RECIPIENT_LIMIT: int = Field(default=5, ge=1)
    OTP_DAILY_IP_LIMIT: int = Field(default=20, ge=1)
    OTP_DAILY_SOURCE_LIMIT: int = Field(default=20, ge=1)
    BOOKING_MAX_ACTIVE_DRAFTS: int = Field(default=3, ge=1)
    BOOKING_MAX_CONFIRMATIONS_PER_DAY: int = Field(default=5, ge=1)

    # ── Database ───────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://serviceos:serviceos@localhost:5432/serviceos"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_IDLE_IN_TRANSACTION_TIMEOUT_SECONDS: int = 60

    # ── Redis ──────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL_SECONDS: int = 300
    REDIS_EVENT_CHANNEL: str = "serviceos:events"

    # ── Auth ───────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "dev-jwt-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Engine Registry ────────────────────────────────────────────
    ENGINE_REGISTRY_CACHE_TTL: int = 300  # seconds

    # ── AI / RAG ───────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    RAG_EMBEDDING_MODEL: str = "text-embedding-3-small"
    RAG_CHAT_MODEL: str = "gpt-4o-mini"
    RAG_CHUNK_SIZE: int = 512
    RAG_CHUNK_OVERLAP: int = 64
    RAG_TOP_K: int = 5

    # ── Masked calling (number privacy / off-platform prevention) ──
    # Platform-owned telephony account: the platform bridges the two legs of
    # a call so neither the technician nor the customer ever sees the other's
    # real number, and the binding dies with the job.
    #
    # Empty MASKED_CALLING_PROVIDER means NOT CONFIGURED. In that state the
    # feature degrades HONESTLY -- the API reports that calling is
    # unavailable rather than falling back to revealing a real number, which
    # would silently defeat the entire point.
    MASKED_CALLING_PROVIDER: str = ""        # "" | "exotel" | "http"
    MASKED_CALLING_API_BASE: str = ""
    MASKED_CALLING_API_KEY: str = ""
    MASKED_CALLING_API_SECRET: str = ""
    MASKED_CALLING_CALLER_ID: str = ""       # the platform number both legs see
    # Shared secret the provider echoes back on status webhooks, so a forged
    # callback cannot mark a call connected or leak a number.
    MASKED_CALLING_WEBHOOK_SECRET: str = ""

    # ── Storage (Cloudinary — direct-upload signed params) ─────────
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # ── Storage (S3-compatible — future / fallback) ────────────────
    AWS_S3_BUCKET: str = "serviceos-media"
    AWS_REGION: str = "ap-south-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # ── Media Engine (Phase 0A) ────────────────────────────────────
    FILE_STORAGE_DRIVER: str = ""         # local | cloudinary | s3_compatible | cloudflare_r2
    FILE_STORAGE_DOCUMENT_DRIVER: str = ""  # optional separate driver for PDF/office/text files
    FILE_STORAGE_BUCKET: str = ""
    FILE_STORAGE_REGION: str = ""
    FILE_STORAGE_ENDPOINT: str = ""
    FILE_STORAGE_ACCESS_KEY: str = ""
    FILE_STORAGE_SECRET_KEY: str = ""
    FILE_STORAGE_PUBLIC_BASE_URL: str = ""
    FILE_STORAGE_SIGNED_URL_EXPIRES_SECONDS: int = 900
    MAX_UPLOAD_SIZE_MB: int = 50

    # ── Payments ───────────────────────────────────────────────────
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    STRIPE_SECRET_KEY: str = ""

    # ── AI (backend-only — never sent to any frontend/mobile client) ─
    DEEPSEEK_API_KEY: str = ""

    # ── Meta Cloud API (WhatsApp / Instagram inbound + outbound) ────
    # All four are required for the messaging gateway to do anything. Empty
    # values fail CLOSED, on purpose: an unconfigured deployment rejects
    # webhook traffic rather than accepting unsigned requests, and outbound
    # sends no-op rather than erroring.
    #   APP_SECRET      — verifies X-Hub-Signature-256 over the raw body
    #   VERIFY_TOKEN    — the string echoed during the one-time GET handshake
    #   ACCESS_TOKEN    — Graph API bearer for sending replies
    #   PHONE_NUMBER_ID — the WhatsApp business number messages are sent from
    META_APP_SECRET: str = ""
    META_VERIFY_TOKEN: str = ""
    META_ACCESS_TOKEN: str = ""
    META_PHONE_NUMBER_ID: str = ""

    # Origin of the customer web surface, used to build chat -> web handoff
    # links. Empty means no handoff link is ever sent: the bot keeps the
    # conversation in chat rather than handing a customer a URL to nowhere.

    # ── Weather ────────────────────────────────────────────────────
    # weatherapi.com. Empty means no weather source, and every dependent feature
    # degrades honestly rather than guessing: the Home widget hides itself, slot
    # advisories are not raised, and a provider cannot claim weather as a
    # reschedule reason the system cannot see.
    WEATHERAPI_KEY: str = ""

    # ── Google Places ──────────────────────────────────────────────
    # Address autocomplete for the customer app, PROXIED through
    # /v1/customer/places -- the key stays server-side, because a key inside a
    # mobile bundle is extractable and Places is billed per request. Empty means the
    # address form is typed by hand, exactly as it was before.
    GOOGLE_PLACES_API_KEY: str = ""

    # ── Notifications ──────────────────────────────────────────────
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_VERIFY_SERVICE_SID: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    SENDGRID_API_KEY: str = ""
    FCM_SERVER_KEY: str = ""
    # Optional dedicated Fernet key for notification-provider credentials.
    # When empty outside production, a stable key is derived from SECRET_KEY.
    NOTIFICATION_CREDENTIAL_KEY: str = ""

    # ── Email (SMTP) ───────────────────────────────────────────────
    EMAIL_USERNAME: str = ""
    EMAIL_PASSWORD: str = ""
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587

    @field_validator("ALLOWED_ORIGINS", "TRUSTED_PROXY_CIDRS", "TURNSTILE_ALLOWED_HOSTNAMES", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            value = v.strip()
            # Deployment scripts commonly provide a JSON array while local
            # .env files use comma-separated origins.  NoDecode intentionally
            # leaves parsing to us, so accept both representations; otherwise
            # values such as `["http://localhost:3000"` silently become an
            # invalid CORS origin and block browser login preflights.
            if value.startswith("["):
                try:
                    decoded = json.loads(value)
                    if isinstance(decoded, list):
                        return [str(origin).strip() for origin in decoded if str(origin).strip()]
                except (json.JSONDecodeError, TypeError):
                    pass
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("TRUSTED_PROXY_CIDRS")
    @classmethod
    def validate_proxy_cidrs(cls, values: list[str]) -> list[str]:
        for value in values:
            try:
                ipaddress.ip_network(value, strict=False)
            except ValueError as exc:
                raise ValueError(f"Invalid trusted proxy CIDR: {value}") from exc
        return values

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_flag(cls, value):
        """Tolerate common build-environment DEBUG conventions.

        Some Windows/CI toolchains expose DEBUG=release or DEBUG=debug as a
        process-wide variable.  Treat those as false/true instead of making
        Fuvay fail before its own .env configuration can be used.
        """
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized == "release":
                return False
            if normalized == "debug":
                return True
        return value

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """Fail fast if production environment has dev/placeholder secrets."""
        if self.MASKED_CALLING_PROVIDER:
            if self.MASKED_CALLING_PROVIDER not in {"exotel", "http"}:
                raise ValueError("MASKED_CALLING_PROVIDER must be 'exotel', 'http', or empty")
            missing = [
                name for name, value in (
                    ("MASKED_CALLING_API_BASE", self.MASKED_CALLING_API_BASE),
                    ("MASKED_CALLING_API_KEY", self.MASKED_CALLING_API_KEY),
                    ("MASKED_CALLING_API_SECRET", self.MASKED_CALLING_API_SECRET),
                    ("MASKED_CALLING_CALLER_ID", self.MASKED_CALLING_CALLER_ID),
                    ("MASKED_CALLING_WEBHOOK_SECRET", self.MASKED_CALLING_WEBHOOK_SECRET),
                ) if not value
            ]
            if missing:
                raise ValueError(
                    "Masked calling is enabled but missing: " + ", ".join(missing)
                )
        if self.APP_ENV == "production":
            errors: list[str] = []
            if self.DEBUG:
                errors.append("DEBUG must be false in production")
            if "dev-secret-key" in self.SECRET_KEY:
                errors.append("SECRET_KEY is still the development placeholder — set a 64-char random string")
            if "dev-jwt-secret" in self.JWT_SECRET_KEY:
                errors.append("JWT_SECRET_KEY is still the development placeholder — set a 64-char random string")
            if not self.DATABASE_URL or "serviceos:serviceos@localhost" in self.DATABASE_URL:
                errors.append("DATABASE_URL points to localhost — set the production database URL")
            # Wildcard CORS in production is dangerous when credentials: true
            if "*" in self.ALLOWED_ORIGINS:
                errors.append("ALLOWED_ORIGINS contains '*' — wildcard CORS with credentials is insecure")
            if not self.TRUSTED_PROXY_CIDRS or set(self.TRUSTED_PROXY_CIDRS).issubset({"127.0.0.1/32", "::1/128"}):
                errors.append("TRUSTED_PROXY_CIDRS must contain the production reverse-proxy network")
            if not self.TURNSTILE_REQUIRED:
                errors.append("TURNSTILE_REQUIRED must be true for public provider registration")
            if not self.TURNSTILE_SECRET_KEY:
                errors.append("TURNSTILE_SECRET_KEY is required in production")
            if not self.TURNSTILE_ALLOWED_HOSTNAMES:
                errors.append("TURNSTILE_ALLOWED_HOSTNAMES must contain the public signup hostnames")
            if errors:
                raise ValueError(
                    "Production config validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
                )
        return self

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def database_url_sync(self) -> str:
        """Sync URL for Alembic migrations."""
        return self.DATABASE_URL.replace("+asyncpg", "+psycopg2")


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton. Override in tests with dependency_overrides."""
    return Settings()
