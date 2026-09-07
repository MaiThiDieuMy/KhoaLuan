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
# REQUIRED LEGAL DOCUMENTS
#
# DOC0003 hiện đã là TT75 Appendix I,
# nên KHÔNG tải Appendix I lần nữa.
# ============================================================

LEGAL_DOCUMENTS = [
    {
        "key": "TT75_MAIN",
        "title": (
            "Thông tư 75/2025/TT-BNNMT - "
            "văn bản chính"
        ),
        "source_id": "S01_PPD",
        "expected_bucket": "B06_PESTICIDE_LEGAL",
        "document_family": "regulation",
        "url": (
            "https://ppd.gov.vn/"
            "FileUpload/Documents/Thuoc%20BVTV/"
            "25.12.30_%20TT%2075.2025.BNNMT.pdf"
        ),
        "notes": (
            "LEGAL_BUNDLE_REQUIRED;"
            "role=BASE_INSTRUMENT_PDF;"
            "instrument=75/2025/TT-BNNMT"
        ),
    },

    {
        "key": "TT75_APPENDIX_II",
        "title": (
            "Thông tư 75/2025/TT-BNNMT - "
            "Phụ lục II danh mục thuốc BVTV cấm sử dụng"
        ),
        "source_id": "S01_PPD",
        "expected_bucket": "B06_PESTICIDE_LEGAL",
        "document_family": "regulatory_attachment",
        "url": (
            "https://sansangxuatkhau.ppd.gov.vn/"
            "FileUpload/Documents/"
            "25.12.30_PL%202%20-%20"
            "Danh%20m%E1%BB%A5c%20"
            "c%E1%BA%A5m%20s%E1%BB%AD%20d%E1%BB%A5ng.pdf"
        ),
        "notes": (
            "LEGAL_BUNDLE_REQUIRED;"
            "role=BASE_BANNED_LIST;"
            "instrument=75/2025/TT-BNNMT"
        ),
    },

    {
        "key": "TT28_MAIN",
        "title": (
            "Thông tư 28/2026/TT-BNNMT - "
            "văn bản sửa đổi Thông tư 75/2025/TT-BNNMT"
        ),
        "source_id": "S01_PPD",
        "expected_bucket": "B06_PESTICIDE_LEGAL",
        "document_family": "regulation",
        "url": (
            "https://ppd.gov.vn/"
            "FileUpload/Documents/Thuoc%20BVTV/"
            "26.07.03_TT%2028-2026%20DM%20"
            "thuoc%20BVTV_260701151148.pdf"
        ),
        "notes": (
            "LEGAL_BUNDLE_REQUIRED;"
            "role=AMENDMENT_INSTRUMENT_PDF;"
            "instrument=28/2026/TT-BNNMT"
        ),
    },

    {
        "key": "TT28_APPENDICES",
        "title": (
            "Thông tư 28/2026/TT-BNNMT - "
            "Phụ lục sửa đổi và bổ sung danh mục thuốc BVTV"
        ),
        "source_id": "S01_PPD",
        "expected_bucket": "B06_PESTICIDE_LEGAL",
        "document_family": "regulatory_attachment",
        "url": (
            "https://ppd.gov.vn/"
            "FileUpload/Documents/Thuoc%20BVTV/"
            "26.07.03_PL%20TT28__"
            "01072026152914_signed.pdf"
        ),
        "notes": (
            "LEGAL_BUNDLE_REQUIRED;"
            "role=AMENDMENT_APPENDICES;"
            "instrument=28/2026/TT-BNNMT"
        ),
    },
]


# ============================================================
# HELPERS
# ============================================================

def read_seeds():
    if not SEEDS_FILE.exists():
        raise FileNotFoundError(
            f"Seeds file not found: {SEEDS_FILE}"
        )

    with SEEDS_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        fieldnames = (
            reader.fieldnames
            or []
        )

        rows = list(reader)

    return fieldnames, rows


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


def find_template(
    rows: list,
):
    """
    Dùng một seed B06 của PPD hiện có làm template.

    Như vậy nếu seeds.csv của project có thêm các cột
    ngoài 4 cột cơ bản thì vẫn giữ được cấu trúc hiện tại.
    """

    for row in rows:

        if (
            (
                row.get("source_id")
                or ""
            ).strip()
            == "S01_PPD"
            and
            (
                row.get(
                    "expected_bucket"
                )
                or ""
            ).strip()
            == "B06_PESTICIDE_LEGAL"
        ):
            return row

    if rows:
        return rows[0]

    return None


def set_if_column_exists(
    row: dict,
    fieldnames: list,
    candidate_names: list,
    value,
):
    for name in candidate_names:

        if name in fieldnames:
            row[name] = value


# ============================================================
# MAIN
# ============================================================

def main():

    fieldnames, rows = (
        read_seeds()
    )

    print()
    print("=" * 78)
    print("ADD LEGAL BUNDLE SEEDS")
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

    required_columns = {
        "seed_id",
        "source_id",
        "url",
        "expected_bucket",
    }

    missing_columns = (
        required_columns
        - set(fieldnames)
    )

    if missing_columns:

        raise ValueError(
            "seeds.csv is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    template = find_template(
        rows
    )

    if template is None:

        raise ValueError(
            "Cannot find a seed row to use as template."
        )

    # ========================================================
    # Existing URLs
    # ========================================================

    existing_urls = {
        (
            row.get("url")
            or ""
        ).strip()
        for row in rows
        if (
            row.get("url")
            or ""
        ).strip()
    }

    # ========================================================
    # Find maximum current SEED number
    # ========================================================

    numbers = []

    for row in rows:

        number = extract_seed_number(
            row.get(
                "seed_id"
            )
        )

        if number is not None:
            numbers.append(
                number
            )

    next_number = (
        max(numbers)
        if numbers
        else 0
    )

    added = []
    skipped = []

    # ========================================================
    # Build rows
    # ========================================================

    for legal_doc in (
        LEGAL_DOCUMENTS
    ):

        url = legal_doc[
            "url"
        ]

        if url in existing_urls:

            skipped.append({
                "key":
                    legal_doc["key"],

                "reason":
                    "URL_ALREADY_EXISTS",
            })

            continue

        next_number += 1

        new_row = deepcopy(
            template
        )

        # Ensure every CSV field exists
        new_row = {
            field:
                new_row.get(
                    field,
                    "",
                )
            for field in fieldnames
        }

        new_row[
            "seed_id"
        ] = (
            f"SEED{next_number:03d}"
        )

        new_row[
            "source_id"
        ] = legal_doc[
            "source_id"
        ]

        new_row[
            "url"
        ] = url

        new_row[
            "expected_bucket"
        ] = legal_doc[
            "expected_bucket"
        ]

        # ----------------------------------------------------
        # Optional columns:
        # tự điền nếu project hiện có.
        # ----------------------------------------------------

        set_if_column_exists(
            new_row,
            fieldnames,
            [
                "title",
                "name",
                "document_title",
            ],
            legal_doc[
                "title"
            ],
        )

        set_if_column_exists(
            new_row,
            fieldnames,
            [
                "description",
            ],
            legal_doc[
                "title"
            ],
        )

        set_if_column_exists(
            new_row,
            fieldnames,
            [
                "notes",
                "note",
            ],
            legal_doc[
                "notes"
            ],
        )

        set_if_column_exists(
            new_row,
            fieldnames,
            [
                "document_family",
            ],
            legal_doc[
                "document_family"
            ],
        )

        # Nếu CSV có expected_keywords thì dùng keyword
        # chung, không copy keyword quá đặc thù từ template.
        set_if_column_exists(
            new_row,
            fieldnames,
            [
                "expected_keywords",
            ],
            "thuốc bảo vệ thực vật",
        )

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
                legal_doc[
                    "key"
                ],

            "url":
                url,
        })

    # ========================================================
    # Save only when something was added
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
    # Output
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
        print("ADDED SEEDS")

        for item in added:

            print(
                f"{item['seed_id']} "
                f"→ {item['key']}"
            )

    if skipped:

        print()
        print("SKIPPED")

        for item in skipped:

            print(
                f"{item['key']} "
                f"→ {item['reason']}"
            )

    print()
    print(
        "Legal seed update finished."
    )


if __name__ == "__main__":
    main()