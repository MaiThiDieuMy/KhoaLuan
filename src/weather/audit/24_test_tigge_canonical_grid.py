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
    "tigge_ecmwf_20260801_00Z_2t_0_360_025deg_binh_dinh.grib2"
)


OLD_TRAINING_FILE = Path(
    "data/weather/reports/"
    "temperature_training_dataset_first_run.csv"
)


OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)


LEAD_TIMES = [
    str(hour)
    for hour in range(
        0,
        361,
        6,
    )
]


# =========================================================
# TIGGE REQUEST
#
# Important:
# - Same forecast run as before
# - Same 61 leads
# - But regrid to regular 0.25° x 0.25°
# - Only retrieve small Bình Định audit box
# =========================================================

dataset = "tigge-forecasts"


request = {
    "origin": "ecmwf",

    "year": "2026",
    "month": "08",
    "day": "01",

    "time": "00:00",

    "level_type": "single_level",

    "variable": [
        "2_m_temperature"
    ],

    "forecast_type":
        "control_forecast",

    "leadtime_hour":
        LEAD_TIMES,

    # Canonical target grid
    "grid":
        "0.25/0.25",

    # North / West / South / East
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
    "\n=== TIGGE CANONICAL GRID TEST ==="
)


print(
    "Run       : 2026-08-01 00 UTC"
)

print(
    "Variable  : 2t"
)

print(
    "Leads     : 0 → 360h / 6h"
)

print(
    "Grid      : 0.25° × 0.25°"
)

print(
    "Area      : 14N,109E → 13.5N,109.5E"
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
    "File:",
    OUTPUT_FILE,
)

print(
    "Size bytes:",
    OUTPUT_FILE.stat().st_size,
)

print(
    "Size KB:",
    round(
        OUTPUT_FILE.stat().st_size
        / 1024,
        3,
    ),
)


# =========================================================
# INSPECT ALL MESSAGES
# =========================================================

rows = []


def safe_get(gid, key):
    try:
        return codes_get(gid, key)
    except Exception:
        return None


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


        value_k = float(
            nearest.value
        )


        rows.append(
            {
                "lead_hours":
                    int(
                        safe_get(
                            gid,
                            "endStep",
                        )
                    ),

                "short_name":
                    safe_get(
                        gid,
                        "shortName",
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

                "temperature_c":
                    value_k
                    - 273.15,
            }
        )


        codes_release(gid)


df = pd.DataFrame(
    rows
).sort_values(
    "lead_hours"
).reset_index(drop=True)


# =========================================================
# AUDIT
# =========================================================

print(
    "\n=== GRID AUDIT ==="
)


print(
    "Messages:",
    len(df),
)

print(
    "Unique leads:",
    df["lead_hours"].nunique(),
)

print(
    "Lead min:",
    df["lead_hours"].min(),
)

print(
    "Lead max:",
    df["lead_hours"].max(),
)


print(
    "\nGrid types:",
    df["grid_type"]
    .unique()
    .tolist(),
)


print(
    "Ni:",
    df["Ni"]
    .unique()
    .tolist(),
)


print(
    "Nj:",
    df["Nj"]
    .unique()
    .tolist(),
)


print(
    "Number of points:",
    df["number_of_points"]
    .unique()
    .tolist(),
)


print(
    "Longitude increment:",
    df["i_increment"]
    .unique()
    .tolist(),
)


print(
    "Latitude increment:",
    df["j_increment"]
    .unique()
    .tolist(),
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
    "\nNearest canonical grid location:"
)

print(
    locations.to_string(
        index=False
    )
)


# =========================================================
# COMPARE LEAD +24
# =========================================================

new_24 = df[
    df["lead_hours"] == 24
].iloc[0]


print(
    "\n=== LEAD +24 COMPARISON ==="
)


print(
    "Regridded TIGGE temperature:",
    round(
        float(
            new_24["temperature_c"]
        ),
        6,
    ),
    "°C",
)


if OLD_TRAINING_FILE.exists():

    old_df = pd.read_csv(
        OLD_TRAINING_FILE
    )


    old_24 = old_df[
        old_df["lead_hours"]
        == 24
    ].iloc[0]


    native_tigge = float(
        old_24[
            "forecast_temperature_c"
        ]
    )


    era5_t = float(
        old_24[
            "verification_temperature_c"
        ]
    )


    canonical_tigge = float(
        new_24[
            "temperature_c"
        ]
    )


    old_error = (
        era5_t
        -
        native_tigge
    )


    new_error = (
        era5_t
        -
        canonical_tigge
    )


    print(
        "\nPrevious native O640 TIGGE:",
        round(
            native_tigge,
            6,
        ),
        "°C",
    )


    print(
        "ERA5 0.25° reference:",
        round(
            era5_t,
            6,
        ),
        "°C",
    )


    print(
        "\nPrevious error:"
    )

    print(
        "ERA5 - native TIGGE =",
        round(
            old_error,
            6,
        ),
        "°C",
    )


    print(
        "\nCanonical-grid error:"
    )

    print(
        "ERA5 - regridded TIGGE =",
        round(
            new_error,
            6,
        ),
        "°C",
    )


# =========================================================
# QUALITY GATE
# =========================================================

passed = (

    len(df) == 61

    and df[
        "lead_hours"
    ].nunique() == 61

    and df[
        "lead_hours"
    ].min() == 0

    and df[
        "lead_hours"
    ].max() == 360

    and df[
        "short_name"
    ].eq("2t").all()

    and df[
        "grid_type"
    ].eq("regular_ll").all()

    and len(
        locations
    ) == 1
)


print(
    "\n=============================="
)


print(
    "CANONICAL GRID STATUS:",
    "PASS"
    if passed
    else "FAIL",
)