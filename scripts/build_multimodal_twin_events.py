import pandas as pd
import numpy as np
from pathlib import Path

TWIN_DIR = Path("data/india/chennai/twin_state")
ERA5_DIR = Path("data/india/chennai/era5")

TWIN_FILE = (
    TWIN_DIR /
    "chennai_twin_state_analysis.csv"
)

ERA5_FILE = (
    ERA5_DIR /
    "chennai_era5_anomalies.csv"
)

OUTPUT = (
    TWIN_DIR /
    "chennai_multimodal_twin_events.csv"
)

print("=" * 70)
print("CHENNAI MULTIMODAL DIGITAL TWIN EVENT ENGINE")
print("=" * 70)

# ------------------------------------------------------------
# Load datasets
# ------------------------------------------------------------

twin = pd.read_csv(TWIN_FILE)
era5 = pd.read_csv(ERA5_FILE)

twin["date"] = pd.to_datetime(twin["date"])
era5["date"] = pd.to_datetime(era5["date"])

print("Prithvi/Twin records :", len(twin))
print("ERA5 records         :", len(era5))

# ------------------------------------------------------------
# Temporal alignment
# ------------------------------------------------------------

merged = pd.merge(
    twin,
    era5,
    on="date",
    how="inner",
    suffixes=("_twin", "_era5")
)

print("Aligned records      :", len(merged))

if len(merged) != len(twin):
    raise RuntimeError(
        "Temporal alignment failed."
    )

# ------------------------------------------------------------
# Extract anomaly signals
# ------------------------------------------------------------

prithvi_score = (
    merged["state_anomaly_score"]
    .to_numpy(dtype=np.float32)
)

era5_score = (
    merged["physical_anomaly_score"]
    .to_numpy(dtype=np.float32)
)

# ------------------------------------------------------------
# Normalize Prithvi anomaly
#
# The Prithvi score is a distance in latent space,
# while ERA5 is an RMS standardized anomaly.
#
# Convert Prithvi scores into relative 0-1 severity
# using the observed Chennai temporal range.
# ------------------------------------------------------------

p_min = prithvi_score.min()
p_max = prithvi_score.max()

if p_max > p_min:
    prithvi_normalized = (
        (prithvi_score - p_min) /
        (p_max - p_min)
    )
else:
    prithvi_normalized = np.zeros_like(
        prithvi_score
    )

# ------------------------------------------------------------
# Normalize ERA5 anomaly to relative 0-1 severity
# ------------------------------------------------------------

e_min = era5_score.min()
e_max = era5_score.max()

if e_max > e_min:
    era5_normalized = (
        (era5_score - e_min) /
        (e_max - e_min)
    )
else:
    era5_normalized = np.zeros_like(
        era5_score
    )

# ------------------------------------------------------------
# Multimodal fusion
# ------------------------------------------------------------

twin_score = (
    0.5 * prithvi_normalized +
    0.5 * era5_normalized
)

merged["prithvi_anomaly_score"] = (
    prithvi_score
)

merged["era5_anomaly_score"] = (
    era5_score
)

merged["prithvi_relative_severity"] = (
    prithvi_normalized
)

merged["era5_relative_severity"] = (
    era5_normalized
)

merged["multimodal_twin_score"] = (
    twin_score
)

# ------------------------------------------------------------
# Dominant signal
# ------------------------------------------------------------

dominant = []

for p, e in zip(
    prithvi_normalized,
    era5_normalized
):
    if abs(p - e) < 0.10:
        dominant.append("BALANCED")
    elif p > e:
        dominant.append("PRITHVI")
    else:
        dominant.append("ERA5")

merged["dominant_signal"] = dominant

# ------------------------------------------------------------
# Event classification
# ------------------------------------------------------------

def classify(score):

    if score < 0.25:
        return "NORMAL"

    if score < 0.50:
        return "MILD"

    if score < 0.75:
        return "MODERATE"

    return "STRONG"


merged["twin_event_class"] = (
    merged["multimodal_twin_score"]
    .apply(classify)
)

# ------------------------------------------------------------
# Event confidence
# ------------------------------------------------------------

confidence = []

for p, e in zip(
    prithvi_normalized,
    era5_normalized
):

    agreement = 1.0 - abs(p - e)

    confidence.append(
        np.clip(agreement, 0.0, 1.0)
    )

merged["signal_agreement"] = confidence

# ------------------------------------------------------------
# Final table
# ------------------------------------------------------------

columns = [
    "date",
    "year",
    "julian_day",
    "latitude_twin",
    "longitude_twin",

    "prithvi_anomaly_score",
    "era5_anomaly_score",

    "prithvi_relative_severity",
    "era5_relative_severity",

    "multimodal_twin_score",

    "dominant_signal",
    "signal_agreement",

    "twin_event_class",
]

# Handle metadata naming if necessary
available = [
    c for c in columns
    if c in merged.columns
]

result = merged[available].copy()

# ------------------------------------------------------------
# Display
# ------------------------------------------------------------

print()
print("=" * 70)
print("MULTIMODAL DIGITAL TWIN EVENTS")
print("=" * 70)

print(
    result.to_string(
        index=False
    )
)

# ------------------------------------------------------------
# Save
# ------------------------------------------------------------

result.to_csv(
    OUTPUT,
    index=False
)

print()
print("=" * 70)
print("MULTIMODAL FUSION VALIDATION")
print("=" * 70)

print(
    "Records           :",
    len(result)
)

print(
    "Missing values    :",
    int(result.isna().sum().sum())
)

print(
    "Maximum twin score:",
    float(
        result[
            "multimodal_twin_score"
        ].max()
    )
)

print()
print("Saved:")
print(OUTPUT)

print()
print("=" * 70)
print("MULTIMODAL DIGITAL TWIN SUCCESS")
print("=" * 70)
