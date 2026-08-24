from pathlib import Path
import sys
import re

import numpy as np
import rasterio
import torch

# Make the official Prithvi-EO source available
MODEL_DIR = (
    Path(__file__).resolve().parent.parent
    / "models"
    / "prithvi-eo-tiny"
)

sys.path.insert(0, str(MODEL_DIR))

from prithvi_mae import PrithviMAE
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "models" / "prithvi-eo-tiny"))
from prithvi_mae import PrithviMAE


# ============================================================
# PATHS
# ============================================================

ROOT = Path("/workspaces/india-climate-digital-twin")

INPUT_DIR = ROOT / "data/india/chennai/prithvi_temporal"

MODEL_DIR = ROOT / "models/prithvi-eo-tiny"

OUTPUT_DIR = ROOT / "data/india/chennai/prithvi_features"

CHECKPOINT = MODEL_DIR / "Prithvi_EO_V2_tiny_TL.pt"

CONFIG = MODEL_DIR / "config.json"


# ============================================================
# SETTINGS
# ============================================================

DEVICE = torch.device("cpu")

EXPECTED_BANDS = 6

EXPECTED_FEATURES = 192

EXPECTED_TOKENS = 3921


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("PRITHVI-EO PER-TIMESTEP FEATURE EXTRACTION")
print("=" * 70)

print("Device     :", DEVICE)
print("Input dir  :", INPUT_DIR)
print("Checkpoint :", CHECKPOINT)
print()


# ============================================================
# FIND INPUT SCENES
# ============================================================

scene_files = sorted(INPUT_DIR.glob("*.tif"))

if len(scene_files) == 0:
    raise FileNotFoundError(
        f"No TIFF files found in {INPUT_DIR}"
    )

print("Scenes found:", len(scene_files))

for path in scene_files:
    print("  ", path.name)

print()


# ============================================================
# READ SCENES
# ============================================================

scene_arrays = []
scene_dates = []

latitude = None
longitude = None

for path in scene_files:

    print("Loading:", path.name)

    match = re.search(
        r"\.(\d{7})T\d{6}\.",
        path.name,
    )

    if match is None:
        raise ValueError(
            f"Could not extract date from filename: {path.name}"
        )

    timestamp = match.group(1)

    year = int(timestamp[:4])
    julian_day = int(timestamp[4:])

    scene_dates.append(
        {
            "timestamp": timestamp,
            "year": year,
            "julian_day": julian_day,
        }
    )

    with rasterio.open(path) as src:

        data = src.read().astype(np.float32)

        if data.shape[0] != EXPECTED_BANDS:
            raise ValueError(
                f"{path.name}: expected "
                f"{EXPECTED_BANDS} bands, "
                f"found {data.shape[0]}"
            )

        if latitude is None:

            transform = src.transform

            center_x = (
                transform.c
                + (src.width / 2) * transform.a
            )

            center_y = (
                transform.f
                + (src.height / 2) * transform.e
            )

            # The dataset is EPSG:32644, so convert the
            # center coordinate to latitude/longitude.
            from rasterio.warp import transform as rio_transform

            longitude_list, latitude_list = rio_transform(
                src.crs,
                "EPSG:4326",
                [center_x],
                [center_y],
            )

            longitude = longitude_list[0]
            latitude = latitude_list[0]

    print("  Shape:", data.shape)

    scene_arrays.append(data)

print()


# ============================================================
# CREATE MODEL
# ============================================================

print("=" * 70)
print("CREATING PRITHVI-EO MODEL")
print("=" * 70)

model = PrithviMAE(
    img_size=224,
    patch_size=(1, 16, 16),
    in_chans=6,
    num_frames=4,
    tubelet_size=1,
    embed_dim=192,
    depth=12,
    num_heads=3,
    decoder_embed_dim=512,
    decoder_depth=8,
    decoder_num_heads=16,
    mlp_ratio=4,
    norm_layer=torch.nn.LayerNorm,
    coords_encoding=("time", "location"),
    coords_scale_learn=True,
)

print("Model created.")


# ============================================================
# LOAD CHECKPOINT
# ============================================================

print("Loading checkpoint...")

checkpoint = torch.load(
    CHECKPOINT,
    map_location=DEVICE,
    weights_only=True,
)

missing, unexpected = model.load_state_dict(
    checkpoint,
    strict=False,
)

print("Missing keys   :", len(missing))
print("Unexpected keys:", len(unexpected))

if len(missing) != 0 or len(unexpected) != 0:
    raise RuntimeError(
        "Checkpoint does not match model architecture."
    )

model.to(DEVICE)

model.eval()

print("Checkpoint loaded successfully.")
print()


# ============================================================
# TEMPORAL FEATURE EXTRACTION
# ============================================================

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

all_scene_features = []

print("=" * 70)
print("EXTRACTING FEATURES")
print("=" * 70)

for index, data in enumerate(scene_arrays):

    info = scene_dates[index]

    print()
    print(
        f"[{index + 1}/{len(scene_arrays)}] "
        f"{info['timestamp']}"
    )

    # --------------------------------------------------------
    # Create a four-frame temporal input.
    #
    # Prithvi expects four temporal frames.
    # For per-date embedding, the target scene is repeated
    # across the four temporal positions.
    # --------------------------------------------------------

    temporal_data = np.stack(
        [data, data, data, data],
        axis=1,
    )

    # Shape:
    # (C, T, H, W)

    model_input = torch.from_numpy(
        temporal_data
    ).unsqueeze(0)

    # Shape:
    # (B, C, T, H, W)

    # --------------------------------------------------------
    # Normalize exactly like the model expects.
    # --------------------------------------------------------

    mean = torch.tensor(
        [
            1087.0,
            1342.0,
            1433.0,
            2734.0,
            1958.0,
            1363.0,
        ],
        dtype=torch.float32,
    ).view(1, 6, 1, 1, 1)

    std = torch.tensor(
        [
            2248.0,
            2179.0,
            2178.0,
            1850.0,
            1242.0,
            1049.0,
        ],
        dtype=torch.float32,
    ).view(1, 6, 1, 1, 1)

    model_input = (
        model_input - mean
    ) / std

    model_input = model_input.to(DEVICE)

    # --------------------------------------------------------
    # Coordinates
    # --------------------------------------------------------

    temporal_coords = torch.tensor(
        [
            [
                [
                    float(info["year"]),
                    float(info["julian_day"]),
                ],
                [
                    float(info["year"]),
                    float(info["julian_day"]),
                ],
                [
                    float(info["year"]),
                    float(info["julian_day"]),
                ],
                [
                    float(info["year"]),
                    float(info["julian_day"]),
                ],
            ]
        ],
        dtype=torch.float32,
        device=DEVICE,
    )

    location_coords = torch.tensor(
        [
            [
                latitude,
                longitude,
            ]
        ],
        dtype=torch.float32,
        device=DEVICE,
    )

    # --------------------------------------------------------
    # Encoder
    # --------------------------------------------------------

    with torch.no_grad():

        features = model.forward_features(
            model_input,
            temporal_coords,
            location_coords,
        )

    if not isinstance(features, list):
        raise TypeError(
            "Expected encoder output to be a list."
        )

    if len(features) != 12:
        raise ValueError(
            f"Expected 12 encoder blocks, "
            f"found {len(features)}"
        )

    final_features = features[-1]

    if tuple(final_features.shape) != (
        1,
        EXPECTED_TOKENS,
        EXPECTED_FEATURES,
    ):
        raise ValueError(
            "Unexpected final feature shape: "
            f"{tuple(final_features.shape)}"
        )

    # --------------------------------------------------------
    # Mean-pool spatial/temporal tokens
    # --------------------------------------------------------

    scene_feature = final_features.mean(
        dim=1
    )

    # Shape:
    # (1, 192)

    scene_feature = (
        scene_feature
        .squeeze(0)
        .cpu()
        .numpy()
        .astype(np.float32)
    )

    all_scene_features.append(
        scene_feature
    )

    print(
        "  Feature shape:",
        scene_feature.shape,
    )

    print(
        "  Mean:",
        float(scene_feature.mean()),
    )

    print(
        "  Std :",
        float(scene_feature.std()),
    )


# ============================================================
# CREATE FEATURE MATRIX
# ============================================================

feature_matrix = np.stack(
    all_scene_features,
    axis=0,
)

print()
print("=" * 70)
print("FEATURE MATRIX")
print("=" * 70)

print(
    "Shape:",
    feature_matrix.shape,
)

print(
    "Expected:",
    (len(scene_files), EXPECTED_FEATURES),
)


# ============================================================
# SAVE NUMPY FILE
# ============================================================

numpy_output = (
    OUTPUT_DIR /
    "chennai_prithvi_temporal_features.npy"
)

np.save(
    numpy_output,
    feature_matrix,
)

print()
print("Saved:")
print(numpy_output)


# ============================================================
# SAVE CSV
# ============================================================

import csv

csv_output = (
    OUTPUT_DIR /
    "chennai_prithvi_temporal_features.csv"
)

header = [
    "timestamp",
    "year",
    "julian_day",
    "latitude",
    "longitude",
]

header += [
    f"prithvi_{i:03d}"
    for i in range(EXPECTED_FEATURES)
]

with open(
    csv_output,
    "w",
    newline="",
) as f:

    writer = csv.writer(f)

    writer.writerow(header)

    for index, feature_vector in enumerate(
        feature_matrix
    ):

        info = scene_dates[index]

        row = [
            info["timestamp"],
            info["year"],
            info["julian_day"],
            latitude,
            longitude,
        ]

        row.extend(
            feature_vector.tolist()
        )

        writer.writerow(row)


print()
print("Saved:")
print(csv_output)


# ============================================================
# FINAL VALIDATION
# ============================================================

print()
print("=" * 70)
print("TEMPORAL PRITHVI FEATURE EXTRACTION SUCCESS")
print("=" * 70)

print(
    "Scenes              :",
    len(scene_files),
)

print(
    "Features per scene  :",
    EXPECTED_FEATURES,
)

print(
    "Feature matrix      :",
    feature_matrix.shape,
)

print(
    "Latitude            :",
    latitude,
)

print(
    "Longitude           :",
    longitude,
)

print()
print("Output files:")

print(
    "  ",
    numpy_output,
)

print(
    "  ",
    csv_output,
)

print("=" * 70)