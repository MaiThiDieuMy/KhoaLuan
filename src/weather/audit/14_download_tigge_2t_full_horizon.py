from pathlib import Path

import cdsapi


# ==========================================
# OUTPUT
# ==========================================

OUTPUT_DIR = Path(
    "data/weather/raw/tigge"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


OUTPUT_FILE = (
    OUTPUT_DIR
    / "tigge_ecmwf_20260801_00Z_2t_0_360.grib2"
)


# ==========================================
# LEAD TIMES
#
# TIGGE ECMWF:
# 0 → 360h
# mỗi 6 giờ
# ==========================================

LEAD_TIMES = [
    str(hour)
    for hour in range(
        0,
        361,
        6,
    )
]


print(
    "Number of requested leads:",
    len(LEAD_TIMES),
)

print(
    "First leads:",
    LEAD_TIMES[:10],
)

print(
    "Last leads:",
    LEAD_TIMES[-10:],
)


# ==========================================
# TIGGE REQUEST
# ==========================================

dataset = "tigge-forecasts"


request = {
    "origin": "ecmwf",

    "year": "2026",
    "month": "08",
    "day": "01",

    "time": "00:00",

    "level_type": "single_level",

    "variable": [
        "2_m_temperature",
    ],

    "forecast_type": "control_forecast",

    "leadtime_hour": LEAD_TIMES,

    "data_format": "grib",
}


# ==========================================
# DOWNLOAD
# ==========================================

print(
    "\nCreating ECDS client..."
)

client = cdsapi.Client()


print(
    "\nDownloading historical "
    "TIGGE 2t 0–360h..."
)


client.retrieve(
    dataset,
    request,
    str(OUTPUT_FILE),
)


# ==========================================
# RESULT
# ==========================================

print(
    "\nDOWNLOAD COMPLETE"
)

print(
    "File:",
    OUTPUT_FILE,
)

print(
    "Size:",
    round(
        OUTPUT_FILE.stat().st_size
        / 1024
        / 1024,
        2,
    ),
    "MB",
)