from pathlib import Path

from eccodes import (
    codes_grib_new_from_file,
    codes_get,
    codes_release,
)


GRIB_FILE = Path(
    "data/weather/raw/tigge/"
    "tigge_ecmwf_20260801_00Z_2t_step24.grib2"
)


def safe_get(gid, key):
    try:
        return codes_get(gid, key)
    except Exception as exc:
        return f"NOT_AVAILABLE ({exc})"


with GRIB_FILE.open("rb") as f:

    gid = codes_grib_new_from_file(f)

    if gid is None:
        raise RuntimeError(
            "No GRIB message found."
        )


    keys = [
        "gridType",
        "N",
        "Nj",
        "Ni",
        "numberOfPoints",
        "isOctahedral",
        "latitudeOfFirstGridPointInDegrees",
        "longitudeOfFirstGridPointInDegrees",
        "latitudeOfLastGridPointInDegrees",
        "longitudeOfLastGridPointInDegrees",
    ]


    print(
        "\n=== TIGGE GRID IDENTIFICATION ==="
    )


    for key in keys:

        print(
            f"{key}:",
            safe_get(gid, key),
        )


    codes_release(gid)