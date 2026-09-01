"""MODULE-L5-10 (Finance) — the credit top-up confirm must be idempotent."""
import inspect


def test_confirm_purchase_short_circuits_an_already_credited_topup():
    """confirm_purchase is fired by the client AND the Razorpay webhook, and is
    retried, so one payment routinely confirms more than once. The credit grant
    is idempotent on the topup id. The handler must short-circuit an already
    credited top-up before another credit grant or revenue increment."""
    from app.engines.platform_commerce.service import CommerceService
    src = inspect.getsource(CommerceService.confirm_purchase)
    assert 'wallet_credit_status == "credited"' in src
    # The guard must precede the canonical credit grant and revenue counters.
    guard = src.index('wallet_credit_status == "credited"')
    assert guard < src.index("grant_topup_credit("), "idempotency guard must precede credit grant"
    assert guard < src.index("p.total_revenue +="), "idempotency guard must precede revenue increment"
    # and it returns an idempotent marker
    assert '"idempotent": True' in src
