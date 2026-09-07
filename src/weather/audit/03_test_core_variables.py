from pathlib import Path

from ecmwf.opendata import Client


OUTPUT_DIR = Path("data/weather/raw/ecmwf_open")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

output_file = OUTPUT_DIR / "core_variables_test.grib2"


client = Client(
    source="ecmwf",
    model="ifs",
)


STEPS = [
    0,
    24,
    72,
    168,
    360,
]


PARAMS = [
    "2t",     # 2 m temperature
    "2d",     # 2 m dew point
    "10u",    # 10 m U wind
    "10v",    # 10 m V wind
    "tp",     # total precipitation
    "ssrd",   # solar radiation
    "tcc",    # total cloud cover
    "sp",     # surface pressure
]


result = client.retrieve(
    time=0,
    stream="oper",
    type="fc",
    step=STEPS,
    param=PARAMS,
    target=str(output_file),
)


print("DONE")
print("Forecast run:", result.datetime)
print("Steps:", STEPS)
print("Parameters:", PARAMS)
print("Saved to:", output_file)
print("Size:", output_file.stat().st_size, "bytes")