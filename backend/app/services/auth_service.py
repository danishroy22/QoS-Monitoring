"""Phase 15 — role-based access (Consumer / Administrator / ISP Administrator).

Dissertation-friendly token auth via headers. When ``QOS_AUTH_REQUIRED=false``
(default), local demos keep working with an implicit administrator principal.
ISP Administrators are hard-scoped to their ISP and cannot read other ISPs'
operational aggregates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.config import get_settings

Role = Literal["consumer", "administrator", "isp_administrator"]


@dataclass(frozen=True)
class Principal:
    role: Role
    isp_scope: str | None = None
    label: str = "anonymous"


class AuthStatusResponse(BaseModel):
    auth_required: bool
    role: Role
    isp_scope: str | None = None
    label: str
    permissions: list[str]
    note: str


class AuthLoginRequest(BaseModel):
    role: Role
    token: str = Field(min_length=1)
    isp_name: str | None = None


def _parse_isp_tokens(raw: str) -> dict[str, str]:
    """Parse ``Emtel:token1,Rogers:token2`` into {normalized_isp: token}."""
    from app.services.admin_service import normalize_isp

    out: dict[str, str] = {}
    for part in (raw or "").split(","):
        chunk = part.strip()
        if not chunk or ":" not in chunk:
            continue
        isp, token = chunk.split(":", 1)
        isp_key = normalize_isp(isp.strip())
        tok = token.strip()
        if isp_key and tok:
            out[isp_key] = tok
    return out


def permissions_for(principal: Principal) -> list[str]:
    if principal.role == "consumer":
        return ["run_tests", "view_own_results", "view_own_history"]
    if principal.role == "isp_administrator":
        return [
            "view_own_isp_data",
            "view_package_performance",
            "view_regional_performance",
            "view_alerts",
            "view_capacity_planning",
        ]
    return [
        "view_aggregated_mauritius",
        "compare_isps",
        "generate_reports",
        "view_heatmaps",
        "configure_benchmarks",
        "configure_packages",
        "view_data_quality",
    ]


def resolve_principal(
    *,
    role_header: str | None,
    token_header: str | None,
    isp_header: str | None,
) -> Principal:
    settings = get_settings()
    role_raw = (role_header or "").strip().lower()
    token = (token_header or "").strip()
    isp_hint = (isp_header or "").strip()

    if not settings.auth_required:
        # Demo mode: honour role header when present; default administrator.
        if role_raw in {"consumer", "administrator", "isp_administrator"}:
            if role_raw == "isp_administrator":
                from app.services.admin_service import normalize_isp

                scope = normalize_isp(isp_hint) if isp_hint else None
                if not scope or scope == "Unknown":
                    raise HTTPException(
                        status_code=400,
                        detail="ISP Administrator requires X-SmartQoS-ISP header in demo mode",
                    )
                return Principal(role="isp_administrator", isp_scope=scope, label=f"isp:{scope}")
            return Principal(role=role_raw, label=f"demo:{role_raw}")  # type: ignore[arg-type]
        return Principal(role="administrator", label="demo-admin")

    if not role_raw or not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required (X-SmartQoS-Role + X-SmartQoS-Token)",
        )
    if role_raw == "administrator":
        if token != settings.admin_token:
            raise HTTPException(status_code=403, detail="Invalid administrator token")
        return Principal(role="administrator", label="administrator")
    if role_raw == "isp_administrator":
        mapping = _parse_isp_tokens(settings.isp_tokens)
        from app.services.admin_service import normalize_isp

        matched_isp = None
        for isp_name, isp_token in mapping.items():
            if token == isp_token:
                matched_isp = isp_name
                break
        if not matched_isp:
            raise HTTPException(status_code=403, detail="Invalid ISP administrator token")
        if isp_hint and normalize_isp(isp_hint) != matched_isp:
            raise HTTPException(
                status_code=403,
                detail="ISP scope mismatch — cannot assume another ISP identity",
            )
        return Principal(role="isp_administrator", isp_scope=matched_isp, label=f"isp:{matched_isp}")
    if role_raw == "consumer":
        # Consumer tokens are not used for /admin; allow identity acknowledgement.
        return Principal(role="consumer", label="consumer")
    raise HTTPException(status_code=400, detail=f"Unknown role '{role_raw}'")


def get_principal(
    x_smartqos_role: Annotated[str | None, Header()] = None,
    x_smartqos_token: Annotated[str | None, Header()] = None,
    x_smartqos_isp: Annotated[str | None, Header()] = None,
) -> Principal:
    return resolve_principal(
        role_header=x_smartqos_role,
        token_header=x_smartqos_token,
        isp_header=x_smartqos_isp,
    )


def require_admin_portal(principal: Principal = Depends(get_principal)) -> Principal:
    if principal.role == "consumer":
        raise HTTPException(
            status_code=403,
            detail="Consumers cannot access the Administrator portal",
        )
    return principal


def require_full_admin(principal: Principal = Depends(require_admin_portal)) -> Principal:
    if principal.role != "administrator":
        raise HTTPException(
            status_code=403,
            detail="Only the national Administrator may perform this action",
        )
    return principal


def apply_isp_scope(
    principal: Principal,
    *,
    requested_isp: str | None = None,
) -> str | None:
    """Return the ISP filter that must be applied for this principal."""
    from app.services.admin_service import normalize_isp

    if principal.role != "isp_administrator":
        return requested_isp
    scope = principal.isp_scope
    if not scope:
        raise HTTPException(status_code=403, detail="ISP Administrator missing ISP scope")
    if requested_isp and normalize_isp(requested_isp) != scope:
        raise HTTPException(
            status_code=403,
            detail="ISP Administrators may only access their own ISP data",
        )
    return scope


def auth_status(principal: Principal) -> AuthStatusResponse:
    settings = get_settings()
    return AuthStatusResponse(
        auth_required=settings.auth_required,
        role=principal.role,
        isp_scope=principal.isp_scope,
        label=principal.label,
        permissions=permissions_for(principal),
        note=(
            "ISP Administrators never receive another ISP's private operational aggregates. "
            "Set QOS_AUTH_REQUIRED=true for enforced token checks."
        ),
    )
