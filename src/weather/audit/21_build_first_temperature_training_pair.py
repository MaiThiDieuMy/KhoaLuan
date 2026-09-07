from pathlib import Path
from datetime import datetime

import pandas as pd

from eccodes import (
    codes_grib_new_from_file,
    codes_get,
    codes_grib_find_nearest,
    codes_release,
)


# ==================================================
# PATHS
# ==================================================

TIGGE_REPORT = Path(
    "data/weather/reports/"
    "tigge_2t_full_horizon_audit.csv"
)

ERA5_FILE = Path(
    "data/weather/raw/era5/"
    "era5_20260802_00Z_2t_binh_dinh.grib2"
)

OUTPUT_FILE = Path(
    "data/weather/reports/"
    "first_temperature_training_pair.csv"
)


# ==================================================
# CANONICAL LOCATION
# ==================================================

LOCATION_ID = "binh_dinh_audit_01"

TARGET_LAT = 13.78
TARGET_LON = 109.22


TARGET_LEAD = 24


def safe_get(gid, key):
    try:
        return codes_get(gid, key)
    except Exception:
        return None


def parse_datetime(date_value, time_value):

    date_string = str(
        int(date_value)
    )

    time_string = str(
        int(time_value)
    ).zfill(4)

    return datetime.strptime(
        date_string + time_string,
        "%Y%m%d%H%M",
    )


# ==================================================
# 1. READ TIGGE FORECAST
# ==================================================

tigge_df = pd.read_csv(
    TIGGE_REPORT,
    parse_dates=[
        "run_time",
        "valid_time",
    ],
)


tigge_match = tigge_df[
    (tigge_df["lead_hours"] == TARGET_LEAD)
    &
    (tigge_df["short_name"] == "2t")
]


if len(tigge_match) != 1:

    raise RuntimeError(
        "Expected exactly one TIGGE "
        f"2t row at lead {TARGET_LEAD}, "
        f"found {len(tigge_match)}."
    )


tigge = tigge_match.iloc[0]


forecast_temperature_c = float(
    tigge["temperature_c"]
)


# ==================================================
# 2. READ ERA5 VERIFICATION
# ==================================================

with ERA5_FILE.open("rb") as f:

    gid = codes_grib_new_from_file(f)

    if gid is None:
        raise RuntimeError(
            "ERA5 GRIB message not found."
        )


    short_name = safe_get(
        gid,
        "shortName",
    )

    units = safe_get(
        gid,
        "units",
    )


    if short_name != "2t":
        raise RuntimeError(
            f"Expected ERA5 2t, got {short_name}."
        )


    if units != "K":
        raise RuntimeError(
            f"Expected ERA5 temperature in K, "
            f"got {units}."
        )


    era5_valid_time = parse_datetime(
        safe_get(
            gid,
            "validityDate",
        ),
        safe_get(
            gid,
            "validityTime",
        ),
    )


    nearest = codes_grib_find_nearest(
        gid,
        TARGET_LAT,
        TARGET_LON,
    )[0]


    verification_temperature_k = float(
        nearest.value
    )


    verification_temperature_c = (
        verification_temperature_k
        - 273.15
    )


    era5_grid_lat = float(
        nearest.lat
    )

    era5_grid_lon = float(
        nearest.lon
    )

    era5_distance_km = float(
        nearest.distance
    )


    codes_release(gid)


# ==================================================
# 3. TEMPORAL ALIGNMENT CHECK
# ==================================================

tigge_valid_time = pd.Timestamp(
    tigge["valid_time"]
).to_pydatetime()


if tigge_valid_time != era5_valid_time:

    raise RuntimeError(
        "Temporal alignment FAILED.\n"
        f"TIGGE valid_time = {tigge_valid_time}\n"
        f"ERA5 valid_time  = {era5_valid_time}"
    )


# ==================================================
# 4. CALCULATE LABEL
#
# error = verification - forecast
# ==================================================

temperature_error_c = (
    verification_temperature_c
    -
    forecast_temperature_c
)


# ==================================================
# 5. CREATE FIRST TRAINING ROW
# ==================================================

training_row = pd.DataFrame(
    [
        {
            "location_id":
                LOCATION_ID,

            "canonical_lat":
                TARGET_LAT,

            "canonical_lon":
                TARGET_LON,

            "run_time":
                tigge["run_time"],

            "lead_hours":
                int(
                    tigge["lead_hours"]
                ),

            "valid_time":
                tigge["valid_time"],

            # ------------------------------
            # FORECAST / X
            # ------------------------------

            "forecast_temperature_c":
                forecast_temperature_c,

            "tigge_grid_lat":
                float(
                    tigge["grid_lat"]
                ),

            "tigge_grid_lon":
                float(
                    tigge["grid_lon"]
                ),

            "tigge_distance_km":
                float(
                    tigge["distance_km"]
                ),

            # ------------------------------
            # VERIFICATION
            # ------------------------------

            "verification_temperature_c":
                verification_temperature_c,

            "era5_grid_lat":
                era5_grid_lat,

            "era5_grid_lon":
                era5_grid_lon,

            "era5_distance_km":
                era5_distance_km,

            # ------------------------------
            # TARGET / Y
            # ------------------------------

            "temperature_error_c":
                temperature_error_c,

            # ------------------------------
            # AUDIT METADATA
            # ------------------------------

            "forecast_source":
                "ECMWF_TIGGE",

            "verification_source":
                "ERA5",

            "spatial_alignment":
                "nearest_to_canonical_audit_only",
        }
    ]
)


# ==================================================
# 6. SAVE
# ==================================================

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)


training_row.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig",
)


# ==================================================
# 7. RESULT
# ==================================================

print(
    "\n=== FIRST REAL TEMPERATURE TRAINING PAIR ==="
)


print(
    "\nLocation:"
)

print(
    LOCATION_ID,
    TARGET_LAT,
    TARGET_LON,
)


print(
    "\nTime:"
)

print(
    "Run time   :",
    tigge["run_time"],
)

print(
    "Lead hours :",
    int(
        tigge["lead_hours"]
    ),
)

print(
    "Valid time :",
    tigge["valid_time"],
)


print(
    "\nForecast:"
)

print(
    "TIGGE temperature:",
    round(
        forecast_temperature_c,
        6,
    ),
    "°C",
)


print(
    "\nVerification:"
)

print(
    "ERA5 temperature:",
    round(
        verification_temperature_c,
        6,
    ),
    "°C",
)


print(
    "\nTARGET:"
)

print(
    "temperature_error_c = "
    "ERA5 - TIGGE"
)

print(
    round(
        temperature_error_c,
        6,
    ),
    "°C",
)


print(
    "\nSpatial representation:"
)

print(
    "TIGGE:",
    round(
        float(tigge["grid_lat"]),
        6,
    ),
    round(
        float(tigge["grid_lon"]),
        6,
    ),
    "distance",
    round(
        float(tigge["distance_km"]),
        3,
    ),
    "km",
)

print(
    "ERA5 :",
    round(
        era5_grid_lat,
        6,
    ),
    round(
        era5_grid_lon,
        6,
    ),
    "distance",
    round(
        era5_distance_km,
        3,
    ),
    "km",
)


print(
    "\nSaved:"
)

print(
    OUTPUT_FILE
)


print(
    "\nSTATUS: PASS"
)