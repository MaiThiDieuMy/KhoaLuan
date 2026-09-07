from pathlib import Path
from datetime import datetime

import pandas as pd

from eccodes import (
    codes_grib_new_from_file,
    codes_get,
    codes_grib_find_nearest,
    codes_release,
)


GRIB_FILE = Path(
    "data/weather/raw/ecmwf_open/latest_full_0_15d.grib2"
)

OUTPUT_FILE = Path(
    "data/weather/reports/"
    "binh_dinh_reference_point.csv"
)


# Chỉ là điểm kiểm thử cho data audit.
# Chưa phải vị trí duy nhất của hệ thống.
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


rows = []


with GRIB_FILE.open("rb") as f:

    while True:

        gid = codes_grib_new_from_file(f)

        if gid is None:
            break


        # ecCodes tự tìm grid point gần
        # tọa độ Bình Định nhất.
        nearest = codes_grib_find_nearest(
            gid,
            TARGET_LAT,
            TARGET_LON,
        )[0]


        run_time = parse_datetime(
            safe_get(gid, "dataDate"),
            safe_get(gid, "dataTime"),
        )

        valid_time = parse_datetime(
            safe_get(gid, "validityDate"),
            safe_get(gid, "validityTime"),
        )


        rows.append(
            {
                "run_time": run_time,

                "valid_time": valid_time,

                "lead_hours":
                    safe_get(
                        gid,
                        "endStep",
                    ),

                "short_name":
                    safe_get(
                        gid,
                        "shortName",
                    ),

                "value_raw":
                    nearest.value,

                "units":
                    safe_get(
                        gid,
                        "units",
                    ),

                "step_type":
                    safe_get(
                        gid,
                        "stepType",
                    ),

                "step_range":
                    safe_get(
                        gid,
                        "stepRange",
                    ),

                "grid_lat":
                    nearest.lat,

                "grid_lon":
                    nearest.lon,

                "distance_km":
                    nearest.distance,

                "grid_index":
                    nearest.index,
            }
        )


        codes_release(gid)


df = pd.DataFrame(rows)


df = df.sort_values(
    [
        "lead_hours",
        "short_name",
    ]
)


OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)


df.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig",
)


print("\n=== TARGET LOCATION ===")

print(
    "Requested latitude:",
    TARGET_LAT,
)

print(
    "Requested longitude:",
    TARGET_LON,
)


print("\n=== NEAREST ECMWF GRID ===")

print(
    df[
        [
            "grid_lat",
            "grid_lon",
            "distance_km",
            "grid_index",
        ]
    ]
    .drop_duplicates()
    .to_string(index=False)
)


print("\n=== DATASET RESULT ===")

print(
    "Rows:",
    len(df),
)

print(
    "Variables:",
    sorted(
        df["short_name"]
        .unique()
    ),
)

print(
    "Number of variables:",
    df["short_name"].nunique(),
)

print(
    "Min lead:",
    df["lead_hours"].min(),
)

print(
    "Max lead:",
    df["lead_hours"].max(),
)

print(
    "Unique leads:",
    df["lead_hours"].nunique(),
)


print("\n=== ROWS PER VARIABLE ===")

print(
    df.groupby(
        "short_name"
    )
    .size()
    .to_string()
)


print("\n=== FIRST 20 ROWS ===")

print(
    df.head(20)
    .to_string(index=False)
)


print("\nSaved:")
print(OUTPUT_FILE)