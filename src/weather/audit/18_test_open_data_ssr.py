from pathlib import Path

from ecmwf.opendata import Client

from eccodes import (
    codes_grib_new_from_file,
    codes_get,
    codes_grib_find_nearest,
    codes_release,
)


OUTPUT_DIR = Path(
    "data/weather/raw/ecmwf_open"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


OUTPUT_FILE = (
    OUTPUT_DIR
    / "open_data_ssr_test.grib2"
)


TARGET_LAT = 13.78
TARGET_LON = 109.22


def safe_get(gid, key):
    try:
        return codes_get(gid, key)
    except Exception:
        return None


# ===============================================
# DOWNLOAD
# ===============================================

print(
    "\n=== TEST OPEN DATA SSR ==="
)


client = Client(
    source="ecmwf",
    model="ifs",
)


print(
    "Requesting:"
)

print(
    "param = ssr"
)

print(
    "step = 24"
)


result = client.retrieve(
    time=0,

    stream="oper",

    type="fc",

    step=24,

    param="ssr",

    target=str(
        OUTPUT_FILE
    ),
)


print(
    "\nDOWNLOAD COMPLETE"
)

print(
    "Forecast run:",
    result.datetime,
)

print(
    "File:",
    OUTPUT_FILE,
)

print(
    "Size:",
    OUTPUT_FILE.stat().st_size,
    "bytes",
)


# ===============================================
# INSPECT
# ===============================================

with OUTPUT_FILE.open(
    "rb"
) as f:

    gid = codes_grib_new_from_file(f)

    if gid is None:
        raise RuntimeError(
            "No GRIB message found."
        )


    nearest = (
        codes_grib_find_nearest(
            gid,
            TARGET_LAT,
            TARGET_LON,
        )[0]
    )


    print(
        "\n=== GRIB SEMANTICS ==="
    )


    print(
        "shortName:",
        safe_get(
            gid,
            "shortName",
        ),
    )

    print(
        "name:",
        safe_get(
            gid,
            "name",
        ),
    )

    print(
        "units:",
        safe_get(
            gid,
            "units",
        ),
    )

    print(
        "stepType:",
        safe_get(
            gid,
            "stepType",
        ),
    )

    print(
        "stepRange:",
        safe_get(
            gid,
            "stepRange",
        ),
    )

    print(
        "startStep:",
        safe_get(
            gid,
            "startStep",
        ),
    )

    print(
        "endStep:",
        safe_get(
            gid,
            "endStep",
        ),
    )


    print(
        "\n=== BINH DINH POINT ==="
    )


    print(
        "grid lat:",
        nearest.lat,
    )

    print(
        "grid lon:",
        nearest.lon,
    )

    print(
        "distance km:",
        nearest.distance,
    )

    print(
        "raw value:",
        nearest.value,
    )


    codes_release(gid)