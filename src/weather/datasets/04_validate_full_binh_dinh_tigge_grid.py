from pathlib import Path

import numpy as np
import pandas as pd
import cdsapi

from eccodes import (
    codes_grib_new_from_file,
    codes_get,
    codes_grib_find_nearest,
    codes_release,
)


# =========================================================
# CONFIG
# =========================================================

RUN_TIME = pd.Timestamp(
    "2026-08-01 00:00:00"
)


# =========================================================
# GEOGRAPHY REGISTRY
# =========================================================

LOCATION_REGISTRY = Path(
    "data/weather/geography/"
    "binh_dinh_location_registry.csv"
)


# =========================================================
# OLD SMALL-AREA FILE
# =========================================================

OLD_FILE = Path(
    "data/weather/raw/tigge/bulk/"
    "tigge_ecmwf_20260801_00Z_8vars_0_360_025deg_binh_dinh.grib2"
)


# =========================================================
# NEW FULL BINH DINH FILE
# =========================================================

OUTPUT_DIR = Path(
    "data/weather/raw/tigge/geography_test"
)


NEW_FILE = (
    OUTPUT_DIR
    /
    "tigge_ecmwf_20260801_00Z_"
    "8vars_0_360_025deg_full_binh_dinh.grib2"
)


REPORT_FILE = Path(
    "data/weather/reports/"
    "full_binh_dinh_tigge_grid_validation.csv"
)


COMPARISON_FILE = Path(
    "data/weather/reports/"
    "full_binh_dinh_old_new_overlap_comparison.csv"
)


OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


REPORT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)


# =========================================================
# TIGGE CONFIG
# =========================================================

DATASET = "tigge-forecasts"


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


LEADS = [
    str(hour)
    for hour in range(
        0,
        361,
        6,
    )
]


EXPECTED_SHORT_NAMES = {
    "10u",
    "10v",
    "2d",
    "2t",
    "sp",
    "ssr",
    "tcc",
    "tp",
}


# =========================================================
# FULL OLD BINH DINH RETRIEVAL AREA
#
# North / West / South / East
# =========================================================

AREA = [
    14.75,
    108.75,
    13.50,
    109.25,
]


GRID = "0.25/0.25"


# =========================================================
# PHYSICAL / PACKING TOLERANCES
#
# Hai retrieval có area khác nhau.
#
# Sau regridding + GRIB packing,
# decoded values có thể lệch cực nhỏ.
#
# Đây KHÔNG phải ngưỡng nông nghiệp.
#
# Đây chỉ là tolerance kỹ thuật để xác nhận
# hai retrieval biểu diễn cùng physical field.
# =========================================================

ABSOLUTE_TOLERANCES = {

    # m/s
    "10u": 0.001,
    "10v": 0.001,

    # Kelvin
    "2d": 0.001,
    "2t": 0.001,

    # Pascal
    "sp": 0.2,

    # cumulative J/m²
    # 2048 J/m² = 0.002048 MJ/m²
    "ssr": 2048.0,

    # percentage point
    "tcc": 0.005,

    # kg/m² ≈ mm
    "tp": 0.0001,
}


# =========================================================
# HELPERS
# =========================================================

def safe_get(gid, key):

    try:

        return codes_get(
            gid,
            key,
        )

    except Exception:

        return None


# =========================================================
# READ GEOGRAPHY REGISTRY
# =========================================================

print(
    "\n=========================================="
)

print(
    "PART A - BINH DINH GEOGRAPHY REGISTRY"
)

print(
    "=========================================="
)


if not LOCATION_REGISTRY.exists():

    raise FileNotFoundError(
        LOCATION_REGISTRY
    )


locations = pd.read_csv(
    LOCATION_REGISTRY
)


print(
    "Selected Bình Định cells:",
    len(locations),
)


print(
    "Center-inside cells:",
    int(
        locations[
            "center_inside_province"
        ].sum()
    ),
)


print(
    "Covered by old audit box:",
    int(
        locations[
            "covered_by_current_audit_box"
        ].sum()
    ),
)


print(
    "Missing from old audit box:",
    int(
        (
            ~locations[
                "covered_by_current_audit_box"
            ]
        ).sum()
    ),
)


if len(locations) != 16:

    raise RuntimeError(
        "Expected 16 selected Bình Định cells."
    )


# =========================================================
# DOWNLOAD FULL BINH DINH TEST RUN
#
# Nếu file đã tồn tại thì KHÔNG tải lại.
# =========================================================

request = {

    "origin":
        "ecmwf",

    "year":
        RUN_TIME.strftime(
            "%Y"
        ),

    "month":
        RUN_TIME.strftime(
            "%m"
        ),

    "day":
        RUN_TIME.strftime(
            "%d"
        ),

    "time":
        "00:00",

    "level_type":
        "single_level",

    "variable":
        VARIABLES,

    "forecast_type":
        "control_forecast",

    "leadtime_hour":
        LEADS,

    "grid":
        GRID,

    "area":
        AREA,

    "data_format":
        "grib",
}


print(
    "\n=========================================="
)

print(
    "PART B - FULL BINH DINH TIGGE FILE"
)

print(
    "=========================================="
)


print(
    "Run:",
    RUN_TIME,
)


print(
    "Area:",
    AREA,
)


print(
    "Grid:",
    GRID,
)


if NEW_FILE.exists():

    print(
        "\nExisting full-area test file found."
    )

    print(
        "NO DOWNLOAD NEEDED."
    )

else:

    print(
        "\nFull-area file does not exist."
    )

    print(
        "Downloading..."
    )


    client = cdsapi.Client()


    client.retrieve(
        DATASET,
        request,
        str(
            NEW_FILE
        ),
    )


print(
    "\nFile:"
)

print(
    NEW_FILE
)


print(
    "File size bytes:",
    NEW_FILE.stat().st_size,
)


print(
    "File size KB:",
    round(
        NEW_FILE.stat().st_size
        /
        1024,
        3,
    ),
)


# =========================================================
# PART C
# RECTANGULAR GRID AUDIT
# =========================================================

print(
    "\n=========================================="
)

print(
    "PART C - RECTANGULAR GRID AUDIT"
)

print(
    "=========================================="
)


message_rows = []


with NEW_FILE.open(
    "rb"
) as f:

    while True:

        gid = codes_grib_new_from_file(
            f
        )


        if gid is None:

            break


        message_rows.append(
            {
                "short_name":
                    safe_get(
                        gid,
                        "shortName",
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
                    int(
                        safe_get(
                            gid,
                            "Ni",
                        )
                    ),

                "Nj":
                    int(
                        safe_get(
                            gid,
                            "Nj",
                        )
                    ),

                "number_of_points":
                    int(
                        safe_get(
                            gid,
                            "numberOfPoints",
                        )
                    ),

                "i_increment":
                    float(
                        safe_get(
                            gid,
                            "iDirectionIncrementInDegrees",
                        )
                    ),

                "j_increment":
                    float(
                        safe_get(
                            gid,
                            "jDirectionIncrementInDegrees",
                        )
                    ),
            }
        )


        codes_release(
            gid
        )


messages = pd.DataFrame(
    message_rows
)


print(
    "Messages:",
    len(messages),
)


print(
    "Expected messages:",
    8 * 61,
)


print(
    "Variables:",
    sorted(
        messages[
            "short_name"
        ]
        .unique()
        .tolist()
    ),
)


print(
    "Ni:",
    sorted(
        messages[
            "Ni"
        ]
        .unique()
        .tolist()
    ),
)


print(
    "Nj:",
    sorted(
        messages[
            "Nj"
        ]
        .unique()
        .tolist()
    ),
)


print(
    "Points/message:",
    sorted(
        messages[
            "number_of_points"
        ]
        .unique()
        .tolist()
    ),
)


print(
    "Grid types:",
    messages[
        "grid_type"
    ]
    .unique()
    .tolist(),
)


# =========================================================
# RECTANGULAR GRID QUALITY GATE
#
# Latitudes:
# 14.75
# 14.50
# 14.25
# 14.00
# 13.75
# 13.50
#
# = 6
#
# Longitudes:
# 108.75
# 109.00
# 109.25
#
# = 3
#
# 6 × 3 = 18 grid points/message
# =========================================================

grid_pass = (

    len(messages)
    ==
    488

    and

    set(
        messages[
            "short_name"
        ]
    )
    ==
    EXPECTED_SHORT_NAMES

    and

    messages[
        "grid_type"
    ]
    .eq(
        "regular_ll"
    )
    .all()

    and

    messages[
        "Ni"
    ]
    .eq(
        3
    )
    .all()

    and

    messages[
        "Nj"
    ]
    .eq(
        6
    )
    .all()

    and

    messages[
        "number_of_points"
    ]
    .eq(
        18
    )
    .all()

    and

    np.isclose(
        messages[
            "i_increment"
        ],
        0.25,
    )
    .all()

    and

    np.isclose(
        messages[
            "j_increment"
        ],
        0.25,
    )
    .all()
)


print(
    "\nFull rectangular grid:",
    "PASS"
    if grid_pass
    else "FAIL",
)


if not grid_pass:

    raise RuntimeError(
        "Full Bình Định TIGGE grid audit failed."
    )


# =========================================================
# PART D
# EXTRACT 16 BINH DINH LOCATIONS
# =========================================================

print(
    "\n=========================================="
)

print(
    "PART D - EXTRACT 16 BINH DINH LOCATIONS"
)

print(
    "=========================================="
)


new_rows = []


with NEW_FILE.open(
    "rb"
) as f:

    while True:

        gid = codes_grib_new_from_file(
            f
        )


        if gid is None:

            break


        short_name = safe_get(
            gid,
            "shortName",
        )


        lead_hours = int(
            safe_get(
                gid,
                "endStep",
            )
        )


        for _, location in (
            locations.iterrows()
        ):

            target_lat = float(
                location[
                    "grid_lat"
                ]
            )


            target_lon = float(
                location[
                    "grid_lon"
                ]
            )


            nearest = (
                codes_grib_find_nearest(
                    gid,
                    target_lat,
                    target_lon,
                )[0]
            )


            coordinate_match = (

                abs(
                    float(
                        nearest.lat
                    )
                    -
                    target_lat
                )
                <
                1e-8

                and

                abs(
                    float(
                        nearest.lon
                    )
                    -
                    target_lon
                )
                <
                1e-8
            )


            new_rows.append(
                {
                    "location_id":
                        location[
                            "location_id"
                        ],

                    "registry_lat":
                        target_lat,

                    "registry_lon":
                        target_lon,

                    "center_inside_province":
                        bool(
                            location[
                                "center_inside_province"
                            ]
                        ),

                    "covered_by_current_audit_box":
                        bool(
                            location[
                                "covered_by_current_audit_box"
                            ]
                        ),

                    "short_name":
                        short_name,

                    "lead_hours":
                        lead_hours,

                    "actual_grid_lat":
                        float(
                            nearest.lat
                        ),

                    "actual_grid_lon":
                        float(
                            nearest.lon
                        ),

                    "distance_km":
                        float(
                            nearest.distance
                        ),

                    "coordinate_match":
                        bool(
                            coordinate_match
                        ),

                    "value_new":
                        float(
                            nearest.value
                        ),
                }
            )


        codes_release(
            gid
        )


new_df = pd.DataFrame(
    new_rows
)


expected_location_rows = (

    16
    *
    8
    *
    61
)


print(
    "Extracted rows:",
    len(
        new_df
    ),
)


print(
    "Expected:",
    expected_location_rows,
)


print(
    "Locations:",
    new_df[
        "location_id"
    ].nunique(),
)


print(
    "Coordinate matches:",
    int(
        new_df[
            "coordinate_match"
        ].sum()
    ),
    "/",
    len(
        new_df
    ),
)


location_extraction_pass = (

    len(
        new_df
    )
    ==
    expected_location_rows

    and

    new_df[
        "location_id"
    ].nunique()
    ==
    16

    and

    new_df[
        "coordinate_match"
    ].all()
)


print(
    "\n16-cell extraction:",
    "PASS"
    if location_extraction_pass
    else "FAIL",
)


if not location_extraction_pass:

    raise RuntimeError(
        "Bình Định location extraction failed."
    )


# =========================================================
# PART E
# OLD VS NEW OVERLAP
#
# IMPORTANT:
#
# Không yêu cầu bit-for-bit equality.
#
# Hai request có spatial area khác nhau.
#
# Sau interpolation/regridding/GRIB packing,
# decoded floating-point values có thể lệch rất nhỏ.
#
# Ta kiểm bằng tolerance có ý nghĩa theo từng variable.
# =========================================================

print(
    "\n=========================================="
)

print(
    "PART E - OLD VS NEW OVERLAP"
)

print(
    "=========================================="
)


if not OLD_FILE.exists():

    raise FileNotFoundError(
        OLD_FILE
    )


overlap_locations = locations[
    locations[
        "covered_by_current_audit_box"
    ]
].copy()


print(
    "Overlap locations:",
    len(
        overlap_locations
    ),
)


old_rows = []


with OLD_FILE.open(
    "rb"
) as f:

    while True:

        gid = codes_grib_new_from_file(
            f
        )


        if gid is None:

            break


        short_name = safe_get(
            gid,
            "shortName",
        )


        lead_hours = int(
            safe_get(
                gid,
                "endStep",
            )
        )


        for _, location in (
            overlap_locations.iterrows()
        ):

            target_lat = float(
                location[
                    "grid_lat"
                ]
            )


            target_lon = float(
                location[
                    "grid_lon"
                ]
            )


            nearest = (
                codes_grib_find_nearest(
                    gid,
                    target_lat,
                    target_lon,
                )[0]
            )


            old_rows.append(
                {
                    "location_id":
                        location[
                            "location_id"
                        ],

                    "short_name":
                        short_name,

                    "lead_hours":
                        lead_hours,

                    "value_old":
                        float(
                            nearest.value
                        ),
                }
            )


        codes_release(
            gid
        )


old_df = pd.DataFrame(
    old_rows
)


new_overlap = new_df[
    new_df[
        "covered_by_current_audit_box"
    ]
][
    [
        "location_id",
        "short_name",
        "lead_hours",
        "value_new",
    ]
].copy()


comparison = old_df.merge(

    new_overlap,

    on=[
        "location_id",
        "short_name",
        "lead_hours",
    ],

    how="inner",

    validate="one_to_one",
)


comparison[
    "absolute_difference"
] = (

    comparison[
        "value_new"
    ]

    -

    comparison[
        "value_old"
    ]

).abs()


# =========================================================
# VARIABLE-SPECIFIC TOLERANCE
# =========================================================

comparison[
    "tolerance"
] = (

    comparison[
        "short_name"
    ]
    .map(
        ABSOLUTE_TOLERANCES
    )
)


if comparison[
    "tolerance"
].isna().any():

    missing_tolerance_vars = (

        comparison.loc[
            comparison[
                "tolerance"
            ].isna(),
            "short_name",
        ]
        .unique()
        .tolist()
    )


    raise RuntimeError(
        "Missing tolerance for variables: "
        f"{missing_tolerance_vars}"
    )


comparison[
    "within_tolerance"
] = (

    comparison[
        "absolute_difference"
    ]

    <=

    comparison[
        "tolerance"
    ]
)


print(
    "Compared values:",
    len(
        comparison
    ),
)


expected_comparisons = (

    5
    *
    8
    *
    61
)


print(
    "Expected comparisons:",
    expected_comparisons,
)


print(
    "Within physical/packing tolerance:",
    int(
        comparison[
            "within_tolerance"
        ].sum()
    ),
)


print(
    "Outside tolerance:",
    int(
        (
            ~comparison[
                "within_tolerance"
            ]
        ).sum()
    ),
)


# =========================================================
# PER-VARIABLE SUMMARY
# =========================================================

comparison_summary = (

    comparison
    .groupby(
        "short_name"
    )
    .agg(

        rows=(
            "within_tolerance",
            "count",
        ),

        within_tolerance=(
            "within_tolerance",
            "sum",
        ),

        max_absolute_difference=(
            "absolute_difference",
            "max",
        ),

        tolerance=(
            "tolerance",
            "first",
        ),

    )
    .reset_index()
)


comparison_summary[
    "status"
] = np.where(

    comparison_summary[
        "max_absolute_difference"
    ]

    <=

    comparison_summary[
        "tolerance"
    ],

    "PASS",

    "FAIL",
)


print(
    "\nPer-variable tolerance comparison:"
)


print(
    comparison_summary.to_string(
        index=False
    )
)


# =========================================================
# ADD NORMALIZED DIFFERENCE FOR INTERPRETABILITY
#
# Đây chỉ là reporting, không dùng làm gate.
# =========================================================

print(
    "\n=========================================="
)

print(
    "INTERPRET MAXIMUM DIFFERENCES"
)

print(
    "=========================================="
)


max_diff_by_var = dict(

    zip(
        comparison_summary[
            "short_name"
        ],

        comparison_summary[
            "max_absolute_difference"
        ],
    )
)


print(
    "2t temperature:",
    max_diff_by_var[
        "2t"
    ],
    "K ≈ same difference in °C",
)


print(
    "2d dewpoint:",
    max_diff_by_var[
        "2d"
    ],
    "K",
)


print(
    "10u wind:",
    max_diff_by_var[
        "10u"
    ],
    "m/s",
)


print(
    "10v wind:",
    max_diff_by_var[
        "10v"
    ],
    "m/s",
)


print(
    "surface pressure:",
    max_diff_by_var[
        "sp"
    ],
    "Pa =",
    max_diff_by_var[
        "sp"
    ]
    /
    100.0,
    "hPa",
)


print(
    "cloud cover:",
    max_diff_by_var[
        "tcc"
    ],
    "percentage point",
)


print(
    "precipitation:",
    max_diff_by_var[
        "tp"
    ],
    "kg/m² ≈ mm",
)


print(
    "solar radiation:",
    max_diff_by_var[
        "ssr"
    ],
    "J/m² =",
    max_diff_by_var[
        "ssr"
    ]
    /
    1_000_000.0,
    "MJ/m²",
)


overlap_pass = (

    len(
        comparison
    )
    ==
    expected_comparisons

    and

    comparison[
        "within_tolerance"
    ].all()
)


print(
    "\nOld/new overlap comparison:",
    "PASS"
    if overlap_pass
    else "FAIL",
)


# =========================================================
# SAVE REPORTS
# =========================================================

new_df.to_csv(
    REPORT_FILE,
    index=False,
    encoding="utf-8-sig",
)


comparison.to_csv(
    COMPARISON_FILE,
    index=False,
    encoding="utf-8-sig",
)


# =========================================================
# FINAL QUALITY GATE
# =========================================================

checks = {

    "registry_16_cells":
        len(
            locations
        )
        ==
        16,

    "full_rectangular_grid":
        grid_pass,

    "16_cell_extraction":
        location_extraction_pass,

    "overlap_5_cells":
        len(
            overlap_locations
        )
        ==
        5,

    "old_new_within_tolerance":
        overlap_pass,
}


print(
    "\n=========================================="
)

print(
    "FINAL QUALITY GATE"
)

print(
    "=========================================="
)


for name, result in checks.items():

    print(
        name,
        ":",
        "PASS"
        if result
        else "FAIL",
    )


overall_pass = all(
    checks.values()
)


print(
    "\n=========================================="
)


print(
    "OVERALL STATUS:",
    "PASS"
    if overall_pass
    else "FAIL",
)


print(
    "\nNew full-area TIGGE file:"
)

print(
    NEW_FILE
)


print(
    "\nExtraction report:"
)

print(
    REPORT_FILE
)


print(
    "\nOld/new comparison report:"
)

print(
    COMPARISON_FILE
)


if not overall_pass:

    raise RuntimeError(
        "Full Bình Định TIGGE geography "
        "validation failed."
    )