from pathlib import Path

import cdsapi


# ==================================================
# OUTPUT
# ==================================================

OUTPUT_DIR = Path(
    "data/weather/raw/tigge"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


OUTPUT_FILE = (
    OUTPUT_DIR
    / "tigge_ecmwf_20260801_00Z_variables_step24.grib2"
)


# ==================================================
# TIGGE REQUEST
#
# Giữ nguyên variable names do ECDS sinh ra.
# Không tự sửa schema.
# ==================================================

dataset = "tigge-forecasts"


VARIABLES = [
    "10_m_u_component_of_wind",
    "10_m_v_component_of_wind",
    "2_m_dewpoint_temperature",
    "2_m_temperature",
    "surface_pressure",
    "total_cloud_cover",
    "surface_net_solar_radiation",
    "total_precipitation",
]


request = {
    "origin": "ecmwf",

    "year": "2026",
    "month": "08",
    "day": "01",

    "time": "00:00",

    "level_type": "single_level",

    "variable": VARIABLES,

    "forecast_type": "control_forecast",

    "leadtime_hour": [
        "24"
    ],

    "data_format": "grib",
}


# ==================================================
# PRINT REQUEST SUMMARY
# ==================================================

print(
    "\n=== TIGGE VARIABLE AUDIT ==="
)

print(
    "Run time : 2026-08-01 00:00 UTC"
)

print(
    "Lead     : +24h"
)

print(
    "Variables:"
)

for variable in VARIABLES:
    print(
        " -",
        variable,
    )


# ==================================================
# DOWNLOAD
# ==================================================

print(
    "\nCreating ECDS client..."
)

client = cdsapi.Client()


print(
    "\nDownloading..."
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
        2,
    ),
    "MB",
)