"""Validate the local Prithvi-WxC configuration against the locked contract.

This script checks configuration only. It does not download the 2.3B model,
perform inference, or invent normalization statistics.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "backend" / "config" / "prithvi_wxc_contract.json"

EXPECTED = {
    "input_channels": 160,
    "input_size_time": 2,
    "static_input_channels": 8,
    "latitude_pixels": 360,
    "longitude_pixels": 576,
    "patch_size_pixels": [2, 2],
    "mask_unit_size_pixels": [30, 32],
    "embed_dim": 2560,
    "encoder_blocks": 12,
    "decoder_blocks": 2,
    "attention_heads": 16,
    "input_delta_hours": 6,
    "forecast_lead_hours": 6,
}


def main() -> int:
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    checks = {
        "input_channels": data["input_channels"],
        "input_size_time": data["input_size_time"],
        "static_input_channels": data["static_input_channels"],
        "latitude_pixels": data["grid"]["latitude_pixels"],
        "longitude_pixels": data["grid"]["longitude_pixels"],
        "patch_size_pixels": data["grid"]["patch_size_pixels"],
        "mask_unit_size_pixels": data["grid"]["mask_unit_size_pixels"],
        "embed_dim": data["architecture"]["embed_dim"],
        "encoder_blocks": data["architecture"]["encoder_blocks"],
        "decoder_blocks": data["architecture"]["decoder_blocks"],
        "attention_heads": data["architecture"]["attention_heads"],
        "input_delta_hours": data["rollout_contract"]["input_delta_hours"],
        "forecast_lead_hours": data["rollout_contract"]["forecast_lead_hours"],
    }

    failed = [(key, EXPECTED[key], value) for key, value in checks.items() if value != EXPECTED[key]]

    print("=" * 70)
    print("PRITHVI-WxC CONTRACT VALIDATION")
    print("=" * 70)
    print(f"Model: {data['model_id']}")
    print(f"Input variables: {data['input_channels']}")
    print(f"Input timestamps: {data['input_size_time']}")
    print(f"Static channels: {data['static_input_channels']}")
    print(f"Grid: {data['grid']['latitude_pixels']} x {data['grid']['longitude_pixels']}")
    print(f"Rollout delta: {data['rollout_contract']['input_delta_hours']} h")
    print(f"Forecast lead: {data['rollout_contract']['forecast_lead_hours']} h")
    print(f"Normalization: {data['normalization']['status']}")

    if failed:
        print("RESULT: FAILED")
        for key, expected, actual in failed:
            print(f"  {key}: expected={expected!r}, actual={actual!r}")
        return 1

    print("RESULT: PASS")
    print("No model weights downloaded; no synthetic statistics created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
