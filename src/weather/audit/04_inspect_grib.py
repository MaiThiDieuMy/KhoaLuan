from pathlib import Path

import pandas as pd

from eccodes import (
    codes_grib_new_from_file,
    codes_get,
    codes_release,
)


GRIB_FILE = Path(
    "data/weather/raw/ecmwf_open/latest_full_0_15d.grib2"
)

REPORT_FILE = Path(
    "data/weather/reports/open_data_audit.csv"
)

REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)


def safe_get(gid, key):
    try:
        return codes_get(gid, key)
    except Exception:
        return None


rows = []


with GRIB_FILE.open("rb") as f:

    while True:

        gid = codes_grib_new_from_file(f)

        if gid is None:
            break

        row = {
            "short_name": safe_get(gid, "shortName"),
            "name": safe_get(gid, "name"),
            "units": safe_get(gid, "units"),

            "data_date": safe_get(gid, "dataDate"),
            "data_time": safe_get(gid, "dataTime"),

            "step_range": safe_get(gid, "stepRange"),
            "start_step": safe_get(gid, "startStep"),
            "end_step": safe_get(gid, "endStep"),

            "validity_date": safe_get(gid, "validityDate"),
            "validity_time": safe_get(gid, "validityTime"),

            "grid_type": safe_get(gid, "gridType"),
        }

        rows.append(row)

        codes_release(gid)


df = pd.DataFrame(rows)

df.to_csv(
    REPORT_FILE,
    index=False,
    encoding="utf-8-sig",
)


print("\n=== VARIABLES ===")
print(sorted(df["short_name"].dropna().unique()))

print("\n=== MAX END STEP ===")
print(df["end_step"].max())

print("\n=== STEPS ===")
print(
    sorted(
        df["end_step"]
        .dropna()
        .unique()
    )
)

print("\n=== MESSAGE COUNT ===")
print(len(df))

print("\nReport:")
print(REPORT_FILE)