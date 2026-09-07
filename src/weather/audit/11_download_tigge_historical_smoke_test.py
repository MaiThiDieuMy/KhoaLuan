from pathlib import Path

import cdsapi


# ===============================================
# OUTPUT
# ===============================================

OUTPUT_DIR = Path(
    "data/weather/raw/tigge"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


OUTPUT_FILE = (
    OUTPUT_DIR
    / "tigge_ecmwf_20260801_00Z_2t_step24.grib2"
)


# ===============================================
# REQUEST
# ===============================================

dataset = "tigge-forecasts"


request = {
    "origin": "ecmwf",

    "year": "2026",
    "month": "08",
    "day": "01",

    "time": "00:00",

    "level_type": "single_level",

    "variable": [
        "2_m_temperature"
    ],

    "forecast_type": "control_forecast",

    "leadtime_hour": [
        "24"
    ],

    "data_format": "grib",
}


# ===============================================
# DOWNLOAD
# ===============================================

print(
    "Creating ECDS client..."
)

client = cdsapi.Client()


print(
    "\nRequesting TIGGE historical forecast..."
)

print(
    "Run time : 2026-08-01 00:00 UTC"
)

print(
    "Lead     : +24 hours"
)

print(
    "Variable : 2 m temperature"
)

print(
    "Origin   : ECMWF"
)


client.retrieve(
    dataset,
    request,
    str(OUTPUT_FILE),
)


# ===============================================
# RESULT
# ===============================================

print(
    "\nDOWNLOAD COMPLETE"
)


print(
    "Saved to:"
)

print(
    OUTPUT_FILE
)


print(
    "Size:"
)

print(
    round(
        OUTPUT_FILE.stat().st_size
        / 1024
        / 1024,
        2,
    ),
    "MB",
)