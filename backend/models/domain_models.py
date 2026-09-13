"""Canonical domain models shared by APIs and persistence adapters."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AssetType(str, Enum):
    building = "building"
    road = "road"
    bridge = "bridge"
    railway = "railway"
    power_plant = "power_plant"
    substation = "substation"
    factory = "factory"
    hospital = "hospital"
    school = "school"
    port = "port"
    airport = "airport"
    water_facility = "water_facility"
    agricultural = "agricultural"
    other = "other"


class Asset(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asset_id: str = Field(min_length=3, max_length=128)
    name: str = Field(min_length=1, max_length=256)
    asset_type: AssetType
    organization_id: str | None = None
    location_id: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    elevation_m: float | None = None
    replacement_cost_inr: float | None = Field(default=None, ge=0)
    annual_revenue_inr: float | None = Field(default=None, ge=0)
    criticality: float = Field(default=0.5, ge=0, le=1)
    attributes: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Exposure(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asset_id: str
    population: float | None = Field(default=None, ge=0)
    replacement_value_inr: float | None = Field(default=None, ge=0)
    annual_revenue_inr: float | None = Field(default=None, ge=0)
    service_criticality: float | None = Field(default=None, ge=0, le=1)
    supply_chain_dependency: float | None = Field(default=None, ge=0, le=1)
    data_quality_score: float | None = Field(default=None, ge=0, le=1)
    source_ids: list[str] = Field(default_factory=list)


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: str
    name: str
    horizon_year: int | None = Field(default=None, ge=2026, le=2200)
    climate_scenario: str | None = None
    precipitation_delta_pct: float = Field(default=0, ge=-100, le=500)
    temperature_delta_c: float = Field(default=0, ge=-20, le=20)
    sea_level_rise_m: float = Field(default=0, ge=0, le=10)
    coupled_models: list[str] = Field(default_factory=list)
    uncoupled_parameters: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Alert(BaseModel):
    model_config = ConfigDict(extra="forbid")
    alert_id: str
    hazard: str
    severity: str
    title: str
    message: str
    language: str = "en"
    region_ids: list[str] = Field(default_factory=list)
    asset_ids: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None
    acknowledgement_required: bool = True
