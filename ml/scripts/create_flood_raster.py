from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone

import numpy as np
from PIL import Image
import rasterio
from rasterio.transform import from_bounds


# ---------------------------------------------------------
# Dataset configuration
# ---------------------------------------------------------

RAW_FILE = Path("data/raw/bhuvan/or_011011_flood.png")
OUTPUT_FILE = Path(
    "data/interim/flood_labels/or_011011_flood.tif"
)
METADATA_FILE = Path(
    "data/raw/bhuvan/or_011011_flood_metadata.json"
)

# Bounding box obtained from the official Bhuvan WMS
# EPSG:4326
WEST = 82.1822
SOUTH = 18.7311
EAST = 87.5074
NORTH = 22.4897


# ---------------------------------------------------------
# Validation
# ---------------------------------------------------------

if not RAW_FILE.exists():
    raise FileNotFoundError(
        f"Raw flood file not found: {RAW_FILE}"
    )


# ---------------------------------------------------------
# Read original WMS image
# ---------------------------------------------------------

image = Image.open(RAW_FILE).convert("P")
pixels = np.array(image, dtype=np.uint8)

height, width = pixels.shape

print("Input file:", RAW_FILE)
print("Image size:", width, "x", height)
print("Unique pixel values:", np.unique(pixels))


# ---------------------------------------------------------
# Convert WMS flood class
#
# Bhuvan rendering:
#   palette index 0 -> background/transparent
#   palette index 1 -> visible flood class
# ---------------------------------------------------------

flood_mask = (pixels == 1).astype(np.uint8)

flood_pixels = int(flood_mask.sum())

print("Flood pixels:", flood_pixels)


# ---------------------------------------------------------
# Create geospatial transform
# ---------------------------------------------------------

transform = from_bounds(
    WEST,
    SOUTH,
    EAST,
    NORTH,
    width,
    height,
)


# ---------------------------------------------------------
# Write GeoTIFF
# ---------------------------------------------------------

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

with rasterio.open(
    OUTPUT_FILE,
    "w",
    driver="GTiff",
    height=height,
    width=width,
    count=1,
    dtype="uint8",
    crs="EPSG:4326",
    transform=transform,
    nodata=0,
    compress="lzw",
) as dst:

    dst.write(flood_mask, 1)


# ---------------------------------------------------------
# SHA-256 of original raw file
# ---------------------------------------------------------

sha256 = hashlib.sha256(
    RAW_FILE.read_bytes()
).hexdigest()


# ---------------------------------------------------------
# Dataset provenance
# ---------------------------------------------------------

metadata = {
    "dataset_id": "DS-BHV-OR-2011-1001",
    "provider": "NRSC / ISRO Bhuvan",
    "layer": "or_011011_flood",
    "event_date": "2011-10-01",
    "study_area": "Odisha, India",
    "source_type": "WMS rendered flood inundation layer",
    "source_url": (
        "https://bhuvan-ras2.nrsc.gov.in/"
        "cgi-bin/flood.exe"
    ),
    "raw_file": str(RAW_FILE).replace("\\", "/"),
    "derived_file": str(OUTPUT_FILE).replace("\\", "/"),
    "crs": "EPSG:4326",
    "bbox": [
        WEST,
        SOUTH,
        EAST,
        NORTH,
    ],
    "width": width,
    "height": height,
    "class_encoding": {
        "0": "background/non-flood in WMS rendering",
        "1": "flood-visible pixel",
    },
    "flood_pixel_count": flood_pixels,
    "raw_sha256": sha256,
    "processed_at": datetime.now(
        timezone.utc
    ).isoformat(),
}


METADATA_FILE.write_text(
    json.dumps(
        metadata,
        indent=2,
    ),
    encoding="utf-8",
)


# ---------------------------------------------------------
# Final verification
# ---------------------------------------------------------

with rasterio.open(OUTPUT_FILE) as dataset:
    print()
    print("GeoTIFF created successfully")
    print("Output:", OUTPUT_FILE)
    print("CRS:", dataset.crs)
    print("Bounds:", dataset.bounds)
    print("Width:", dataset.width)
    print("Height:", dataset.height)
    print("NoData:", dataset.nodata)

print("Metadata:", METADATA_FILE)
print()
print("FLOOD RASTER PROCESSING COMPLETE")