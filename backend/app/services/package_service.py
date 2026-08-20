"""Internet package CRUD and fulfilment helpers (Phase 4)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.package import InternetPackage
from app.schemas.packages import InternetPackageCreate, InternetPackageOut, InternetPackageUpdate
from app.services.admin_service import normalize_isp


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def fulfilment_pct(measured: float | None, advertised: float | None) -> float | None:
    """Measured / advertised × 100. Returns None if either side is missing/invalid."""
    if measured is None or advertised is None:
        return None
    adv = float(advertised)
    if adv <= 0:
        return None
    return round((float(measured) / adv) * 100.0, 2)


def _to_out(row: InternetPackage) -> InternetPackageOut:
    return InternetPackageOut.model_validate(row)


def list_packages(db: Session, *, active_only: bool = False) -> list[InternetPackageOut]:
    stmt = select(InternetPackage).order_by(
        InternetPackage.isp_name.asc(), InternetPackage.package_name.asc()
    )
    if active_only:
        stmt = stmt.where(InternetPackage.active.is_(True))
    return [_to_out(row) for row in db.scalars(stmt)]


def get_package(db: Session, package_id: int) -> InternetPackage | None:
    return db.get(InternetPackage, package_id)


def create_package(db: Session, payload: InternetPackageCreate) -> InternetPackageOut:
    row = InternetPackage(
        isp_name=payload.isp_name.strip(),
        package_name=payload.package_name.strip(),
        advertised_download_mbps=float(payload.advertised_download_mbps),
        advertised_upload_mbps=float(payload.advertised_upload_mbps),
        notes=(payload.notes or None),
        active=bool(payload.active),
        updated_at=_utcnow(),
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("A package with this ISP and name already exists") from exc
    db.refresh(row)
    return _to_out(row)


def update_package(
    db: Session, package_id: int, payload: InternetPackageUpdate
) -> InternetPackageOut | None:
    row = get_package(db, package_id)
    if row is None:
        return None
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        if key in ("isp_name", "package_name") and isinstance(value, str):
            value = value.strip()
        setattr(row, key, value)
    row.updated_at = _utcnow()
    db.commit()
    db.refresh(row)
    return _to_out(row)


def deactivate_package(db: Session, package_id: int) -> InternetPackageOut | None:
    row = get_package(db, package_id)
    if row is None:
        return None
    row.active = False
    row.updated_at = _utcnow()
    db.commit()
    db.refresh(row)
    return _to_out(row)


def resolve_package(
    db: Session,
    *,
    package_id: int | None = None,
    internet_package: str | None = None,
    isp_name: str | None = None,
) -> InternetPackage | None:
    """Resolve an active package by id, or by ISP + package name."""
    if package_id is not None:
        row = get_package(db, package_id)
        if row is not None and row.active:
            return row
        return None

    name = (internet_package or "").strip()
    if not name:
        return None

    rows = list(
        db.scalars(
            select(InternetPackage).where(
                InternetPackage.active.is_(True),
                InternetPackage.package_name == name,
            )
        )
    )
    if not rows:
        # Case-insensitive fallback
        lowered = name.lower()
        rows = [
            r
            for r in db.scalars(select(InternetPackage).where(InternetPackage.active.is_(True)))
            if (r.package_name or "").strip().lower() == lowered
        ]
    if not rows:
        return None
    if len(rows) == 1:
        return rows[0]

    wanted = normalize_isp(isp_name)
    for row in rows:
        if normalize_isp(row.isp_name) == wanted:
            return row
    return rows[0]


def apply_package_to_measurement(db: Session, measured) -> None:
    """Attach package metadata and fulfilment % onto a MeasurementResult-like object."""
    package = resolve_package(
        db,
        package_id=getattr(measured, "package_id", None),
        internet_package=getattr(measured, "internet_package", None),
        isp_name=getattr(measured, "isp_name", None),
    )
    if package is None:
        measured.download_fulfilment_pct = None
        measured.upload_fulfilment_pct = None
        return

    measured.package_id = package.id
    measured.internet_package = package.package_name
    measured.advertised_download_mbps = package.advertised_download_mbps
    measured.advertised_upload_mbps = package.advertised_upload_mbps
    measured.download_fulfilment_pct = fulfilment_pct(
        getattr(measured, "download_mbps", None), package.advertised_download_mbps
    )
    measured.upload_fulfilment_pct = fulfilment_pct(
        getattr(measured, "upload_mbps", None), package.advertised_upload_mbps
    )
