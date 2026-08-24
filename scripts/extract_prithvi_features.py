from pathlib import Path
import json
import sys

import numpy as np
import rasterio
import torch
from rasterio.warp import transform

ROOT = Path("/workspaces/india-climate-digital-twin")

MODEL_DIR = ROOT / "models/prithvi-eo-tiny"
DATA_DIR = ROOT / "data/india/chennai/prithvi_temporal"
OUTPUT_DIR = ROOT / "data/india/chennai/prithvi_features"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CHECKPOINT = MODEL_DIR / "Prithvi_EO_V2_tiny_TL.pt"
CONFIG = MODEL_DIR / "config.json"

sys.path.insert(0, str(MODEL_DIR))

from prithvi_mae import PrithviMAE


DEVICE = torch.device("cpu")

DATES = [
    "2025034T045929",
    "2025044T045829",
    "2025049T045911",
    "2025054T045719",
]

FILES = [
    DATA_DIR / f"Chennai_HLS.S30.T44PMV.{date}.v2.0.tif"
    for date in DATES
]


print("=" * 70)
print("PRITHVI-EO LATENT FEATURE EXTRACTION")
print("=" * 70)

print("Device     :", DEVICE)
print("Checkpoint :", CHECKPOINT)
print("Scenes     :", len(FILES))


for path in FILES:
    print("  ", path.name)

    if not path.exists():
        raise FileNotFoundError(
            f"Required input file not found:\n{path}"
        )


with open(CONFIG, "r") as f:
    config = json.load(f)

params = config["pretrained_cfg"]

MEAN = np.asarray(params["mean"], dtype=np.float32)
STD = np.asarray(params["std"], dtype=np.float32)


# ------------------------------------------------------------
# Load and normalize the four temporal scenes
# ------------------------------------------------------------

images = []

for path in FILES:

    print("\nLoading:", path.name)

    with rasterio.open(path) as src:
        image = src.read().astype(np.float32)
        source_crs = src.crs
        bounds = src.bounds

    if image.shape[0] != 6:
        raise ValueError(
            f"{path.name}: expected 6 bands, "
            f"found {image.shape[0]}"
        )

    print("  Shape:", image.shape)

    image = (
        image - MEAN[:, None, None]
    ) / STD[:, None, None]

    images.append(image)


# ------------------------------------------------------------
# Stack as B,C,T,H,W
# ------------------------------------------------------------

data = np.stack(images, axis=0)

print("\nOriginal stack T,C,H,W:", data.shape)

data = np.transpose(data, (1, 0, 2, 3))

data = np.expand_dims(data, axis=0)

print("Model input B,C,T,H,W:", data.shape)


# ------------------------------------------------------------
# Temporal coordinates
# ------------------------------------------------------------

temporal_coords = []

for date in DATES:

    year = int(date[:4])
    julian_day = int(date[4:7])

    temporal_coords.append(
        [year, julian_day]
    )

temporal_coords = torch.tensor(
    [temporal_coords],
    dtype=torch.float32,
    device=DEVICE,
)

print("\nTemporal coordinates:")
print(temporal_coords)


# ------------------------------------------------------------
# Geographic center
# ------------------------------------------------------------

center_x = (
    bounds.left + bounds.right
) / 2

center_y = (
    bounds.bottom + bounds.top
) / 2

lon, lat = transform(
    source_crs,
    "EPSG:4326",
    [center_x],
    [center_y],
)

location_coords = torch.tensor(
    [[lat[0], lon[0]]],
    dtype=torch.float32,
    device=DEVICE,
)

print("\nLocation:")
print("  Latitude :", lat[0])
print("  Longitude:", lon[0])


# ------------------------------------------------------------
# Tensor
# ------------------------------------------------------------

pixel_values = torch.from_numpy(
    data
).float().to(DEVICE)

print("\nInput tensor:", tuple(pixel_values.shape))


# ------------------------------------------------------------
# Create model
# ------------------------------------------------------------

print("\nCreating Prithvi-EO model...")

model = PrithviMAE(
    img_size=params["img_size"],
    patch_size=tuple(params["patch_size"]),
    num_frames=params["num_frames"],
    in_chans=params["in_chans"],
    embed_dim=params["embed_dim"],
    depth=params["depth"],
    num_heads=params["num_heads"],
    decoder_embed_dim=params["decoder_embed_dim"],
    decoder_depth=params["decoder_depth"],
    decoder_num_heads=params["decoder_num_heads"],
    mlp_ratio=params["mlp_ratio"],
    coords_encoding=params["coords_encoding"],
    coords_scale_learn=params["coords_scale_learn"],
    mask_ratio=params["mask_ratio"],
    norm_pix_loss=params["norm_pix_loss"],
)

model.to(DEVICE)


# ------------------------------------------------------------
# Load checkpoint
# ------------------------------------------------------------

print("Loading checkpoint...")

checkpoint = torch.load(
    CHECKPOINT,
    map_location=DEVICE,
    weights_only=True,
)

if "model" in checkpoint:
    state_dict = checkpoint["model"]
else:
    state_dict = checkpoint

missing, unexpected = model.load_state_dict(
    state_dict,
    strict=False,
)

print("Missing keys   :", len(missing))
print("Unexpected keys:", len(unexpected))

if missing:
    print("WARNING: missing checkpoint keys.")

if unexpected:
    print("WARNING: unexpected checkpoint keys.")

print("Checkpoint loaded.")


# ------------------------------------------------------------
# Extract encoder representation
# ------------------------------------------------------------

model.eval()

print("\nRunning encoder...")
print("CPU feature extraction started.")

with torch.no_grad():

    features = model.encoder.forward_features(
        pixel_values,
        temporal_coords,
        location_coords,
    )


# ------------------------------------------------------------
# Results
# ------------------------------------------------------------

print()
print("=" * 70)
print("FEATURE EXTRACTION COMPLETE")
print("=" * 70)

print()
print("=" * 70)
print("ENCODER OUTPUT INSPECTION")
print("=" * 70)

print("Feature type :", type(features))
print("List length  :", len(features))

for i, item in enumerate(features):

    print()
    print(f"FEATURE [{i}]")
    print("-" * 50)
    print("Type :", type(item))

    if hasattr(item, "shape"):
        print("Shape:", tuple(item.shape))

    if hasattr(item, "dtype"):
        print("Dtype:", item.dtype)

    if hasattr(item, "numel"):
        print("Elements:", item.numel())

print()
print("=" * 70)
print("INSPECTION COMPLETE")
print("=" * 70)

# ------------------------------------------------------------
# Select final encoder representation
# ------------------------------------------------------------

final_features = features[-1]

print()
print("=" * 70)
print("FINAL PRITHVI REPRESENTATION")
print("=" * 70)

print("Final feature shape:", tuple(final_features.shape))
print("Final feature dtype:", final_features.dtype)

print(
    "Final feature min  :",
    float(final_features.min())
)

print(
    "Final feature max  :",
    float(final_features.max())
)

print(
    "Final feature mean :",
    float(final_features.mean())
)

print(
    "Final feature std  :",
    float(final_features.std())
)


# ------------------------------------------------------------
# Create scene-level embedding
#
# 3921 spatial/temporal tokens
#             ↓
#       mean pooling
#             ↓
#        192 features
# ------------------------------------------------------------

scene_features = final_features.mean(dim=1)

print()
print("Scene-level feature shape:")
print(tuple(scene_features.shape))


# ------------------------------------------------------------
# Save token-level representation
# ------------------------------------------------------------

token_output = (
    OUTPUT_DIR /
    "chennai_prithvi_tokens.npy"
)

np.save(
    token_output,
    final_features.cpu().numpy(),
)

print()
print("Token features saved:")
print(token_output)


# ------------------------------------------------------------
# Save scene-level representation
# ------------------------------------------------------------

scene_output = (
    OUTPUT_DIR /
    "chennai_prithvi_scene_features.npy"
)

np.save(
    scene_output,
    scene_features.cpu().numpy(),
)

print()
print("Scene features saved:")
print(scene_output)


# ------------------------------------------------------------
# Final summary
# ------------------------------------------------------------

print()
print("=" * 70)
print("PRITHVI FEATURE EXTRACTION SUCCESS")
print("=" * 70)

print("Token representation :", tuple(final_features.shape))
print("Scene representation :", tuple(scene_features.shape))

print(
    "Token file size:",
    round(
        token_output.stat().st_size /
        (1024 * 1024),
        2,
    ),
    "MB",
)

print(
    "Scene file size:",
    round(
        scene_output.stat().st_size /
        (1024 * 1024),
        2,
    ),
    "MB",
)

print("=" * 70)