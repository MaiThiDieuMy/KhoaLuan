from pathlib import Path
from datetime import datetime, timezone
import shutil
import time

import cdsapi
import pandas as pd

from eccodes import (
    codes_grib_new_from_file,
    codes_get,
    codes_release,
)


# =========================================================
# INPUT
# =========================================================

REGISTRY_FILE = Path(
    "data/weather/registry/"
    "historical_run_registry.csv"
)


# =========================================================
# OUTPUT
# =========================================================

OUTPUT_DIR = Path(
    "data/weather/raw/tigge/"
    "bulk_full_binh_dinh"
)


MANIFEST_FILE = Path(
    "data/weather/registry/"
    "tigge_full_binh_dinh_bulk_manifest.csv"
)


# =========================================================
# EXISTING FULL-AREA TEST FILE
#
# Bước 04 đã kiểm file này PASS.
#
# Nếu gặp run 2026-08-01 thì có thể copy file này
# thay vì download lại.
# =========================================================

GEOGRAPHY_TEST_FILE = Path(
    "data/weather/raw/tigge/geography_test/"
    "tigge_ecmwf_20260801_00Z_"
    "8vars_0_360_025deg_full_binh_dinh.grib2"
)


GEOGRAPHY_TEST_RUN = pd.Timestamp(
    "2026-08-01 00:00:00"
)


# =========================================================
# TIGGE CONFIG
# =========================================================

DATASET = "tigge-forecasts"

ORIGIN = "ecmwf"

FORECAST_TYPE = "control_forecast"

GRID = "0.25/0.25"


# =========================================================
# FULL OLD BINH DINH AREA
#
# North / West / South / East
#
# Geography Registry đã xác định:
#
# North = 14.75
# West  = 108.75
# South = 13.50
# East  = 109.25
#
# Rectangle này tạo:
#
# 6 latitude points
# ×
# 3 longitude points
# =
# 18 grid points/message
#
# Geography filtering về 16 cells sẽ làm ở bước sau.
# =========================================================

AREA = [
    14.75,
    108.75,
    13.50,
    109.25,
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
    "ssr",
    "tcc",
    "tp",
}


LEADS = [
    str(hour)
    for hour in range(
        0,
        361,
        6,
    )
]


EXPECTED_LEADS = set(
    range(
        0,
        361,
        6,
    )
)


EXPECTED_MESSAGES = (
    8
    *
    61
)


EXPECTED_POINTS_PER_MESSAGE = 18


# =========================================================
# RETRY CONFIG
# =========================================================

MAX_ATTEMPTS = 3

RETRY_WAIT_SECONDS = 20

WAIT_BETWEEN_RUNS_SECONDS = 1


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


def utc_now_string():

    return datetime.now(
        timezone.utc
    ).isoformat()


# =========================================================
# OUTPUT FILE NAME
# =========================================================

def get_output_file(
    run_time: pd.Timestamp
):

    return (

        OUTPUT_DIR

        /

        (
            "tigge_ecmwf_"

            +

            run_time.strftime(
                "%Y%m%d"
            )

            +

            "_00Z_8vars_0_360_025deg_"
            "full_binh_dinh.grib2"
        )
    )


# =========================================================
# REQUEST
# =========================================================

def build_request(
    run_time: pd.Timestamp
):

    return {

        "origin":
            ORIGIN,

        "year":
            run_time.strftime(
                "%Y"
            ),

        "month":
            run_time.strftime(
                "%m"
            ),

        "day":
            run_time.strftime(
                "%d"
            ),

        "time":
            "00:00",

        "level_type":
            "single_level",

        "variable":
            VARIABLES,

        "forecast_type":
            FORECAST_TYPE,

        "leadtime_hour":
            LEADS,

        "grid":
            GRID,

        "area":
            AREA,

        "data_format":
            "grib",
    }


# =========================================================
# VERIFY ONE FULL BINH DINH GRIB
#
# Đây là verification của rectangle 18 points.
#
# Chưa filter 16 province cells ở đây.
# =========================================================

def verify_grib_file(
    grib_file: Path
):

    if not grib_file.exists():

        return {
            "verified": False,
            "message_count": 0,
            "variable_count": 0,
            "min_lead": None,
            "max_lead": None,
            "error":
                "File does not exist.",
        }


    if (
        grib_file.stat().st_size
        ==
        0
    ):

        return {
            "verified": False,
            "message_count": 0,
            "variable_count": 0,
            "min_lead": None,
            "max_lead": None,
            "error":
                "File size is zero.",
        }


    rows = []


    try:

        with grib_file.open(
            "rb"
        ) as f:

            while True:

                gid = (
                    codes_grib_new_from_file(
                        f
                    )
                )


                if gid is None:

                    break


                rows.append(
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


    except Exception as exc:

        return {
            "verified": False,
            "message_count": 0,
            "variable_count": 0,
            "min_lead": None,
            "max_lead": None,
            "error":
                f"GRIB read error: {exc}",
        }


    df = pd.DataFrame(
        rows
    )


    if df.empty:

        return {
            "verified": False,
            "message_count": 0,
            "variable_count": 0,
            "min_lead": None,
            "max_lead": None,
            "error":
                "No GRIB messages.",
        }


    actual_variables = set(
        df[
            "short_name"
        ]
        .dropna()
        .unique()
        .tolist()
    )


    # =====================================================
    # BASIC STRUCTURE
    # =====================================================

    message_count_ok = (
        len(df)
        ==
        EXPECTED_MESSAGES
    )


    variables_ok = (
        actual_variables
        ==
        EXPECTED_SHORT_NAMES
    )


    # =====================================================
    # FULL BINH DINH RECTANGLE
    # =====================================================

    grid_ok = (

        df[
            "grid_type"
        ]
        .eq(
            "regular_ll"
        )
        .all()

        and

        df[
            "Ni"
        ]
        .eq(
            3
        )
        .all()

        and

        df[
            "Nj"
        ]
        .eq(
            6
        )
        .all()

        and

        df[
            "number_of_points"
        ]
        .eq(
            EXPECTED_POINTS_PER_MESSAGE
        )
        .all()

        and

        df[
            "i_increment"
        ]
        .sub(
            0.25
        )
        .abs()
        .lt(
            1e-8
        )
        .all()

        and

        df[
            "j_increment"
        ]
        .sub(
            0.25
        )
        .abs()
        .lt(
            1e-8
        )
        .all()
    )


    # =====================================================
    # EACH VARIABLE MUST HAVE ALL 61 LEADS
    # =====================================================

    horizon_ok = True


    for variable in (
        EXPECTED_SHORT_NAMES
    ):

        subset = df[
            df[
                "short_name"
            ]
            ==
            variable
        ]


        if (
            len(subset)
            !=
            61
        ):

            horizon_ok = False
            break


        if (
            subset[
                "lead_hours"
            ].nunique()
            !=
            61
        ):

            horizon_ok = False
            break


        if (
            set(
                subset[
                    "lead_hours"
                ].tolist()
            )
            !=
            EXPECTED_LEADS
        ):

            horizon_ok = False
            break


    verified = all(
        [
            message_count_ok,
            variables_ok,
            grid_ok,
            horizon_ok,
        ]
    )


    problems = []


    if not message_count_ok:

        problems.append(
            "message_count"
        )


    if not variables_ok:

        problems.append(
            "variables"
        )


    if not grid_ok:

        problems.append(
            "grid"
        )


    if not horizon_ok:

        problems.append(
            "horizons"
        )


    return {

        "verified":
            verified,

        "message_count":
            len(df),

        "variable_count":
            len(
                actual_variables
            ),

        "min_lead":
            int(
                df[
                    "lead_hours"
                ].min()
            ),

        "max_lead":
            int(
                df[
                    "lead_hours"
                ].max()
            ),

        "error":
            (
                ""
                if verified
                else
                "Failed checks: "
                +
                ", ".join(
                    problems
                )
            ),
    }


# =========================================================
# LOAD REGISTRY
# =========================================================

print(
    "\n=========================================="
)

print(
    "FULL BINH DINH TIGGE BULK DOWNLOAD"
)

print(
    "=========================================="
)


if not REGISTRY_FILE.exists():

    raise FileNotFoundError(
        REGISTRY_FILE
    )


registry = pd.read_csv(
    REGISTRY_FILE,
    parse_dates=[
        "run_time",
        "verification_start",
        "verification_end",
    ],
)


registry = (

    registry
    .sort_values(
        "run_time"
    )
    .reset_index(
        drop=True
    )
)


print(
    "Runs:",
    len(
        registry
    ),
)


print(
    "First:",
    registry[
        "run_time"
    ].min(),
)


print(
    "Last:",
    registry[
        "run_time"
    ].max(),
)


print(
    "\nFull Bình Định request area:"
)

print(
    AREA
)


print(
    "Rectangular points/message:",
    EXPECTED_POINTS_PER_MESSAGE,
)


print(
    "Selected province cells later:",
    16,
)


print(
    "Messages/run:",
    EXPECTED_MESSAGES,
)


# =========================================================
# DIRECTORIES
# =========================================================

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


MANIFEST_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)


# =========================================================
# ECDS CLIENT
# =========================================================

client = cdsapi.Client()


# =========================================================
# RESULTS
# =========================================================

results = []


downloaded_count = 0

reused_count = 0

skipped_count = 0

failed_count = 0


total_runs = len(
    registry
)


# =========================================================
# PROCESS RUNS
# =========================================================

for index, row in (
    registry.iterrows()
):

    run_time = pd.Timestamp(
        row[
            "run_time"
        ]
    )


    split = str(
        row[
            "split"
        ]
    )


    output_file = (
        get_output_file(
            run_time
        )
    )


    print(
        "\n=========================================="
    )

    print(
        f"RUN {index + 1}/{total_runs}"
    )

    print(
        "=========================================="
    )


    print(
        "Run time:",
        run_time,
    )


    print(
        "Split:",
        split,
    )


    print(
        "File:",
        output_file,
    )


    # =====================================================
    # CASE 1:
    # FINAL FILE ALREADY EXISTS
    # =====================================================

    if output_file.exists():

        print(
            "\nExisting full-area file detected."
        )


        verification = (
            verify_grib_file(
                output_file
            )
        )


        if verification[
            "verified"
        ]:

            print(
                "Verification: PASS"
            )

            print(
                "Skipping download."
            )


            skipped_count += 1


            results.append(
                {
                    "run_time":
                        run_time,

                    "split":
                        split,

                    "status":
                        "skipped_existing_valid",

                    "attempts":
                        0,

                    "file_size_bytes":
                        output_file
                        .stat()
                        .st_size,

                    "message_count":
                        verification[
                            "message_count"
                        ],

                    "variable_count":
                        verification[
                            "variable_count"
                        ],

                    "min_lead":
                        verification[
                            "min_lead"
                        ],

                    "max_lead":
                        verification[
                            "max_lead"
                        ],

                    "verified":
                        True,

                    "output_file":
                        str(
                            output_file
                        ),

                    "error":
                        "",

                    "processed_at_utc":
                        utc_now_string(),
                }
            )


            continue


        print(
            "Existing file FAILED verification."
        )


        print(
            verification[
                "error"
            ]
        )


        output_file.unlink()


    # =====================================================
    # CASE 2:
    # REUSE STEP-04 FILE FOR 2026-08-01
    # =====================================================

    if (
        run_time
        ==
        GEOGRAPHY_TEST_RUN

        and

        GEOGRAPHY_TEST_FILE.exists()
    ):

        print(
            "\nStep-04 geography test file available."
        )


        geography_verification = (
            verify_grib_file(
                GEOGRAPHY_TEST_FILE
            )
        )


        if geography_verification[
            "verified"
        ]:

            print(
                "Geography test file verification: PASS"
            )


            shutil.copy2(
                GEOGRAPHY_TEST_FILE,
                output_file,
            )


            print(
                "Copied into full bulk directory."
            )


            reused_count += 1


            results.append(
                {
                    "run_time":
                        run_time,

                    "split":
                        split,

                    "status":
                        "reused_geography_test",

                    "attempts":
                        0,

                    "file_size_bytes":
                        output_file
                        .stat()
                        .st_size,

                    "message_count":
                        geography_verification[
                            "message_count"
                        ],

                    "variable_count":
                        geography_verification[
                            "variable_count"
                        ],

                    "min_lead":
                        geography_verification[
                            "min_lead"
                        ],

                    "max_lead":
                        geography_verification[
                            "max_lead"
                        ],

                    "verified":
                        True,

                    "output_file":
                        str(
                            output_file
                        ),

                    "error":
                        "",

                    "processed_at_utc":
                        utc_now_string(),
                }
            )


            continue


    # =====================================================
    # CASE 3:
    # DOWNLOAD
    # =====================================================

    request = (
        build_request(
            run_time
        )
    )


    success = False

    attempts_used = 0

    last_error = ""


    for attempt in range(
        1,
        MAX_ATTEMPTS + 1,
    ):

        attempts_used = attempt


        print(
            f"\nDownload attempt "
            f"{attempt}/{MAX_ATTEMPTS}"
        )


        try:

            client.retrieve(
                DATASET,
                request,
                str(
                    output_file
                ),
            )


            print(
                "Download completed."
            )


            print(
                "Size bytes:",
                output_file
                .stat()
                .st_size,
            )


            print(
                "Verifying..."
            )


            verification = (
                verify_grib_file(
                    output_file
                )
            )


            if not verification[
                "verified"
            ]:

                raise RuntimeError(
                    "Downloaded GRIB failed "
                    "verification: "
                    +
                    verification[
                        "error"
                    ]
                )


            print(
                "Verification: PASS"
            )


            success = True

            downloaded_count += 1

            break


        except Exception as exc:

            last_error = str(
                exc
            )


            print(
                "\nAttempt FAILED:"
            )

            print(
                last_error
            )


            if output_file.exists():

                try:

                    output_file.unlink()

                except Exception:

                    pass


            if (
                attempt
                <
                MAX_ATTEMPTS
            ):

                print(
                    f"\nWaiting "
                    f"{RETRY_WAIT_SECONDS} seconds..."
                )


                time.sleep(
                    RETRY_WAIT_SECONDS
                )


    # =====================================================
    # RESULT
    # =====================================================

    if success:

        verification = (
            verify_grib_file(
                output_file
            )
        )


        results.append(
            {
                "run_time":
                    run_time,

                "split":
                    split,

                "status":
                    "downloaded",

                "attempts":
                    attempts_used,

                "file_size_bytes":
                    output_file
                    .stat()
                    .st_size,

                "message_count":
                    verification[
                        "message_count"
                    ],

                "variable_count":
                    verification[
                        "variable_count"
                    ],

                "min_lead":
                    verification[
                        "min_lead"
                    ],

                "max_lead":
                    verification[
                        "max_lead"
                    ],

                "verified":
                    True,

                "output_file":
                    str(
                        output_file
                    ),

                "error":
                    "",

                "processed_at_utc":
                    utc_now_string(),
            }
        )


    else:

        failed_count += 1


        results.append(
            {
                "run_time":
                    run_time,

                "split":
                    split,

                "status":
                    "failed",

                "attempts":
                    attempts_used,

                "file_size_bytes":
                    0,

                "message_count":
                    0,

                "variable_count":
                    0,

                "min_lead":
                    None,

                "max_lead":
                    None,

                "verified":
                    False,

                "output_file":
                    str(
                        output_file
                    ),

                "error":
                    last_error,

                "processed_at_utc":
                    utc_now_string(),
            }
        )


    # =====================================================
    # SAVE PROGRESS AFTER EACH RUN
    # =====================================================

    pd.DataFrame(
        results
    ).to_csv(
        MANIFEST_FILE,
        index=False,
        encoding="utf-8-sig",
    )


    if (
        index
        <
        total_runs - 1
    ):

        time.sleep(
            WAIT_BETWEEN_RUNS_SECONDS
        )


# =========================================================
# FINAL MANIFEST
# =========================================================

manifest = pd.DataFrame(
    results
)


manifest.to_csv(
    MANIFEST_FILE,
    index=False,
    encoding="utf-8-sig",
)


# =========================================================
# SUMMARY
# =========================================================

print(
    "\n\n=========================================="
)

print(
    "FULL BINH DINH BULK SUMMARY"
)

print(
    "=========================================="
)


print(
    "Registry runs:",
    total_runs,
)


print(
    "Downloaded now:",
    downloaded_count,
)


print(
    "Reused Step-04 file:",
    reused_count,
)


print(
    "Skipped existing valid:",
    skipped_count,
)


print(
    "Failed:",
    failed_count,
)


verified_runs = int(

    manifest[
        "verified"
    ]
    .fillna(
        False
    )
    .astype(
        bool
    )
    .sum()
)


print(
    "Verified runs:",
    verified_runs,
)


print(
    "Expected verified runs:",
    total_runs,
)


total_size = int(

    manifest[
        "file_size_bytes"
    ]
    .fillna(
        0
    )
    .sum()
)


print(
    "Total size:",
    round(
        total_size
        /
        1024
        /
        1024,
        3,
    ),
    "MB",
)


# =========================================================
# SPLIT SUMMARY
# =========================================================

split_summary = (

    manifest
    .groupby(
        "split",
        sort=False,
    )
    .agg(

        runs=(
            "run_time",
            "count",
        ),

        verified=(
            "verified",
            "sum",
        ),

    )
    .reset_index()
)


print(
    "\n=========================================="
)

print(
    "SPLIT SUMMARY"
)

print(
    "=========================================="
)


print(
    split_summary.to_string(
        index=False
    )
)


# =========================================================
# DATASET SIZE AFTER GEOGRAPHY FILTER
# =========================================================

candidate_rows = (

    total_runs
    *
    61
    *
    16
)


print(
    "\n=========================================="
)

print(
    "EXPECTED MULTI-LOCATION DATASET"
)

print(
    "=========================================="
)


print(
    "Runs:",
    total_runs,
)


print(
    "Leads/run:",
    61,
)


print(
    "Bình Định locations:",
    16,
)


print(
    "Expected candidate rows:",
    candidate_rows,
)


# =========================================================
# FINAL QUALITY GATE
# =========================================================

overall_pass = (

    len(
        manifest
    )
    ==
    total_runs

    and

    verified_runs
    ==
    total_runs

    and

    failed_count
    ==
    0
)


print(
    "\n=========================================="
)


print(
    "OVERALL STATUS:",
    "PASS"
    if overall_pass
    else "INCOMPLETE",
)


print(
    "\nManifest:"
)

print(
    MANIFEST_FILE
)


print(
    "\nFull Bình Định TIGGE directory:"
)

print(
    OUTPUT_DIR
)


if not overall_pass:

    print(
        "\nSome runs are missing."
    )

    print(
        "Run this SAME script again."
    )

    print(
        "Already verified files will be skipped."
    )