"""
India Climate Digital Twin
Step 11D - AI Forecast Adapter

This module defines the interface for the AI weather model.

The actual Prithvi WxC inference is intentionally separated from
the existing IMD rainfall pipeline.

No synthetic forecast is generated here.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AIForecastResult:
    """
    Standardized output expected from an AI weather model.
    """

    model_name: str

    model_version: str

    forecast_time: str

    lead_time_hours: int

    variable: str

    unit: str

    status: str

    message: str


class AIWeatherForecast:

    MODEL_NAME = (
        "Prithvi-WxC"
    )

    MODEL_VERSION = (
        "Prithvi-WxC-1.0-2300M-rollout"
    )

    def __init__(self) -> None:

        self.loaded = False

    def load_model(self) -> None:
        """
        Load the AI weather model.

        Actual model loading will be implemented after
        compatible MERRA-2/weather input preparation.
        """

        raise NotImplementedError(
            "Prithvi WxC inference is not yet enabled. "
            "Compatible atmospheric input preparation "
            "must be completed first."
        )

    def forecast(
        self,
        forecast_time: str,
        lead_time_hours: int,
    ) -> AIForecastResult:
        """
        Generate an AI weather forecast.

        This method deliberately does not generate fake data.
        """

        raise NotImplementedError(
            "AI forecast inference is not yet configured."
        )


def get_ai_model_info() -> dict:

    return {

        "model": (
            "Prithvi-WxC"
        ),

        "version": (
            "Prithvi-WxC-1.0-2300M-rollout"
        ),

        "provider": (
            "IBM / NASA"
        ),

        "purpose": (
            "Weather and climate forecasting"
        ),

        "status": (
            "integration_planned"
        ),

        "input_source": (
            "MERRA-2-compatible atmospheric fields"
        ),

        "current_project_data": (
            "IMD rainfall-only"
        ),

        "direct_inference_supported": False,

        "reason": (
            "Current IMD dataset contains only rainfall "
            "and is not equivalent to the multi-variable "
            "Prithvi WxC input."
        ),
    }
