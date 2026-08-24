import pandas as pd
import numpy as np
from pathlib import Path

BASE = Path("data/india/chennai/era5")
CLIM_FILE = BASE / "baseline/chennai_era5_february_climatology.csv"
OBS_FILE = BASE / "chennai_era5_daily_features.csv"

OUTPUT = BASE / "chennai_era5_anomalies.csv"
NPY_OUTPUT = BASE / "chennai_era5_anomalies.npy"

print("=" * 70)
print("CHENNAI ERA5 CLIMATE ANOMALY ANALYSIS")
print("=" * 70)

clim = pd.read_csv(CLIM_FILE)
obs = pd.read_csv(OBS_FILE)

obs["date"] = pd.to_datetime(obs["date"])

obs["month"] = obs["date"].dt.month
obs["day"] = obs["date"].dt.day

merged = obs.merge(
    clim,
    on=["month", "day"],
    how="left"
)

if len(merged) != len(obs):
    raise RuntimeError("Climatology alignment failed.")

# ------------------------------------------------------------
# Variables
# ------------------------------------------------------------

variables = {
    "temperature_mean_c":
        "temperature_mean_c",

    "temperature_min_c":
        "temperature_min_c",

    "temperature_max_c":
        "temperature_max_c",

    "dewpoint_mean_c":
        "dewpoint_mean_c",

    "wind_speed_mean_ms":
        "wind_speed_mean_ms",

    "surface_pressure_mean_pa":
        "surface_pressure_mean_pa",

    "precipitation_total_mm":
        "precipitation_total_mm",
}

anomaly_columns = []

# ------------------------------------------------------------
# Calculate standardized anomalies
# ------------------------------------------------------------

for variable, label in variables.items():

    mean_col = f"{label}_mean"
    std_col = f"{label}_std"

    anomaly_col = f"{variable}_zscore"

    denominator = merged[std_col].replace(
        0,
        np.nan
    )

    merged[anomaly_col] = (
        merged[variable] - merged[mean_col]
    ) / denominator

    anomaly_columns.append(anomaly_col)

# ------------------------------------------------------------
# Overall physical anomaly score
# ------------------------------------------------------------

z = merged[anomaly_columns].to_numpy(
    dtype=np.float32
)

physical_anomaly = np.sqrt(
    np.nanmean(z ** 2, axis=1)
)

merged["physical_anomaly_score"] = (
    physical_anomaly
)

# ------------------------------------------------------------
# Classification
# ------------------------------------------------------------

def classify(score):

    if score < 0.5:
        return "NORMAL"

    if score < 1.0:
        return "MILD"

    if score < 2.0:
        return "MODERATE"

    return "STRONG"


merged["anomaly_class"] = (
    merged["physical_anomaly_score"]
    .apply(classify)
)

# ------------------------------------------------------------
# Display
# ------------------------------------------------------------

print()
print("=" * 70)
print("2025 ERA5 CLIMATE ANOMALIES")
print("=" * 70)

display_columns = [
    "date",
    "temperature_mean_c",
    "temperature_mean_c_zscore",
    "temperature_max_c_zscore",
    "dewpoint_mean_c_zscore",
    "wind_speed_mean_ms_zscore",
    "surface_pressure_mean_pa_zscore",
    "precipitation_total_mm_zscore",
    "physical_anomaly_score",
    "anomaly_class",
]

print(
    merged[display_columns].to_string(
        index=False
    )
)

# ------------------------------------------------------------
# Save clean output
# ------------------------------------------------------------

metadata_columns = [
    "date",
    "year",
    "julian_day",
    "latitude",
    "longitude",
]

final_columns = (
    metadata_columns +
    list(variables.keys()) +
    anomaly_columns +
    [
        "physical_anomaly_score",
        "anomaly_class",
    ]
)

result = merged[final_columns].copy()

result.to_csv(
    OUTPUT,
    index=False
)

np.save(
    NPY_OUTPUT,
    result[anomaly_columns].to_numpy(
        dtype=np.float32
    )
)

# ------------------------------------------------------------
# Validation
# ------------------------------------------------------------

print()
print("=" * 70)
print("ANOMALY VALIDATION")
print("=" * 70)

print(
    "Records              :",
    len(result)
)

print(
    "Anomaly dimensions    :",
    len(anomaly_columns)
)

print(
    "Missing values        :",
    int(result.isna().sum().sum())
)

print(
    "Mean physical score   :",
    float(
        result["physical_anomaly_score"].mean()
    )
)

print(
    "Maximum physical score:",
    float(
        result["physical_anomaly_score"].max()
    )
)

print()
print("Saved:")
print(OUTPUT)
print(NPY_OUTPUT)

print()
print("=" * 70)
print("ERA5 ANOMALY ANALYSIS SUCCESS")
print("=" * 70)
