"""
India Climate Digital Twin
Step 11D.1 - Prithvi WxC Input Adapter

Purpose:
    Define and validate the atmospheric input contract required
    before Prithvi WxC inference is attempted.

Important:
    The current IMD dataset contains rainfall only.
    It is NOT directly compatible with Prithvi WxC inference.

    This module therefore performs validation only.
    It does not generate synthetic atmospheric variables.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


# ============================================================
# PRITHVI-WXC CONFIGURATION
# ============================================================

MODEL_NAME = (
    "Prithvi-WxC-1.0-2300M-rollout"
)

MODEL_PROVIDER = (
    "IBM / NASA"
)

EXPECTED_VARIABLE_COUNT = 160

INPUT_INTERVAL_HOURS = 6

FORECAST_LEAD_HOURS = 6


# ============================================================
# INPUT CONTRACT
# ============================================================

@dataclass(frozen=True)
class PrithviInputContract:

    model_name: str

    variable_count: int

    input_interval_hours: int

    forecast_lead_hours: int

    source: str


# ============================================================
# CURRENT PROJECT DATASET
# ============================================================

CURRENT_PROJECT_VARIABLES = (
    "RAINFALL",
)


def get_input_contract() -> PrithviInputContract:

    return PrithviInputContract(

        model_name=MODEL_NAME,

        variable_count=EXPECTED_VARIABLE_COUNT,

        input_interval_hours=INPUT_INTERVAL_HOURS,

        forecast_lead_hours=FORECAST_LEAD_HOURS,

        source="MERRA-2 compatible atmospheric fields",

    )


# ============================================================
# VALIDATE INPUT VARIABLES
# ============================================================

def validate_variables(
    variables: Sequence[str],
) -> dict:

    supplied = list(variables)

    return {

        "valid":
            len(supplied)
            == EXPECTED_VARIABLE_COUNT,

        "expected_variable_count":
            EXPECTED_VARIABLE_COUNT,

        "supplied_variable_count":
            len(supplied),

        "variables":
            supplied,

    }


# ============================================================
# CURRENT IMD COMPATIBILITY CHECK
# ============================================================

def validate_current_imd_dataset() -> dict:

    supplied_variables = (
        CURRENT_PROJECT_VARIABLES
    )

    validation = validate_variables(
        supplied_variables
    )

    return {

        "dataset":
            "RF25_ind2024_rfp25.nc",

        "provider":
            "IMD",

        "variables":
            supplied_variables,

        "prithvi_compatible":
            False,

        "reason":
            (
                "The current dataset contains "
                "rainfall only. Prithvi WxC "
                "requires its compatible "
                "multi-variable atmospheric "
                "input configuration."
            ),

        "validation":
            validation,

    }


# ============================================================
# PRINT CONFIGURATION
# ============================================================

def print_configuration() -> None:

    contract = get_input_contract()

    print("=" * 70)
    print("INDIA CLIMATE DIGITAL TWIN")
    print("PRITHVI WxC INPUT CONTRACT")
    print("=" * 70)

    print()

    print(
        f"Model: "
        f"{contract.model_name}"
    )

    print(
        f"Provider: "
        f"{MODEL_PROVIDER}"
    )

    print(
        f"Expected variables: "
        f"{contract.variable_count}"
    )

    print(
        f"Input interval: "
        f"{contract.input_interval_hours} hours"
    )

    print(
        f"Forecast lead: "
        f"{contract.forecast_lead_hours} hours"
    )

    print()

    result = (
        validate_current_imd_dataset()
    )

    print("-" * 70)
    print("CURRENT IMD DATASET")
    print("-" * 70)

    print(
        f"Dataset: "
        f"{result['dataset']}"
    )

    print(
        f"Variables: "
        f"{result['variables']}"
    )

    print(
        f"Prithvi compatible: "
        f"{result['prithvi_compatible']}"
    )

    print()

    print(
        result["reason"]
    )

    print()

    print("=" * 70)


if __name__ == "__main__":
    print_configuration()
