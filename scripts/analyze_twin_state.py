import numpy as np
import pandas as pd
from pathlib import Path

BASE = Path("data/india/chennai/twin_state")

STATE_FILE = BASE / "chennai_twin_states.npy"
CSV_FILE = BASE / "chennai_twin_states.csv"

print("=" * 70)
print("CHENNAI DIGITAL TWIN TEMPORAL STATE ANALYSIS")
print("=" * 70)

states = np.load(STATE_FILE).astype(np.float32)
df = pd.read_csv(CSV_FILE)

print("State matrix:", states.shape)

# ------------------------------------------------------------
# Temporal state changes
# ------------------------------------------------------------

print()
print("=" * 70)
print("TEMPORAL STATE DISTANCES")
print("=" * 70)

distances = []

for i in range(1, len(states)):
    distance = np.linalg.norm(states[i] - states[i - 1])

    distances.append(distance)

    print(
        f"{df.iloc[i-1]['date']} → "
        f"{df.iloc[i]['date']} : "
        f"{distance:.4f}"
    )

# ------------------------------------------------------------
# Overall state variation
# ------------------------------------------------------------

mean_state = states.mean(axis=0)

print()
print("=" * 70)
print("STATE VARIATION")
print("=" * 70)

for i, state in enumerate(states):
    distance = np.linalg.norm(state - mean_state)

    print(
        f"{df.iloc[i]['date']} : "
        f"distance from mean state = {distance:.4f}"
    )

# ------------------------------------------------------------
# Most dynamic dimensions
# ------------------------------------------------------------

std_per_dimension = states.std(axis=0)

top_indices = np.argsort(
    std_per_dimension
)[::-1][:10]

print()
print("=" * 70)
print("TOP 10 MOST VARIABLE TWIN DIMENSIONS")
print("=" * 70)

for rank, idx in enumerate(top_indices, 1):
    print(
        f"{rank:2d}. twin_state_{idx:03d} "
        f"std={std_per_dimension[idx]:.6f}"
    )

# ------------------------------------------------------------
# Global anomaly score
# ------------------------------------------------------------

# Distance from the temporal mean state.
anomaly_scores = np.linalg.norm(
    states - mean_state,
    axis=1
)

df["state_anomaly_score"] = anomaly_scores

print()
print("=" * 70)
print("TWIN STATE ANOMALY SCORES")
print("=" * 70)

for _, row in df.iterrows():
    print(
        f"{row['date']} : "
        f"{row['state_anomaly_score']:.4f}"
    )

# ------------------------------------------------------------
# Save analysis
# ------------------------------------------------------------

output_file = BASE / "chennai_twin_state_analysis.csv"

df.to_csv(
    output_file,
    index=False
)

np.save(
    BASE / "chennai_twin_state_anomaly_scores.npy",
    anomaly_scores.astype(np.float32)
)

print()
print("=" * 70)
print("TEMPORAL STATE ANALYSIS COMPLETE")
print("=" * 70)

print("Saved:")
print(output_file)

print(
    BASE /
    "chennai_twin_state_anomaly_scores.npy"
)

print("=" * 70)
