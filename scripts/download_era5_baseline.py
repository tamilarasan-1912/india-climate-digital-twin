import cdsapi
from pathlib import Path

OUTPUT_DIR = Path("data/india/chennai/era5/baseline")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = (
    OUTPUT_DIR /
    "chennai_era5_february_2020_2024.nc"
)

client = cdsapi.Client(
    quiet=False,
    debug=False,
)

print("=" * 70)
print("ERA5 CHENNAI HISTORICAL BASELINE DOWNLOAD")
print("=" * 70)

print("Location:")
print("  Latitude :", 13.05)
print("  Longitude:", 80.25)

print()
print("Period:")
print("  February 2020–2024")

print()
print("Variables:")
print("  2m temperature")
print("  2m dewpoint temperature")
print("  10m u-component of wind")
print("  10m v-component of wind")
print("  Surface pressure")
print("  Total precipitation")

print()
print("Output:")
print(OUTPUT_FILE)

print("=" * 70)

client.retrieve(
    "reanalysis-era5-single-levels",
    {
        "product_type": "reanalysis",

        "variable": [
            "2m_temperature",
            "2m_dewpoint_temperature",
            "10m_u_component_of_wind",
            "10m_v_component_of_wind",
            "surface_pressure",
            "total_precipitation",
        ],

        "year": [
            "2020",
            "2021",
            "2022",
            "2023",
            "2024",
        ],

        "month": "02",

        "day": [
            f"{day:02d}"
            for day in range(1, 29)
        ],

        "time": [
            f"{hour:02d}:00"
            for hour in range(24)
        ],

        # North, West, South, East
        "area": [
            13.10,
            80.20,
            13.00,
            80.30,
        ],

        "data_format": "netcdf",

        "download_format": "unarchived",

    },
    str(OUTPUT_FILE),
)

print()
print("=" * 70)
print("ERA5 BASELINE DOWNLOAD COMPLETE")
print("=" * 70)

print("File:")
print(OUTPUT_FILE)

print("=" * 70)
