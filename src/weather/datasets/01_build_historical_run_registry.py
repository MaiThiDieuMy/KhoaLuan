from pathlib import Path

import pandas as pd


# =========================================================
# STUDY DATASET SPECIFICATION
#
# Pilot period:
# - Start: first 00 UTC run safely after IFS Cycle 50r1
# - End: latest run chosen so full +360h verification
#        is already old enough for ERA5T availability
# =========================================================

START_RUN = pd.Timestamp(
    "2026-05-14 00:00:00"
)

END_RUN = pd.Timestamp(
    "2026-08-15 00:00:00"
)


# =========================================================
# FORECAST CONFIG
# =========================================================

RUN_HOUR_UTC = 0

MAX_LEAD_HOURS = 360

LEAD_INTERVAL_HOURS = 6

LEADS_PER_RUN = (
    MAX_LEAD_HOURS
    // LEAD_INTERVAL_HOURS
    + 1
)


# =========================================================
# CHRONOLOGICAL SPLIT
#
# IMPORTANT:
#
# Split theo RUN, không random từng row.
#
# Mọi lead của cùng một forecast run
# phải nằm trong cùng một split.
# =========================================================

TRAIN_END = pd.Timestamp(
    "2026-07-15 00:00:00"
)

VALIDATION_START = pd.Timestamp(
    "2026-07-16 00:00:00"
)

VALIDATION_END = pd.Timestamp(
    "2026-07-31 00:00:00"
)

TEST_START = pd.Timestamp(
    "2026-08-01 00:00:00"
)

TEST_END = pd.Timestamp(
    "2026-08-15 00:00:00"
)


# =========================================================
# OUTPUT
# =========================================================

OUTPUT_DIR = Path(
    "data/weather/registry"
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "historical_run_registry.csv"
)


# =========================================================
# CREATE DAILY 00 UTC RUNS
# =========================================================

run_times = pd.date_range(
    start=START_RUN,
    end=END_RUN,
    freq="1D",
)


registry = pd.DataFrame(
    {
        "run_time": run_times,
    }
)


# =========================================================
# VERIFICATION WINDOW
#
# Example:
#
# run_time:
# 2026-08-01 00 UTC
#
# max lead:
# +360h
#
# verification_end:
# 2026-08-16 00 UTC
# =========================================================

registry[
    "verification_start"
] = registry[
    "run_time"
]


registry[
    "verification_end"
] = (

    registry[
        "run_time"
    ]

    +

    pd.to_timedelta(
        MAX_LEAD_HOURS,
        unit="h",
    )
)


# =========================================================
# ASSIGN CHRONOLOGICAL SPLIT
# =========================================================

def assign_split(run_time):

    if (
        START_RUN
        <= run_time
        <= TRAIN_END
    ):
        return "train"

    if (
        VALIDATION_START
        <= run_time
        <= VALIDATION_END
    ):
        return "validation"

    if (
        TEST_START
        <= run_time
        <= TEST_END
    ):
        return "test"

    raise RuntimeError(
        f"Run {run_time} does not belong "
        "to any configured split."
    )


registry[
    "split"
] = registry[
    "run_time"
].apply(
    assign_split
)


# =========================================================
# DATASET METADATA
# =========================================================

registry[
    "forecast_source"
] = "ECMWF_TIGGE"


registry[
    "verification_source"
] = "ERA5"


registry[
    "forecast_type"
] = "control_forecast"


registry[
    "run_hour_utc"
] = RUN_HOUR_UTC


registry[
    "max_lead_hours"
] = MAX_LEAD_HOURS


registry[
    "lead_interval_hours"
] = LEAD_INTERVAL_HOURS


registry[
    "leads_per_run"
] = LEADS_PER_RUN


registry[
    "canonical_grid"
] = "0.25/0.25"


registry[
    "canonical_area"
] = "14/109/13.5/109.5"


registry[
    "location_id"
] = "binh_dinh_audit_01"


# =========================================================
# EXPECTED TRAINING ROWS
#
# một run:
# 61 leads
#
# nên:
# rows = number_of_runs × 61
# =========================================================

registry[
    "expected_rows"
] = LEADS_PER_RUN


# =========================================================
# QUALITY CHECKS
# =========================================================

print(
    "\n=========================================="
)

print(
    "HISTORICAL RUN REGISTRY"
)

print(
    "=========================================="
)


print(
    "First run:",
    registry[
        "run_time"
    ].min(),
)


print(
    "Last run:",
    registry[
        "run_time"
    ].max(),
)


print(
    "Total runs:",
    len(registry),
)


print(
    "Leads per run:",
    LEADS_PER_RUN,
)


print(
    "Expected total ML rows:",
    len(registry)
    *
    LEADS_PER_RUN,
)


# =========================================================
# SPLIT SUMMARY
# =========================================================

summary = (

    registry
    .groupby(
        "split",
        sort=False,
    )
    .agg(
        runs=(
            "run_time",
            "count",
        ),

        first_run=(
            "run_time",
            "min",
        ),

        last_run=(
            "run_time",
            "max",
        ),
    )
    .reset_index()
)


summary[
    "expected_rows"
] = (

    summary[
        "runs"
    ]

    *
    LEADS_PER_RUN
)


print(
    "\n=========================================="
)

print(
    "CHRONOLOGICAL SPLIT"
)

print(
    "=========================================="
)


print(
    summary.to_string(
        index=False
    )
)


# =========================================================
# CHECK:
# NO DATE DUPLICATES
# =========================================================

duplicate_runs = int(

    registry[
        "run_time"
    ]
    .duplicated()
    .sum()
)


# =========================================================
# CHECK:
# DAILY CONTINUITY
# =========================================================

run_diffs = (

    registry[
        "run_time"
    ]
    .diff()
    .dropna()
)


daily_continuity = (

    run_diffs
    .eq(
        pd.Timedelta(
            days=1
        )
    )
    .all()
)


# =========================================================
# CHECK:
# VERIFICATION WINDOW
# =========================================================

verification_window_ok = (

    (
        registry[
            "verification_end"
        ]

        -

        registry[
            "run_time"
        ]
    )

    .eq(
        pd.Timedelta(
            hours=360
        )
    )
    .all()
)


# =========================================================
# CHECK:
# EXPECTED SPLIT COUNTS
#
# Train:
# 14 May → 15 Jul = 63
#
# Validation:
# 16 Jul → 31 Jul = 16
#
# Test:
# 01 Aug → 15 Aug = 15
#
# Total = 94
# =========================================================

actual_counts = (

    registry[
        "split"
    ]
    .value_counts()
    .to_dict()
)


expected_counts = {
    "train": 63,
    "validation": 16,
    "test": 15,
}


split_counts_ok = (
    actual_counts
    ==
    expected_counts
)


# =========================================================
# FINAL QUALITY GATE
# =========================================================

checks = {

    "total_runs":
        len(registry)
        == 94,

    "duplicate_runs":
        duplicate_runs
        == 0,

    "daily_continuity":
        bool(
            daily_continuity
        ),

    "verification_window":
        bool(
            verification_window_ok
        ),

    "split_counts":
        split_counts_ok,

    "leads_per_run":
        LEADS_PER_RUN
        == 61,
}


print(
    "\n=========================================="
)

print(
    "REGISTRY QUALITY GATE"
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


# =========================================================
# SAVE
# =========================================================

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


registry.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig",
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


if not overall_pass:

    raise RuntimeError(
        "Historical run registry "
        "quality gate failed."
    )