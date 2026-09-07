from pathlib import Path

import numpy as np
import pandas as pd


INPUT_FILE = Path(
    "data/weather/reports/"
    "binh_dinh_reference_point.csv"
)

OUTPUT_FILE = Path(
    "data/weather/reports/"
    "binh_dinh_normalized_weather.csv"
)


df = pd.read_csv(
    INPUT_FILE,
    parse_dates=[
        "run_time",
        "valid_time",
    ],
)


# --------------------------------------------------
# 1. LONG FORMAT → WIDE FORMAT
# --------------------------------------------------

wide = (
    df.pivot_table(
        index=[
            "run_time",
            "valid_time",
            "lead_hours",
            "grid_lat",
            "grid_lon",
        ],
        columns="short_name",
        values="value_raw",
        aggfunc="first",
    )
    .reset_index()
    .sort_values(
        [
            "run_time",
            "lead_hours",
        ]
    )
)


# --------------------------------------------------
# 2. TEMPERATURE
# Kelvin → Celsius
# --------------------------------------------------

wide["temperature_c"] = (
    wide["2t"] - 273.15
)

wide["dewpoint_c"] = (
    wide["2d"] - 273.15
)


# --------------------------------------------------
# 3. RELATIVE HUMIDITY
# từ Temperature + Dew Point
#
# Magnus approximation
# --------------------------------------------------

a = 17.625
b = 243.04


wide["relative_humidity_pct"] = (
    100
    *
    np.exp(
        (
            a
            * wide["dewpoint_c"]
        )
        /
        (
            b
            + wide["dewpoint_c"]
        )
        -
        (
            a
            * wide["temperature_c"]
        )
        /
        (
            b
            + wide["temperature_c"]
        )
    )
)


wide["relative_humidity_pct"] = (
    wide["relative_humidity_pct"]
    .clip(
        lower=0,
        upper=100,
    )
)


# --------------------------------------------------
# 4. WIND SPEED
# sqrt(U² + V²)
# --------------------------------------------------

wide["wind_speed_ms"] = np.sqrt(
    wide["10u"] ** 2
    +
    wide["10v"] ** 2
)


# --------------------------------------------------
# 5. CLOUD COVER
# 0-1 → %
# --------------------------------------------------

wide["cloud_cover_pct"] = (
    wide["tcc"] * 100
)


# --------------------------------------------------
# 6. SURFACE PRESSURE
# Pa → hPa
# --------------------------------------------------

wide["surface_pressure_hpa"] = (
    wide["sp"] / 100
)


# --------------------------------------------------
# 7. PRECIPITATION
# metre → mm
#
# Đây vẫn là cumulative từ run start
# --------------------------------------------------

wide["rain_cumulative_mm"] = (
    wide["tp"] * 1000
)


# De-accumulate:
# interval = cumulative hiện tại - cumulative trước
#
# group theo run_time vì mỗi forecast run
# phải bắt đầu lại từ 0.
# --------------------------------------------------

wide["rain_interval_mm"] = (
    wide
    .groupby("run_time")[
        "rain_cumulative_mm"
    ]
    .diff()
)


# lead 0 không có previous step.
wide["rain_interval_mm"] = (
    wide["rain_interval_mm"]
    .fillna(
        wide["rain_cumulative_mm"]
    )
)


# Numerical noise nhỏ có thể làm giá trị
# hơi âm. Không được âm lượng mưa.
#
# Trước mắt chỉ clip noise nhỏ.
# --------------------------------------------------

wide.loc[
    (
        wide["rain_interval_mm"] < 0
    )
    &
    (
        wide["rain_interval_mm"] > -0.01
    ),
    "rain_interval_mm",
] = 0


# Nếu âm đáng kể → cần kiểm tra,
# không tự sửa.
if (
    wide["rain_interval_mm"]
    < -0.01
).any():

    raise ValueError(
        "Found significant negative "
        "de-accumulated precipitation."
    )


# --------------------------------------------------
# 8. SOLAR RADIATION
# J/m² → MJ/m² cumulative
# --------------------------------------------------

wide[
    "solar_cumulative_mj_m2"
] = (
    wide["ssrd"]
    / 1_000_000
)


wide[
    "solar_interval_mj_m2"
] = (
    wide
    .groupby("run_time")[
        "solar_cumulative_mj_m2"
    ]
    .diff()
)


wide[
    "solar_interval_mj_m2"
] = (
    wide[
        "solar_interval_mj_m2"
    ]
    .fillna(
        wide[
            "solar_cumulative_mj_m2"
        ]
    )
)


# --------------------------------------------------
# 9. INTERVAL LENGTH
# --------------------------------------------------

wide["interval_hours"] = (
    wide
    .groupby("run_time")[
        "lead_hours"
    ]
    .diff()
)


wide["interval_hours"] = (
    wide["interval_hours"]
    .fillna(0)
)


# --------------------------------------------------
# 10. AVERAGE SOLAR FLUX
#
# J/m² / seconds = W/m²
# --------------------------------------------------

wide["solar_interval_j_m2"] = (
    wide["solar_interval_mj_m2"]
    *
    1_000_000
)


wide["solar_mean_w_m2"] = np.where(
    wide["interval_hours"] > 0,

    wide["solar_interval_j_m2"]
    /
    (
        wide["interval_hours"]
        * 3600
    ),

    0,
)


# --------------------------------------------------
# 11. VIETNAM LOCAL TIME
# UTC + 7
# --------------------------------------------------

wide[
    "valid_time_vietnam"
] = (
    wide["valid_time"]
    +
    pd.Timedelta(hours=7)
)


# --------------------------------------------------
# 12. CHỌN OUTPUT CUỐI
# --------------------------------------------------

output_columns = [
    "run_time",
    "valid_time",
    "valid_time_vietnam",

    "lead_hours",

    "grid_lat",
    "grid_lon",

    "temperature_c",
    "dewpoint_c",
    "relative_humidity_pct",

    "10u",
    "10v",
    "wind_speed_ms",

    "cloud_cover_pct",
    "surface_pressure_hpa",

    "rain_cumulative_mm",
    "rain_interval_mm",

    "solar_cumulative_mj_m2",
    "solar_interval_mj_m2",
    "solar_mean_w_m2",
]


result = wide[
    output_columns
].copy()


# --------------------------------------------------
# 13. SAVE
# --------------------------------------------------

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)


result.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig",
)


print(
    "\n=== NORMALIZED WEATHER ==="
)

print(
    result.head(10)
    .round(3)
    .to_string(index=False)
)


print(
    "\nRows:",
    len(result),
)


print(
    "\nLead range:",
    result["lead_hours"].min(),
    "→",
    result["lead_hours"].max(),
)


print(
    "\nTemperature range °C:",
    round(
        result[
            "temperature_c"
        ].min(),
        2,
    ),
    "→",
    round(
        result[
            "temperature_c"
        ].max(),
        2,
    ),
)


print(
    "\nRH range %:",
    round(
        result[
            "relative_humidity_pct"
        ].min(),
        2,
    ),
    "→",
    round(
        result[
            "relative_humidity_pct"
        ].max(),
        2,
    ),
)


print(
    "\nTotal rain over forecast mm:",
    round(
        result[
            "rain_interval_mm"
        ].sum(),
        3,
    ),
)


print(
    "\nSaved:"
)

print(
    OUTPUT_FILE
)