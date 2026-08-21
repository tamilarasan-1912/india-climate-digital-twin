import sys
from pathlib import Path

# Add the project root to Python's import path.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(
    0,
    str(PROJECT_ROOT)
)

from backend.services.rainfall_service import (
    get_dataset_info,
    get_daily_statistics,
    get_india_daily_summary,
)


print("=" * 70)
print("INDIA CLIMATE DIGITAL TWIN")
print("IMD RAINFALL DATA TEST")
print("=" * 70)


print("\nDATASET INFORMATION")
print("-" * 70)

info = get_dataset_info()

print(
    "File:",
    info["file"]
)

print(
    "Variable:",
    info["variable"]
)

print(
    "Units:",
    info["units"]
)

print(
    "Dimensions:",
    info["dimensions"]
)

print(
    "Latitude:",
    info["latitude"]
)

print(
    "Longitude:",
    info["longitude"]
)

print(
    "Time:",
    info["time"]
)


print("\nDAILY RAINFALL STATISTICS")
print("-" * 70)

date = "2024-07-15"

statistics = get_daily_statistics(
    date
)

print(
    "Date:",
    statistics["date"]
)

print(
    "Minimum rainfall:",
    statistics["minimum"],
    "mm"
)

print(
    "Maximum rainfall:",
    statistics["maximum"],
    "mm"
)

print(
    "Mean rainfall:",
    statistics["mean"],
    "mm"
)

print(
    "Median rainfall:",
    statistics["median"],
    "mm"
)

print(
    "Valid grid points:",
    statistics["grid_points"]
)


print("\nINDIA DAILY SUMMARY")
print("-" * 70)

summary = get_india_daily_summary(
    date
)

print(summary)


print("\n")
print("=" * 70)
print("IMD RAINFALL PROCESSING TEST COMPLETE")
print("=" * 70)