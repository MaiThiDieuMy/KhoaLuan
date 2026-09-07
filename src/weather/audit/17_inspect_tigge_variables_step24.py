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
    "tigge_ecmwf_20260801_00Z_variables_step24.grib2"
)

REPORT_FILE = Path(
    "data/weather/reports/"
    "tigge_variables_step24_audit.csv"
)


TARGET_LAT = 13.78
TARGET_LON = 109.22


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


        nearest = codes_grib_find_nearest(
            gid,
            TARGET_LAT,
            TARGET_LON,
        )[0]


        run_time = parse_datetime(
            safe_get(
                gid,
                "dataDate",
            ),
            safe_get(
                gid,
                "dataTime",
            ),
        )


        valid_time = parse_datetime(
            safe_get(
                gid,
                "validityDate",
            ),
            safe_get(
                gid,
                "validityTime",
            ),
        )


        rows.append(
            {
                "short_name":
                    safe_get(
                        gid,
                        "shortName",
                    ),

                "name":
                    safe_get(
                        gid,
                        "name",
                    ),

                "param_id":
                    safe_get(
                        gid,
                        "paramId",
                    ),

                "units":
                    safe_get(
                        gid,
                        "units",
                    ),

                "step_type":
                    safe_get(
                        gid,
                        "stepType",
                    ),

                "step_range":
                    safe_get(
                        gid,
                        "stepRange",
                    ),

                "start_step":
                    safe_get(
                        gid,
                        "startStep",
                    ),

                "end_step":
                    safe_get(
                        gid,
                        "endStep",
                    ),

                "run_time":
                    run_time,

                "valid_time":
                    valid_time,

                "data_type":
                    safe_get(
                        gid,
                        "dataType",
                    ),

                "type_of_level":
                    safe_get(
                        gid,
                        "typeOfLevel",
                    ),

                "level":
                    safe_get(
                        gid,
                        "level",
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

                "value_raw":
                    nearest.value,
            }
        )


        codes_release(gid)


df = pd.DataFrame(rows)


df = df.sort_values(
    "short_name"
).reset_index(drop=True)


REPORT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)


df.to_csv(
    REPORT_FILE,
    index=False,
    encoding="utf-8-sig",
)


# ==================================================
# SUMMARY
# ==================================================

print(
    "\n=== TIGGE VARIABLE SEMANTICS AUDIT ==="
)


print(
    "\nGRIB messages:",
    len(df),
)


print(
    "Unique variables:",
    df["short_name"].nunique(),
)


print(
    "\n=== VARIABLE TABLE ==="
)


print(
    df[
        [
            "short_name",
            "name",
            "param_id",
            "units",
            "step_type",
            "step_range",
            "start_step",
            "end_step",
        ]
    ]
    .to_string(index=False)
)


# ==================================================
# TIME
# ==================================================

print(
    "\n=== TIME ==="
)


print(
    df[
        [
            "short_name",
            "run_time",
            "valid_time",
            "end_step",
        ]
    ]
    .to_string(index=False)
)


# ==================================================
# GRID
# ==================================================

print(
    "\n=== GRID ==="
)


print(
    df[
        [
            "short_name",
            "grid_type",
            "grid_N",
            "grid_lat",
            "grid_lon",
            "distance_km",
        ]
    ]
    .to_string(index=False)
)


# ==================================================
# RAW VALUES AT BINH DINH TEST POINT
# ==================================================

print(
    "\n=== RAW VALUES AT BINH DINH TEST POINT ==="
)


print(
    df[
        [
            "short_name",
            "value_raw",
            "units",
        ]
    ]
    .to_string(index=False)
)


# ==================================================
# EXPECTED VARIABLES
# ==================================================

expected_short_names = {
    "10u",
    "10v",
    "2d",
    "2t",
    "sp",
    "tcc",
    "ssr",
    "tp",
}


actual_short_names = set(
    df["short_name"]
    .tolist()
)


missing = sorted(
    expected_short_names
    -
    actual_short_names
)


unexpected = sorted(
    actual_short_names
    -
    expected_short_names
)


print(
    "\n=== VARIABLE AVAILABILITY ==="
)


print(
    "Expected:",
    sorted(expected_short_names),
)


print(
    "Actual:",
    sorted(actual_short_names),
)


print(
    "Missing:",
    missing,
)


print(
    "Unexpected:",
    unexpected,
)


# ==================================================
# BASIC STRUCTURAL CHECKS
# ==================================================

all_same_run = (
    df["run_time"].nunique()
    == 1
)


all_same_valid = (
    df["valid_time"].nunique()
    == 1
)


all_lead_24 = (
    df["end_step"]
    .eq(24)
    .all()
)


all_same_grid = (
    df[
        [
            "grid_type",
            "grid_N",
        ]
    ]
    .drop_duplicates()
    .shape[0]
    == 1
)


all_same_location = (
    df[
        [
            "grid_lat",
            "grid_lon",
        ]
    ]
    .drop_duplicates()
    .shape[0]
    == 1
)


print(
    "\n=== STRUCTURAL CHECKS ==="
)


print(
    "Same run time:",
    all_same_run,
)


print(
    "Same valid time:",
    all_same_valid,
)


print(
    "All lead +24:",
    all_lead_24,
)


print(
    "Same grid:",
    all_same_grid,
)


print(
    "Same nearest location:",
    all_same_location,
)


# ==================================================
# OVERALL
# ==================================================

overall_pass = (
    len(df) == 8
    and len(missing) == 0
    and len(unexpected) == 0
    and all_same_run
    and all_same_valid
    and all_lead_24
    and all_same_grid
    and all_same_location
)


print(
    "\n=============================="
)


if overall_pass:

    print(
        "OVERALL STRUCTURAL STATUS: PASS"
    )

else:

    print(
        "OVERALL STRUCTURAL STATUS: FAIL"
    )


print(
    "\nSaved:"
)

print(
    REPORT_FILE
)