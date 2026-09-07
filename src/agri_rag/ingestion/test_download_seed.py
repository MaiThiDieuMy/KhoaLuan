import csv
import json
from pathlib import Path

from src.agri_rag.ingestion.download import (
    download_url,
)

from src.agri_rag.ingestion.registry import (
    upsert_download_registry,
    build_document_record,
    save_document_record,
)


SEEDS_FILE = Path(
    "data/agri_rag/registry/seeds.csv"
)


def get_seed(
    seed_id: str,
):
    with SEEDS_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            if row["seed_id"] == seed_id:
                return row

    raise ValueError(
        f"Không tìm thấy seed: {seed_id}"
    )


# ============================================================
# 1. READ SEED
# ============================================================

seed = get_seed("SEED001")

print()
print("====================================")
print("SEED FOUND")
print("====================================")

print(
    json.dumps(
        seed,
        ensure_ascii=False,
        indent=2,
    )
)


# ============================================================
# 2. DOWNLOAD
# ============================================================

result = download_url(
    url=seed["url"],
    document_id="DOC0001",
)

print()
print("====================================")
print("DOWNLOAD RESULT")
print("====================================")

print(
    json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
    )
)


# ============================================================
# 3. WRITE DOWNLOAD REGISTRY
# ============================================================

upsert_download_registry(
    seed=seed,
    result=result,
)

print()
print(
    "[OK] Download registry updated"
)


# ============================================================
# 4. CREATE DOCUMENT RECORD
# ============================================================

if result.get("success"):

    document = build_document_record(
        seed=seed,
        result=result,
    )

    document_path = save_document_record(
        document
    )

    print(
        f"[OK] Document record saved: "
        f"{document_path}"
    )

    print()

    print("====================================")
    print("DOCUMENT RECORD")
    print("====================================")

    print(
        json.dumps(
            document.to_dict(),
            ensure_ascii=False,
            indent=2,
        )
    )

else:

    print()
    print(
        "[WARNING] Download failed. "
        "DocumentRecord was not created."
    )