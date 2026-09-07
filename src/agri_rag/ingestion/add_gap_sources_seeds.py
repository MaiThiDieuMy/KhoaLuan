import csv
import re
from copy import deepcopy
from pathlib import Path


# ============================================================
# PATH
# ============================================================

SEEDS_FILE = Path(
    "data/agri_rag/registry/seeds.csv"
)


# ============================================================
# TARGETED GAP SOURCES
#
# Chỉ bổ sung những nguồn phục vụ gap đã được
# coverage_audit phát hiện.
#
# Không crawl chung chung.
# ============================================================

TARGETED_SOURCES = [

    # ========================================================
    # VIETNAMESE OFFICIAL SOURCE
    #
    # One large multi-crop PDF.
    #
    # Later we DO NOT accept the whole PDF directly.
    # It will be sectioned into:
    #   - Rau mùi
    #   - Cải cúc
    # ========================================================

    {
        "key":
            "KONTUM_ANNUAL_CROP_PROCESSES",

        "source_id":
            "S04_VBPL_KONTUM",

        "url":
            (
                "https://vbpl.vn/FileData/TW/Lists/"
                "vbpq/Attachments/173075/"
                "VanBanGoc_81.2024.QD.UBND.%20"
                "PL%2001%2012.2024%20"
                "Phu%20luc%20cay%20hang%20nam.pdf"
            ),

        "expected_bucket":
            "B01_CROP_PROFILE",
    },


    # ========================================================
    # CORIANDER - INDEPENDENT UNIVERSITY SOURCE
    # ========================================================

    {
        "key":
            "TNAU_CORIANDER",

        "source_id":
            "S05_TNAU",

        "url":
            (
                "https://agritech.tnau.ac.in/"
                "horticulture/"
                "horti_spice%20crops_corinader.html"
            ),

        "expected_bucket":
            "B01_CROP_PROFILE",
    },


    # ========================================================
    # CROWN DAISY / TẦN Ô - INDEPENDENT UNIVERSITY SOURCE
    # ========================================================

    {
        "key":
            "UF_IFAS_TONG_HAO",

        "source_id":
            "S06_UF_IFAS",

        "url":
            (
                "https://ask.ifas.ufl.edu/"
                "publication/HS1276"
            ),

        "expected_bucket":
            "B01_CROP_PROFILE",
    },
]


# ============================================================
# IO
# ============================================================

def read_seeds():

    if not SEEDS_FILE.exists():

        raise FileNotFoundError(
            f"Seeds file not found: "
            f"{SEEDS_FILE}"
        )

    with SEEDS_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(
            file
        )

        fieldnames = (
            reader.fieldnames
            or []
        )

        rows = list(
            reader
        )

    return (
        fieldnames,
        rows,
    )


# ============================================================
# SEED ID
# ============================================================

def extract_seed_number(
    seed_id: str,
):

    match = re.fullmatch(
        r"SEED(\d+)",
        (
            seed_id
            or ""
        ).strip(),
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    return int(
        match.group(1)
    )


# ============================================================
# TEMPLATE
# ============================================================

def find_template(
    rows: list,
):

    if not rows:
        return None

    return rows[0]


# ============================================================
# MAIN
# ============================================================

def main():

    (
        fieldnames,
        rows,
    ) = read_seeds()

    print()
    print("=" * 78)
    print(
        "ADD TARGETED KNOWLEDGE GAP SEEDS"
    )
    print("=" * 78)

    print(
        f"Seeds file      : "
        f"{SEEDS_FILE}"
    )

    print(
        f"Existing seeds  : "
        f"{len(rows)}"
    )

    print(
        f"Columns         : "
        f"{fieldnames}"
    )

    # ========================================================
    # REQUIRED COLUMNS
    # ========================================================

    required_columns = {
        "seed_id",
        "source_id",
        "url",
        "expected_bucket",
    }

    missing_columns = (
        required_columns
        - set(
            fieldnames
        )
    )

    if missing_columns:

        raise ValueError(
            "seeds.csv missing required columns: "
            f"{sorted(missing_columns)}"
        )

    # ========================================================
    # TEMPLATE
    # ========================================================

    template = find_template(
        rows
    )

    if template is None:

        raise ValueError(
            "Cannot find seed template."
        )

    # ========================================================
    # EXISTING URLS
    # ========================================================

    existing_urls = {

        (
            row.get(
                "url"
            )
            or ""
        ).strip()

        for row in rows

        if (
            row.get(
                "url"
            )
            or ""
        ).strip()
    }

    # ========================================================
    # CURRENT MAX SEED NUMBER
    # ========================================================

    seed_numbers = []

    for row in rows:

        number = (
            extract_seed_number(
                row.get(
                    "seed_id"
                )
            )
        )

        if number is not None:

            seed_numbers.append(
                number
            )

    next_number = (
        max(
            seed_numbers
        )
        if seed_numbers
        else 0
    )

    added = []
    skipped = []

    # ========================================================
    # ADD
    # ========================================================

    for item in (
        TARGETED_SOURCES
    ):

        url = (
            item[
                "url"
            ]
        )

        if url in existing_urls:

            skipped.append({

                "key":
                    item[
                        "key"
                    ],

                "reason":
                    "URL_ALREADY_EXISTS",
            })

            continue

        next_number += 1

        new_row = deepcopy(
            template
        )

        # Ensure output row exactly follows
        # the existing CSV schema.
        new_row = {

            field:
                new_row.get(
                    field,
                    ""
                )

            for field
            in fieldnames
        }

        new_row[
            "seed_id"
        ] = (
            f"SEED{next_number:03d}"
        )

        new_row[
            "source_id"
        ] = (
            item[
                "source_id"
            ]
        )

        new_row[
            "url"
        ] = url

        new_row[
            "expected_bucket"
        ] = (
            item[
                "expected_bucket"
            ]
        )

        # New seeds must be available
        # to downloader.
        if "status" in fieldnames:

            new_row[
                "status"
            ] = ""

        rows.append(
            new_row
        )

        existing_urls.add(
            url
        )

        added.append({

            "seed_id":
                new_row[
                    "seed_id"
                ],

            "key":
                item[
                    "key"
                ],

            "source_id":
                item[
                    "source_id"
                ],
        })

    # ========================================================
    # SAVE
    # ========================================================

    if added:

        with SEEDS_FILE.open(
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames,
            )

            writer.writeheader()

            writer.writerows(
                rows
            )

    # ========================================================
    # OUTPUT
    # ========================================================

    print()
    print("-" * 78)

    print(
        f"Added           : "
        f"{len(added)}"
    )

    print(
        f"Already present : "
        f"{len(skipped)}"
    )

    print(
        f"Total seeds now : "
        f"{len(rows)}"
    )

    if added:

        print()
        print("ADDED")

        for item in added:

            print(
                f"{item['seed_id']} "
                f"→ "
                f"{item['key']} "
                f"({item['source_id']})"
            )

    if skipped:

        print()
        print("SKIPPED")

        for item in skipped:

            print(
                f"{item['key']} "
                f"→ "
                f"{item['reason']}"
            )

    print()
    print(
        "Targeted seed update finished."
    )


if __name__ == "__main__":
    main()