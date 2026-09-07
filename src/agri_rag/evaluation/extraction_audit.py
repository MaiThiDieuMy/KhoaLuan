import json
from pathlib import Path
from collections import Counter


DOCUMENT_DIR = Path(
    "data/agri_rag/registry/documents"
)

EXTRACTED_DIR = Path(
    "data/agri_rag/extracted"
)


EXPECTED_KEYWORDS = {
    "DOC0001": [
        "75/2025",
        "thuốc bảo vệ thực vật",
    ],

    "DOC0002": [
        "28/2026",
        "75/2025",
    ],

    "DOC0003": [
        "Danh mục",
        "thuốc bảo vệ thực vật",
    ],

    "DOC0005": [
        "Bình Định",
        "rau cải xanh",
        "phân hữu cơ",
    ],

    "DOC0006": [
        "Tưới nước",
        "rau ăn lá",
    ],

    "DOC0007": [
        "cải ngọt",
        "Tưới nước",
    ],

    "DOC0010": [
        "thủy canh",
        "dung dịch dinh dưỡng",
    ],

    "DOC0012": [
        "Nam Trung Bộ",
    ],
}


def load_json(path: Path):

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        return json.load(file)


def main():

    registry_files = sorted(
        DOCUMENT_DIR.glob(
            "DOC*.json"
        )
    )

    status_counter = Counter()

    issues = []

    print()
    print("=" * 72)
    print("RAG EXTRACTION AUDIT")
    print("=" * 72)

    for registry_path in registry_files:

        document = load_json(
            registry_path
        )

        document_id = document[
            "document_id"
        ]

        status = document.get(
            "extraction_status",
            "UNKNOWN",
        )

        status_counter[
            status
        ] += 1

        extracted_path = document.get(
            "extracted_path"
        )

        print()
        print("-" * 72)
        print(document_id)

        print(
            f"Status     : {status}"
        )

        print(
            "Characters : "
            f"{document.get('extracted_char_count')}"
        )

        print(
            f"Title      : "
            f"{document.get('title')}"
        )

        # =====================================================
        # Không kiểm text đối với OCR_REQUIRED
        # =====================================================

        if status == "OCR_REQUIRED":

            print(
                "Audit      : OCR_REQUIRED"
            )

            continue

        # =====================================================
        # Extracted path
        # =====================================================

        if not extracted_path:

            issues.append({
                "document_id": document_id,
                "reason": "EXTRACTED_PATH_MISSING",
            })

            print(
                "Audit      : FAIL "
                "(missing extracted path)"
            )

            continue

        extracted_file = Path(
            extracted_path
        )

        if not extracted_file.exists():

            issues.append({
                "document_id": document_id,
                "reason": "EXTRACTED_FILE_NOT_FOUND",
            })

            print(
                "Audit      : FAIL "
                "(extracted file not found)"
            )

            continue

        extracted = load_json(
            extracted_file
        )

        text = (
            extracted.get("text")
            or ""
        )

        # =====================================================
        # Text length
        # =====================================================

        if len(text) < 200:

            issues.append({
                "document_id": document_id,
                "reason": "TEXT_TOO_SHORT",
                "char_count": len(text),
            })

        # =====================================================
        # Expected keywords
        # =====================================================

        expected = EXPECTED_KEYWORDS.get(
            document_id,
            [],
        )

        missing_keywords = []

        title = (
            document.get("title")
            or ""
        )

        # Audit relevance trên cả title + body
        searchable_text = (
            title
            + "\n"
            + text
        ).lower()


        for keyword in expected:

            if (
                keyword.lower()
                not in searchable_text
            ):
                missing_keywords.append(
                    keyword
                )

        if missing_keywords:

            issues.append({
                "document_id": document_id,
                "reason": "EXPECTED_KEYWORDS_MISSING",
                "keywords": missing_keywords,
            })

            print(
                "Missing keywords: "
                f"{missing_keywords}"
            )

        # =====================================================
        # Preview
        # =====================================================

        preview = (
            text[:300]
            .replace(
                "\n",
                " ",
            )
        )

        print(
            f"Preview    : {preview}"
        )

        if (
            len(text) >= 200
            and not missing_keywords
        ):
            print(
                "Audit      : PASS"
            )
        else:
            print(
                "Audit      : REVIEW"
            )

    # =========================================================
    # Summary
    # =========================================================

    print()
    print()
    print("=" * 72)
    print("EXTRACTION AUDIT SUMMARY")
    print("=" * 72)

    print()

    for status, count in sorted(
        status_counter.items()
    ):
        print(
            f"{status:<20}: {count}"
        )

    print()
    print(
        f"Issues found       : "
        f"{len(issues)}"
    )

    if issues:

        print()
        print("ISSUES")
        print("-" * 72)

        print(
            json.dumps(
                issues,
                ensure_ascii=False,
                indent=2,
            )
        )

    else:

        print(
            "No extraction issues detected."
        )


if __name__ == "__main__":
    main()