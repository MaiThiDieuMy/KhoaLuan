from pathlib import Path

import numpy as np
import pandas as pd


INPUT_FILE = Path(
    "data/weather/reports/"
    "binh_dinh_normalized_weather.csv"
)


df = pd.read_csv(
    INPUT_FILE,
    parse_dates=[
        "run_time",
        "valid_time",
        "valid_time_vietnam",
    ],
)


checks = []


def check(name, condition, detail):
    checks.append(
        {
            "check": name,
            "status": (
                "PASS"
                if condition
                else "FAIL"
            ),
            "detail": detail,
        }
    )


# ================================================
# 1. NUMBER OF ROWS
# ================================================

check(
    "row_count",
    len(df) == 61,
    f"rows={len(df)}, expected=61",
)


# ================================================
# 2. LEADS
# ================================================

expected_leads = list(
    range(0, 361, 6)
)

actual_leads = (
    sorted(
        df["lead_hours"]
        .unique()
        .tolist()
    )
)


check(
    "lead_sequence",
    actual_leads == expected_leads,
    (
        f"min={min(actual_leads)}, "
        f"max={max(actual_leads)}, "
        f"count={len(actual_leads)}"
    ),
)


# ================================================
# 3. DUPLICATE LEADS
# ================================================

duplicates = (
    df.duplicated(
        subset=[
            "run_time",
            "lead_hours",
        ]
    )
    .sum()
)


check(
    "duplicate_leads",
    duplicates == 0,
    f"duplicates={duplicates}",
)


# ================================================
# 4. VALID TIME CONSISTENCY
# ================================================

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


check(
    "valid_time",
    valid_time_ok,
    "valid_time = run_time + lead_hours",
)


# ================================================
# 5. VIETNAM TIME
# ================================================

expected_vn_time = (
    df["valid_time"]
    +
    pd.Timedelta(hours=7)
)


vn_time_ok = (
    expected_vn_time
    ==
    df["valid_time_vietnam"]
).all()


check(
    "vietnam_time",
    vn_time_ok,
    "Vietnam = UTC + 7h",
)


# ================================================
# 6. MISSING VALUES
# ================================================

core_columns = [
    "temperature_c",
    "dewpoint_c",
    "relative_humidity_pct",
    "wind_speed_ms",
    "cloud_cover_pct",
    "surface_pressure_hpa",
    "rain_interval_mm",
    "solar_interval_mj_m2",
]


missing = (
    df[core_columns]
    .isna()
    .sum()
    .sum()
)


check(
    "missing_values",
    missing == 0,
    f"missing={missing}",
)


# ================================================
# 7. RH RANGE
# ================================================

rh_ok = (
    df["relative_humidity_pct"]
    .between(0, 100)
    .all()
)


check(
    "rh_range",
    rh_ok,
    (
        f"min="
        f"{df['relative_humidity_pct'].min():.2f}, "
        f"max="
        f"{df['relative_humidity_pct'].max():.2f}"
    ),
)


# ================================================
# 8. CLOUD COVER RANGE
# ================================================

cloud_ok = (
    df["cloud_cover_pct"]
    .between(0, 100)
    .all()
)


check(
    "cloud_range",
    cloud_ok,
    (
        f"min="
        f"{df['cloud_cover_pct'].min():.2f}, "
        f"max="
        f"{df['cloud_cover_pct'].max():.2f}"
    ),
)


# ================================================
# 9. WIND NON-NEGATIVE
# ================================================

wind_ok = (
    df["wind_speed_ms"]
    >= 0
).all()


check(
    "wind_non_negative",
    wind_ok,
    (
        f"min="
        f"{df['wind_speed_ms'].min():.3f}"
    ),
)


# ================================================
# 10. RAIN NON-NEGATIVE
# ================================================

rain_ok = (
    df["rain_interval_mm"]
    >= -1e-6
).all()


check(
    "rain_non_negative",
    rain_ok,
    (
        f"min="
        f"{df['rain_interval_mm'].min():.6f}"
    ),
)


# ================================================
# 11. RAIN DE-ACCUMULATION CONSISTENCY
# ================================================

rain_sum = (
    df["rain_interval_mm"]
    .sum()
)

rain_final = (
    df
    .sort_values("lead_hours")
    ["rain_cumulative_mm"]
    .iloc[-1]
)


rain_consistent = np.isclose(
    rain_sum,
    rain_final,
    atol=0.01,
)


check(
    "rain_deaccumulation",
    rain_consistent,
    (
        f"interval_sum={rain_sum:.3f}, "
        f"final_cumulative={rain_final:.3f}"
    ),
)


# ================================================
# 12. SOLAR NON-NEGATIVE
# ================================================

solar_ok = (
    df["solar_interval_mj_m2"]
    >= -1e-6
).all()


check(
    "solar_non_negative",
    solar_ok,
    (
        f"min="
        f"{df['solar_interval_mj_m2'].min():.6f}"
    ),
)


# ================================================
# 13. SOLAR DE-ACCUMULATION CONSISTENCY
# ================================================

solar_sum = (
    df["solar_interval_mj_m2"]
    .sum()
)

solar_final = (
    df
    .sort_values("lead_hours")
    ["solar_cumulative_mj_m2"]
    .iloc[-1]
)


solar_consistent = np.isclose(
    solar_sum,
    solar_final,
    atol=0.01,
)


check(
    "solar_deaccumulation",
    solar_consistent,
    (
        f"interval_sum={solar_sum:.3f}, "
        f"final_cumulative={solar_final:.3f}"
    ),
)


# ================================================
# RESULT
# ================================================

result = pd.DataFrame(checks)


print(
    "\n=== WEATHER DATA QUALITY GATE ===\n"
)


print(
    result.to_string(index=False)
)


failed = result[
    result["status"] == "FAIL"
]


print(
    "\n=============================="
)


if failed.empty:

    print(
        "OVERALL STATUS: PASS"
    )

else:

    print(
        "OVERALL STATUS: FAIL"
    )

    print(
        "\nFailed checks:"
    )

    print(
        failed.to_string(index=False)
    )


REPORT_FILE = Path(
    "data/weather/reports/"
    "normalized_weather_quality.csv"
)


result.to_csv(
    REPORT_FILE,
    index=False,
    encoding="utf-8-sig",
)


print(
    "\nSaved:"
)

print(
    REPORT_FILE
)