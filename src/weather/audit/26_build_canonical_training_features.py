from pathlib import Path

import numpy as np
import pandas as pd


# =========================================================
# CONFIG
# =========================================================

RUN_TIME = pd.Timestamp(
    "2026-08-01 00:00:00"
)

LOCATION_ID = (
    "binh_dinh_audit_01"
)

CANONICAL_LAT = 13.78
CANONICAL_LON = 109.22


# =========================================================
# NUMERICAL TOLERANCES
#
# Đây là tolerance kỹ thuật để xử lý sai số rất nhỏ
# do interpolation / regridding / GRIB packing.
#
# KHÔNG phải ngưỡng nông nghiệp.
# =========================================================

RAIN_NEGATIVE_TOLERANCE_MM = 0.05

SOLAR_NEGATIVE_TOLERANCE_MJ_M2 = 0.001

CLOUD_RANGE_TOLERANCE_PCT = 0.01


# =========================================================
# INPUT / OUTPUT
# =========================================================

TIGGE_AUDIT = Path(
    "data/weather/reports/"
    "tigge_8vars_canonical_full_horizon_audit.csv"
)

ERA5_AUDIT = Path(
    "data/weather/reports/"
    "era5_2t_61_valid_times_audit.csv"
)

OUTPUT_FILE = Path(
    "data/weather/reports/"
    "temperature_training_dataset_canonical_first_run.csv"
)


# =========================================================
# PART A
# READ TIGGE LONG FORMAT
# =========================================================

print(
    "\n=========================================="
)

print(
    "PART A - READ CANONICAL TIGGE"
)

print(
    "=========================================="
)


tigge_long = pd.read_csv(
    TIGGE_AUDIT
)


print(
    "Raw rows:",
    len(tigge_long),
)

print(
    "Variables:",
    sorted(
        tigge_long[
            "short_name"
        ]
        .unique()
        .tolist()
    ),
)


if len(tigge_long) != 488:

    raise RuntimeError(
        "Expected 488 TIGGE rows "
        "(8 variables × 61 leads)."
    )


# =========================================================
# PART B
# LONG FORMAT → WIDE FORMAT
#
# 488 GRIB records:
#
# 8 variables × 61 leads
#
# trở thành:
#
# 61 weather records
# mỗi row = một forecast horizon
# =========================================================

wide = tigge_long.pivot(
    index="lead_hours",
    columns="short_name",
    values="value_raw",
)


wide = (
    wide
    .sort_index()
    .reset_index()
)


required_variables = {
    "2t",
    "2d",
    "10u",
    "10v",
    "sp",
    "tcc",
    "tp",
    "ssr",
}


missing_variables = (
    required_variables
    -
    set(
        wide.columns
    )
)


if missing_variables:

    raise RuntimeError(
        "Missing variables: "
        f"{sorted(missing_variables)}"
    )


print(
    "\nCanonical rows:",
    len(wide),
)

print(
    "Lead min:",
    wide["lead_hours"].min(),
)

print(
    "Lead max:",
    wide["lead_hours"].max(),
)


if (
    len(wide) != 61
    or wide["lead_hours"].nunique() != 61
):

    raise RuntimeError(
        "Expected exactly 61 unique leads."
    )


# =========================================================
# PART C
# TIME COLUMNS
# =========================================================

wide[
    "run_time"
] = RUN_TIME


wide[
    "valid_time"
] = (

    RUN_TIME

    +

    pd.to_timedelta(
        wide["lead_hours"],
        unit="h",
    )
)


# Việt Nam = UTC + 7
wide[
    "valid_time_vn"
] = (

    wide[
        "valid_time"
    ]

    +

    pd.Timedelta(
        hours=7
    )
)


# =========================================================
# PART D
# TEMPERATURE
#
# TIGGE:
# Kelvin → Celsius
# =========================================================

wide[
    "temperature_c"
] = (
    wide["2t"]
    -
    273.15
)


wide[
    "dewpoint_c"
] = (
    wide["2d"]
    -
    273.15
)


# =========================================================
# SURFACE PRESSURE
#
# Pa → hPa
# =========================================================

wide[
    "surface_pressure_hpa"
] = (
    wide["sp"]
    /
    100.0
)


# =========================================================
# CLOUD COVER
#
# TIGGE tcc đã có đơn vị %
#
# Sau regridding có thể xuất hiện numerical overshoot
# cực nhỏ, ví dụ:
#
# 100.000061 %
#
# Đây không phải cloud cover thật > 100%.
#
# Quy tắc:
#
# - nếu sai lệch nhỏ trong tolerance:
#       clip về 0–100
#
# - nếu sai lệch lớn:
#       FAIL pipeline
# =========================================================

cloud_raw = wide["tcc"]


cloud_outside_tolerance = wide[
    (
        cloud_raw
        <
        -CLOUD_RANGE_TOLERANCE_PCT
    )
    |
    (
        cloud_raw
        >
        100.0
        +
        CLOUD_RANGE_TOLERANCE_PCT
    )
].copy()


print(
    "\n=========================================="
)

print(
    "CLOUD COVER NORMALIZATION"
)

print(
    "=========================================="
)


print(
    "Raw cloud range:",
    float(
        cloud_raw.min()
    ),
    "→",
    float(
        cloud_raw.max()
    ),
    "%",
)


if not cloud_outside_tolerance.empty:

    print(
        "\nCloud values outside numerical tolerance:"
    )

    print(
        cloud_outside_tolerance[
            [
                "lead_hours",
                "tcc",
            ]
        ]
        .to_string(
            index=False
        )
    )

    raise RuntimeError(
        "Cloud cover is materially outside "
        "the physical range 0–100%."
    )


tiny_cloud_violations = wide[
    (
        cloud_raw < 0
    )
    |
    (
        cloud_raw > 100
    )
].copy()


print(
    "Tiny numerical boundary violations:",
    len(
        tiny_cloud_violations
    ),
)


if not tiny_cloud_violations.empty:

    print(
        tiny_cloud_violations[
            [
                "lead_hours",
                "tcc",
            ]
        ]
        .to_string(
            index=False
        )
    )


# Chỉ clip sau khi đã kiểm tra rằng
# violation nằm trong tolerance kỹ thuật.
wide[
    "cloud_cover_pct"
] = (
    cloud_raw
    .clip(
        lower=0,
        upper=100,
    )
)


# =========================================================
# WIND COMPONENTS
# =========================================================

wide[
    "wind_u_ms"
] = wide["10u"]


wide[
    "wind_v_ms"
] = wide["10v"]


# =========================================================
# WIND SPEED
#
# sqrt(u² + v²)
# =========================================================

wide[
    "wind_speed_ms"
] = np.sqrt(
    wide["wind_u_ms"] ** 2
    +
    wide["wind_v_ms"] ** 2
)


# =========================================================
# WIND DIRECTION
#
# Meteorological direction:
#
# hướng mà gió THỔI TỪ ĐÂU tới.
#
# 0°   = North
# 90°  = East
# 180° = South
# 270° = West
# =========================================================

wide[
    "wind_direction_deg"
] = (

    270.0

    -

    np.degrees(
        np.arctan2(
            wide["wind_v_ms"],
            wide["wind_u_ms"],
        )
    )

) % 360.0


# =========================================================
# PART E
# RELATIVE HUMIDITY
#
# RH được suy ra từ:
#
# - temperature
# - dewpoint temperature
#
# Dùng Magnus approximation.
# =========================================================

A = 17.625
B = 243.04


gamma_t = (

    A
    *
    wide[
        "temperature_c"
    ]

    /

    (
        B
        +
        wide[
            "temperature_c"
        ]
    )
)


gamma_td = (

    A
    *
    wide[
        "dewpoint_c"
    ]

    /

    (
        B
        +
        wide[
            "dewpoint_c"
        ]
    )
)


wide[
    "relative_humidity_pct"
] = (

    100.0

    *

    np.exp(
        gamma_td
        -
        gamma_t
    )
)


wide[
    "relative_humidity_pct"
] = (

    wide[
        "relative_humidity_pct"
    ]
    .clip(
        lower=0,
        upper=100,
    )
)


# =========================================================
# PART F
# PRECIPITATION
#
# TIGGE tp:
#
# units = kg/m²
#
# 1 kg/m² water ≈ 1 mm water
#
# tp là cumulative:
#
# lead 6  = tổng 0 → 6h
# lead 12 = tổng 0 → 12h
#
# Ta cần de-accumulate để lấy mưa từng interval.
# =========================================================

wide[
    "precipitation_cumulative_mm"
] = wide["tp"]


wide[
    "precipitation_interval_raw_mm"
] = (

    wide[
        "precipitation_cumulative_mm"
    ]
    .diff()
)


# Lead 0
wide.loc[
    wide.index[0],
    "precipitation_interval_raw_mm"
] = (

    wide.loc[
        wide.index[0],
        "precipitation_cumulative_mm"
    ]
)


negative_rain = wide[

    wide[
        "precipitation_interval_raw_mm"
    ]
    < 0

].copy()


print(
    "\n=========================================="
)

print(
    "PRECIPITATION DE-ACCUMULATION"
)

print(
    "=========================================="
)


print(
    "Negative raw intervals:",
    len(
        negative_rain
    ),
)


if not negative_rain.empty:

    print(
        negative_rain[
            [
                "lead_hours",
                "precipitation_cumulative_mm",
                "precipitation_interval_raw_mm",
            ]
        ]
        .to_string(
            index=False
        )
    )


    most_negative = float(

        negative_rain[
            "precipitation_interval_raw_mm"
        ]
        .min()
    )


    if (
        most_negative
        <
        -RAIN_NEGATIVE_TOLERANCE_MM
    ):

        raise RuntimeError(
            "Significant negative precipitation "
            "increment detected: "
            f"{most_negative:.6f} mm"
        )


# Nếu chỉ là numerical artefact rất nhỏ
# thì interval precipitation được clip về 0.
wide[
    "precipitation_interval_mm"
] = (

    wide[
        "precipitation_interval_raw_mm"
    ]
    .clip(
        lower=0
    )
)


# =========================================================
# PART G
# SOLAR NET RADIATION
#
# TIGGE ssr:
#
# units = J/m²
#
# cumulative từ forecast start.
#
# Chuyển:
#
# J/m² → MJ/m²
# =========================================================

wide[
    "solar_net_cumulative_mj_m2"
] = (

    wide["ssr"]
    /
    1_000_000.0
)


wide[
    "solar_net_interval_raw_mj_m2"
] = (

    wide[
        "solar_net_cumulative_mj_m2"
    ]
    .diff()
)


wide.loc[
    wide.index[0],
    "solar_net_interval_raw_mj_m2"
] = (

    wide.loc[
        wide.index[0],
        "solar_net_cumulative_mj_m2"
    ]
)


negative_solar = wide[

    wide[
        "solar_net_interval_raw_mj_m2"
    ]
    < 0

].copy()


print(
    "\n=========================================="
)

print(
    "SOLAR DE-ACCUMULATION"
)

print(
    "=========================================="
)


print(
    "Negative raw intervals:",
    len(
        negative_solar
    ),
)


if not negative_solar.empty:

    print(
        negative_solar[
            [
                "lead_hours",
                "solar_net_cumulative_mj_m2",
                "solar_net_interval_raw_mj_m2",
            ]
        ]
        .to_string(
            index=False
        )
    )


    most_negative_solar = float(

        negative_solar[
            "solar_net_interval_raw_mj_m2"
        ]
        .min()
    )


    if (
        most_negative_solar
        <
        -SOLAR_NEGATIVE_TOLERANCE_MJ_M2
    ):

        raise RuntimeError(
            "Significant negative solar increment "
            "detected: "
            f"{most_negative_solar:.6f} MJ/m²"
        )


wide[
    "solar_net_interval_mj_m2"
] = (

    wide[
        "solar_net_interval_raw_mj_m2"
    ]
    .clip(
        lower=0
    )
)


# =========================================================
# INTERVAL HOURS
# =========================================================

wide[
    "interval_hours"
] = (

    wide[
        "lead_hours"
    ]
    .diff()
)


wide.loc[
    wide.index[0],
    "interval_hours"
] = 0


# =========================================================
# AVERAGE SOLAR FLUX
#
# interval MJ/m²
# →
# mean W/m²
# =========================================================

wide[
    "solar_net_mean_w_m2"
] = np.where(

    wide[
        "interval_hours"
    ]
    > 0,

    (
        wide[
            "solar_net_interval_mj_m2"
        ]
        *
        1_000_000
    )

    /

    (
        wide[
            "interval_hours"
        ]
        *
        3600
    ),

    0.0,
)


# =========================================================
# PART H
# SPATIAL METADATA
# =========================================================

locations = (

    tigge_long[
        [
            "grid_lat",
            "grid_lon",
            "distance_km",
        ]
    ]
    .drop_duplicates()
)


if len(locations) != 1:

    raise RuntimeError(
        "Expected one canonical TIGGE grid location."
    )


tigge_grid_lat = float(
    locations.iloc[0][
        "grid_lat"
    ]
)


tigge_grid_lon = float(
    locations.iloc[0][
        "grid_lon"
    ]
)


tigge_distance_km = float(
    locations.iloc[0][
        "distance_km"
    ]
)


wide[
    "location_id"
] = LOCATION_ID


wide[
    "canonical_lat"
] = CANONICAL_LAT


wide[
    "canonical_lon"
] = CANONICAL_LON


wide[
    "tigge_grid_lat"
] = tigge_grid_lat


wide[
    "tigge_grid_lon"
] = tigge_grid_lon


wide[
    "tigge_distance_km"
] = tigge_distance_km


# =========================================================
# PART I
# READ ERA5 VERIFICATION
# =========================================================

print(
    "\n=========================================="
)

print(
    "ERA5 TARGET JOIN"
)

print(
    "=========================================="
)


era5 = pd.read_csv(
    ERA5_AUDIT,
    parse_dates=[
        "valid_time"
    ],
)


era5 = era5[
    era5[
        "short_name"
    ] == "2t"
].copy()


if len(era5) != 61:

    raise RuntimeError(
        "Expected 61 ERA5 verification rows."
    )


# =========================================================
# ERA5 SPATIAL CHECK
# =========================================================

era5_locations = (

    era5[
        [
            "grid_lat",
            "grid_lon",
        ]
    ]
    .drop_duplicates()
)


if len(
    era5_locations
) != 1:

    raise RuntimeError(
        "ERA5 grid location changed "
        "between timestamps."
    )


era5_grid_lat = float(
    era5_locations.iloc[0][
        "grid_lat"
    ]
)


era5_grid_lon = float(
    era5_locations.iloc[0][
        "grid_lon"
    ]
)


print(
    "TIGGE grid:",
    tigge_grid_lat,
    tigge_grid_lon,
)


print(
    "ERA5 grid :",
    era5_grid_lat,
    era5_grid_lon,
)


same_grid_point = (

    abs(
        tigge_grid_lat
        -
        era5_grid_lat
    )
    < 1e-8

    and

    abs(
        tigge_grid_lon
        -
        era5_grid_lon
    )
    < 1e-8
)


print(
    "Same canonical grid point:",
    same_grid_point,
)


if not same_grid_point:

    raise RuntimeError(
        "TIGGE and ERA5 are not aligned "
        "to the same canonical grid point."
    )


# =========================================================
# JOIN TIGGE + ERA5
#
# Join theo VALID TIME.
#
# KHÔNG join ERA5 với TIGGE run_time.
# =========================================================

training = wide.merge(

    era5[
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
        "",
        "_era5",
    ),
)


training = training.rename(
    columns={
        "grid_lat":
            "era5_grid_lat",

        "grid_lon":
            "era5_grid_lon",

        "distance_km":
            "era5_distance_km",
    }
)


# =========================================================
# PART J
# CREATE ML TARGET
#
# error =
# verification - raw forecast
# =========================================================

training[
    "temperature_error_c"
] = (

    training[
        "verification_temperature_c"
    ]

    -

    training[
        "temperature_c"
    ]
)


# =========================================================
# PART K
# FINAL CANONICAL ML FEATURE TABLE
# =========================================================

final_columns = [

    # -----------------------------------------------------
    # Identity / lineage
    # -----------------------------------------------------

    "location_id",

    "canonical_lat",
    "canonical_lon",

    "run_time",
    "valid_time",
    "valid_time_vn",

    "lead_hours",
    "interval_hours",


    # -----------------------------------------------------
    # Raw / normalized forecast predictors
    # -----------------------------------------------------

    "temperature_c",
    "dewpoint_c",

    "wind_u_ms",
    "wind_v_ms",

    "surface_pressure_hpa",

    "cloud_cover_pct",

    "precipitation_cumulative_mm",
    "precipitation_interval_mm",

    "solar_net_cumulative_mj_m2",
    "solar_net_interval_mj_m2",


    # -----------------------------------------------------
    # Derived weather variables
    # -----------------------------------------------------

    "relative_humidity_pct",

    "wind_speed_ms",
    "wind_direction_deg",

    "solar_net_mean_w_m2",


    # -----------------------------------------------------
    # Verification + ML target
    # -----------------------------------------------------

    "verification_temperature_c",

    "temperature_error_c",


    # -----------------------------------------------------
    # Spatial provenance
    # -----------------------------------------------------

    "tigge_grid_lat",
    "tigge_grid_lon",
    "tigge_distance_km",

    "era5_grid_lat",
    "era5_grid_lon",
    "era5_distance_km",
]


training = training[
    final_columns
].sort_values(
    "lead_hours"
).reset_index(
    drop=True
)


# =========================================================
# PART L
# FINAL QUALITY GATE
# =========================================================

print(
    "\n=========================================="
)

print(
    "FINAL QUALITY GATE"
)

print(
    "=========================================="
)


checks = {}


checks[
    "row_count"
] = (
    len(training) == 61
)


checks[
    "lead_count"
] = (
    training[
        "lead_hours"
    ].nunique()
    == 61
)


checks[
    "missing_values"
] = (
    training.isna()
    .sum()
    .sum()
    == 0
)


checks[
    "rh_range"
] = (

    training[
        "relative_humidity_pct"
    ]
    .between(
        0,
        100
    )
    .all()
)


checks[
    "cloud_range"
] = (

    training[
        "cloud_cover_pct"
    ]
    .between(
        0,
        100
    )
    .all()
)


checks[
    "wind_non_negative"
] = (

    training[
        "wind_speed_ms"
    ]
    .ge(0)
    .all()
)


checks[
    "rain_non_negative"
] = (

    training[
        "precipitation_interval_mm"
    ]
    .ge(0)
    .all()
)


checks[
    "solar_non_negative"
] = (

    training[
        "solar_net_interval_mj_m2"
    ]
    .ge(0)
    .all()
)


checks[
    "temperature_target_complete"
] = (

    training[
        "temperature_error_c"
    ]
    .notna()
    .all()
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


# =========================================================
# SAVE OUTPUT
#
# File vẫn được lưu để audit.
# Nhưng chỉ khi OVERALL STATUS = PASS
# mới được coi là approved training artifact.
# =========================================================

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)


training.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig",
)


# =========================================================
# DIAGNOSTICS
# =========================================================

error = training[
    "temperature_error_c"
]


bias = error.mean()


mae = (
    error
    .abs()
    .mean()
)


rmse = np.sqrt(
    np.mean(
        error ** 2
    )
)


print(
    "\n=========================================="
)

print(
    "CANONICAL ONE-RUN DIAGNOSTICS"
)

print(
    "=========================================="
)


print(
    "Bias:",
    round(
        bias,
        4
    ),
    "°C",
)


print(
    "MAE:",
    round(
        mae,
        4
    ),
    "°C",
)


print(
    "RMSE:",
    round(
        rmse,
        4
    ),
    "°C",
)


# =========================================================
# FIRST 10 ROWS
# =========================================================

print(
    "\n=== FIRST 10 ROWS ==="
)


print(
    training[
        [
            "lead_hours",

            "temperature_c",
            "dewpoint_c",
            "relative_humidity_pct",

            "wind_speed_ms",

            "cloud_cover_pct",

            "precipitation_interval_mm",

            "solar_net_interval_mj_m2",

            "verification_temperature_c",

            "temperature_error_c",
        ]
    ]
    .head(10)
    .round(4)
    .to_string(
        index=False
    )
)


# =========================================================
# FINAL RESULT
# =========================================================

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
    "\nSaved:"
)

print(
    OUTPUT_FILE
)