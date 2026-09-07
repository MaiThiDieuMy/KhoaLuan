import json
from pathlib import Path
from collections import Counter

from src.agri_rag.processing.normalize import (
    normalize_text,
    text_sha256,
)


DOCUMENT_DIR = Path(
    "data/agri_rag/registry/documents"
)


EXPECTED_KEYWORDS = {
    "DOC0001": [
        "75/2025/TT-BNNMT",
        "thuốc bảo vệ thực vật",
    ],

    "DOC0002": [
        "28/2026/TT-BNNMT",
        "75/2025/TT-BNNMT",
    ],

    "DOC0003": [
        "DANH MỤC",
        "THUỐC BẢO VỆ THỰC VẬT",
    ],

    "DOC0005": [
        "Bình Định",
        "cải xanh",
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
        "NAM TRUNG BỘ",
    ],
}


def load_json(path: Path) -> dict:

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
    print("=" * 74)
    print("RAG NORMALIZATION AUDIT")
    print("=" * 74)

    for registry_path in registry_files:

        document = load_json(
            registry_path
        )

        document_id = document[
            "document_id"
        ]

        extraction_status = (
            document.get(
                "extraction_status"
            )
        )

        normalization_status = (
            document.get(
                "normalization_status",
                "MISSING",
            )
        )

        status_counter[
            normalization_status
        ] += 1

        print()
        print("-" * 74)

        print(document_id)

        print(
            "Extraction    : "
            f"{extraction_status}"
        )

        print(
            "Normalization : "
            f"{normalization_status}"
        )

        # ==================================================
        # Document chưa extract được
        # ==================================================

        if extraction_status != "SUCCESS":

            if (
                normalization_status
                != "SKIPPED"
            ):

                issues.append({
                    "document_id":
                        document_id,

                    "reason":
                        "EXPECTED_NORMALIZATION_SKIPPED",
                })

                print(
                    "Audit          : REVIEW"
                )

            else:

                print(
                    "Audit          : SKIPPED_OK"
                )

            continue

        # ==================================================
        # Extraction SUCCESS thì normalization phải SUCCESS
        # ==================================================

        if (
            normalization_status
            != "SUCCESS"
        ):

            issues.append({
                "document_id":
                    document_id,

                "reason":
                    "NORMALIZATION_NOT_SUCCESS",
            })

            print(
                "Audit          : REVIEW"
            )

            continue

        # ==================================================
        # Paths
        # ==================================================

        extracted_path_value = (
            document.get(
                "extracted_path"
            )
        )

        normalized_path_value = (
            document.get(
                "normalized_path"
            )
        )

        if not extracted_path_value:

            issues.append({
                "document_id":
                    document_id,

                "reason":
                    "EXTRACTED_PATH_MISSING",
            })

            print(
                "Audit          : REVIEW"
            )

            continue

        if not normalized_path_value:

            issues.append({
                "document_id":
                    document_id,

                "reason":
                    "NORMALIZED_PATH_MISSING",
            })

            print(
                "Audit          : REVIEW"
            )

            continue

        extracted_path = Path(
            extracted_path_value
        )

        normalized_path = Path(
            normalized_path_value
        )

        if not extracted_path.exists():

            issues.append({
                "document_id":
                    document_id,

                "reason":
                    "EXTRACTED_FILE_NOT_FOUND",
            })

            print(
                "Audit          : REVIEW"
            )

            continue

        if not normalized_path.exists():

            issues.append({
                "document_id":
                    document_id,

                "reason":
                    "NORMALIZED_FILE_NOT_FOUND",
            })

            print(
                "Audit          : REVIEW"
            )

            continue

        # ==================================================
        # Load contents
        # ==================================================

        extracted = load_json(
            extracted_path
        )

        extracted_text = (
            extracted.get("text")
            or ""
        )

        normalized_text = (
            normalized_path.read_text(
                encoding="utf-8"
            )
        )

        before_chars = len(
            extracted_text
        )

        after_chars = len(
            normalized_text
        )

        ratio = (
            after_chars / before_chars
            if before_chars
            else 0
        )

        print(
            f"Before chars   : "
            f"{before_chars}"
        )

        print(
            f"After chars    : "
            f"{after_chars}"
        )

        print(
            f"Retention      : "
            f"{ratio:.2%}"
        )

        # ==================================================
        # Empty / excessive loss
        # ==================================================

        if after_chars < 200:

            issues.append({
                "document_id":
                    document_id,

                "reason":
                    "NORMALIZED_TEXT_TOO_SHORT",

                "char_count":
                    after_chars,
            })

        # Safe normalization có thể bỏ nhiều whitespace
        # ở PDF, nhưng không nên mất phần lớn nội dung.
        if ratio < 0.75:

            issues.append({
                "document_id":
                    document_id,

                "reason":
                    "EXCESSIVE_TEXT_REDUCTION",

                "retention_ratio":
                    ratio,
            })

        # ==================================================
        # Deterministic check
        # ==================================================

        expected_normalized = (
            normalize_text(
                extracted_text
            )
        )

        if (
            expected_normalized
            != normalized_text
        ):

            issues.append({
                "document_id":
                    document_id,

                "reason":
                    "NORMALIZATION_NOT_REPRODUCIBLE",
            })

        # ==================================================
        # Checksum
        # ==================================================

        actual_checksum = (
            text_sha256(
                normalized_text
            )
        )

        registry_checksum = (
            document.get(
                "normalized_checksum"
            )
        )

        if (
            not registry_checksum
            or actual_checksum
            != registry_checksum
        ):

            issues.append({
                "document_id":
                    document_id,

                "reason":
                    "NORMALIZED_CHECKSUM_MISMATCH",
            })

        # ==================================================
        # Character count registry
        # ==================================================

        registry_char_count = (
            document.get(
                "normalized_char_count"
            )
        )

        if (
            registry_char_count
            != after_chars
        ):

            issues.append({
                "document_id":
                    document_id,

                "reason":
                    "NORMALIZED_CHAR_COUNT_MISMATCH",

                "registry":
                    registry_char_count,

                "actual":
                    after_chars,
            })

        # ==================================================
        # Expected keywords
        # ==================================================

        searchable = (
            (
                document.get(
                    "title"
                )
                or ""
            )
            + "\n"
            + normalized_text
        ).lower()

        missing_keywords = []

        for keyword in (
            EXPECTED_KEYWORDS.get(
                document_id,
                [],
            )
        ):

            if (
                keyword.lower()
                not in searchable
            ):

                missing_keywords.append(
                    keyword
                )

        if missing_keywords:

            issues.append({
                "document_id":
                    document_id,

                "reason":
                    "EXPECTED_KEYWORDS_MISSING",

                "keywords":
                    missing_keywords,
            })

        document_issues = [
            issue
            for issue in issues
            if (
                issue["document_id"]
                == document_id
            )
        ]

        if document_issues:

            print(
                "Audit          : REVIEW"
            )

        else:

            print(
                "Audit          : PASS"
            )

    # ======================================================
    # SUMMARY
    # ======================================================

    print()
    print()
    print("=" * 74)
    print("NORMALIZATION AUDIT SUMMARY")
    print("=" * 74)

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
        print("-" * 74)

        print(
            json.dumps(
                issues,
                ensure_ascii=False,
                indent=2,
            )
        )

    else:

        print(
            "No normalization issues detected."
        )


if __name__ == "__main__":
    main()