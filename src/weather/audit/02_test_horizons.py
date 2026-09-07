from pathlib import Path

from ecmwf.opendata import Client


OUTPUT_DIR = Path("data/weather/raw/ecmwf_open")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

output_file = OUTPUT_DIR / "horizon_test_2t.grib2"


client = Client(
    source="ecmwf",
    model="ifs",
)


TEST_STEPS = [
    0,
    24,     # ngày 1
    72,     # ngày 3
    168,    # ngày 7
    240,    # ngày 10
    360,    # ngày 15
]


result = client.retrieve(
    time=0,
    stream="oper",
    type="fc",
    step=TEST_STEPS,
    param="2t",
    target=str(output_file),
)


print("DONE")
print("Forecast run:", result.datetime)
print("Requested steps:", TEST_STEPS)
print("Saved to:", output_file)
print("Size:", output_file.stat().st_size, "bytes")