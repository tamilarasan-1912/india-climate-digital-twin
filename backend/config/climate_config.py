"""
Climate variable configuration for the
India Climate Digital Twin.

This file defines the climate variables supported
by the application.

At this stage, rainfall is the first fully connected
scientific dataset.

Other variables are registered here so that the
architecture is ready for future datasets.
"""


CLIMATE_VARIABLES = {

    "rainfall": {
        "name": "Rainfall",

        "short_name": "RF",

        "unit": "mm",

        "description":
            "Daily rainfall from IMD gridded data.",

        "provider": "IMD",

        "dataset":
            "RF25_ind2024_rfp25.nc",

        "variable":
            "RAINFALL",

        "status": "active",

        "endpoint":
            "/api/rainfall",
    },


    "temperature": {
        "name": "Temperature",

        "short_name": "TEMP",

        "unit": "°C",

        "description":
            "Air temperature data.",

        "provider": "IMD",

        "dataset": None,

        "variable": None,

        "status": "planned",

        "endpoint":
            "/api/temperature",
    },


    "wind": {
        "name": "Wind",

        "short_name": "WIND",

        "unit": "m/s",

        "description":
            "Wind speed and direction data.",

        "provider": "IMD",

        "dataset": None,

        "variable": None,

        "status": "planned",

        "endpoint":
            "/api/wind",
    },


    "humidity": {
        "name": "Humidity",

        "short_name": "RH",

        "unit": "%",

        "description":
            "Atmospheric relative humidity.",

        "provider": "IMD",

        "dataset": None,

        "variable": None,

        "status": "planned",

        "endpoint":
            "/api/humidity",
    },


    "land_surface_temperature": {
        "name":
            "Land Surface Temperature",

        "short_name": "LST",

        "unit": "°C",

        "description":
            "Land surface temperature derived from satellite observations.",

        "provider": "ISRO / MOSDAC",

        "dataset": None,

        "variable": None,

        "status": "planned",

        "endpoint":
            "/api/land-surface-temperature",
    },

}