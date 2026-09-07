import json
from pathlib import Path

from src.agri_rag.processing.normalize import (
    normalize_text,
    text_sha256,
    NORMALIZATION_METHOD,
)


DOCUMENT_DIR = Path(
    "data/agri_rag/registry/documents"
)

NORMALIZED_DIR = Path(
    "data/agri_rag/normalized"
)

NORMALIZED_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


def load_json(path: Path) -> dict:

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        return json.load(file)


def save_json(
    path: Path,
    data: dict,
):

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )


def normalize_document(
    registry_path: Path,
) -> dict:

    # ======================================================
    # 1. Load Document Registry
    # ======================================================

    document = load_json(
        registry_path
    )

    document_id = document[
        "document_id"
    ]

    extraction_status = document.get(
        "extraction_status"
    )

    # ======================================================
    # 2. Chỉ normalize document extraction SUCCESS
    # ======================================================

    if extraction_status != "SUCCESS":

        document[
            "normalization_status"
        ] = "SKIPPED"

        save_json(
            registry_path,
            document,
        )

        return {
            "document_id": document_id,
            "status": "SKIPPED",
            "reason": (
                f"EXTRACTION_STATUS="
                f"{extraction_status}"
            ),
        }

    # ======================================================
    # 3. Kiểm tra extracted_path
    # ======================================================

    extracted_path_value = (
        document.get(
            "extracted_path"
        )
    )

    if not extracted_path_value:

        document[
            "normalization_status"
        ] = "REVIEW_REQUIRED"

        document[
            "quality_status"
        ] = "REVIEW_REQUIRED"

        document[
            "review_notes"
        ] = (
            "Normalization cannot start "
            "because extracted_path is missing."
        )

        save_json(
            registry_path,
            document,
        )

        return {
            "document_id": document_id,
            "status": "REVIEW_REQUIRED",
            "reason": "EXTRACTED_PATH_MISSING",
        }

    extracted_path = Path(
        extracted_path_value
    )

    if not extracted_path.exists():

        document[
            "normalization_status"
        ] = "REVIEW_REQUIRED"

        document[
            "quality_status"
        ] = "REVIEW_REQUIRED"

        document[
            "review_notes"
        ] = (
            "Extracted file does not exist."
        )

        save_json(
            registry_path,
            document,
        )

        return {
            "document_id": document_id,
            "status": "REVIEW_REQUIRED",
            "reason": "EXTRACTED_FILE_NOT_FOUND",
        }

    # ======================================================
    # 4. Load extracted text
    # ======================================================

    extracted = load_json(
        extracted_path
    )

    original_text = (
        extracted.get("text")
        or ""
    )

    # ======================================================
    # 5. Normalize
    # ======================================================

    normalized_text = normalize_text(
        original_text
    )

    # ======================================================
    # 6. Text quá ngắn → review
    # ======================================================

    if len(normalized_text) < 200:

        document[
            "normalization_status"
        ] = "REVIEW_REQUIRED"

        document[
            "quality_status"
        ] = "REVIEW_REQUIRED"

        document[
            "review_notes"
        ] = (
            "Normalized text is too short "
            "for downstream RAG processing."
        )

        save_json(
            registry_path,
            document,
        )

        return {
            "document_id": document_id,
            "status": "REVIEW_REQUIRED",
            "reason": "NORMALIZED_TEXT_TOO_SHORT",
            "char_count": len(
                normalized_text
            ),
        }

    # ======================================================
    # 7. Save normalized text
    # ======================================================

    normalized_path = (
        NORMALIZED_DIR
        / f"{document_id}.txt"
    )

    normalized_path.write_text(
        normalized_text,
        encoding="utf-8",
    )

    normalized_checksum = (
        text_sha256(
            normalized_text
        )
    )

    # ======================================================
    # 8. Update registry automatically
    # ======================================================

    document[
        "normalized_path"
    ] = str(
        normalized_path
    )

    document[
        "normalized_checksum"
    ] = normalized_checksum

    document[
        "normalization_method"
    ] = NORMALIZATION_METHOD

    document[
        "normalized_char_count"
    ] = len(
        normalized_text
    )

    document[
        "normalization_status"
    ] = "SUCCESS"

    # Vẫn chưa ACCEPTED.
    # Còn metadata + quality gate.
    document[
        "quality_status"
    ] = "PENDING_REVIEW"

    save_json(
        registry_path,
        document,
    )

    return {
        "document_id": document_id,
        "status": "SUCCESS",
        "before_chars": len(
            original_text
        ),
        "after_chars": len(
            normalized_text
        ),
        "normalized_path": str(
            normalized_path
        ),
        "normalized_checksum": (
            normalized_checksum
        ),
    }


def main():

    registry_files = sorted(
        DOCUMENT_DIR.glob(
            "DOC*.json"
        )
    )

    print()
    print("=" * 70)
    print("AGRI RAG - NORMALIZATION")
    print("=" * 70)

    print(
        f"Documents found: "
        f"{len(registry_files)}"
    )

    success_count = 0
    skipped_count = 0
    review_count = 0
    failed_count = 0

    failed_items = []

    for index, registry_path in enumerate(
        registry_files,
        start=1,
    ):

        print()
        print("-" * 70)

        print(
            f"[{index}/{len(registry_files)}] "
            f"{registry_path.stem}"
        )

        try:

            result = normalize_document(
                registry_path
            )

            status = result[
                "status"
            ]

            print(
                f"Status : {status}"
            )

            if status == "SUCCESS":

                success_count += 1

                print(
                    "Before : "
                    f"{result['before_chars']}"
                )

                print(
                    "After  : "
                    f"{result['after_chars']}"
                )

                print(
                    "Output : "
                    f"{result['normalized_path']}"
                )

            elif status == "SKIPPED":

                skipped_count += 1

                print(
                    "Reason : "
                    f"{result['reason']}"
                )

            elif (
                status
                == "REVIEW_REQUIRED"
            ):

                review_count += 1

                print(
                    "Reason : "
                    f"{result['reason']}"
                )

        except Exception as exc:

            failed_count += 1

            failed_items.append({
                "document_id": (
                    registry_path.stem
                ),
                "error": str(exc),
            })

            print(
                f"[FAILED] {exc}"
            )

    # ======================================================
    # SUMMARY
    # ======================================================

    print()
    print()
    print("=" * 70)
    print("NORMALIZATION SUMMARY")
    print("=" * 70)

    print(
        f"Total documents : "
        f"{len(registry_files)}"
    )

    print(
        f"SUCCESS         : "
        f"{success_count}"
    )

    print(
        f"SKIPPED         : "
        f"{skipped_count}"
    )

    print(
        f"REVIEW_REQUIRED : "
        f"{review_count}"
    )

    print(
        f"FAILED          : "
        f"{failed_count}"
    )

    if failed_items:

        print()
        print("FAILED ITEMS")
        print("-" * 70)

        print(
            json.dumps(
                failed_items,
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    main()