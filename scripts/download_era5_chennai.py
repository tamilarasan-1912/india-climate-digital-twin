cat > scripts/extract_era5_features.py <<'PY'
import xarray as xr
import pandas as pd
import numpy as np
from pathlib import Path

BASE = Path("data/india/chennai/era5/extracted")
OUTPUT = Path("data/india/chennai/era5")

INSTANT = BASE / "data_stream-oper_stepType-instant.nc"
ACCUM = BASE / "data_stream-oper_stepType-accum.nc"

OUTPUT.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("ERA5 CHENNAI FEATURE EXTRACTION")
print("=" * 70)

instant = xr.open_dataset(INSTANT, engine="netcdf4")
accum = xr.open_dataset(ACCUM, engine="netcdf4")

ds = xr.merge([instant, accum])

print("Input dimensions:")
print(ds.sizes)

print("\nVariables:")
for name in ds.data_vars:
    print(f"  {name}")

# Select the ERA5 grid cell closest to Chennai.
ds = ds.sel(
    latitude=13.05,
    longitude=80.25,
    method="nearest",
)

print("\nSelected location:")
print("  Latitude :", float(ds.latitude))
print("  Longitude:", float(ds.longitude))

# Temperature: Kelvin -> Celsius
temperature_c = ds["t2m"] - 273.15
dewpoint_c = ds["d2m"] - 273.15

# Wind speed from u/v components
wind_speed = np.sqrt(
    ds["u10"] ** 2 +
    ds["v10"] ** 2
)

# Precipitation: metres -> millimetres
precip_mm = ds["tp"] * 1000.0

# Create hourly dataframe
daily = pd.DataFrame({
    "timestamp": pd.to_datetime(ds.valid_time.values),
    "temperature_c": temperature_c.values,
    "dewpoint_c": dewpoint_c.values,
    "u10_ms": ds["u10"].values,
    "v10_ms": ds["v10"].values,
    "wind_speed_ms": wind_speed.values,
    "surface_pressure_pa": ds["sp"].values,
    "precipitation_mm": precip_mm.values,
})

daily["date"] = daily["timestamp"].dt.strftime("%Y-%m-%d")

# Aggregate hourly ERA5 values to daily features.
features = (
    daily
    .groupby("date")
    .agg(
        temperature_mean_c=("temperature_c", "mean"),
        temperature_min_c=("temperature_c", "min"),
        temperature_max_c=("temperature_c", "max"),

        dewpoint_mean_c=("dewpoint_c", "mean"),

        u10_mean_ms=("u10_ms", "mean"),
        v10_mean_ms=("v10_ms", "mean"),
        wind_speed_mean_ms=("wind_speed_ms", "mean"),

        surface_pressure_mean_pa=("surface_pressure_pa", "mean"),

        precipitation_total_mm=("precipitation_mm", "sum"),
    )
    .reset_index()
)

# Temporal identifiers matching the Prithvi dataset.
timestamps = pd.to_datetime(features["date"])

features["year"] = timestamps.dt.year
features["julian_day"] = timestamps.dt.dayofyear

features["latitude"] = 13.05
features["longitude"] = 80.25

features = features[
    [
        "date",
        "year",
        "julian_day",
        "latitude",
        "longitude",

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
]

print("\n" + "=" * 70)
print("DAILY ERA5 FEATURES")
print("=" * 70)

print(features.to_string(index=False))

# Save CSV
csv_path = OUTPUT / "chennai_era5_daily_features.csv"

features.to_csv(
    csv_path,
    index=False,
)

print("\nSaved:")
print(csv_path)

# Save numerical feature matrix
feature_columns = [
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

matrix = features[feature_columns].to_numpy(
    dtype=np.float32
)

npy_path = OUTPUT / "chennai_era5_daily_features.npy"

np.save(
    npy_path,
    matrix,
)

print("\nFeature matrix:")
print("Shape:", matrix.shape)

print("\nSaved:")
print(npy_path)

print("\nMissing values:", int(np.isnan(matrix).sum()))

instant.close()
accum.close()

print("\n" + "=" * 70)
print("ERA5 FEATURE EXTRACTION SUCCESS")
print("=" * 70)
PY