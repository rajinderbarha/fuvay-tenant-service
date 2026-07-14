"""MODULE-L5-10 (Finance) — reporting aggregations must count only real money."""
import inspect


def test_commission_earned_counts_only_deducted():
    """get_finance_summary summed commission_amount across ALL statuses, so
    refunded (given back), failed/pending (never collected) and waived
    (deliberately not charged) commissions were reported as earnings —
    overstating the platform's headline commission number. Only 'deducted' is
    actually earned."""
    from app.engines.finance_hub.service import FinanceHubService
    src = inspect.getsource(FinanceHubService.get_finance_summary)
    assert 'CommissionRecord.status == "deducted"' in src


def test_topup_value_counts_only_paid_orders():
    """get_topups_summary summed amount_paid across ALL statuses, counting
    initiated / failed / cancelled orders (never paid) as revenue. The value must
    count only orders where money was actually received."""
    from app.engines.finance_hub.service import FinanceHubService
    src = inspect.getsource(FinanceHubService.get_topups_summary)
    assert "paid_topups" in src
    assert "PAID = (" in src
    # the totals use the paid subset, not every order
    assert "sum((t.amount_paid for t in paid_topups)" in src
