import json
from pathlib import Path

from src.agri_rag.processing.extract_html import (
    extract_html,
)

from src.agri_rag.processing.extract_pdf import (
    extract_pdf,
)


DOCUMENT_REGISTRY_DIR = Path(
    "data/agri_rag/registry/documents"
)

EXTRACTED_DIR = Path(
    "data/agri_rag/extracted"
)

EXTRACTED_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


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


def process_document(
    registry_path: Path,
):
    # ======================================================
    # 1. Load DocumentRecord JSON
    # ======================================================

    with registry_path.open(
        "r",
        encoding="utf-8",
    ) as file:

        document = json.load(file)

    document_id = document[
        "document_id"
    ]

    raw_path_value = document.get(
        "raw_path"
    )

    if not raw_path_value:
        raise ValueError(
            f"{document_id}: raw_path missing"
        )

    raw_path = Path(
        raw_path_value
    )

    if not raw_path.exists():
        raise FileNotFoundError(
            f"{document_id}: "
            f"raw file not found: "
            f"{raw_path}"
        )

    extension = (
        raw_path.suffix.lower()
    )

    # ======================================================
    # 2. Extract
    # ======================================================

    if extension == ".html":

        result = extract_html(
            str(raw_path)
        )

        extraction_status = (
            result["status"]
        )

    elif extension == ".pdf":

        result = extract_pdf(
            str(raw_path)
        )

        extraction_status = (
            result["status"]
        )

    else:
        raise ValueError(
            f"{document_id}: "
            f"unsupported extension "
            f"{extension}"
        )

    # ======================================================
    # 3. Save extracted result
    # ======================================================

    extracted_path = (
        EXTRACTED_DIR
        / f"{document_id}.json"
    )

    extracted_record = {
        "document_id": document_id,
        "source_id": document.get(
            "source_id"
        ),
        "url": document.get(
            "url"
        ),
        **result,
    }

    save_json(
        extracted_path,
        extracted_record,
    )

    # ======================================================
    # 4. Update Document Registry
    # ======================================================

    document[
        "extracted_path"
    ] = str(extracted_path)

    document[
        "extraction_method"
    ] = result.get(
        "extraction_method"
    )

    document[
        "extracted_char_count"
    ] = result.get(
        "char_count",
        0,
    )

    document[
        "extraction_status"
    ] = extraction_status

    # ======================================================
    # Update quality status automatically
    # ======================================================

    if extraction_status == "SUCCESS":

        # Chưa được ACCEPTED.
        # Còn phải qua normalize + metadata + quality gate.
        document["quality_status"] = "PENDING_REVIEW"

    elif extraction_status == "OCR_REQUIRED":

        document["quality_status"] = "REVIEW_REQUIRED"

        document["review_notes"] = (
            "Extraction requires OCR. "
            "Raw document is preserved. "
            "Document is not ready for RAG indexing."
        )

    elif extraction_status == "FAILED":

        document["quality_status"] = "REVIEW_REQUIRED"

        document["review_notes"] = (
            "Extraction failed. "
            "Manual investigation required."
        )

    # HTML có thể lấy title sơ bộ
    extracted_title = result.get(
        "title"
    )

    if (
        extracted_title
        and not document.get("title")
    ):
        document[
            "title"
        ] = extracted_title

    save_json(
        registry_path,
        document,
    )

    return {
        "document_id": document_id,
        "extension": extension,
        "status": extraction_status,
        "char_count": result.get(
            "char_count",
            0,
        ),
        "extracted_path": str(
            extracted_path
        ),
    }


def main():

    registry_files = sorted(
        DOCUMENT_REGISTRY_DIR.glob(
            "DOC*.json"
        )
    )

    print()
    print("=" * 70)
    print("AGRI RAG - CONTENT EXTRACTION")
    print("=" * 70)

    print(
        f"Documents found: "
        f"{len(registry_files)}"
    )

    print()

    success_count = 0
    ocr_required_count = 0
    failed_count = 0

    failed_items = []

    for index, registry_path in enumerate(
        registry_files,
        start=1,
    ):

        print("-" * 70)

        print(
            f"[{index}/{len(registry_files)}] "
            f"{registry_path.stem}"
        )

        try:

            result = process_document(
                registry_path
            )

            status = result[
                "status"
            ]

            print(
                f"Type       : "
                f"{result['extension']}"
            )

            print(
                f"Status     : "
                f"{status}"
            )

            print(
                f"Characters : "
                f"{result['char_count']}"
            )

            print(
                f"Output     : "
                f"{result['extracted_path']}"
            )

            if status == "SUCCESS":

                success_count += 1

            elif (
                status
                == "OCR_REQUIRED"
            ):

                ocr_required_count += 1

        except Exception as exc:

            failed_count += 1

            failed_items.append({
                "document": (
                    registry_path.stem
                ),
                "error": str(exc),
            })

            print(
                f"[FAILED] {exc}"
            )

        print()

    # ======================================================
    # SUMMARY
    # ======================================================

    print()
    print("=" * 70)
    print("EXTRACTION SUMMARY")
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
        f"OCR_REQUIRED    : "
        f"{ocr_required_count}"
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