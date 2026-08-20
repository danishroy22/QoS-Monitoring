"""Schemas for configurable ISP internet packages (Phase 4)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InternetPackageCreate(BaseModel):
    isp_name: str = Field(min_length=1, max_length=120)
    package_name: str = Field(min_length=1, max_length=120)
    advertised_download_mbps: float = Field(gt=0)
    advertised_upload_mbps: float = Field(gt=0)
    notes: str | None = None
    active: bool = True


class InternetPackageUpdate(BaseModel):
    isp_name: str | None = Field(default=None, min_length=1, max_length=120)
    package_name: str | None = Field(default=None, min_length=1, max_length=120)
    advertised_download_mbps: float | None = Field(default=None, gt=0)
    advertised_upload_mbps: float | None = Field(default=None, gt=0)
    notes: str | None = None
    active: bool | None = None


class InternetPackageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    isp_name: str
    package_name: str
    advertised_download_mbps: float
    advertised_upload_mbps: float
    notes: str | None = None
    active: bool
    created_at: datetime
    updated_at: datetime


class InternetPackageListResponse(BaseModel):
    count: int
    packages: list[InternetPackageOut]
    note: str = (
        "Packages are administrator-configured. No commercial plans are hard-coded."
    )
