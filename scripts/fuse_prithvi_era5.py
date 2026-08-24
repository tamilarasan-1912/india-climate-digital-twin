import numpy as np
import pandas as pd
from pathlib import Path

BASE = Path("data/india/chennai")

PRITHVI_FILE = (
    BASE / "prithvi_features/"
    "chennai_prithvi_temporal_features.csv"
)

ERA5_FILE = (
    BASE / "era5/"
    "chennai_era5_daily_features.csv"
)

OUTPUT_DIR = BASE / "fused_features"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("PRITHVI + ERA5 MULTIMODAL FEATURE FUSION")
print("=" * 70)

# ------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------

prithvi = pd.read_csv(PRITHVI_FILE)
era5 = pd.read_csv(ERA5_FILE)

print("Prithvi rows:", len(prithvi))
print("ERA5 rows   :", len(era5))

# ------------------------------------------------------------
# ALIGN TEMPORALLY
# ------------------------------------------------------------

prithvi["date"] = pd.to_datetime(
    prithvi["julian_day"].astype(str) + "-01-01",
    format="%j-%m-%d",
    errors="coerce",
)

# Construct exact dates from year + Julian day.
prithvi["date"] = pd.to_datetime(
    prithvi["year"].astype(str)
    + prithvi["julian_day"].astype(str),
    format="%Y%j",
)

era5["date"] = pd.to_datetime(era5["date"])

prithvi = prithvi.sort_values("date").reset_index(drop=True)
era5 = era5.sort_values("date").reset_index(drop=True)

print("\nPrithvi dates:")
print(prithvi["date"].dt.strftime("%Y-%m-%d").to_list())

print("\nERA5 dates:")
print(era5["date"].dt.strftime("%Y-%m-%d").to_list())

# ------------------------------------------------------------
# CHECK ALIGNMENT
# ------------------------------------------------------------

if not prithvi["date"].equals(era5["date"]):
    raise ValueError(
        "Prithvi and ERA5 dates are not aligned."
    )

print("\nTemporal alignment: SUCCESS")

# ------------------------------------------------------------
# EXTRACT FEATURE MATRICES
# ------------------------------------------------------------

prithvi_columns = [
    c for c in prithvi.columns
    if c.startswith("prithvi_")
]

era5_columns = [
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

X_prithvi = prithvi[prithvi_columns].to_numpy(
    dtype=np.float32
)

X_era5 = era5[era5_columns].to_numpy(
    dtype=np.float32
)

print("\nPrithvi matrix:")
print("Shape:", X_prithvi.shape)

print("\nERA5 matrix:")
print("Shape:", X_era5.shape)

# ------------------------------------------------------------
# STANDARDIZATION
# ------------------------------------------------------------

def standardize(X):
    mean = X.mean(axis=0)
    std = X.std(axis=0)

    # Avoid division by zero for constant features.
    std_safe = np.where(
        std < 1e-8,
        1.0,
        std,
    )

    X_scaled = (X - mean) / std_safe

    return (
        X_scaled.astype(np.float32),
        mean.astype(np.float32),
        std_safe.astype(np.float32),
    )


X_prithvi_scaled, prithvi_mean, prithvi_std = standardize(
    X_prithvi
)

X_era5_scaled, era5_mean, era5_std = standardize(
    X_era5
)

# ------------------------------------------------------------
# FUSION
# ------------------------------------------------------------

X_fused = np.concatenate(
    [
        X_prithvi_scaled,
        X_era5_scaled,
    ],
    axis=1,
)

print("\nFused matrix:")
print("Shape:", X_fused.shape)

expected_shape = (
    len(prithvi),
    len(prithvi_columns) + len(era5_columns),
)

if X_fused.shape != expected_shape:
    raise ValueError(
        f"Unexpected fused shape: {X_fused.shape}; "
        f"expected {expected_shape}"
    )

# ------------------------------------------------------------
# BUILD DATAFRAME
# ------------------------------------------------------------

metadata = prithvi[
    [
        "date",
        "year",
        "julian_day",
        "latitude",
        "longitude",
    ]
].copy()

metadata["date"] = metadata["date"].dt.strftime(
    "%Y-%m-%d"
)

feature_names = (
    [f"prithvi_{i:03d}" for i in range(192)]
    +
    [f"era5_{name}" for name in era5_columns]
)

fused_df = pd.DataFrame(
    X_fused,
    columns=feature_names,
)

fused_df = pd.concat(
    [
        metadata.reset_index(drop=True),
        fused_df,
    ],
    axis=1,
)

# ------------------------------------------------------------
# SAVE
# ------------------------------------------------------------

csv_path = (
    OUTPUT_DIR /
    "chennai_prithvi_era5_fused_features.csv"
)

npy_path = (
    OUTPUT_DIR /
    "chennai_prithvi_era5_fused_features.npy"
)

np.save(
    npy_path,
    X_fused,
)

fused_df.to_csv(
    csv_path,
    index=False,
)

# Save normalization parameters.
np.savez(
    OUTPUT_DIR / "normalization_parameters.npz",
    prithvi_mean=prithvi_mean,
    prithvi_std=prithvi_std,
    era5_mean=era5_mean,
    era5_std=era5_std,
)

# ------------------------------------------------------------
# VALIDATION
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("FUSION VALIDATION")
print("=" * 70)

print("Rows              :", X_fused.shape[0])
print("Prithvi features  :", X_prithvi.shape[1])
print("ERA5 features     :", X_era5.shape[1])
print("Total features    :", X_fused.shape[1])

print(
    "Missing values    :",
    int(np.isnan(X_fused).sum()),
)

print(
    "Overall mean      :",
    float(X_fused.mean()),
)

print(
    "Overall std       :",
    float(X_fused.std()),
)

print("\nDate records:")

for date in metadata["date"]:
    print("  ", date)

print("\nSaved:")
print(csv_path)
print(npy_path)
print(
    OUTPUT_DIR /
    "normalization_parameters.npz"
)

print("\n" + "=" * 70)
print("PRITHVI + ERA5 FUSION SUCCESS")
print("=" * 70)
