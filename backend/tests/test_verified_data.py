from backend.services.verified_data_service import AUTHORITATIVE_SOURCES, get_verified_sources


def test_authoritative_registry_contains_required_sources():
    ids = {source["id"] for source in AUTHORITATIVE_SOURCES}
    assert "imd-rainfall-rf25" in ids
    assert "mosdac-gsmap-isro" in ids
    assert "era5-single-levels" in ids
    assert "nasa-merra2" in ids


def test_verified_sources_never_promote_missing_sources_to_connected():
    result = get_verified_sources()
    statuses = {source["id"]: source["status"] for source in result["sources"]}
    assert statuses["mosdac-gsmap-isro"] == "access_required"
    assert statuses["era5-single-levels"] == "access_required"
