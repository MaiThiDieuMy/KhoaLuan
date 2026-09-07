import csv
import hashlib
from pathlib import Path
from collections import Counter, defaultdict


REGISTRY_FILE = Path(
    "data/agri_rag/registry/download_registry.csv"
)


def sha256_file(path: Path) -> str:
    """
    Tính SHA256 trực tiếp từ file trên ổ đĩa.
    """

    hasher = hashlib.sha256()

    with path.open("rb") as file:
        while True:
            block = file.read(1024 * 1024)

            if not block:
                break

            hasher.update(block)

    return hasher.hexdigest()


def main():

    # =========================================================
    # 1. Kiểm tra registry có tồn tại không
    # =========================================================

    if not REGISTRY_FILE.exists():
        raise FileNotFoundError(
            f"Không tìm thấy registry: {REGISTRY_FILE}"
        )

    # =========================================================
    # 2. Đọc download registry
    # =========================================================

    with REGISTRY_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        rows = list(
            csv.DictReader(file)
        )

    # =========================================================
    # 3. Các biến dùng cho audit
    # =========================================================

    status_counter = Counter()

    file_type_counter = Counter()

    missing_files = []

    suspicious_files = []

    checksum_groups = defaultdict(list)

    successful_documents = []

    # =========================================================
    # 4. Kiểm tra từng document
    # =========================================================

    for row in rows:

        document_id = (
            row.get("document_id") or ""
        ).strip()

        status = (
            row.get("status") or ""
        ).strip()

        status_counter[status] += 1

        # Nếu download FAILED thì không audit raw file
        if status != "SUCCESS":
            continue

        raw_path_string = (
            row.get("raw_path") or ""
        ).strip()

        if not raw_path_string:

            missing_files.append({
                "document_id": document_id,
                "reason": "RAW_PATH_EMPTY",
            })

            continue

        raw_path = Path(
            raw_path_string
        )

        # =====================================================
        # File có tồn tại thật không?
        # =====================================================

        if not raw_path.exists():

            missing_files.append({
                "document_id": document_id,
                "reason": "RAW_FILE_NOT_FOUND",
                "path": str(raw_path),
            })

            continue

        successful_documents.append(
            document_id
        )

        # =====================================================
        # Loại file
        # =====================================================

        extension = (
            raw_path.suffix.lower()
            or "unknown"
        )

        file_type_counter[
            extension
        ] += 1

        # =====================================================
        # File size
        # =====================================================

        file_size = (
            raw_path.stat().st_size
        )

        # dưới 5 KB đáng nghi
        if file_size < 5000:

            suspicious_files.append({
                "document_id": document_id,
                "reason": "FILE_TOO_SMALL",
                "size_bytes": file_size,
                "path": str(raw_path),
            })

        # =====================================================
        # Check checksum
        # =====================================================

        actual_checksum = sha256_file(
            raw_path
        )

        registry_checksum = (
            row.get("checksum") or ""
        ).strip()

        if (
            registry_checksum
            and actual_checksum
            != registry_checksum
        ):

            suspicious_files.append({
                "document_id": document_id,
                "reason": "CHECKSUM_MISMATCH",
                "registry_checksum": registry_checksum,
                "actual_checksum": actual_checksum,
                "path": str(raw_path),
            })

        # =====================================================
        # Gom checksum để tìm duplicate
        # =====================================================

        checksum_groups[
            actual_checksum
        ].append(
            document_id
        )

    # =========================================================
    # 5. Detect duplicate
    # =========================================================

    duplicates = {
        checksum: documents
        for checksum, documents
        in checksum_groups.items()
        if len(documents) > 1
    }

    # =========================================================
    # 6. PRINT REPORT
    # =========================================================

    print()
    print("=" * 70)
    print("RAG DOWNLOAD AUDIT")
    print("=" * 70)

    print()
    print("TOTAL REGISTRY RECORDS")
    print("-" * 70)
    print(len(rows))

    print()
    print("STATUS")
    print("-" * 70)

    if status_counter:
        for status, count in sorted(
            status_counter.items()
        ):
            print(
                f"{status:<25}: {count}"
            )
    else:
        print("None")

    print()
    print("SUCCESSFUL RAW DOCUMENTS")
    print("-" * 70)
    print(len(successful_documents))

    print()
    print("FILE TYPES")
    print("-" * 70)

    if file_type_counter:
        for file_type, count in sorted(
            file_type_counter.items()
        ):
            print(
                f"{file_type:<15}: {count}"
            )
    else:
        print("None")

    print()
    print("MISSING RAW FILES")
    print("-" * 70)

    if missing_files:

        for item in missing_files:
            print(item)

    else:
        print("None")

    print()
    print("SUSPICIOUS FILES")
    print("-" * 70)

    if suspicious_files:

        for item in suspicious_files:
            print(item)

    else:
        print("None")

    print()
    print("RAW CHECKSUM DUPLICATES")
    print("-" * 70)

    if duplicates:

        for checksum, documents in duplicates.items():

            print(
                f"{checksum}"
                f" -> "
                f"{', '.join(documents)}"
            )

    else:
        print("None")

    print()
    print("=" * 70)
    print("AUDIT FINISHED")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()