from pathlib import Path
from datetime import datetime

from eccodes import (
    codes_grib_new_from_file,
    codes_get,
    codes_grib_find_nearest,
    codes_release,
)


GRIB_FILE = Path(
    "data/weather/raw/era5/"
    "era5_20260802_00Z_2t_binh_dinh.grib2"
)


TARGET_LAT = 13.78
TARGET_LON = 109.22


def safe_get(gid, key):
    try:
        return codes_get(gid, key)
    except Exception:
        return None


def parse_datetime(date_value, time_value):

    date_string = str(
        int(date_value)
    )

    time_string = str(
        int(time_value)
    ).zfill(4)

    return datetime.strptime(
        date_string + time_string,
        "%Y%m%d%H%M",
    )


# ==================================================
# FILE CHECK
# ==================================================

print(
    "\n=== ERA5 FILE CHECK ==="
)

print(
    "File:",
    GRIB_FILE,
)

print(
    "Exists:",
    GRIB_FILE.exists(),
)


if not GRIB_FILE.exists():
    raise FileNotFoundError(
        GRIB_FILE
    )


size_bytes = GRIB_FILE.stat().st_size


print(
    "Size bytes:",
    size_bytes,
)

print(
    "Size KB:",
    round(
        size_bytes / 1024,
        3,
    ),
)

print(
    "Size MB:",
    round(
        size_bytes / 1024 / 1024,
        6,
    ),
)


# ==================================================
# READ GRIB
# ==================================================

with GRIB_FILE.open("rb") as f:

    gid = codes_grib_new_from_file(f)

    if gid is None:
        raise RuntimeError(
            "File exists but no GRIB message was found."
        )


    print(
        "\n=== VARIABLE ==="
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
        "paramId:",
        safe_get(
            gid,
            "paramId",
        ),
    )


    # ==============================================
    # TIME
    # ==============================================

    print(
        "\n=== TIME ==="
    )


    data_date = safe_get(
        gid,
        "dataDate",
    )

    data_time = safe_get(
        gid,
        "dataTime",
    )


    validity_date = safe_get(
        gid,
        "validityDate",
    )

    validity_time = safe_get(
        gid,
        "validityTime",
    )


    run_or_reference_time = parse_datetime(
        data_date,
        data_time,
    )


    valid_time = parse_datetime(
        validity_date,
        validity_time,
    )


    print(
        "dataDate:",
        data_date,
    )

    print(
        "dataTime:",
        data_time,
    )

    print(
        "reference/data time:",
        run_or_reference_time,
    )

    print(
        "valid_time:",
        valid_time,
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


    # ==============================================
    # PRODUCT TYPE
    # ==============================================

    print(
        "\n=== PRODUCT ==="
    )

    print(
        "dataType:",
        safe_get(
            gid,
            "dataType",
        ),
    )

    print(
        "typeOfLevel:",
        safe_get(
            gid,
            "typeOfLevel",
        ),
    )

    print(
        "level:",
        safe_get(
            gid,
            "level",
        ),
    )


    # ==============================================
    # GRID
    # ==============================================

    print(
        "\n=== ERA5 GRID ==="
    )

    print(
        "gridType:",
        safe_get(
            gid,
            "gridType",
        ),
    )

    print(
        "numberOfPoints:",
        safe_get(
            gid,
            "numberOfPoints",
        ),
    )

    print(
        "Ni:",
        safe_get(
            gid,
            "Ni",
        ),
    )

    print(
        "Nj:",
        safe_get(
            gid,
            "Nj",
        ),
    )

    print(
        "iDirectionIncrementInDegrees:",
        safe_get(
            gid,
            "iDirectionIncrementInDegrees",
        ),
    )

    print(
        "jDirectionIncrementInDegrees:",
        safe_get(
            gid,
            "jDirectionIncrementInDegrees",
        ),
    )


    # ==============================================
    # NEAREST POINT
    # ==============================================

    nearest = codes_grib_find_nearest(
        gid,
        TARGET_LAT,
        TARGET_LON,
    )[0]


    temperature_k = nearest.value

    temperature_c = (
        temperature_k
        - 273.15
    )


    print(
        "\n=== BINH DINH TEST POINT ==="
    )

    print(
        "requested:",
        TARGET_LAT,
        TARGET_LON,
    )

    print(
        "nearest ERA5 grid:",
        nearest.lat,
        nearest.lon,
    )

    print(
        "distance km:",
        nearest.distance,
    )

    print(
        "raw temperature:",
        temperature_k,
        "K",
    )

    print(
        "temperature °C:",
        round(
            temperature_c,
            3,
        ),
    )


    codes_release(gid)