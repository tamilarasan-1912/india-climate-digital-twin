-- Industry-grade spatial core for Bharat Climate Twin.
-- PostgreSQL + PostGIS. Large raster/array data stays in object storage/Zarr;
-- this database stores authoritative metadata, vectors, assets and results.

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS organizations (
    organization_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    organization_type TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS locations (
    location_id TEXT PRIMARY KEY,
    parent_location_id TEXT REFERENCES locations(location_id),
    location_type TEXT NOT NULL,
    name TEXT NOT NULL,
    admin_code TEXT,
    geom GEOMETRY(GEOMETRY, 4326) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_locations_geom ON locations USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_locations_parent ON locations(parent_location_id);

CREATE TABLE IF NOT EXISTS assets (
    asset_id TEXT PRIMARY KEY,
    organization_id UUID REFERENCES organizations(organization_id),
    location_id TEXT REFERENCES locations(location_id),
    asset_type TEXT NOT NULL,
    name TEXT NOT NULL,
    geom GEOMETRY(GEOMETRY, 4326) NOT NULL,
    elevation_m DOUBLE PRECISION,
    replacement_cost_inr NUMERIC(20,2),
    annual_revenue_inr NUMERIC(20,2),
    criticality DOUBLE PRECISION NOT NULL DEFAULT 0.5 CHECK (criticality BETWEEN 0 AND 1),
    attributes JSONB NOT NULL DEFAULT '{}',
    valid_from TIMESTAMPTZ,
    valid_to TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_assets_geom ON assets USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_assets_location ON assets(location_id);
CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(asset_type);

CREATE TABLE IF NOT EXISTS datasets (
    dataset_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    title TEXT NOT NULL,
    license TEXT,
    spatial_resolution TEXT,
    temporal_resolution TEXT,
    crs TEXT,
    catalog_url TEXT,
    update_frequency TEXT,
    quality_score DOUBLE PRECISION CHECK (quality_score BETWEEN 0 AND 1),
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS data_assets (
    data_asset_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id TEXT NOT NULL REFERENCES datasets(dataset_id),
    stac_collection TEXT,
    stac_item TEXT,
    object_uri TEXT NOT NULL,
    content_hash TEXT,
    acquired_at TIMESTAMPTZ,
    valid_time_start TIMESTAMPTZ,
    valid_time_end TIMESTAMPTZ,
    bbox GEOMETRY(POLYGON, 4326),
    metadata JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_data_assets_bbox ON data_assets USING GIST (bbox);

CREATE TABLE IF NOT EXISTS model_registry (
    model_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    provider TEXT,
    task TEXT NOT NULL,
    artifact_uri TEXT,
    checksum TEXT,
    validation_status TEXT NOT NULL DEFAULT 'unvalidated',
    metrics JSONB NOT NULL DEFAULT '{}',
    limitations JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(name, version)
);

CREATE TABLE IF NOT EXISTS risk_assessments (
    assessment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id TEXT NOT NULL REFERENCES assets(asset_id),
    hazard_type TEXT NOT NULL,
    assessment_time TIMESTAMPTZ NOT NULL,
    hazard_value DOUBLE PRECISION,
    exposure_value DOUBLE PRECISION,
    vulnerability_value DOUBLE PRECISION,
    risk_score DOUBLE PRECISION CHECK (risk_score BETWEEN 0 AND 1),
    confidence DOUBLE PRECISION CHECK (confidence BETWEEN 0 AND 1),
    data_quality_score DOUBLE PRECISION CHECK (data_quality_score BETWEEN 0 AND 1),
    expected_annual_loss_inr NUMERIC(20,2),
    model_id TEXT REFERENCES model_registry(model_id),
    validation_status TEXT NOT NULL,
    status TEXT NOT NULL,
    provenance JSONB NOT NULL DEFAULT '{}',
    limitations JSONB NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_risk_asset_time ON risk_assessments(asset_id, assessment_time DESC);
CREATE INDEX IF NOT EXISTS idx_risk_hazard ON risk_assessments(hazard_type);

CREATE TABLE IF NOT EXISTS scenarios (
    scenario_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    horizon_year INTEGER,
    climate_scenario TEXT,
    parameters JSONB NOT NULL DEFAULT '{}',
    coupled_models JSONB NOT NULL DEFAULT '[]',
    uncoupled_parameters JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hazard_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'en',
    region_ids JSONB NOT NULL DEFAULT '[]',
    asset_ids JSONB NOT NULL DEFAULT '[]',
    issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ,
    acknowledgement_required BOOLEAN NOT NULL DEFAULT TRUE,
    provenance JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS audit_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id TEXT,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    request_id TEXT,
    event_time TIMESTAMPTZ NOT NULL DEFAULT now(),
    ip_hash TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_events(event_time DESC);
