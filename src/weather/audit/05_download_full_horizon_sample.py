from pathlib import Path

from ecmwf.opendata import Client


OUTPUT_DIR = Path("data/weather/raw/ecmwf_open")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

output_file = OUTPUT_DIR / "latest_full_0_15d.grib2"


# 0 → 144h, lấy mỗi 6h
early_steps = list(
    range(0, 145, 6)
)

# ECMWF chuyển sang 6h từ 150 → 360
late_steps = list(
    range(150, 361, 6)
)

STEPS = early_steps + late_steps


PARAMS = [
    "2t",
    "2d",
    "10u",
    "10v",
    "tp",
    "ssrd",
    "tcc",
    "sp",
]


client = Client(
    source="ecmwf",
    model="ifs",
)


result = client.retrieve(
    time=0,
    stream="oper",
    type="fc",
    step=STEPS,
    param=PARAMS,
    target=str(output_file),
)


print("DONE")

print("Forecast run:")
print(result.datetime)

print("Number of leads:")
print(len(STEPS))

print("First leads:")
print(STEPS[:10])

print("Last leads:")
print(STEPS[-10:])

print("Max horizon:")
print(max(STEPS), "hours")

print("Saved:")
print(output_file)

print(
    "Size:",
    round(output_file.stat().st_size / 1024 / 1024, 2),
    "MB",
)