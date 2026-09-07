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

DOWNLOAD_REGISTRY_FILE = Path(
    "data/agri_rag/registry/download_registry.csv"
)


def load_seeds():
    """
    Đọc seeds.csv và chỉ nhận các seed hợp lệ.

    Seed hợp lệ phải có dạng:
        SEED001
        SEED002
        ...
    """

    valid_seeds = []

    with SEEDS_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        for line_number, row in enumerate(
            reader,
            start=2,
        ):
            seed_id = (
                row.get("seed_id") or ""
            ).strip()

            # Bỏ dòng rỗng
            if not seed_id:
                print(
                    f"[WARNING] Skip empty seed "
                    f"at CSV line {line_number}"
                )
                continue

            # Kiểm tra format SEEDxxx
            if not (
                seed_id.startswith("SEED")
                and seed_id[4:].isdigit()
            ):
                print(
                    f"[WARNING] Skip invalid seed_id "
                    f"'{seed_id}' "
                    f"at CSV line {line_number}"
                )
                continue

            # Normalize whitespace
            row["seed_id"] = seed_id

            row["source_id"] = (
                row.get("source_id") or ""
            ).strip()

            row["url"] = (
                row.get("url") or ""
            ).strip()

            row["expected_bucket"] = (
                row.get("expected_bucket") or ""
            ).strip()

            row["status"] = (
                row.get("status") or ""
            ).strip()

            # URL bắt buộc
            if not row["url"]:
                print(
                    f"[WARNING] Skip {seed_id}: "
                    "URL is empty"
                )
                continue

            valid_seeds.append(row)

    return valid_seeds


def load_successful_seed_ids():
    """
    Đọc download_registry.csv và lấy các seed
    đã download SUCCESS.
    """

    successful = set()

    if not DOWNLOAD_REGISTRY_FILE.exists():
        return successful

    with DOWNLOAD_REGISTRY_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:
            if row.get("status") == "SUCCESS":
                successful.add(
                    row["seed_id"]
                )

    return successful


def seed_to_document_id(seed_id: str):
    """
    Convert:
        SEED001 -> DOC0001
        SEED012 -> DOC0012
    """

    if not seed_id:
        raise ValueError(
            "seed_id cannot be empty"
        )

    seed_id = seed_id.strip()

    if not seed_id.startswith("SEED"):
        raise ValueError(
            f"Invalid seed_id format: {seed_id}"
        )

    numeric_part = seed_id[4:]

    if not numeric_part.isdigit():
        raise ValueError(
            f"Invalid seed_id format: {seed_id}"
        )

    number = int(numeric_part)

    return f"DOC{number:04d}"


def main():

    seeds = load_seeds()

    successful_seed_ids = (
        load_successful_seed_ids()
    )

    print()
    print("=" * 60)
    print("AGRI RAG - BATCH SEED DOWNLOAD")
    print("=" * 60)

    print(
        f"Total seeds: {len(seeds)}"
    )

    print(
        "Already successful: "
        f"{len(successful_seed_ids)}"
    )

    print()

    success_count = 0
    failed_count = 0
    skipped_count = 0

    failed_items = []

    for index, seed in enumerate(
        seeds,
        start=1,
    ):

        seed_id = seed["seed_id"]

        document_id = (
            seed_to_document_id(
                seed_id
            )
        )

        print()
        print("-" * 60)

        print(
            f"[{index}/{len(seeds)}] "
            f"{seed_id} -> {document_id}"
        )

        print(
            f"Source: {seed['source_id']}"
        )

        print(
            "Expected bucket: "
            f"{seed.get('expected_bucket')}"
        )

        # ----------------------------------------
        # Skip nếu seed đã tải thành công trước đó
        # ----------------------------------------

        if seed_id in successful_seed_ids:

            print(
                "[SKIP] Already downloaded "
                "successfully."
            )

            skipped_count += 1
            continue

        # ----------------------------------------
        # Download
        # ----------------------------------------

        result = download_url(
            url=seed["url"],
            document_id=document_id,
        )

        # ----------------------------------------
        # Registry
        # ----------------------------------------

        upsert_download_registry(
            seed=seed,
            result=result,
        )

        # ----------------------------------------
        # Success
        # ----------------------------------------

        if result.get("success"):

            document = (
                build_document_record(
                    seed=seed,
                    result=result,
                )
            )

            document_path = (
                save_document_record(
                    document
                )
            )

            success_count += 1

            print(
                "[SUCCESS] "
                f"{document_id}"
            )

            print(
                f"File: "
                f"{result['raw_path']}"
            )

            print(
                f"Size: "
                f"{result['file_size_bytes']} bytes"
            )

            print(
                "Document record: "
                f"{document_path}"
            )

        # ----------------------------------------
        # Failed
        # ----------------------------------------

        else:

            failed_count += 1

            error = result.get(
                "error",
                "UNKNOWN_ERROR",
            )

            failed_items.append({
                "seed_id": seed_id,
                "document_id": document_id,
                "url": seed["url"],
                "error": error,
            })

            print(
                "[FAILED] "
                f"{document_id}"
            )

            print(
                f"Error: {error}"
            )

    # ==================================================
    # SUMMARY
    # ==================================================

    print()
    print()
    print("=" * 60)
    print("DOWNLOAD SUMMARY")
    print("=" * 60)

    print(
        f"Total seeds      : {len(seeds)}"
    )

    print(
        f"Skipped existing : {skipped_count}"
    )

    print(
        f"New successes    : {success_count}"
    )

    print(
        f"Failed           : {failed_count}"
    )

    if failed_items:

        print()
        print("FAILED ITEMS")
        print("-" * 60)

        print(
            json.dumps(
                failed_items,
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    main()