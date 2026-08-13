from app.config import Settings


def test_debug_release_alias_is_false():
    assert Settings(DEBUG="release").DEBUG is False


def test_debug_debug_alias_is_true():
    assert Settings(DEBUG="debug").DEBUG is True


def test_database_idle_transaction_timeout_has_safe_default():
    assert Settings().DATABASE_IDLE_IN_TRANSACTION_TIMEOUT_SECONDS == 60
