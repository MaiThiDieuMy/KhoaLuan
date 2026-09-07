from pathlib import Path

from ecmwf.opendata import Client


OUTPUT_DIR = Path("data/weather/raw/ecmwf_open")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

output_file = OUTPUT_DIR / "smoke_test_2t.grib2"


client = Client(
    source="ecmwf",
    model="ifs",
)


result = client.retrieve(
    time=0,
    stream="oper",
    type="fc",

    # chỉ test nhiệt độ +24h
    step=24,

    param="2t",

    target=str(output_file),
)


print("DONE")
print("Forecast run:", result.datetime)
print("Saved to:", output_file)
print("Size:", output_file.stat().st_size, "bytes")