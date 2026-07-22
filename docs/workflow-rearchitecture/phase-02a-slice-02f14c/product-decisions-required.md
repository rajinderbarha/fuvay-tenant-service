# Product Decisions Required

1. **`JobMedia` internal/customer-visible schema decision** (carried over from Slice 2F-14A/14B,
   unchanged, still open — explicitly out of scope this slice per "do not add a JobMedia
   visibility column").
2. **Legacy `Job.checklist`/`update_checklist` deprecation timing** (carried over, unchanged).
3. **Legacy vs. richer quote-surface consolidation** (carried over from Slice 2F-14B, unchanged).
4. **`create_job`'s `address` dict vs. a normalized `address_id`** — the route currently accepts
   a free-form address dict rather than a reference to any canonical address record. Whether to
   normalize this is a data-model question, not a security gap (no cross-tenant risk exists in
   free-form fields).
