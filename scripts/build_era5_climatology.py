import xarray as xr
import pandas as pd
import numpy as np
from pathlib import Path

BASE = Path(
    "data/india/chennai/era5/baseline/extracted"
)

OUTPUT = Path(
    "data/india/chennai/era5/baseline"
)

INSTANT = BASE / "data_stream-oper_stepType-instant.nc"
ACCUM = BASE / "data_stream-oper_stepType-accum.nc"

print("=" * 70)
print("CHENNAI ERA5 HISTORICAL CLIMATOLOGY")
print("=" * 70)

instant = xr.open_dataset(INSTANT)
accum = xr.open_dataset(ACCUM)

print("Instant observations:", instant.sizes["valid_time"])
print("Accum observations  :", accum.sizes["valid_time"])

# ------------------------------------------------------------
# Convert to pandas
# ------------------------------------------------------------

instant_df = instant[
    ["t2m", "d2m", "u10", "v10", "sp"]
].to_dataframe().reset_index()

accum_df = accum[
    ["tp"]
].to_dataframe().reset_index()

# Remove spatial dimensions
instant_df = instant_df.drop(
    columns=["latitude", "longitude"],
    errors="ignore"
)

accum_df = accum_df.drop(
    columns=["latitude", "longitude"],
    errors="ignore"
)

# ------------------------------------------------------------
# Merge
# ------------------------------------------------------------

df = pd.merge(
    instant_df,
    accum_df,
    on="valid_time",
    how="inner"
)

df["valid_time"] = pd.to_datetime(
    df["valid_time"]
)

df["date"] = df["valid_time"].dt.date
df["year"] = df["valid_time"].dt.year
df["month"] = df["valid_time"].dt.month
df["day"] = df["valid_time"].dt.day

# ------------------------------------------------------------
# Unit conversions
# ------------------------------------------------------------

# Kelvin → Celsius
df["temperature_c"] = (
    df["t2m"] - 273.15
)

df["dewpoint_c"] = (
    df["d2m"] - 273.15
)

# Wind speed
df["wind_speed_ms"] = np.sqrt(
    df["u10"] ** 2 +
    df["v10"] ** 2
)

# Precipitation: metres → millimetres
df["precipitation_mm"] = (
    df["tp"] * 1000.0
)

# ------------------------------------------------------------
# Daily aggregation
# ------------------------------------------------------------

daily = (
    df
    .groupby(["year", "month", "day"])
    .agg(
        temperature_mean_c=(
            "temperature_c",
            "mean"
        ),
        temperature_min_c=(
            "temperature_c",
            "min"
        ),
        temperature_max_c=(
            "temperature_c",
            "max"
        ),
        dewpoint_mean_c=(
            "dewpoint_c",
            "mean"
        ),
        wind_speed_mean_ms=(
            "wind_speed_ms",
            "mean"
        ),
        surface_pressure_mean_pa=(
            "sp",
            "mean"
        ),
        precipitation_total_mm=(
            "precipitation_mm",
            "sum"
        ),
    )
    .reset_index()
)

# ------------------------------------------------------------
# Historical climatology
# ------------------------------------------------------------

climatology = (
    daily
    .groupby(["month", "day"])
    .agg(
        temperature_mean_c_mean=(
            "temperature_mean_c",
            "mean"
        ),
        temperature_mean_c_std=(
            "temperature_mean_c",
            "std"
        ),

        temperature_min_c_mean=(
            "temperature_min_c",
            "mean"
        ),
        temperature_min_c_std=(
            "temperature_min_c",
            "std"
        ),

        temperature_max_c_mean=(
            "temperature_max_c",
            "mean"
        ),
        temperature_max_c_std=(
            "temperature_max_c",
            "std"
        ),

        dewpoint_mean_c_mean=(
            "dewpoint_mean_c",
            "mean"
        ),
        dewpoint_mean_c_std=(
            "dewpoint_mean_c",
            "std"
        ),

        wind_speed_mean_ms_mean=(
            "wind_speed_mean_ms",
            "mean"
        ),
        wind_speed_mean_ms_std=(
            "wind_speed_mean_ms",
            "std"
        ),

        surface_pressure_mean_pa_mean=(
            "surface_pressure_mean_pa",
            "mean"
        ),
        surface_pressure_mean_pa_std=(
            "surface_pressure_mean_pa",
            "std"
        ),

        precipitation_total_mm_mean=(
            "precipitation_total_mm",
            "mean"
        ),
        precipitation_total_mm_std=(
            "precipitation_total_mm",
            "std"
        ),
    )
    .reset_index()
)

# ------------------------------------------------------------
# Save
# ------------------------------------------------------------

daily_path = OUTPUT / "chennai_era5_baseline_daily.csv"

climatology_path = (
    OUTPUT /
    "chennai_era5_february_climatology.csv"
)

daily.to_csv(
    daily_path,
    index=False
)

climatology.to_csv(
    climatology_path,
    index=False
)

# ------------------------------------------------------------
# Validation
# ------------------------------------------------------------

print()
print("=" * 70)
print("CLIMATOLOGY VALIDATION")
print("=" * 70)

print(
    "Historical daily records:",
    len(daily)
)

print(
    "Calendar days:",
    len(climatology)
)

print()
print("Expected:")
print("  Daily records : 140")
print("  Calendar days : 28")

print()
print("Sample climatology:")

print(
    climatology.head(5).to_string(
        index=False
    )
)

print()
print("Missing values:")

print(
    int(
        climatology.isna().sum().sum()
    )
)

print()
print("Saved:")
print(daily_path)
print(climatology_path)

print()
print("=" * 70)
print("ERA5 CLIMATOLOGY BUILD SUCCESS")
print("=" * 70)

instant.close()
accum.close()
