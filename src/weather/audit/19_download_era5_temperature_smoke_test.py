from pathlib import Path

import cdsapi


# ==================================================
# OUTPUT
# ==================================================

OUTPUT_DIR = Path(
    "data/weather/raw/era5"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


OUTPUT_FILE = (
    OUTPUT_DIR
    / "era5_20260802_00Z_2t_binh_dinh.grib2"
)


# ==================================================
# REQUEST
#
# Giữ nguyên request được CDS sinh ra.
# ==================================================

dataset = "reanalysis-era5-single-levels"


request = {
    "product_type": [
        "reanalysis"
    ],

    "variable": [
        "2m_temperature"
    ],

    "year": [
        "2026"
    ],

    "month": [
        "08"
    ],

    "day": [
        "02"
    ],

    "time": [
        "00:00"
    ],

    "data_format": "grib",

    "download_format": "unarchived",

    "area": [
        14,
        109,
        13.5,
        109.5,
    ],
}


# ==================================================
# EXPLAIN REQUEST
# ==================================================

print(
    "\n=== ERA5 TEMPERATURE SMOKE TEST ==="
)

print(
    "Reference time : 2026-08-02 00:00 UTC"
)

print(
    "Variable       : 2 m temperature"
)

print(
    "Purpose        : verify TIGGE +24h forecast"
)

print(
    "Area           : Bình Định audit bounding box"
)


# ==================================================
# DOWNLOAD
# ==================================================

print(
    "\nCreating CDS client..."
)

client = cdsapi.Client()


print(
    "\nDownloading ERA5..."
)


client.retrieve(
    dataset,
    request,
    str(OUTPUT_FILE),
)


# ==================================================
# RESULT
# ==================================================

print(
    "\nDOWNLOAD COMPLETE"
)

print(
    "Saved:"
)

print(
    OUTPUT_FILE
)


print(
    "Size:",
    round(
        OUTPUT_FILE.stat().st_size
        / 1024
        / 1024,
        3,
    ),
    "MB",
)