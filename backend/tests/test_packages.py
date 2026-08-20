"""Tests for ISP package fulfilment (Phase 4)."""

from __future__ import annotations

from types import SimpleNamespace

from app.schemas.packages import InternetPackageCreate
from app.services.package_service import (
    apply_package_to_measurement,
    create_package,
    fulfilment_pct,
    list_packages,
)


def test_fulfilment_pct_formula():
    assert fulfilment_pct(80, 100) == 80.0
    assert fulfilment_pct(120, 100) == 120.0
    assert fulfilment_pct(None, 100) is None
    assert fulfilment_pct(50, 0) is None


def test_create_and_apply_package(db_session):
    assert list_packages(db_session) == []
    created = create_package(
        db_session,
        InternetPackageCreate(
            isp_name="Emtel",
            package_name="100 Mbps",
            advertised_download_mbps=100,
            advertised_upload_mbps=40,
        ),
    )
    assert created.id > 0
    assert created.package_name == "100 Mbps"

    measured = SimpleNamespace(
        package_id=created.id,
        internet_package=None,
        isp_name="Emtel Ltd",
        download_mbps=85,
        upload_mbps=30,
        advertised_download_mbps=None,
        advertised_upload_mbps=None,
        download_fulfilment_pct=None,
        upload_fulfilment_pct=None,
    )
    apply_package_to_measurement(db_session, measured)
    assert measured.internet_package == "100 Mbps"
    assert measured.advertised_download_mbps == 100
    assert measured.advertised_upload_mbps == 40
    assert measured.download_fulfilment_pct == 85.0
    assert measured.upload_fulfilment_pct == 75.0


def test_no_package_skips_fulfilment(db_session):
    measured = SimpleNamespace(
        package_id=None,
        internet_package=None,
        isp_name="Emtel",
        download_mbps=85,
        upload_mbps=30,
        download_fulfilment_pct="keep",
        upload_fulfilment_pct="keep",
    )
    apply_package_to_measurement(db_session, measured)
    assert measured.download_fulfilment_pct is None
    assert measured.upload_fulfilment_pct is None
