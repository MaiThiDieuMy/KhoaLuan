from pathlib import Path
import json
import math
import unicodedata

import pandas as pd
import requests
import geopandas as gpd

from shapely.geometry import box


# =========================================================
# CONFIG
# =========================================================

GRID_RESOLUTION = 0.25

HALF_GRID = GRID_RESOLUTION / 2.0


# =========================================================
# CURRENT AUDIT BOX
#
# Đây là vùng đã dùng cho 94 TIGGE files hiện tại.
# Dùng để xem bao nhiêu grid cells của Bình Định
# thực sự nằm trong vùng đã download.
# =========================================================

AUDIT_NORTH = 14.0
AUDIT_WEST = 109.0
AUDIT_SOUTH = 13.5
AUDIT_EAST = 109.5


# =========================================================
# SOURCE
#
# geoBoundaries ADM1 Viet Nam
#
# API metadata sẽ trả link GeoJSON.
# =========================================================

GEOB_API = (
    "https://www.geoboundaries.org/"
    "api/current/gbOpen/VNM/ADM1/"
)


# =========================================================
# OUTPUT
# =========================================================

OUTPUT_DIR = Path(
    "data/weather/geography"
)


BOUNDARY_FILE = (
    OUTPUT_DIR
    / "binh_dinh_old_boundary.geojson"
)


GRID_FILE = (
    OUTPUT_DIR
    / "binh_dinh_weather_grid_025.geojson"
)


REGISTRY_FILE = (
    OUTPUT_DIR
    / "binh_dinh_location_registry.csv"
)


METADATA_FILE = (
    OUTPUT_DIR
    / "binh_dinh_geography_metadata.json"
)


OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =========================================================
# HELPERS
# =========================================================

def normalize_text(value):

    value = str(value)

    value = unicodedata.normalize(
        "NFD",
        value,
    )

    value = "".join(
        char
        for char in value
        if unicodedata.category(char)
        != "Mn"
    )

    return (
        value
        .lower()
        .strip()
        .replace("đ", "d")
    )


def floor_to_grid(value, grid):

    return (
        math.floor(
            value / grid
        )
        *
        grid
    )


def ceil_to_grid(value, grid):

    return (
        math.ceil(
            value / grid
        )
        *
        grid
    )


# =========================================================
# PART A
# GET GEOboundaries METADATA
# =========================================================

print(
    "\n=========================================="
)

print(
    "PART A - LOAD VIET NAM ADM1 BOUNDARY"
)

print(
    "=========================================="
)


response = requests.get(
    GEOB_API,
    timeout=60,
)


response.raise_for_status()


metadata = response.json()


print(
    "Boundary:",
    metadata.get(
        "boundaryName"
    ),
)


print(
    "Boundary type:",
    metadata.get(
        "boundaryType"
    ),
)


print(
    "Boundary year represented:",
    metadata.get(
        "boundaryYearRepresented"
    ),
)


print(
    "Source:",
    metadata.get(
        "boundarySource"
    ),
)


geojson_url = metadata.get(
    "gjDownloadURL"
)


if not geojson_url:

    raise RuntimeError(
        "geoBoundaries API did not return "
        "a GeoJSON download URL."
    )


print(
    "GeoJSON source:",
    geojson_url,
)


# =========================================================
# PART B
# READ VIET NAM ADM1
# =========================================================

vietnam = gpd.read_file(
    geojson_url
)


print(
    "\nADM1 rows:",
    len(vietnam),
)


print(
    "Columns:",
    vietnam.columns.tolist(),
)


# =========================================================
# DETECT PROVINCE NAME COLUMN
# =========================================================

candidate_name_columns = [
    "shapeName",
    "NAME_1",
    "name",
    "Name",
    "NAME",
]


name_column = None


for candidate in candidate_name_columns:

    if candidate in vietnam.columns:

        name_column = candidate
        break


if name_column is None:

    raise RuntimeError(
        "Could not identify province name column."
    )


print(
    "Province name column:",
    name_column,
)


# =========================================================
# PART C
# FIND OLD BÌNH ĐỊNH
# =========================================================

normalized_names = (
    vietnam[
        name_column
    ]
    .astype(str)
    .map(
        normalize_text
    )
)


matches = vietnam[
    normalized_names.str.contains(
        "binh dinh",
        regex=False,
    )
].copy()


if len(matches) != 1:

    print(
        "\nPossible province names:"
    )

    print(
        vietnam[
            name_column
        ]
        .astype(str)
        .sort_values()
        .to_string(
            index=False
        )
    )

    raise RuntimeError(
        "Expected exactly one Bình Định "
        f"boundary, found {len(matches)}."
    )


binh_dinh = matches.copy()


province_name = str(
    binh_dinh.iloc[0][
        name_column
    ]
)


print(
    "\nMatched province:",
    province_name,
)


# Ensure WGS84.
binh_dinh = (
    binh_dinh
    .to_crs(
        "EPSG:4326"
    )
)


# =========================================================
# SAVE PROVINCE BOUNDARY
# =========================================================

binh_dinh.to_file(
    BOUNDARY_FILE,
    driver="GeoJSON",
)


# =========================================================
# PART D
# PROVINCE BOUNDS
# =========================================================

min_lon, min_lat, max_lon, max_lat = (
    binh_dinh.total_bounds
)


print(
    "\n=========================================="
)

print(
    "OLD BÌNH ĐỊNH BOUNDS"
)

print(
    "=========================================="
)


print(
    "South:",
    round(
        min_lat,
        6,
    ),
)


print(
    "North:",
    round(
        max_lat,
        6,
    ),
)


print(
    "West :",
    round(
        min_lon,
        6,
    ),
)


print(
    "East :",
    round(
        max_lon,
        6,
    ),
)


# =========================================================
# PART E
# BUILD CANONICAL 0.25 DEGREE CELLS
#
# Weather grid point is treated as center of a
# 0.25° × 0.25° cell.
#
# We keep cells that INTERSECT Bình Định polygon.
#
# This is safer than only keeping centers that happen
# to lie inside the province because edge/coastal cells
# could otherwise be lost.
# =========================================================

start_lat = floor_to_grid(
    min_lat - HALF_GRID,
    GRID_RESOLUTION,
)


end_lat = ceil_to_grid(
    max_lat + HALF_GRID,
    GRID_RESOLUTION,
)


start_lon = floor_to_grid(
    min_lon - HALF_GRID,
    GRID_RESOLUTION,
)


end_lon = ceil_to_grid(
    max_lon + HALF_GRID,
    GRID_RESOLUTION,
)


latitudes = []


current = start_lat


while (
    current
    <=
    end_lat
    +
    1e-9
):

    latitudes.append(
        round(
            current,
            8,
        )
    )

    current += (
        GRID_RESOLUTION
    )


longitudes = []


current = start_lon


while (
    current
    <=
    end_lon
    +
    1e-9
):

    longitudes.append(
        round(
            current,
            8,
        )
    )

    current += (
        GRID_RESOLUTION
    )


province_geometry = (
    binh_dinh
    .geometry
    .union_all()
)


selected_cells = []


for lat in latitudes:

    for lon in longitudes:

        cell = box(
            lon - HALF_GRID,
            lat - HALF_GRID,
            lon + HALF_GRID,
            lat + HALF_GRID,
        )


        if not cell.intersects(
            province_geometry
        ):

            continue


        center_inside = (
            province_geometry
            .covers(
                cell.centroid
            )
        )


        covered_by_current_audit_box = (

            AUDIT_SOUTH
            <= lat
            <= AUDIT_NORTH

            and

            AUDIT_WEST
            <= lon
            <= AUDIT_EAST
        )


        selected_cells.append(
            {
                "grid_lat":
                    lat,

                "grid_lon":
                    lon,

                "cell_south":
                    lat
                    -
                    HALF_GRID,

                "cell_north":
                    lat
                    +
                    HALF_GRID,

                "cell_west":
                    lon
                    -
                    HALF_GRID,

                "cell_east":
                    lon
                    +
                    HALF_GRID,

                "center_inside_province":
                    bool(
                        center_inside
                    ),

                "cell_intersects_province":
                    True,

                "covered_by_current_audit_box":
                    bool(
                        covered_by_current_audit_box
                    ),

                "geometry":
                    cell,
            }
        )


if not selected_cells:

    raise RuntimeError(
        "No weather cells intersect Bình Định."
    )


grid_gdf = gpd.GeoDataFrame(
    selected_cells,
    geometry="geometry",
    crs="EPSG:4326",
)


# =========================================================
# SORT NORTH → SOUTH, WEST → EAST
# =========================================================

grid_gdf = (
    grid_gdf
    .sort_values(
        [
            "grid_lat",
            "grid_lon",
        ],
        ascending=[
            False,
            True,
        ],
    )
    .reset_index(
        drop=True
    )
)


# =========================================================
# LOCATION IDS
# =========================================================

grid_gdf[
    "location_id"
] = [

    f"binh_dinh_grid_{index:03d}"

    for index in range(
        1,
        len(grid_gdf)
        +
        1,
    )
]


# =========================================================
# ORDER COLUMNS
# =========================================================

columns = [
    "location_id",

    "grid_lat",
    "grid_lon",

    "cell_south",
    "cell_north",
    "cell_west",
    "cell_east",

    "center_inside_province",
    "cell_intersects_province",

    "covered_by_current_audit_box",

    "geometry",
]


grid_gdf = grid_gdf[
    columns
]


# =========================================================
# SAVE GRID GEOJSON
# =========================================================

grid_gdf.to_file(
    GRID_FILE,
    driver="GeoJSON",
)


# =========================================================
# SAVE CSV REGISTRY
# =========================================================

registry_columns = [
    "location_id",

    "grid_lat",
    "grid_lon",

    "cell_south",
    "cell_north",
    "cell_west",
    "cell_east",

    "center_inside_province",
    "cell_intersects_province",

    "covered_by_current_audit_box",
]


grid_gdf[
    registry_columns
].to_csv(
    REGISTRY_FILE,
    index=False,
    encoding="utf-8-sig",
)


# =========================================================
# PART F
# STATISTICS
# =========================================================

total_cells = len(
    grid_gdf
)


center_inside_count = int(
    grid_gdf[
        "center_inside_province"
    ].sum()
)


current_audit_cells = int(
    grid_gdf[
        "covered_by_current_audit_box"
    ].sum()
)


missing_from_current_audit = (

    total_cells
    -
    current_audit_cells
)


# =========================================================
# WEATHER RETRIEVAL BOUNDING BOX
#
# Build rectangular ECMWF request containing all
# selected grid centers.
# =========================================================

retrieval_north = float(
    grid_gdf[
        "grid_lat"
    ].max()
)


retrieval_south = float(
    grid_gdf[
        "grid_lat"
    ].min()
)


retrieval_west = float(
    grid_gdf[
        "grid_lon"
    ].min()
)


retrieval_east = float(
    grid_gdf[
        "grid_lon"
    ].max()
)


print(
    "\n=========================================="
)

print(
    "CANONICAL WEATHER GRID"
)

print(
    "=========================================="
)


print(
    "Resolution:",
    GRID_RESOLUTION,
    "degree",
)


print(
    "Cells intersecting province:",
    total_cells,
)


print(
    "Cell centers inside province:",
    center_inside_count,
)


print(
    "Cells covered by CURRENT audit box:",
    current_audit_cells,
)


print(
    "Cells NOT covered by current audit box:",
    missing_from_current_audit,
)


print(
    "\nRequired ECMWF retrieval box:"
)


print(
    "North:",
    retrieval_north,
)

print(
    "West :",
    retrieval_west,
)

print(
    "South:",
    retrieval_south,
)

print(
    "East :",
    retrieval_east,
)


# =========================================================
# PART G
# METADATA
# =========================================================

output_metadata = {

    "province_name":
        province_name,

    "boundary_source":
        metadata.get(
            "boundarySource"
        ),

    "boundary_year_represented":
        metadata.get(
            "boundaryYearRepresented"
        ),

    "boundary_api":
        GEOB_API,

    "boundary_geojson_source":
        geojson_url,

    "grid_resolution_degree":
        GRID_RESOLUTION,

    "selection_method":
        (
            "0.25-degree weather cells "
            "intersecting old Binh Dinh polygon"
        ),

    "province_bounds": {

        "south":
            float(
                min_lat
            ),

        "north":
            float(
                max_lat
            ),

        "west":
            float(
                min_lon
            ),

        "east":
            float(
                max_lon
            ),
    },

    "retrieval_area": {

        "north":
            retrieval_north,

        "west":
            retrieval_west,

        "south":
            retrieval_south,

        "east":
            retrieval_east,
    },

    "total_selected_cells":
        total_cells,

    "center_inside_cells":
        center_inside_count,

    "covered_by_existing_audit_box":
        current_audit_cells,

    "not_covered_by_existing_audit_box":
        missing_from_current_audit,
}


with METADATA_FILE.open(
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        output_metadata,
        f,
        ensure_ascii=False,
        indent=2,
    )


# =========================================================
# QUALITY GATE
# =========================================================

checks = {

    "province_found":
        len(
            binh_dinh
        )
        == 1,

    "boundary_valid":
        bool(
            binh_dinh
            .geometry
            .is_valid
            .all()
        ),

    "grid_cells_exist":
        total_cells
        > 0,

    "all_cells_intersect":
        bool(
            grid_gdf[
                "cell_intersects_province"
            ]
            .all()
        ),

    "location_ids_unique":
        (
            grid_gdf[
                "location_id"
            ]
            .nunique()
            ==
            total_cells
        ),

    "grid_coordinates_unique":
        (
            grid_gdf[
                [
                    "grid_lat",
                    "grid_lon",
                ]
            ]
            .drop_duplicates()
            .shape[0]
            ==
            total_cells
        ),
}


print(
    "\n=========================================="
)

print(
    "GEOGRAPHY QUALITY GATE"
)

print(
    "=========================================="
)


for name, result in checks.items():

    print(
        name,
        ":",
        "PASS"
        if result
        else "FAIL",
    )


overall_pass = all(
    checks.values()
)


print(
    "\n=========================================="
)


print(
    "OVERALL STATUS:",
    "PASS"
    if overall_pass
    else "FAIL",
)


print(
    "\nBoundary:"
)

print(
    BOUNDARY_FILE
)


print(
    "\nWeather grid:"
)

print(
    GRID_FILE
)


print(
    "\nLocation registry:"
)

print(
    REGISTRY_FILE
)


print(
    "\nMetadata:"
)

print(
    METADATA_FILE
)


if not overall_pass:

    raise RuntimeError(
        "Bình Định geography registry failed."
    )