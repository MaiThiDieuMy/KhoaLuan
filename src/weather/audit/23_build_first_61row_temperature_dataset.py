from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

from eccodes import (
    codes_grib_new_from_file,
    codes_get,
    codes_grib_find_nearest,
    codes_release,
)


# =========================================================
# PATHS
# =========================================================

TIGGE_REPORT = Path(
    "data/weather/reports/"
    "tigge_2t_full_horizon_audit.csv"
)

ERA5_FILES = [
    Path(
        "data/weather/raw/era5/"
        "era5_20260801_15_2t_6hourly_binh_dinh.grib2"
    ),
    Path(
        "data/weather/raw/era5/"
        "era5_20260816_00Z_2t_binh_dinh.grib2"
    ),
]

ERA5_AUDIT_OUTPUT = Path(
    "data/weather/reports/"
    "era5_2t_61_valid_times_audit.csv"
)

TRAINING_OUTPUT = Path(
    "data/weather/reports/"
    "temperature_training_dataset_first_run.csv"
)


# =========================================================
# CANONICAL LOCATION
# =========================================================

LOCATION_ID = "binh_dinh_audit_01"

TARGET_LAT = 13.78
TARGET_LON = 109.22


# =========================================================
# HELPERS
# =========================================================

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


# =========================================================
# PART A
# READ TIGGE FORECAST DATA
# =========================================================

print(
    "\n=========================================="
)

print(
    "PART A - READ TIGGE FORECAST"
)

print(
    "=========================================="
)


tigge_df = pd.read_csv(
    TIGGE_REPORT,
    parse_dates=[
        "run_time",
        "valid_time",
    ],
)


tigge_df = tigge_df[
    tigge_df["short_name"] == "2t"
].copy()


tigge_df = tigge_df.sort_values(
    "lead_hours"
).reset_index(drop=True)


print(
    "TIGGE rows:",
    len(tigge_df),
)

print(
    "Unique leads:",
    tigge_df["lead_hours"].nunique(),
)

print(
    "Lead min:",
    tigge_df["lead_hours"].min(),
)

print(
    "Lead max:",
    tigge_df["lead_hours"].max(),
)


if len(tigge_df) != 61:
    raise RuntimeError(
        f"Expected 61 TIGGE rows, "
        f"found {len(tigge_df)}."
    )


# =========================================================
# PART B
# READ ALL ERA5 GRIB MESSAGES
# =========================================================

print(
    "\n=========================================="
)

print(
    "PART B - READ ERA5 VERIFICATION"
)

print(
    "=========================================="
)


era5_rows = []


for grib_file in ERA5_FILES:

    print(
        "\nReading:",
        grib_file,
    )

    if not grib_file.exists():

        raise FileNotFoundError(
            grib_file
        )


    with grib_file.open("rb") as f:

        while True:

            gid = codes_grib_new_from_file(f)

            if gid is None:
                break


            short_name = safe_get(
                gid,
                "shortName",
            )

            units = safe_get(
                gid,
                "units",
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


            nearest = codes_grib_find_nearest(
                gid,
                TARGET_LAT,
                TARGET_LON,
            )[0]


            temperature_k = float(
                nearest.value
            )


            temperature_c = (
                temperature_k
                - 273.15
            )


            era5_rows.append(
                {
                    "valid_time":
                        valid_time,

                    "short_name":
                        short_name,

                    "units":
                        units,

                    "step_type":
                        safe_get(
                            gid,
                            "stepType",
                        ),

                    "grid_type":
                        safe_get(
                            gid,
                            "gridType",
                        ),

                    "grid_lat":
                        float(
                            nearest.lat
                        ),

                    "grid_lon":
                        float(
                            nearest.lon
                        ),

                    "distance_km":
                        float(
                            nearest.distance
                        ),

                    "verification_temperature_c":
                        temperature_c,

                    "source_file":
                        grib_file.name,
                }
            )


            codes_release(gid)


era5_df = pd.DataFrame(
    era5_rows
)


era5_df = era5_df.sort_values(
    "valid_time"
).reset_index(drop=True)


print(
    "\nERA5 messages:",
    len(era5_df),
)

print(
    "Unique valid times:",
    era5_df["valid_time"].nunique(),
)

print(
    "First valid time:",
    era5_df["valid_time"].min(),
)

print(
    "Last valid time:",
    era5_df["valid_time"].max(),
)


# =========================================================
# PART C
# ERA5 STRUCTURAL AUDIT
# =========================================================

print(
    "\n=========================================="
)

print(
    "PART C - ERA5 STRUCTURAL AUDIT"
)

print(
    "=========================================="
)


duplicate_valid_times = (
    era5_df["valid_time"]
    .duplicated()
    .sum()
)


expected_valid_times = set(
    pd.to_datetime(
        tigge_df["valid_time"]
    )
)


actual_valid_times = set(
    pd.to_datetime(
        era5_df["valid_time"]
    )
)


missing_valid_times = sorted(
    expected_valid_times
    -
    actual_valid_times
)


unexpected_valid_times = sorted(
    actual_valid_times
    -
    expected_valid_times
)


variables = sorted(
    era5_df["short_name"]
    .dropna()
    .unique()
    .tolist()
)


units = sorted(
    era5_df["units"]
    .dropna()
    .unique()
    .tolist()
)


grid_types = sorted(
    era5_df["grid_type"]
    .dropna()
    .unique()
    .tolist()
)


unique_locations = (
    era5_df[
        [
            "grid_lat",
            "grid_lon",
        ]
    ]
    .drop_duplicates()
)


print(
    "Message count:",
    len(era5_df),
)

print(
    "Expected:",
    61,
)

print(
    "Unique timestamps:",
    era5_df["valid_time"].nunique(),
)

print(
    "Duplicate timestamps:",
    duplicate_valid_times,
)

print(
    "Missing timestamps:",
    len(missing_valid_times),
)

print(
    "Unexpected timestamps:",
    len(unexpected_valid_times),
)

print(
    "Variables:",
    variables,
)

print(
    "Units:",
    units,
)

print(
    "Grid types:",
    grid_types,
)

print(
    "Unique nearest locations:",
    len(unique_locations),
)


if missing_valid_times:

    print(
        "\nMissing:"
    )

    for value in missing_valid_times:
        print(
            " -",
            value,
        )


if unexpected_valid_times:

    print(
        "\nUnexpected:"
    )

    for value in unexpected_valid_times:
        print(
            " -",
            value,
        )


# =========================================================
# ERA5 QUALITY GATE
# =========================================================

era5_pass = (
    len(era5_df) == 61

    and era5_df[
        "valid_time"
    ].nunique() == 61

    and duplicate_valid_times == 0

    and len(
        missing_valid_times
    ) == 0

    and len(
        unexpected_valid_times
    ) == 0

    and era5_df[
        "short_name"
    ].eq("2t").all()

    and era5_df[
        "units"
    ].eq("K").all()

    and len(
        unique_locations
    ) == 1
)


print(
    "\nERA5 AUDIT STATUS:",
    "PASS"
    if era5_pass
    else "FAIL",
)


# =========================================================
# SAVE ERA5 AUDIT
# =========================================================

ERA5_AUDIT_OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)


era5_df.to_csv(
    ERA5_AUDIT_OUTPUT,
    index=False,
    encoding="utf-8-sig",
)


if not era5_pass:

    raise RuntimeError(
        "ERA5 audit failed. "
        "Training dataset will NOT be created."
    )


# =========================================================
# PART D
# JOIN TIGGE + ERA5
# =========================================================

print(
    "\n=========================================="
)

print(
    "PART D - BUILD TRAINING DATASET"
)

print(
    "=========================================="
)


training_df = tigge_df.merge(

    era5_df[
        [
            "valid_time",
            "verification_temperature_c",
            "grid_lat",
            "grid_lon",
            "distance_km",
        ]
    ],

    on="valid_time",

    how="inner",

    validate="one_to_one",

    suffixes=(
        "_tigge",
        "_era5",
    ),
)


# =========================================================
# CREATE ML TARGET
# =========================================================

training_df[
    "temperature_error_c"
] = (

    training_df[
        "verification_temperature_c"
    ]

    -

    training_df[
        "temperature_c"
    ]
)


# =========================================================
# CANONICAL COLUMN NAMES
# =========================================================

training_df = training_df.rename(
    columns={
        "temperature_c":
            "forecast_temperature_c",

        "grid_lat_tigge":
            "tigge_grid_lat",

        "grid_lon_tigge":
            "tigge_grid_lon",

        "distance_km_tigge":
            "tigge_distance_km",

        "grid_lat_era5":
            "era5_grid_lat",

        "grid_lon_era5":
            "era5_grid_lon",

        "distance_km_era5":
            "era5_distance_km",
    }
)


# =========================================================
# ADD DATA-LINEAGE METADATA
# =========================================================

training_df.insert(
    0,
    "location_id",
    LOCATION_ID,
)


training_df.insert(
    1,
    "canonical_lat",
    TARGET_LAT,
)


training_df.insert(
    2,
    "canonical_lon",
    TARGET_LON,
)


training_df[
    "forecast_source"
] = "ECMWF_TIGGE"


training_df[
    "verification_source"
] = "ERA5"


training_df[
    "spatial_alignment"
] = (
    "nearest_to_canonical_audit_only"
)


# =========================================================
# SELECT FINAL TRAINING COLUMNS
# =========================================================

final_columns = [

    "location_id",

    "canonical_lat",
    "canonical_lon",

    "run_time",
    "lead_hours",
    "valid_time",

    "forecast_temperature_c",

    "verification_temperature_c",

    "temperature_error_c",

    "tigge_grid_lat",
    "tigge_grid_lon",
    "tigge_distance_km",

    "era5_grid_lat",
    "era5_grid_lon",
    "era5_distance_km",

    "forecast_source",
    "verification_source",

    "spatial_alignment",
]


training_df = training_df[
    final_columns
].copy()


training_df = training_df.sort_values(
    "lead_hours"
).reset_index(drop=True)


# =========================================================
# TRAINING DATA QUALITY GATE
# =========================================================

training_pass = (

    len(
        training_df
    ) == 61

    and training_df[
        "lead_hours"
    ].nunique() == 61

    and training_df[
        "valid_time"
    ].nunique() == 61

    and training_df[
        "temperature_error_c"
    ].notna().all()
)


print(
    "Training rows:",
    len(training_df),
)

print(
    "Unique leads:",
    training_df[
        "lead_hours"
    ].nunique(),
)

print(
    "Missing labels:",
    training_df[
        "temperature_error_c"
    ].isna().sum(),
)


if not training_pass:

    raise RuntimeError(
        "Training dataset quality gate FAILED."
    )


# =========================================================
# SAVE TRAINING DATASET
# =========================================================

TRAINING_OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)


training_df.to_csv(
    TRAINING_OUTPUT,
    index=False,
    encoding="utf-8-sig",
)


# =========================================================
# PART E
# WITHIN-RUN DIAGNOSTICS
# =========================================================

errors = training_df[
    "temperature_error_c"
].to_numpy()


mean_error = float(
    np.mean(
        errors
    )
)


mae = float(
    np.mean(
        np.abs(
            errors
        )
    )
)


rmse = float(
    np.sqrt(
        np.mean(
            errors ** 2
        )
    )
)


print(
    "\n=========================================="
)

print(
    "PART E - ONE-RUN DIAGNOSTICS"
)

print(
    "=========================================="
)


print(
    "Mean error / bias:",
    round(
        mean_error,
        4,
    ),
    "°C",
)


print(
    "MAE:",
    round(
        mae,
        4,
    ),
    "°C",
)


print(
    "RMSE:",
    round(
        rmse,
        4,
    ),
    "°C",
)


print(
    "\nError range:"
)

print(
    round(
        training_df[
            "temperature_error_c"
        ].min(),
        4,
    ),
    "→",
    round(
        training_df[
            "temperature_error_c"
        ].max(),
        4,
    ),
    "°C",
)


# =========================================================
# DISPLAY FIRST / LAST ROWS
# =========================================================

display_columns = [
    "lead_hours",
    "valid_time",
    "forecast_temperature_c",
    "verification_temperature_c",
    "temperature_error_c",
]


print(
    "\n=== FIRST 10 TRAINING ROWS ==="
)


print(
    training_df[
        display_columns
    ]
    .head(10)
    .round(4)
    .to_string(
        index=False
    )
)


print(
    "\n=== LAST 10 TRAINING ROWS ==="
)


print(
    training_df[
        display_columns
    ]
    .tail(10)
    .round(4)
    .to_string(
        index=False
    )
)


print(
    "\n=========================================="
)

print(
    "FINAL STATUS: PASS"
)

print(
    "=========================================="
)


print(
    "\nERA5 audit saved:"
)

print(
    ERA5_AUDIT_OUTPUT
)


print(
    "\nTraining dataset saved:"
)

print(
    TRAINING_OUTPUT
)