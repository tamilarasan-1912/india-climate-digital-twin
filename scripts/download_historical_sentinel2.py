import pystac_client
import planetary_computer
import rasterio
from rasterio.windows import from_bounds
from pathlib import Path
import requests
from urllib.parse import urlparse

# ============================================================
# CONFIGURATION
# ============================================================

OUTPUT = Path(
    "data/india/chennai/sentinel2_historical"
)

OUTPUT.mkdir(
    parents=True,
    exist_ok=True
)

BBOX = [
    80.15,
    12.90,
    80.35,
    13.20
]

BANDS = [
    "B02",
    "B03",
    "B04",
    "B05",
    "B06",
    "B07",
    "SCL",
]

SCENES = [
    # 2021
    (
        "2021-02-04",
        "S2B_MSIL2A_20210204T050009_R119_T44PMV_20210209T203854"
    ),
    (
        "2021-02-09",
        "S2A_MSIL2A_20210209T045941_R119_T44PMV_20210212T050714"
    ),
    (
        "2021-02-14",
        "S2B_MSIL2A_20210214T045909_R119_T44PMV_20210215T170941"
    ),
    (
        "2021-02-24",
        "S2B_MSIL2A_20210224T045759_R119_T44PMV_20210224T155143"
    ),

    # 2022
    (
        "2022-02-04",
        "S2A_MSIL2A_20220204T050011_R119_T44PMV_20220218T111946"
    ),
    (
        "2022-02-24",
        "S2A_MSIL2A_20220224T045811_R119_T44PMV_20220301T071501"
    ),

    # 2023
    (
        "2023-02-14",
        "S2B_MSIL2A_20230214T045909_R119_T44PMV_20230214T135437"
    ),
    (
        "2023-02-19",
        "S2A_MSIL2A_20230219T045841_R119_T44PMV_20230221T020040"
    ),
    (
        "2023-02-24",
        "S2B_MSIL2A_20230224T045809_R119_T44PMV_20230226T131449"
    ),

    # 2024
    (
        "2024-02-04",
        "S2A_MSIL2A_20240204T050011_R119_T44PMV_20240204T091031"
    ),
    (
        "2024-02-09",
        "S2B_MSIL2A_20240209T045949_R119_T44PMV_20240209T092438"
    ),
    (
        "2024-02-14",
        "S2A_MSIL2A_20240214T045911_R119_T44PMV_20240214T091808"
    ),
    (
        "2024-02-24",
        "S2A_MSIL2A_20240224T045811_R119_T44PMV_20240224T100911"
    ),
]

# ============================================================
# STAC
# ============================================================

catalog = pystac_client.Client.open(
    "https://planetarycomputer.microsoft.com/api/stac/v1",
    modifier=planetary_computer.sign_inplace,
)

# ============================================================
# DOWNLOAD
# ============================================================

print("=" * 70)
print("HISTORICAL SENTINEL-2 DOWNLOAD")
print("=" * 70)

print("Scenes:", len(SCENES))
print("Bands :", len(BANDS))
print("Files :", len(SCENES) * len(BANDS))

for index, (date, scene_id) in enumerate(SCENES, 1):

    print()
    print("=" * 70)
    print(f"[{index}/{len(SCENES)}] {date}")
    print(scene_id)
    print("=" * 70)

    search = catalog.search(
        collections=["sentinel-2-l2a"],
        ids=[scene_id],
    )

    items = list(search.items())

    if not items:
        raise RuntimeError(
            f"Scene not found: {scene_id}"
        )

    item = items[0]

    for band in BANDS:

        asset = item.assets.get(band)

        if asset is None:
            raise RuntimeError(
                f"{band} missing in {scene_id}"
            )

        output_file = (
            OUTPUT /
            f"{date.replace('-', '')}_{band}.tif"
        )

        if output_file.exists():
            print(
                f"SKIP {band} "
                f"(already exists)"
            )
            continue

        print(
            f"Downloading {band}..."
        )

        signed_href = asset.href

        response = requests.get(
            signed_href,
            stream=True,
            timeout=120
        )

        response.raise_for_status()

        temp_file = (
            OUTPUT /
            f".{output_file.name}.tmp"
        )

        with open(temp_file, "wb") as f:

            for chunk in response.iter_content(
                chunk_size=1024 * 1024
            ):

                if chunk:
                    f.write(chunk)

        temp_file.rename(output_file)

        print(
            f"Saved: {output_file}"
        )

print()
print("=" * 70)
print("HISTORICAL SENTINEL-2 DOWNLOAD COMPLETE")
print("=" * 70)

print(
    "Expected files:",
    len(SCENES) * len(BANDS)
)

print(
    "Actual files:",
    len(list(OUTPUT.glob("*.tif")))
)

print("=" * 70)
