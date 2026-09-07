from pathlib import Path
from datetime import datetime

import pandas as pd

from eccodes import (
    codes_grib_new_from_file,
    codes_get,
    codes_grib_find_nearest,
    codes_release,
)


GRIB_FILE = Path(
    "data/weather/raw/tigge/"
    "tigge_ecmwf_20260801_00Z_2t_0_360.grib2"
)

REPORT_FILE = Path(
    "data/weather/reports/"
    "tigge_2t_full_horizon_audit.csv"
)


TARGET_LAT = 13.78
TARGET_LON = 109.22


EXPECTED_LEADS = list(
    range(
        0,
        361,
        6,
    )
)


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


rows = []


with GRIB_FILE.open("rb") as f:

    while True:

        gid = codes_grib_new_from_file(f)

        if gid is None:
            break


        data_date = safe_get(
            gid,
            "dataDate",
        )

        data_time = safe_get(
            gid,
            "dataTime",
        )

        validity_date = safe_get(
            gid,
            "validityDate",
        )

        validity_time = safe_get(
            gid,
            "validityTime",
        )


        run_time = parse_datetime(
            data_date,
            data_time,
        )

        valid_time = parse_datetime(
            validity_date,
            validity_time,
        )


        lead_hours = safe_get(
            gid,
            "endStep",
        )


        nearest = codes_grib_find_nearest(
            gid,
            TARGET_LAT,
            TARGET_LON,
        )[0]


        raw_value = nearest.value


        rows.append(
            {
                "run_time": run_time,

                "valid_time": valid_time,

                "lead_hours": lead_hours,

                "short_name":
                    safe_get(
                        gid,
                        "shortName",
                    ),

                "step_type":
                    safe_get(
                        gid,
                        "stepType",
                    ),

                "units":
                    safe_get(
                        gid,
                        "units",
                    ),

                "grid_type":
                    safe_get(
                        gid,
                        "gridType",
                    ),

                "grid_N":
                    safe_get(
                        gid,
                        "N",
                    ),

                "grid_lat":
                    nearest.lat,

                "grid_lon":
                    nearest.lon,

                "distance_km":
                    nearest.distance,

                "temperature_k":
                    raw_value,

                "temperature_c":
                    raw_value - 273.15,
            }
        )


        codes_release(gid)


df = pd.DataFrame(rows)


df = df.sort_values(
    "lead_hours"
).reset_index(drop=True)


# ==========================================
# EXPECTED VS ACTUAL LEADS
# ==========================================

actual_leads = (
    df["lead_hours"]
    .astype(int)
    .tolist()
)


missing_leads = sorted(
    set(EXPECTED_LEADS)
    -
    set(actual_leads)
)


unexpected_leads = sorted(
    set(actual_leads)
    -
    set(EXPECTED_LEADS)
)


duplicate_leads = (
    df["lead_hours"]
    .duplicated()
    .sum()
)


# ==========================================
# VALID TIME CHECK
# ==========================================

expected_valid_time = (
    df["run_time"]
    +
    pd.to_timedelta(
        df["lead_hours"],
        unit="h",
    )
)


valid_time_ok = (
    expected_valid_time
    ==
    df["valid_time"]
).all()


# ==========================================
# GRID CONSISTENCY
# ==========================================

unique_grid_types = (
    df["grid_type"]
    .dropna()
    .unique()
    .tolist()
)


unique_grid_N = (
    df["grid_N"]
    .dropna()
    .unique()
    .tolist()
)


unique_locations = (
    df[
        [
            "grid_lat",
            "grid_lon",
        ]
    ]
    .drop_duplicates()
)


# ==========================================
# SAVE
# ==========================================

REPORT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)


df.to_csv(
    REPORT_FILE,
    index=False,
    encoding="utf-8-sig",
)


# ==========================================
# PRINT RESULT
# ==========================================

print(
    "\n=== TIGGE 2T FULL HORIZON AUDIT ==="
)


print(
    "\nGRIB messages:",
    len(df),
)


print(
    "Expected messages:",
    len(EXPECTED_LEADS),
)


print(
    "\nLead min:",
    df["lead_hours"].min(),
)


print(
    "Lead max:",
    df["lead_hours"].max(),
)


print(
    "Unique leads:",
    df["lead_hours"].nunique(),
)


print(
    "\nMissing leads:",
    missing_leads,
)


print(
    "Unexpected leads:",
    unexpected_leads,
)


print(
    "Duplicate leads:",
    duplicate_leads,
)


print(
    "\nValid time consistency:",
    valid_time_ok,
)


print(
    "\nVariables:",
    df["short_name"]
    .unique()
    .tolist(),
)


print(
    "Step types:",
    df["step_type"]
    .unique()
    .tolist(),
)


print(
    "\nGrid types:",
    unique_grid_types,
)


print(
    "Grid N:",
    unique_grid_N,
)


print(
    "Unique nearest locations:",
    len(unique_locations),
)


print(
    "\nNearest location(s):"
)

print(
    unique_locations
    .to_string(index=False)
)


print(
    "\nTemperature range °C:"
)

print(
    round(
        df["temperature_c"].min(),
        2,
    ),
    "→",
    round(
        df["temperature_c"].max(),
        2,
    ),
)


print(
    "\n=== FIRST 10 LEADS ==="
)

print(
    df[
        [
            "run_time",
            "valid_time",
            "lead_hours",
            "temperature_c",
            "grid_lat",
            "grid_lon",
            "distance_km",
        ]
    ]
    .head(10)
    .round(3)
    .to_string(index=False)
)


print(
    "\n=== LAST 10 LEADS ==="
)

print(
    df[
        [
            "run_time",
            "valid_time",
            "lead_hours",
            "temperature_c",
            "grid_lat",
            "grid_lon",
            "distance_km",
        ]
    ]
    .tail(10)
    .round(3)
    .to_string(index=False)
)


print(
    "\nSaved:"
)

print(
    REPORT_FILE
)


# ==========================================
# OVERALL STATUS
# ==========================================

overall_pass = (
    len(df) == 61
    and df["lead_hours"].nunique() == 61
    and len(missing_leads) == 0
    and len(unexpected_leads) == 0
    and duplicate_leads == 0
    and valid_time_ok
    and df["short_name"].eq("2t").all()
)


print(
    "\n=============================="
)


if overall_pass:

    print(
        "OVERALL STATUS: PASS"
    )

else:

    print(
        "OVERALL STATUS: FAIL"
    )