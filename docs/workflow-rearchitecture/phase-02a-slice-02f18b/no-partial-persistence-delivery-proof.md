# No Partial Persistence / No Delivery Proof (this slice's new paths)

| Rejected scenario | Where validation fires | db.add called? | db.commit called? | Test |
|---|---|---|---|---|
| Wrong `media_context` | `_validate_attachments`, before `ChatMessage(...)` construction | No | No | `test_wrong_media_context_rejected` |
| Soft-deleted asset (`deleted_at` set) | same | No | No | `test_soft_deleted_asset_rejected` |
| Inactive/quarantined asset (`status != "active"`) | same | No | No | `test_inactive_status_asset_rejected` |
| Cross-customer asset (same tenant) | same | No | No | `test_cross_customer_media_within_same_tenant_rejected` |
| `MediaAccessService` denial (customer referencing another customer's upload) | same | No | No | `test_customer_cannot_attach_another_customers_upload` |
| Missing asset / cross-tenant asset (re-confirmed with the new check ordering) | same | No | No | `test_missing_asset_and_cross_tenant_asset_share_error_code` |

All 6 new rejected-path tests assert `db.add.assert_not_called()`. Since
`_notify_other_participants` (the only delivery-adjacent call on this
router) executes strictly AFTER attachment validation succeeds, every one
of these also proves zero delivery-side-effect (`InAppNotification`) rows
are created — no separate assertion needed, `db.add.assert_not_called()`
covers both.

## Pre-existing rejected paths (unchanged, re-confirmed by 2F-18/2F-18A, not re-tested here)
See:
- `docs/workflow-rearchitecture/phase-02a-slice-02f18/no-partial-persistence-delivery-proof.md`
- `docs/workflow-rearchitecture/phase-02a-slice-02f18a/no-partial-persistence-delivery-proof.md`

both re-confirmed still passing by this slice's full regression run.
