"""
ServiceOS — HATEOAS Link Builder
Every entity response includes links and allowed_actions.
Clients never construct URLs manually — they follow links.
"""
from dataclasses import dataclass, field


@dataclass
class Link:
    href: str
    method: str
    rel: str
    description: str = ""

    def to_dict(self) -> dict:
        return {"href": self.href, "method": self.method, "rel": self.rel, "description": self.description}


@dataclass
class AllowedAction:
    action: str
    href: str
    method: str
    label: str
    requires_payload: bool = False
    payload_hint: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {"action": self.action, "href": self.href, "method": self.method, "label": self.label, "requires_payload": self.requires_payload}
        if self.payload_hint:
            d["payload_hint"] = self.payload_hint
        return d


def build_links(*links: Link) -> list[dict]:
    return [l.to_dict() for l in links]


def build_actions(*actions: AllowedAction) -> list[dict]:
    return [a.to_dict() for a in actions]


# ── Auth links ─────────────────────────────────────────────────────────────────
def user_links(user_id: str) -> list[dict]:
    base = f"/v1/auth"
    return build_links(
        Link(href=f"{base}/me", method="GET", rel="self", description="Get current user profile"),
        Link(href=f"{base}/sessions", method="GET", rel="sessions", description="List active sessions"),
        Link(href=f"{base}/password/change", method="PUT", rel="change_password"),
        Link(href=f"{base}/mfa/setup", method="POST", rel="setup_mfa"),
        Link(href=f"{base}/logout", method="POST", rel="logout"),
    )


def session_links(session_id: str) -> list[dict]:
    base = f"/v1/auth/sessions/{session_id}"
    return build_links(
        Link(href=base, method="DELETE", rel="revoke", description="Revoke this session"),
        Link(href=f"{base}/trust", method="PUT", rel="trust", description="Mark device as trusted"),
    )


def api_key_links(key_id: str) -> list[dict]:
    base = f"/v1/auth/api-keys/{key_id}"
    return build_links(
        Link(href=base, method="PUT", rel="update"),
        Link(href=base, method="DELETE", rel="revoke"),
    )


# ── Tenant links ────────────────────────────────────────────────────────────────
def tenant_links(tenant_id: str, status: str) -> list[dict]:
    base = f"/v1/tenants/{tenant_id}"
    links = [
        Link(href=base, method="GET", rel="self"),
        Link(href=f"{base}/360", method="GET", rel="360_view"),
        Link(href=f"{base}/health", method="GET", rel="health_score"),
        Link(href=f"{base}/engines", method="GET", rel="engines"),
        Link(href=f"{base}/audit-log", method="GET", rel="audit_log"),
        Link(href=f"{base}/limits", method="GET", rel="limits"),
    ]
    if status == "active":
        links.append(Link(href=f"{base}/suspend", method="POST", rel="suspend"))
    elif status == "suspended":
        links.append(Link(href=f"{base}/reinstate", method="POST", rel="reinstate"))
    return build_links(*links)


def tenant_allowed_actions(tenant_id: str, status: str, plan_type: str) -> list[dict]:
    actions = []
    if status == "active":
        actions.append(AllowedAction("suspend", f"/v1/tenants/{tenant_id}/suspend", "POST", "Suspend tenant", True, {"reason": "string"}))
        actions.append(AllowedAction("change_plan", f"/v1/tenants/{tenant_id}/plan", "PUT", "Change plan", True, {"plan_type": "starter|growth|enterprise"}))
    elif status == "suspended":
        actions.append(AllowedAction("reinstate", f"/v1/tenants/{tenant_id}/reinstate", "POST", "Reinstate tenant"))
    if status not in ("terminated",):
        actions.append(AllowedAction("terminate", f"/v1/tenants/{tenant_id}/terminate/begin", "POST", "Begin termination", True, {"reason": "string"}))
    return build_actions(*actions)


def onboarding_links(request_id: str, status: str) -> list[dict]:
    base = f"/v1/tenants/onboarding/{request_id}"
    links = [Link(href=base, method="GET", rel="self")]
    if status == "submitted":
        links.append(Link(href=f"{base}/start-review", method="POST", rel="start_review"))
        links.append(Link(href=f"{base}/reject", method="POST", rel="reject"))
    elif status == "reviewing":
        links.append(Link(href=f"{base}/checklist", method="GET", rel="checklist"))
        links.append(Link(href=f"{base}/request-documents", method="POST", rel="request_documents"))
        links.append(Link(href=f"{base}/preflight", method="POST", rel="preflight_check"))
    elif status == "configuring":
        links.append(Link(href=f"{base}/activate", method="POST", rel="activate"))
    return build_links(*links)
