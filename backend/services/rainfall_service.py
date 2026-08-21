from pathlib import Path

import numpy as np
import xarray as xr


# ============================================================
# CONFIGURATION
# ============================================================

DATA_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "RF25_ind2024_rfp25.nc"
)


# ============================================================
# LOAD DATASET
# ============================================================

def load_dataset():
    """
    Open the IMD rainfall NetCDF dataset.

    Dataset structure:

        TIME
        LATITUDE
        LONGITUDE
        RAINFALL

    Rainfall unit:
        mm
    """

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Rainfall dataset not found: {DATA_FILE}"
        )

    return xr.open_dataset(DATA_FILE)


# ============================================================
# DATASET INFORMATION
# ============================================================

def get_dataset_info():
    """
    Return metadata about the IMD rainfall dataset.
    """

    dataset = load_dataset()

    try:
        rainfall = dataset["RAINFALL"]

        return {
            "file": DATA_FILE.name,

            "variable": "RAINFALL",

            "units": rainfall.attrs.get(
                "units",
                "mm"
            ),

            "description": rainfall.attrs.get(
                "long_name",
                rainfall.attrs.get(
                    "description",
                    "Rainfall"
                )
            ),

            "dimensions": {
                name: int(size)
                for name, size
                in rainfall.sizes.items()
            },

            "latitude": {
                "min": float(
                    dataset["LATITUDE"].min().values
                ),

                "max": float(
                    dataset["LATITUDE"].max().values
                ),

                "count": int(
                    dataset["LATITUDE"].size
                ),
            },

            "longitude": {
                "min": float(
                    dataset["LONGITUDE"].min().values
                ),

                "max": float(
                    dataset["LONGITUDE"].max().values
                ),

                "count": int(
                    dataset["LONGITUDE"].size
                ),
            },

            "time": {
                "start": str(
                    dataset["TIME"].min().values
                ),

                "end": str(
                    dataset["TIME"].max().values
                ),

                "count": int(
                    dataset["TIME"].size
                ),
            },
        }

    finally:
        dataset.close()


# ============================================================
# VALIDATE DATE
# ============================================================

def validate_date(
    dataset,
    date: str
):
    """
    Validate that the requested date exists
    in the NetCDF dataset.
    """

    try:
        selected = dataset["RAINFALL"].sel(
            TIME=date
        )

        return selected

    except Exception as error:
        raise ValueError(
            f"Invalid or unavailable date '{date}'. "
            f"Dataset covers "
            f"{str(dataset['TIME'].min().values)} "
            f"to "
            f"{str(dataset['TIME'].max().values)}."
        ) from error


# ============================================================
# CLEAN RAINFALL VALUES
# ============================================================

def clean_rainfall_values(
    values
):
    """
    Convert rainfall values to float32 and
    remove invalid values.

    Invalid values include:

    - NaN
    - infinity
    - extremely large values
    """

    values = np.asarray(
        values,
        dtype=np.float32
    )

    values[
        ~np.isfinite(values)
    ] = np.nan

    values[
        np.abs(values) > 10000
    ] = np.nan

    return values


# ============================================================
# DAILY RAINFALL GRID
# ============================================================

def get_daily_rainfall(
    date: str
):
    """
    Return the complete rainfall grid
    for one date.

    The result contains:

        latitude
        longitude
        rainfall values
    """

    dataset = load_dataset()

    try:
        selected = validate_date(
            dataset,
            date
        )

        values = clean_rainfall_values(
            selected.values
        )

        return {
            "date": date,

            "variable": "RAINFALL",

            "units": "mm",

            "latitude": (
                dataset["LATITUDE"]
                .values
                .tolist()
            ),

            "longitude": (
                dataset["LONGITUDE"]
                .values
                .tolist()
            ),

            "values": np.where(
                np.isnan(values),
                None,
                values
            ).tolist(),
        }

    finally:
        dataset.close()


# ============================================================
# DAILY STATISTICS
# ============================================================

def get_daily_statistics(
    date: str
):
    """
    Calculate statistics for the rainfall
    field on a specific date.
    """

    dataset = load_dataset()

    try:
        selected = validate_date(
            dataset,
            date
        )

        values = clean_rainfall_values(
            selected.values
        )

        valid_values = values[
            np.isfinite(values)
        ]

        if valid_values.size == 0:
            raise ValueError(
                f"No valid rainfall values "
                f"were found for {date}."
            )

        return {
            "date": date,

            "units": "mm",

            "minimum": float(
                np.min(valid_values)
            ),

            "maximum": float(
                np.max(valid_values)
            ),

            "mean": float(
                np.mean(valid_values)
            ),

            "median": float(
                np.median(valid_values)
            ),

            "grid_points": int(
                valid_values.size
            ),
        }

    finally:
        dataset.close()


# ============================================================
# INDIA DAILY SUMMARY
# ============================================================

def get_india_daily_summary(
    date: str
):
    """
    Return a compact India-wide rainfall
    summary for one date.
    """

    statistics = get_daily_statistics(
        date
    )

    return {
        "date": statistics["date"],

        "rainfall": {
            "minimum_mm":
                statistics["minimum"],

            "maximum_mm":
                statistics["maximum"],

            "mean_mm":
                statistics["mean"],

            "median_mm":
                statistics["median"],
        },

        "grid_points":
            statistics["grid_points"],
    }


# ============================================================
# RAINFALL GRID AS GEOJSON
# ============================================================

def get_rainfall_grid(
    date: str
):
    """
    Convert one day's IMD rainfall grid
    into GeoJSON point features.

    Each valid 0.25-degree grid point becomes
    one GeoJSON Point.

    Example feature:

        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [
                    longitude,
                    latitude
                ]
            },
            "properties": {
                "rainfall_mm": 12.5,
                "date": "2024-07-15"
            }
        }
    """

    dataset = load_dataset()

    try:
        selected = validate_date(
            dataset,
            date
        )

        values = clean_rainfall_values(
            selected.values
        )

        latitudes = (
            dataset["LATITUDE"]
            .values
        )

        longitudes = (
            dataset["LONGITUDE"]
            .values
        )

        features = []

        for lat_index, latitude in enumerate(
            latitudes
        ):

            for lon_index, longitude in enumerate(
                longitudes
            ):

                value = values[
                    lat_index,
                    lon_index
                ]

                if not np.isfinite(value):
                    continue

                features.append(
                    {
                        "type": "Feature",

                        "geometry": {
                            "type": "Point",

                            "coordinates": [
                                float(longitude),
                                float(latitude),
                            ],
                        },

                        "properties": {
                            "rainfall_mm":
                                float(value),

                            "date":
                                date,
                        },
                    }
                )

        return {
            "type": "FeatureCollection",

            "features": features,
        }

    finally:
        dataset.close()


# ============================================================
# RAINFALL GRID METADATA
# ============================================================

def get_rainfall_grid_info(
    date: str
):
    """
    Return metadata about a particular
    rainfall grid without returning all
    grid values.
    """

    dataset = load_dataset()

    try:
        selected = validate_date(
            dataset,
            date
        )

        values = clean_rainfall_values(
            selected.values
        )

        valid_values = values[
            np.isfinite(values)
        ]

        return {
            "date": date,

            "variable": "RAINFALL",

            "units": "mm",

            "grid": {
                "latitude_count":
                    int(
                        dataset[
                            "LATITUDE"
                        ].size
                    ),

                "longitude_count":
                    int(
                        dataset[
                            "LONGITUDE"
                        ].size
                    ),

                "total_points":
                    int(
                        values.size
                    ),

                "valid_points":
                    int(
                        valid_values.size
                    ),
            },

            "statistics": {
                "minimum_mm":
                    float(
                        np.min(
                            valid_values
                        )
                    ),

                "maximum_mm":
                    float(
                        np.max(
                            valid_values
                        )
                    ),

                "mean_mm":
                    float(
                        np.mean(
                            valid_values
                        )
                    ),
            },
        }

    finally:
        dataset.close()