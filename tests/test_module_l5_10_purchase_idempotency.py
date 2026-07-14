"""MODULE-L5-10 (Finance) — the credit top-up confirm must be idempotent."""
import inspect


def test_confirm_purchase_short_circuits_an_already_credited_topup():
    """confirm_purchase is fired by the client AND the Razorpay webhook, and is
    retried, so one payment routinely confirms more than once. The credit grant
    is idempotent on the topup id, but credit_deposit() has no idempotency and
    purchase_count/total_revenue were incremented unconditionally — so a duplicate
    confirm replenished the security deposit TWICE and double-counted revenue for
    a single payment. It must short-circuit an already-credited top-up before any
    money moves."""
    from app.engines.platform_commerce.service import CommerceService
    src = inspect.getsource(CommerceService.confirm_purchase)
    assert 'wallet_credit_status == "credited"' in src
    # the guard must precede the deposit replenishment and the revenue counters
    guard = src.index('wallet_credit_status == "credited"')
    assert guard < src.index("await credit_deposit("), "idempotency guard must precede credit_deposit"
    assert guard < src.index("p.total_revenue +="), "idempotency guard must precede revenue increment"
    # and it returns an idempotent marker
    assert '"idempotent": True' in src
