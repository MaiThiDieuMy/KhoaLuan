import csv
import json
from pathlib import Path

from src.agri_rag.schemas.document import DocumentRecord


REGISTRY_DIR = Path("data/agri_rag/registry")

DOWNLOAD_REGISTRY_FILE = (
    REGISTRY_DIR / "download_registry.csv"
)

DOCUMENT_REGISTRY_DIR = (
    REGISTRY_DIR / "documents"
)


DOWNLOAD_FIELDS = [
    "document_id",
    "seed_id",
    "source_id",
    "requested_url",
    "final_url",
    "expected_bucket",
    "http_status",
    "content_type",
    "file_size_bytes",
    "checksum",
    "raw_path",
    "status",
    "error",
]


def upsert_download_registry(
    seed: dict,
    result: dict,
):
    """
    Ghi kết quả download vào download_registry.csv.

    Nếu document_id đã tồn tại thì cập nhật record cũ,
    tránh tạo duplicate khi chạy test nhiều lần.
    """

    REGISTRY_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    document_id = result["document_id"]

    new_row = {
        "document_id": document_id,
        "seed_id": seed["seed_id"],
        "source_id": seed["source_id"],
        "requested_url": result.get(
            "requested_url",
            seed["url"],
        ),
        "final_url": result.get(
            "final_url",
            "",
        ),
        "expected_bucket": seed.get(
            "expected_bucket",
            "",
        ),
        "http_status": result.get(
            "http_status",
            "",
        ),
        "content_type": result.get(
            "content_type",
            "",
        ),
        "file_size_bytes": result.get(
            "file_size_bytes",
            "",
        ),
        "checksum": result.get(
            "checksum",
            "",
        ),
        "raw_path": result.get(
            "raw_path",
            "",
        ),
        "status": (
            "SUCCESS"
            if result.get("success")
            else "FAILED"
        ),
        "error": result.get(
            "error",
            "",
        ),
    }

    existing_rows = []

    if DOWNLOAD_REGISTRY_FILE.exists():
        with DOWNLOAD_REGISTRY_FILE.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:

            reader = csv.DictReader(file)

            for row in reader:
                if (
                    row["document_id"]
                    != document_id
                ):
                    existing_rows.append(row)

    existing_rows.append(new_row)

    with DOWNLOAD_REGISTRY_FILE.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=DOWNLOAD_FIELDS,
        )

        writer.writeheader()
        writer.writerows(existing_rows)


def build_document_record(
    seed: dict,
    result: dict,
) -> DocumentRecord:
    """
    Chuyển seed + download result thành DocumentRecord.

    Lưu ý:
    expected_bucket từ seed mới chỉ là gợi ý.
    Chưa đưa vào buckets chính thức trước khi review metadata.
    """

    return DocumentRecord(
        document_id=result["document_id"],

        source_id=seed["source_id"],

        url=result.get(
            "final_url",
            seed["url"],
        ),

        content_type=result.get(
            "content_type"
        ),

        # Bucket chính thức sẽ xác nhận
        # ở Metadata / Quality Review.
        buckets=[],

        crop_entities=[],

        raw_path=result.get(
            "raw_path"
        ),

        checksum=result.get(
            "checksum"
        ),

        extraction_status="PENDING",

        quality_status="PENDING_REVIEW",

        review_notes=(
            f"seed_id={seed['seed_id']}; "
            f"expected_bucket="
            f"{seed.get('expected_bucket', '')}"
        ),
    )


def save_document_record(
    document: DocumentRecord,
):
    """
    Lưu DocumentRecord thành JSON.
    """

    DOCUMENT_REGISTRY_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        DOCUMENT_REGISTRY_DIR
        / f"{document.document_id}.json"
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            document.to_dict(),
            file,
            ensure_ascii=False,
            indent=2,
        )

    return output_path