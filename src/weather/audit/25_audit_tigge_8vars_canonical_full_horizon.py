from pathlib import Path

import cdsapi
import pandas as pd

from eccodes import (
    codes_grib_new_from_file,
    codes_get,
    codes_grib_find_nearest,
    codes_release,
)


# =========================================================
# CONFIG
# =========================================================

TARGET_LAT = 13.78
TARGET_LON = 109.22


OUTPUT_FILE = Path(
    "data/weather/raw/tigge/"
    "tigge_ecmwf_20260801_00Z_8vars_0_360_025deg_binh_dinh.grib2"
)


REPORT_FILE = Path(
    "data/weather/reports/"
    "tigge_8vars_canonical_full_horizon_audit.csv"
)


OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

REPORT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)


LEADS = [
    str(hour)
    for hour in range(
        0,
        361,
        6,
    )
]


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


EXPECTED_SHORT_NAMES = {
    "10u",
    "10v",
    "2d",
    "2t",
    "sp",
    "tcc",
    "ssr",
    "tp",
}


EXPECTED_STEP_TYPES = {
    "10u": "instant",
    "10v": "instant",
    "2d": "instant",
    "2t": "instant",
    "sp": "instant",
    "tcc": "instant",
    "ssr": "accum",
    "tp": "accum",
}


EXPECTED_UNITS = {
    "10u": "m s**-1",
    "10v": "m s**-1",
    "2d": "K",
    "2t": "K",
    "sp": "Pa",
    "tcc": "%",
    "ssr": "J m**-2",
    "tp": "kg m**-2",
}


# =========================================================
# REQUEST
# =========================================================

dataset = "tigge-forecasts"


request = {
    "origin": "ecmwf",

    "year": "2026",
    "month": "08",
    "day": "01",

    "time": "00:00",

    "level_type": "single_level",

    "variable": VARIABLES,

    "forecast_type":
        "control_forecast",

    "leadtime_hour":
        LEADS,

    "grid":
        "0.25/0.25",

    "area": [
        14,
        109,
        13.5,
        109.5,
    ],

    "data_format":
        "grib",
}


# =========================================================
# DOWNLOAD
# =========================================================

print(
    "\n=== TIGGE 8-VARIABLE CANONICAL AUDIT ==="
)

print(
    "Run       : 2026-08-01 00 UTC"
)

print(
    "Variables :",
    len(VARIABLES),
)

print(
    "Leads     :",
    len(LEADS),
)

print(
    "Expected messages:",
    len(VARIABLES) * len(LEADS),
)

print(
    "Grid      : 0.25° × 0.25°"
)

print(
    "Area      : Bình Định audit box"
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


print(
    "\nDOWNLOAD COMPLETE"
)

print(
    "Size bytes:",
    OUTPUT_FILE.stat().st_size,
)

print(
    "Size KB:",
    round(
        OUTPUT_FILE.stat().st_size / 1024,
        3,
    ),
)


# =========================================================
# HELPERS
# =========================================================

def safe_get(gid, key):
    try:
        return codes_get(gid, key)
    except Exception:
        return None


# =========================================================
# READ GRIB
# =========================================================

rows = []


with OUTPUT_FILE.open("rb") as f:

    while True:

        gid = codes_grib_new_from_file(f)

        if gid is None:
            break


        nearest = codes_grib_find_nearest(
            gid,
            TARGET_LAT,
            TARGET_LON,
        )[0]


        rows.append(
            {
                "short_name":
                    safe_get(
                        gid,
                        "shortName",
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

                "lead_hours":
                    int(
                        safe_get(
                            gid,
                            "endStep",
                        )
                    ),

                "grid_type":
                    safe_get(
                        gid,
                        "gridType",
                    ),

                "Ni":
                    safe_get(
                        gid,
                        "Ni",
                    ),

                "Nj":
                    safe_get(
                        gid,
                        "Nj",
                    ),

                "number_of_points":
                    safe_get(
                        gid,
                        "numberOfPoints",
                    ),

                "i_increment":
                    safe_get(
                        gid,
                        "iDirectionIncrementInDegrees",
                    ),

                "j_increment":
                    safe_get(
                        gid,
                        "jDirectionIncrementInDegrees",
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

                "value_raw":
                    float(
                        nearest.value
                    ),
            }
        )


        codes_release(gid)


df = pd.DataFrame(rows)


df = df.sort_values(
    [
        "short_name",
        "lead_hours",
    ]
).reset_index(drop=True)


df.to_csv(
    REPORT_FILE,
    index=False,
    encoding="utf-8-sig",
)


# =========================================================
# BASIC AUDIT
# =========================================================

print(
    "\n========================================"
)

print(
    "BASIC AUDIT"
)

print(
    "========================================"
)


print(
    "Messages:",
    len(df),
)

print(
    "Expected:",
    8 * 61,
)


actual_variables = sorted(
    df[
        "short_name"
    ]
    .unique()
    .tolist()
)


print(
    "\nVariables:",
    actual_variables,
)


missing_variables = sorted(
    EXPECTED_SHORT_NAMES
    -
    set(actual_variables)
)


unexpected_variables = sorted(
    set(actual_variables)
    -
    EXPECTED_SHORT_NAMES
)


print(
    "Missing variables:",
    missing_variables,
)

print(
    "Unexpected variables:",
    unexpected_variables,
)


# =========================================================
# PER-VARIABLE HORIZON AUDIT
# =========================================================

print(
    "\n========================================"
)

print(
    "PER-VARIABLE HORIZON AUDIT"
)

print(
    "========================================"
)


expected_leads = set(
    range(
        0,
        361,
        6,
    )
)


horizon_pass = True


for variable in sorted(
    EXPECTED_SHORT_NAMES
):

    subset = df[
        df["short_name"] == variable
    ].copy()


    actual_leads = set(
        subset[
            "lead_hours"
        ].tolist()
    )


    missing_leads = sorted(
        expected_leads
        -
        actual_leads
    )


    unexpected_leads = sorted(
        actual_leads
        -
        expected_leads
    )


    duplicate_count = int(
        subset[
            "lead_hours"
        ]
        .duplicated()
        .sum()
    )


    print(
        "\nVariable:",
        variable,
    )

    print(
        "Rows:",
        len(subset),
    )

    print(
        "Unique leads:",
        subset[
            "lead_hours"
        ].nunique(),
    )

    print(
        "Min:",
        subset[
            "lead_hours"
        ].min()
        if len(subset)
        else None,
    )

    print(
        "Max:",
        subset[
            "lead_hours"
        ].max()
        if len(subset)
        else None,
    )

    print(
        "Missing leads:",
        missing_leads,
    )

    print(
        "Unexpected leads:",
        unexpected_leads,
    )

    print(
        "Duplicate leads:",
        duplicate_count,
    )


    if (
        len(subset) != 61
        or len(missing_leads) != 0
        or len(unexpected_leads) != 0
        or duplicate_count != 0
    ):

        horizon_pass = False


# =========================================================
# SEMANTICS AUDIT
# =========================================================

print(
    "\n========================================"
)

print(
    "SEMANTICS AUDIT"
)

print(
    "========================================"
)


semantics_pass = True


for variable in sorted(
    EXPECTED_SHORT_NAMES
):

    subset = df[
        df[
            "short_name"
        ] == variable
    ]


    actual_step_types = (
        subset[
            "step_type"
        ]
        .dropna()
        .unique()
        .tolist()
    )


    actual_units = (
        subset[
            "units"
        ]
        .dropna()
        .unique()
        .tolist()
    )


    expected_step_type = (
        EXPECTED_STEP_TYPES[
            variable
        ]
    )


    expected_unit = (
        EXPECTED_UNITS[
            variable
        ]
    )


    step_ok = (
        actual_step_types
        ==
        [
            expected_step_type
        ]
    )


    unit_ok = (
        actual_units
        ==
        [
            expected_unit
        ]
    )


    print(
        variable,
        "| step:",
        actual_step_types,
        "| units:",
        actual_units,
        "|",
        "PASS"
        if step_ok and unit_ok
        else "FAIL",
    )


    if not (
        step_ok
        and unit_ok
    ):

        semantics_pass = False


# =========================================================
# GRID AUDIT
# =========================================================

print(
    "\n========================================"
)

print(
    "GRID AUDIT"
)

print(
    "========================================"
)


grid_types = (
    df[
        "grid_type"
    ]
    .unique()
    .tolist()
)


Ni_values = (
    df["Ni"]
    .unique()
    .tolist()
)


Nj_values = (
    df["Nj"]
    .unique()
    .tolist()
)


point_counts = (
    df[
        "number_of_points"
    ]
    .unique()
    .tolist()
)


i_increments = (
    df[
        "i_increment"
    ]
    .unique()
    .tolist()
)


j_increments = (
    df[
        "j_increment"
    ]
    .unique()
    .tolist()
)


locations = (
    df[
        [
            "grid_lat",
            "grid_lon",
            "distance_km",
        ]
    ]
    .drop_duplicates()
)


print(
    "Grid types:",
    grid_types,
)

print(
    "Ni:",
    Ni_values,
)

print(
    "Nj:",
    Nj_values,
)

print(
    "Points:",
    point_counts,
)

print(
    "Longitude increments:",
    i_increments,
)

print(
    "Latitude increments:",
    j_increments,
)


print(
    "\nNearest location:"
)

print(
    locations.to_string(
        index=False
    )
)


grid_pass = (

    grid_types == [
        "regular_ll"
    ]

    and Ni_values == [
        3
    ]

    and Nj_values == [
        3
    ]

    and point_counts == [
        9
    ]

    and len(
        locations
    ) == 1

    and abs(
        float(
            locations.iloc[0][
                "grid_lat"
            ]
        )
        -
        13.75
    )
    < 1e-6

    and abs(
        float(
            locations.iloc[0][
                "grid_lon"
            ]
        )
        -
        109.25
    )
    < 1e-6
)


# =========================================================
# ACCUMULATION CHECK
# =========================================================

print(
    "\n========================================"
)

print(
    "ACCUMULATION CHECK"
)

print(
    "========================================"
)


for variable in [
    "tp",
    "ssr",
]:

    subset = (
        df[
            df[
                "short_name"
            ] == variable
        ]
        .sort_values(
            "lead_hours"
        )
    )


    print(
        "\n",
        variable,
        sep="",
    )


    print(
        subset[
            [
                "lead_hours",
                "step_range",
                "start_step",
                "value_raw",
            ]
        ]
        .head(10)
        .to_string(
            index=False
        )
    )


# =========================================================
# FINAL STATUS
# =========================================================

message_count_pass = (
    len(df)
    ==
    8 * 61
)


variable_pass = (
    len(
        missing_variables
    ) == 0

    and len(
        unexpected_variables
    ) == 0
)


overall_pass = (

    message_count_pass

    and variable_pass

    and horizon_pass

    and semantics_pass

    and grid_pass
)


print(
    "\n========================================"
)

print(
    "FINAL RESULT"
)

print(
    "========================================"
)


print(
    "Message count:",
    "PASS"
    if message_count_pass
    else "FAIL",
)


print(
    "Variables:",
    "PASS"
    if variable_pass
    else "FAIL",
)


print(
    "61 leads / variable:",
    "PASS"
    if horizon_pass
    else "FAIL",
)


print(
    "Semantics:",
    "PASS"
    if semantics_pass
    else "FAIL",
)


print(
    "Canonical grid:",
    "PASS"
    if grid_pass
    else "FAIL",
)


print(
    "\nOVERALL STATUS:",
    "PASS"
    if overall_pass
    else "FAIL",
)


print(
    "\nAudit saved:"
)

print(
    REPORT_FILE
)