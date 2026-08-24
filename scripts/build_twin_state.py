import numpy as np
import pandas as pd
from pathlib import Path

BASE = Path("data/india/chennai/fused_features")

CSV_PATH = BASE / "chennai_prithvi_era5_fused_features.csv"
NPY_PATH = BASE / "chennai_prithvi_era5_fused_features.npy"

OUTPUT_DIR = Path("data/india/chennai/twin_state")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_NPY = OUTPUT_DIR / "chennai_twin_states.npy"
OUTPUT_CSV = OUTPUT_DIR / "chennai_twin_states.csv"


print("=" * 70)
print("CHENNAI DIGITAL TWIN STATE BUILDER")
print("=" * 70)


# ------------------------------------------------------------
# Load data
# ------------------------------------------------------------

df = pd.read_csv(CSV_PATH)
X = np.load(NPY_PATH).astype(np.float32)

print("Input feature matrix :", X.shape)


# ------------------------------------------------------------
# Deterministic state projection
# ------------------------------------------------------------
#
# For the prototype we use a fixed dimensionality reduction
# rather than training a neural network on only four samples.
#
# 201-D fused representation
#          ↓
#       128-D state
#
# SVD/PCA-like projection is appropriate here because we do not
# have enough observations to train a neural encoder.
# ------------------------------------------------------------

X_centered = X - X.mean(axis=0, keepdims=True)

U, S, Vt = np.linalg.svd(
    X_centered,
    full_matrices=False
)

n_components = min(128, Vt.shape[0])

states = X_centered @ Vt[:n_components].T

# Pad to exactly 128 dimensions if necessary.
if states.shape[1] < 128:
    padding = np.zeros(
        (states.shape[0], 128 - states.shape[1]),
        dtype=np.float32
    )
    states = np.concatenate(
        [states, padding],
        axis=1
    )

states = states.astype(np.float32)


# ------------------------------------------------------------
# Build output dataframe
# ------------------------------------------------------------

metadata = df[
    [
        "date",
        "year",
        "julian_day",
        "latitude",
        "longitude",
    ]
].copy()

state_df = metadata.copy()

for i in range(128):
    state_df[f"twin_state_{i:03d}"] = states[:, i]


# ------------------------------------------------------------
# Save
# ------------------------------------------------------------

np.save(
    OUTPUT_NPY,
    states
)

state_df.to_csv(
    OUTPUT_CSV,
    index=False
)


# ------------------------------------------------------------
# Validation
# ------------------------------------------------------------

print()
print("=" * 70)
print("TWIN STATE VALIDATION")
print("=" * 70)

print("State matrix shape :", states.shape)
print("Expected           :", (4, 128))

print()
print("State statistics:")
print("  Min  :", float(states.min()))
print("  Max  :", float(states.max()))
print("  Mean :", float(states.mean()))
print("  Std  :", float(states.std()))

print()
print("Missing values :", int(np.isnan(states).sum()))

print()
print("Dates:")
for date in metadata["date"]:
    print(" ", date)

assert states.shape == (4, 128)
assert not np.isnan(states).any()

print()
print("Saved:")
print(OUTPUT_NPY)
print(OUTPUT_CSV)

print()
print("=" * 70)
print("DIGITAL TWIN STATE BUILD: SUCCESS")
print("=" * 70)
