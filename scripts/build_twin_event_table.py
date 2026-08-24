import pandas as pd
from pathlib import Path

TWIN_DIR = Path("data/india/chennai/twin_state")
ERA5_DIR = Path("data/india/chennai/era5")

TWIN_FILE = TWIN_DIR / "chennai_twin_state_analysis.csv"
ERA5_FILE = ERA5_DIR / "chennai_era5_daily_features.csv"

OUTPUT = TWIN_DIR / "chennai_twin_event_table.csv"

print("=" * 70)
print("CHENNAI DIGITAL TWIN EVENT TABLE")
print("=" * 70)

twin = pd.read_csv(TWIN_FILE)
era5 = pd.read_csv(ERA5_FILE)

print("Twin records :", len(twin))
print("ERA5 records :", len(era5))

# ------------------------------------------------------------
# Normalize dates
# ------------------------------------------------------------

twin["date"] = pd.to_datetime(twin["date"]).dt.normalize()
era5["date"] = pd.to_datetime(era5["date"]).dt.normalize()

# ------------------------------------------------------------
# Normalize spatial coordinates
# ------------------------------------------------------------
#
# Coordinates represent the same Chennai point, but floating
# point representations differ slightly between datasets.
#
# Use rounded coordinates only for validation/reference.
# Temporal alignment itself is performed by date.
# ------------------------------------------------------------

twin["latitude"] = twin["latitude"].round(2)
twin["longitude"] = twin["longitude"].round(2)

era5["latitude"] = era5["latitude"].round(2)
era5["longitude"] = era5["longitude"].round(2)

# ------------------------------------------------------------
# Temporal alignment
# ------------------------------------------------------------

merged = pd.merge(
    twin,
    era5,
    on="date",
    how="inner",
    suffixes=("_twin", "_era5"),
)

print()
print("Aligned records :", len(merged))

if len(merged) != len(twin):
    print()
    print("Twin dates:")
    print(twin["date"].tolist())

    print()
    print("ERA5 dates:")
    print(era5["date"].tolist())

    raise RuntimeError(
        "Temporal alignment failed. "
        "The datasets do not contain matching dates."
    )

# ------------------------------------------------------------
# Verify spatial agreement
# ------------------------------------------------------------

lat_difference = (
    merged["latitude_twin"] -
    merged["latitude_era5"]
).abs()

lon_difference = (
    merged["longitude_twin"] -
    merged["longitude_era5"]
).abs()

print("Maximum latitude difference  :", lat_difference.max())
print("Maximum longitude difference :", lon_difference.max())

# ------------------------------------------------------------
# State anomaly ranking
# ------------------------------------------------------------

merged["anomaly_rank"] = (
    merged["state_anomaly_score"]
    .rank(
        ascending=False,
        method="dense"
    )
    .astype(int)
)

# ------------------------------------------------------------
# Physical variables
# ------------------------------------------------------------

physical_columns = [
    "temperature_mean_c",
    "temperature_min_c",
    "temperature_max_c",
    "dewpoint_mean_c",
    "u10_mean_ms",
    "v10_mean_ms",
    "wind_speed_mean_ms",
    "surface_pressure_mean_pa",
    "precipitation_total_mm",
]

# ------------------------------------------------------------
# Physical changes
# ------------------------------------------------------------

for column in physical_columns:
    merged[f"{column}_change"] = (
        merged[column].diff()
    )

# First observation has no previous observation.
for column in physical_columns:
    merged.loc[
        merged.index[0],
        f"{column}_change"
    ] = 0.0

# ------------------------------------------------------------
# State change
# ------------------------------------------------------------

merged["state_change"] = (
    merged["state_anomaly_score"].diff()
)

merged.loc[
    merged.index[0],
    "state_change"
] = 0.0

# ------------------------------------------------------------
# Prototype event classification
# ------------------------------------------------------------
#
# This is only a descriptive prototype.
# It is NOT a scientifically validated climate threshold.
# ------------------------------------------------------------

def classify(score):

    if score >= 20:
        return "HIGH_STATE_DEVIATION"

    if score >= 10:
        return "MODERATE_STATE_DEVIATION"

    return "NORMAL_RANGE"


merged["event_class"] = (
    merged["state_anomaly_score"]
    .apply(classify)
)

# ------------------------------------------------------------
# Save
# ------------------------------------------------------------

merged.to_csv(
    OUTPUT,
    index=False
)

# ------------------------------------------------------------
# Display
# ------------------------------------------------------------

display_columns = [
    "date",
    "state_anomaly_score",
    "anomaly_rank",
    "event_class",
    "temperature_mean_c",
    "temperature_min_c",
    "temperature_max_c",
    "wind_speed_mean_ms",
    "surface_pressure_mean_pa",
    "precipitation_total_mm",
]

print()
print("=" * 70)
print("DIGITAL TWIN EVENT TABLE")
print("=" * 70)

print(
    merged[display_columns].to_string(
        index=False
    )
)

print()
print("=" * 70)
print("EVENT TABLE COMPLETE")
print("=" * 70)

print("Saved:")
print(OUTPUT)

print("=" * 70)
