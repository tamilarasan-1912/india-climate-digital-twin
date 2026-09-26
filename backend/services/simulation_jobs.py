"""Simulation Job Service for Bharat Climate Twin.

Provides async job execution for long-running simulations using Celery + Redis.
Jobs are submitted via API, executed by workers, and results retrieved via polling.
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure project root is in Python path for Celery workers
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from celery import Celery
from celery.result import AsyncResult

# Celery configuration
REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

celery_app = Celery(
    "bharat_climate_twin",
    broker=REDIS_URL,
    backend=RESULT_BACKEND,
    include=["backend.services.simulation_jobs"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3000,  # 50 min soft limit
    worker_prefetch_multiplier=1,
    result_expires=86400,  # 24 hours
    # Ensure worker uses correct working directory
    worker_cwd=str(PROJECT_ROOT),
)

# Job status constants
JOB_STATUS_PENDING = "pending"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_FAILED = "failed"
JOB_STATUS_CANCELLED = "cancelled"


def _job_dir() -> Path:
    """Directory for job metadata persistence."""
    job_dir = Path(os.getenv("SIMULATION_JOB_DIR", "/tmp/bharat-twin-jobs"))
    job_dir.mkdir(parents=True, exist_ok=True)
    return job_dir


def _job_file(job_id: str) -> Path:
    return _job_dir() / f"{job_id}.json"


def _save_job_meta(job_id: str, meta: dict[str, Any]) -> None:
    _job_file(job_id).write_text(json.dumps(meta, default=str), encoding="utf-8")


def _load_job_meta(job_id: str) -> dict[str, Any] | None:
    path = _job_file(job_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def submit_simulation_job(
    simulation_type: str,
    parameters: dict[str, Any],
    spatial_scope: dict[str, str] | None = None,
    requested_by: str | None = None,
) -> str:
    """Submit a simulation job and return job_id.

    Args:
        simulation_type: Type of simulation (e.g., "gr4j_hydro", "flood_hecras", "scenario_sensitivity")
        parameters: Simulation-specific parameters
        spatial_scope: Optional spatial scope (e.g., {"type": "basin", "id": "mahanadi_delta_sub_1"})
        requested_by: Optional identifier of requester

    Returns:
        job_id string
    """
    job_id = str(uuid.uuid4())
    meta = {
        "job_id": job_id,
        "simulation_type": simulation_type,
        "parameters": parameters,
        "spatial_scope": spatial_scope or {"type": "country", "id": "IN"},
        "requested_by": requested_by,
        "status": JOB_STATUS_PENDING,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "started_at": None,
        "completed_at": None,
        "result": None,
        "error": None,
        "progress": 0,
        "current_step": "queued",
    }
    _save_job_meta(job_id, meta)

    # Dispatch to Celery worker
    run_simulation_task.delay(job_id)
    return job_id


def get_job_status(job_id: str) -> dict[str, Any] | None:
    """Get job status and metadata."""
    meta = _load_job_meta(job_id)
    if meta is None:
        return None

    # Also check Celery task state if running
    if meta["status"] in (JOB_STATUS_PENDING, JOB_STATUS_RUNNING):
        # We don't have the task_id stored, so we rely on file-based status
        # In production, store task_id in meta
        pass

    return meta


def get_job_result(job_id: str) -> dict[str, Any] | None:
    """Get job result if completed."""
    meta = _load_job_meta(job_id)
    if meta is None:
        return None
    if meta["status"] != JOB_STATUS_COMPLETED:
        return None
    return meta.get("result")


def cancel_job(job_id: str) -> bool:
    """Attempt to cancel a running job."""
    meta = _load_job_meta(job_id)
    if meta is None:
        return False
    if meta["status"] in (JOB_STATUS_COMPLETED, JOB_STATUS_FAILED, JOB_STATUS_CANCELLED):
        return False

    # Mark as cancelled
    meta["status"] = JOB_STATUS_CANCELLED
    meta["completed_at"] = datetime.now(timezone.utc).isoformat()
    meta["error"] = "Cancelled by user"
    _save_job_meta(job_id, meta)
    return True


def list_jobs(
    status: str | None = None,
    simulation_type: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """List jobs with optional filters."""
    jobs = []
    for path in _job_dir().glob("*.json"):
        try:
            meta = json.loads(path.read_text(encoding="utf-8"))
            if status and meta.get("status") != status:
                continue
            if simulation_type and meta.get("simulation_type") != simulation_type:
                continue
            jobs.append(meta)
        except Exception:
            continue

    # Sort by creation time, newest first
    jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)
    return jobs[:limit]


# Celery tasks
@celery_app.task(bind=True, name="backend.services.simulation_jobs.run_simulation_task")
def run_simulation_task(self, job_id: str) -> dict[str, Any]:
    """Execute a simulation job. This runs in the Celery worker."""
    meta = _load_job_meta(job_id)
    if meta is None:
        return {"error": "Job metadata not found"}

    # Update status to running
    meta["status"] = JOB_STATUS_RUNNING
    meta["started_at"] = datetime.now(timezone.utc).isoformat()
    meta["current_step"] = "initializing"
    meta["progress"] = 5
    _save_job_meta(job_id, meta)

    try:
        simulation_type = meta["simulation_type"]
        parameters = meta["parameters"]
        spatial_scope = meta["spatial_scope"]

        # Dispatch to appropriate simulation function
        if simulation_type == "scenario_sensitivity":
            result = _run_scenario_sensitivity(job_id, parameters)
        elif simulation_type == "gr4j_hydro":
            result = _run_gr4j_hydro(job_id, parameters, spatial_scope)
        elif simulation_type == "flood_hecras":
            result = _run_flood_hecras(job_id, parameters, spatial_scope)
        else:
            raise ValueError(f"Unknown simulation type: {simulation_type}")

        # Success
        meta["status"] = JOB_STATUS_COMPLETED
        meta["completed_at"] = datetime.now(timezone.utc).isoformat()
        meta["result"] = result
        meta["progress"] = 100
        meta["current_step"] = "completed"
        _save_job_meta(job_id, meta)
        return result

    except Exception as e:
        # Failure
        meta["status"] = JOB_STATUS_FAILED
        meta["completed_at"] = datetime.now(timezone.utc).isoformat()
        meta["error"] = str(e)
        meta["current_step"] = "failed"
        _save_job_meta(job_id, meta)
        return {"error": str(e)}


def _run_scenario_sensitivity(job_id: str, parameters: dict[str, Any]) -> dict[str, Any]:
    """Run a scenario sensitivity experiment (rainfall hazard only)."""
    from backend.services.twin_state_contract import build_scenario_state

    meta = _load_job_meta(job_id)
    meta["current_step"] = "computing_scenario"
    meta["progress"] = 30
    _save_job_meta(job_id, meta)

    base_date = parameters.get("base_date")
    precip_delta = parameters.get("precipitation_delta_pct", 0.0)
    temp_delta = parameters.get("temperature_delta_c", 0.0)
    sea_level = parameters.get("sea_level_rise_m", 0.0)
    scenario = parameters.get("scenario", "custom")

    if not base_date:
        raise ValueError("base_date is required for scenario_sensitivity")

    result = build_scenario_state(
        base_date=base_date,
        precipitation_delta_pct=precip_delta,
        temperature_delta_c=temp_delta,
        sea_level_rise_m=sea_level,
        scenario=scenario,
    )

    meta = _load_job_meta(job_id)
    meta["current_step"] = "finalizing"
    meta["progress"] = 90
    _save_job_meta(job_id, meta)

    return {
        "simulation_type": "scenario_sensitivity",
        "contract_version": result["contract_version"],
        "scenario": result["scenario"],
        "parameters": result["parameters"],
        "baseline": result["baseline"],
        "scenario_result": result["scenario_result"],
        "coupling": result["coupling"],
        "scientific_status": result["scientific_status"],
        "provenance": result["provenance"],
    }


def _run_gr4j_hydro(job_id: str, parameters: dict[str, Any], spatial_scope: dict[str, str]) -> dict[str, Any]:
    """Run GR4J rainfall-runoff simulation."""
    from backend.services.gr4j_model import run_gr4j_simulation

    meta = _load_job_meta(job_id)
    meta["current_step"] = "preparing_hydro_inputs"
    meta["progress"] = 20
    _save_job_meta(job_id, meta)

    # Extract parameters
    basin_id = spatial_scope.get("id", "mahanadi_delta_sub_1")
    start_date = parameters.get("start_date")
    end_date = parameters.get("end_date")
    rainfall_source = parameters.get("rainfall_source", "imd_rf25")

    if not start_date or not end_date:
        raise ValueError("start_date and end_date required for GR4J simulation")

    meta["current_step"] = "running_gr4j"
    meta["progress"] = 50
    _save_job_meta(job_id, meta)

    result = run_gr4j_simulation(
        basin_id=basin_id,
        start_date=start_date,
        end_date=end_date,
        rainfall_source=rainfall_source,
        parameters=parameters.get("gr4j_params"),
    )

    meta["current_step"] = "finalizing"
    meta["progress"] = 90
    _save_job_meta(job_id, meta)

    return {
        "simulation_type": "gr4j_hydro",
        "basin_id": basin_id,
        "period": {"start": start_date, "end": end_date},
        "discharge": result,
        "model": "GR4J",
        "model_version": "1.0.0",
        "parameters_used": parameters.get("gr4j_params"),
        "scientific_status": "simulation" if parameters.get("gr4j_params") else "uncalibrated",
    }


def _run_flood_hecras(job_id: str, parameters: dict[str, Any], spatial_scope: dict[str, str]) -> dict[str, Any]:
    """Generate HEC-RAS run manifest for external execution."""
    from backend.services.flood_twin_service import build_flood_run_manifest

    meta = _load_job_meta(job_id)
    meta["current_step"] = "generating_hecras_manifest"
    meta["progress"] = 30
    _save_job_meta(job_id, meta)

    basin_id = spatial_scope.get("id", "mahanadi_delta_sub_1")
    scenario_id = parameters.get("scenario_id", f"flood_{job_id[:8]}")

    manifest = build_flood_run_manifest(
        scenario_id=scenario_id,
        rainfall_asset_uri=parameters["rainfall_asset_uri"],
        terrain_asset_uri=parameters["terrain_asset_uri"],
        geometry_asset_uri=parameters["geometry_asset_uri"],
        boundary_condition_uri=parameters.get("boundary_condition_uri"),
    )

    meta["current_step"] = "manifest_ready"
    meta["progress"] = 90
    _save_job_meta(job_id, meta)

    return {
        "simulation_type": "flood_hecras",
        "status": "manifest_generated",
        "scenario_id": scenario_id,
        "basin_id": basin_id,
        "manifest": manifest,
        "note": "HEC-RAS model must be executed externally. Results can be ingested via /api/v1/simulation/jobs/{job_id}/flood-result",
        "scientific_status": "manifest_only",
    }


# Worker entrypoint
def start_worker() -> None:
    """Start Celery worker (for direct execution)."""
    celery_app.worker_main(["worker", "--loglevel=info"])


if __name__ == "__main__":
    start_worker()