# DELETE /v1/webhooks/endpoints/{endpoint_id} - Evidence (Slice 2F-27A)

- Mounted: yes, single instance, app.engines.webhook.router:52, endpoint delete_endpoint.
- Guard: require_permission(P.TENANT_UPDATE) (runtime-extensible tenant permission).
- Request: tenant_id from Query(...), client-asserted.
- Service: WebhookService.delete_endpoint(endpoint_id, tenant_id) - soft-delete:
  `SELECT WebhookEndpoint WHERE id==endpoint_id AND tenant_id==tenant_id`; if not
  found -> 404; else `ep.status = WebhookStatus.DELETED`. Genuine persistent mutation.
- Ownership: the object is scoped to the CLIENT-asserted tenant_id, with NO
  assertion that the caller belongs to that tenant. A TENANT_UPDATE holder in
  tenant A could delete tenant B's endpoint by supplying tenant_id=B and the
  endpoint id.
- Canonical/matrix: absent from both (verified). No alias route.
- Final protection: PERMISSION_ONLY_NOT_SCOPE_AWARE (UNPROTECTED). NOT
  FULLY_PROTECTED - permission presence alone does not establish ownership.
