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


FILE_01_15 = (
    OUTPUT_DIR
    / "era5_20260801_15_2t_6hourly_binh_dinh.grib2"
)


FILE_16 = (
    OUTPUT_DIR
    / "era5_20260816_00Z_2t_binh_dinh.grib2"
)


# ==================================================
# EXPECTED VALID TIMES
# ==================================================

DAYS_01_TO_15 = [
    f"{day:02d}"
    for day in range(
        1,
        16,
    )
]


TIMES_6H = [
    "00:00",
    "06:00",
    "12:00",
    "18:00",
]


expected_first_request = (
    len(DAYS_01_TO_15)
    *
    len(TIMES_6H)
)


expected_second_request = 1


expected_total = (
    expected_first_request
    +
    expected_second_request
)


print(
    "\n=== ERA5 FULL VALID-TIME DOWNLOAD ==="
)


print(
    "\nTIGGE forecast run:"
)

print(
    "2026-08-01 00:00 UTC"
)


print(
    "\nForecast leads:"
)

print(
    "0 → 360 hours, every 6 hours"
)


print(
    "\nExpected ERA5 verification times:"
)

print(
    "Request A:",
    expected_first_request,
)

print(
    "Request B:",
    expected_second_request,
)

print(
    "Total:",
    expected_total,
)


# ==================================================
# CDS CLIENT
# ==================================================

dataset = (
    "reanalysis-era5-single-levels"
)


client = cdsapi.Client()


# ==================================================
# REQUEST A
#
# 01 Aug → 15 Aug
# 4 timestamps/day
#
# 15 × 4 = 60
# ==================================================

request_01_15 = {

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

    "day":
        DAYS_01_TO_15,

    "time":
        TIMES_6H,

    "data_format":
        "grib",

    "download_format":
        "unarchived",

    "area": [
        14,
        109,
        13.5,
        109.5,
    ],
}


print(
    "\n================================"
)

print(
    "REQUEST A"
)

print(
    "01 Aug → 15 Aug"
)

print(
    "00 / 06 / 12 / 18 UTC"
)

print(
    "Expected times:",
    expected_first_request,
)

print(
    "================================"
)


client.retrieve(
    dataset,
    request_01_15,
    str(FILE_01_15),
)


print(
    "\nREQUEST A DOWNLOAD COMPLETE"
)

print(
    "File:",
    FILE_01_15,
)

print(
    "Size bytes:",
    FILE_01_15.stat().st_size,
)


# ==================================================
# REQUEST B
#
# Final required valid time:
# 16 Aug 00 UTC
# ==================================================

request_16 = {

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
        "16"
    ],

    "time": [
        "00:00"
    ],

    "data_format":
        "grib",

    "download_format":
        "unarchived",

    "area": [
        14,
        109,
        13.5,
        109.5,
    ],
}


print(
    "\n================================"
)

print(
    "REQUEST B"
)

print(
    "16 Aug 00 UTC"
)

print(
    "Expected times:",
    expected_second_request,
)

print(
    "================================"
)


client.retrieve(
    dataset,
    request_16,
    str(FILE_16),
)


print(
    "\nREQUEST B DOWNLOAD COMPLETE"
)

print(
    "File:",
    FILE_16,
)

print(
    "Size bytes:",
    FILE_16.stat().st_size,
)


# ==================================================
# SUMMARY
# ==================================================

print(
    "\n================================"
)

print(
    "DOWNLOAD SUMMARY"
)

print(
    "================================"
)


print(
    "Expected ERA5 timestamps:",
    expected_total,
)


print(
    "\nFile A:"
)

print(
    FILE_01_15,
)


print(
    "\nFile B:"
)

print(
    FILE_16,
)


print(
    "\nDOWNLOAD STATUS: PASS"
)

print(
    "\nNOTE:"
)

print(
    "PASS here only means both CDS downloads completed."
)

print(
    "The next audit must still verify that the GRIB files"
)

print(
    "actually contain all 61 expected timestamps."
)