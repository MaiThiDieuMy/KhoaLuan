from pathlib import Path
from datetime import datetime

from eccodes import (
    codes_grib_new_from_file,
    codes_get,
    codes_grib_find_nearest,
    codes_release,
)


GRIB_FILE = Path(
    "data/weather/raw/tigge/"
    "tigge_ecmwf_20260801_00Z_2t_step24.grib2"
)


# Điểm audit Bình Định đang dùng
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


message_count = 0


with GRIB_FILE.open("rb") as f:

    while True:

        gid = codes_grib_new_from_file(f)

        if gid is None:
            break

        message_count += 1


        print(
            "\n================================"
        )

        print(
            "GRIB MESSAGE:",
            message_count,
        )

        print(
            "================================"
        )


        # ---------------------------------------
        # VARIABLE
        # ---------------------------------------

        short_name = safe_get(
            gid,
            "shortName",
        )

        name = safe_get(
            gid,
            "name",
        )

        units = safe_get(
            gid,
            "units",
        )


        print(
            "\n=== VARIABLE ==="
        )

        print(
            "shortName:",
            short_name,
        )

        print(
            "name:",
            name,
        )

        print(
            "units:",
            units,
        )


        # ---------------------------------------
        # FORECAST TIME
        # ---------------------------------------

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


        run_time = parse_datetime(
            data_date,
            data_time,
        )

        valid_time = parse_datetime(
            validity_date,
            validity_time,
        )


        print(
            "\n=== FORECAST TIME ==="
        )

        print(
            "run_time:",
            run_time,
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
            "stepRange:",
            safe_get(
                gid,
                "stepRange",
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
            "valid_time:",
            valid_time,
        )


        # ---------------------------------------
        # FORECAST / LEVEL METADATA
        # ---------------------------------------

        print(
            "\n=== FORECAST METADATA ==="
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


        # ---------------------------------------
        # GRID
        # ---------------------------------------

        print(
            "\n=== GRID ==="
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


        # ---------------------------------------
        # BÌNH ĐỊNH POINT
        # ---------------------------------------

        nearest = codes_grib_find_nearest(
            gid,
            TARGET_LAT,
            TARGET_LON,
        )[0]


        print(
            "\n=== BINH DINH TEST POINT ==="
        )

        print(
            "requested:",
            TARGET_LAT,
            TARGET_LON,
        )

        print(
            "nearest grid:",
            nearest.lat,
            nearest.lon,
        )

        print(
            "distance km:",
            nearest.distance,
        )

        print(
            "raw value:",
            nearest.value,
            units,
        )


        if short_name == "2t":

            temperature_c = (
                nearest.value
                - 273.15
            )

            print(
                "temperature °C:",
                round(
                    temperature_c,
                    3,
                ),
            )


        codes_release(gid)


print(
    "\n================================"
)

print(
    "TOTAL GRIB MESSAGES:",
    message_count,
)

print(
    "================================"
)