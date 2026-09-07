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
    "data/weather/reports/open_data_parameter_semantics.csv"
)


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

        rows.append(
            {
                "short_name": safe_get(gid, "shortName"),
                "name": safe_get(gid, "name"),
                "units": safe_get(gid, "units"),

                "step_type": safe_get(gid, "stepType"),
                "step_range": safe_get(gid, "stepRange"),

                "start_step": safe_get(gid, "startStep"),
                "end_step": safe_get(gid, "endStep"),

                "type_of_statistical_processing":
                    safe_get(
                        gid,
                        "typeOfStatisticalProcessing"
                    ),
            }
        )

        codes_release(gid)


df = pd.DataFrame(rows)

REPORT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

df.to_csv(
    REPORT_FILE,
    index=False,
    encoding="utf-8-sig",
)


print("\n=== PARAMETER SEMANTICS ===")

summary = (
    df[
        [
            "short_name",
            "units",
            "step_type",
        ]
    ]
    .drop_duplicates()
    .sort_values("short_name")
)

print(summary.to_string(index=False))


print("\n=== TP SAMPLE ===")

print(
    df[df["short_name"] == "tp"][
        [
            "short_name",
            "step_type",
            "step_range",
            "start_step",
            "end_step",
            "units",
        ]
    ]
    .head(10)
    .to_string(index=False)
)


print("\n=== SSRD SAMPLE ===")

print(
    df[df["short_name"] == "ssrd"][
        [
            "short_name",
            "step_type",
            "step_range",
            "start_step",
            "end_step",
            "units",
        ]
    ]
    .head(10)
    .to_string(index=False)
)


print("\nSaved:")
print(REPORT_FILE)