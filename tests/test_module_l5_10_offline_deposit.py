"""The retired offline security-deposit writer must stay absent."""


def test_offline_security_deposit_writer_is_retired():
    from app.engines.finance_hub.service import FinanceHubService
    assert not hasattr(FinanceHubService, "record_offline_deposit")
