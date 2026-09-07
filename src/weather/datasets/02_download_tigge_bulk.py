from pathlib import Path
from datetime import datetime, timezone
import time

import cdsapi
import pandas as pd

from eccodes import (
    codes_grib_new_from_file,
    codes_get,
    codes_release,
)


# =========================================================
# CONFIG
# =========================================================

REGISTRY_FILE = Path(
    "data/weather/registry/"
    "historical_run_registry.csv"
)


OUTPUT_DIR = Path(
    "data/weather/raw/tigge/bulk"
)


MANIFEST_FILE = Path(
    "data/weather/registry/"
    "tigge_bulk_download_manifest.csv"
)


# =========================================================
# RETRIEVAL CONFIG
# =========================================================

DATASET = "tigge-forecasts"

ORIGIN = "ecmwf"

FORECAST_TYPE = "control_forecast"

GRID = "0.25/0.25"


# North / West / South / East
AREA = [
    14,
    109,
    13.5,
    109.5,
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


EXPECTED_MESSAGES = (
    len(VARIABLES)
    *
    len(LEADS)
)


# =========================================================
# RETRY CONFIG
# =========================================================

MAX_ATTEMPTS = 3

RETRY_WAIT_SECONDS = 15

WAIT_BETWEEN_RUNS_SECONDS = 1


# =========================================================
# HELPERS
# =========================================================

def safe_get(gid, key):
    try:
        return codes_get(gid, key)
    except Exception:
        return None


def utc_now_string():

    return datetime.now(
        timezone.utc
    ).isoformat()


# =========================================================
# VERIFY ONE GRIB FILE
#
# Không chỉ kiểm tra file tồn tại.
#
# Phải xác nhận:
#
# - 488 messages
# - 8 variables
# - mỗi variable có 61 leads
# - lead 0 → 360
# - regular_ll
# - 0.25° grid
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


    if grib_file.stat().st_size == 0:

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


                short_name = safe_get(
                    gid,
                    "shortName",
                )


                end_step = safe_get(
                    gid,
                    "endStep",
                )


                grid_type = safe_get(
                    gid,
                    "gridType",
                )


                Ni = safe_get(
                    gid,
                    "Ni",
                )


                Nj = safe_get(
                    gid,
                    "Nj",
                )


                i_increment = safe_get(
                    gid,
                    "iDirectionIncrementInDegrees",
                )


                j_increment = safe_get(
                    gid,
                    "jDirectionIncrementInDegrees",
                )


                rows.append(
                    {
                        "short_name":
                            short_name,

                        "lead_hours":
                            int(
                                end_step
                            ),

                        "grid_type":
                            grid_type,

                        "Ni":
                            Ni,

                        "Nj":
                            Nj,

                        "i_increment":
                            i_increment,

                        "j_increment":
                            j_increment,
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
                "No GRIB messages found.",
        }


    actual_variables = set(
        df[
            "short_name"
        ]
        .dropna()
        .tolist()
    )


    # =====================================================
    # MESSAGE COUNT
    # =====================================================

    message_count_ok = (
        len(df)
        ==
        EXPECTED_MESSAGES
    )


    # =====================================================
    # VARIABLE SET
    # =====================================================

    variables_ok = (
        actual_variables
        ==
        EXPECTED_SHORT_NAMES
    )


    # =====================================================
    # GRID
    # =====================================================

    grid_type_ok = (
        df[
            "grid_type"
        ]
        .eq(
            "regular_ll"
        )
        .all()
    )


    Ni_ok = (
        df[
            "Ni"
        ]
        .eq(
            3
        )
        .all()
    )


    Nj_ok = (
        df[
            "Nj"
        ]
        .eq(
            3
        )
        .all()
    )


    longitude_increment_ok = (

        df[
            "i_increment"
        ]
        .astype(float)
        .sub(
            0.25
        )
        .abs()
        .lt(
            1e-8
        )
        .all()
    )


    latitude_increment_ok = (

        df[
            "j_increment"
        ]
        .astype(float)
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
    # EACH VARIABLE MUST HAVE 61 LEADS
    # =====================================================

    horizon_ok = True


    expected_lead_set = set(
        range(
            0,
            361,
            6,
        )
    )


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


        actual_leads = set(
            subset[
                "lead_hours"
            ]
            .tolist()
        )


        if (
            len(subset) != 61
            or subset[
                "lead_hours"
            ].nunique() != 61
            or actual_leads
            != expected_lead_set
        ):

            horizon_ok = False
            break


    verified = all(
        [
            message_count_ok,
            variables_ok,
            grid_type_ok,
            Ni_ok,
            Nj_ok,
            longitude_increment_ok,
            latitude_increment_ok,
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


    if not horizon_ok:

        problems.append(
            "horizons"
        )


    if not grid_type_ok:

        problems.append(
            "grid_type"
        )


    if not Ni_ok:

        problems.append(
            "Ni"
        )


    if not Nj_ok:

        problems.append(
            "Nj"
        )


    if not longitude_increment_ok:

        problems.append(
            "longitude_increment"
        )


    if not latitude_increment_ok:

        problems.append(
            "latitude_increment"
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
# CREATE REQUEST FOR ONE RUN
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
# OUTPUT FILE NAME
# =========================================================

def get_output_file(
    run_time: pd.Timestamp
):

    filename = (

        "tigge_ecmwf_"

        +

        run_time.strftime(
            "%Y%m%d"
        )

        +

        "_00Z_8vars_0_360_025deg_binh_dinh.grib2"
    )


    return (
        OUTPUT_DIR
        /
        filename
    )


# =========================================================
# LOAD REGISTRY
# =========================================================

print(
    "\n=========================================="
)

print(
    "TIGGE BULK HISTORICAL DOWNLOAD"
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
    "Registry:",
    REGISTRY_FILE,
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
    "Last :",
    registry[
        "run_time"
    ].max(),
)


print(
    "Expected messages per run:",
    EXPECTED_MESSAGES,
)


print(
    "Expected variables:",
    len(
        EXPECTED_SHORT_NAMES
    ),
)


print(
    "Expected leads / variable:",
    len(
        LEADS
    ),
)


# =========================================================
# OUTPUT DIRECTORY
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
# LOAD EXISTING MANIFEST
#
# Manifest chỉ là history/status.
#
# Verification của actual GRIB file vẫn là nguồn chính.
# =========================================================

if MANIFEST_FILE.exists():

    manifest = pd.read_csv(
        MANIFEST_FILE
    )

else:

    manifest = pd.DataFrame()


# =========================================================
# CLIENT
# =========================================================

client = cdsapi.Client()


# =========================================================
# RESULTS FOR THIS RUN
# =========================================================

results = []


successful_count = 0

skipped_count = 0

failed_count = 0


# =========================================================
# PROCESS EACH HISTORICAL RUN
# =========================================================

total_runs = len(
    registry
)


for index, row in (
    registry.iterrows()
):

    run_time = pd.Timestamp(
        row[
            "run_time"
        ]
    )


    split = row[
        "split"
    ]


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
    # EXISTING FILE
    #
    # Nếu file tồn tại:
    # kiểm tra trước.
    #
    # Nếu đúng:
    # skip download.
    # =====================================================

    if output_file.exists():

        print(
            "\nExisting file detected."
        )

        print(
            "Verifying..."
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
                "Existing file: PASS"
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

                    "output_file":
                        str(
                            output_file
                        ),

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

                    "error":
                        "",

                    "processed_at_utc":
                        utc_now_string(),
                }
            )


            continue


        else:

            print(
                "Existing file FAILED verification."
            )

            print(
                "Reason:",
                verification[
                    "error"
                ],
            )

            print(
                "Deleting invalid file..."
            )


            output_file.unlink()


    # =====================================================
    # DOWNLOAD WITH RETRY
    # =====================================================

    request = (
        build_request(
            run_time
        )
    )


    success = False

    last_error = ""

    attempts_used = 0


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
                "Verifying GRIB..."
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
                    "Downloaded file failed "
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

            successful_count += 1

            last_error = ""

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


            # Delete partial/invalid file.
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
                    f"{RETRY_WAIT_SECONDS} "
                    f"seconds before retry..."
                )


                time.sleep(
                    RETRY_WAIT_SECONDS
                )


    # =====================================================
    # RECORD RESULT
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

                "output_file":
                    str(
                        output_file
                    ),

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

                "output_file":
                    str(
                        output_file
                    ),

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

                "error":
                    last_error,

                "processed_at_utc":
                    utc_now_string(),
            }
        )


    # =====================================================
    # SAVE PROGRESS AFTER EVERY RUN
    #
    # Nếu process bị dừng giữa chừng,
    # manifest hiện tại vẫn còn.
    # =====================================================

    current_results = pd.DataFrame(
        results
    )


    current_results.to_csv(
        MANIFEST_FILE,
        index=False,
        encoding="utf-8-sig",
    )


    # Small pause between requests.
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
# FINAL SUMMARY
# =========================================================

print(
    "\n\n=========================================="
)

print(
    "BULK DOWNLOAD SUMMARY"
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
    successful_count,
)


print(
    "Skipped valid existing:",
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


total_size_bytes = int(

    manifest[
        "file_size_bytes"
    ]
    .fillna(
        0
    )
    .sum()
)


print(
    "Total downloaded size:",
    round(
        total_size_bytes
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
# FINAL QUALITY GATE
# =========================================================

overall_pass = (

    len(
        manifest
    )
    ==
    total_runs

    and verified_runs
    ==
    total_runs

    and failed_count
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
    "\nTIGGE directory:"
)

print(
    OUTPUT_DIR
)


if not overall_pass:

    print(
        "\nSome runs are missing or failed."
    )

    print(
        "Run this SAME script again."
    )

    print(
        "Valid existing files will be skipped."
    )