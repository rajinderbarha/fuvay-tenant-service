"""Regression coverage for browser login CORS configuration."""

from app.config import Settings


def test_allowed_origins_accepts_json_array_environment_format():
    settings = Settings(
        ALLOWED_ORIGINS='["http://localhost:3000","http://localhost:3001"]'
    )

    assert settings.ALLOWED_ORIGINS == [
        "http://localhost:3000",
        "http://localhost:3001",
    ]


def test_allowed_origins_accepts_comma_separated_environment_format():
    settings = Settings(
        ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"
    )

    assert settings.ALLOWED_ORIGINS == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
