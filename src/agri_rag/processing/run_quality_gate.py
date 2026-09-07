import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml


# ============================================================
# PATHS
# ============================================================

DOCUMENT_DIR = Path(
    "data/agri_rag/registry/documents"
)

SOURCE_CONFIG_FILE = Path(
    "src/agri_rag/config/approved_sources.yaml"
)

REGISTRY_DIR = Path(
    "data/agri_rag/registry"
)

ACCEPTED_DIR = Path(
    "data/agri_rag/accepted"
)

REVIEW_DIR = Path(
    "data/agri_rag/review"
)

REJECTED_DIR = Path(
    "data/agri_rag/rejected"
)


QUALITY_REPORT_FILE = (
    REGISTRY_DIR
    / "quality_report.csv"
)

REVIEW_QUEUE_FILE = (
    REGISTRY_DIR
    / "review_queue.csv"
)

ACCEPTED_MANIFEST_FILE = (
    REGISTRY_DIR
    / "accepted_manifest.jsonl"
)

REVIEW_MANIFEST_FILE = (
    REGISTRY_DIR
    / "review_manifest.jsonl"
)

REJECTED_MANIFEST_FILE = (
    REGISTRY_DIR
    / "rejected_manifest.jsonl"
)


# ============================================================
# QUALITY DECISIONS
# ============================================================

ACCEPTED = "ACCEPTED"

REVIEW_REQUIRED = (
    "REVIEW_REQUIRED"
)

REJECTED = "REJECTED"


# ============================================================
# DOCUMENT FAMILIES
# ============================================================

LEGAL_FAMILIES = {
    "regulation",
    "regulatory_attachment",
}

MULTI_TOPIC_FAMILIES = {
    "extension_bulletin",
    "conference_proceedings",
}


# ============================================================
# IO
# ============================================================

def load_json(
    path: Path,
) -> dict:

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


def load_yaml(
    path: Path,
) -> dict:

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        return (
            yaml.safe_load(file)
            or {}
        )


def write_jsonl(
    path: Path,
    records: list,
):

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:

        for record in records:

            file.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
            )

            file.write("\n")


# ============================================================
# OUTPUT DIRECTORY SETUP
# ============================================================

def prepare_output_directories():
    """
    Chỉ xóa các snapshot DOC*.json
    do Quality Gate tạo ở lần chạy trước.

    KHÔNG xóa:
    - raw
    - extracted
    - normalized
    - registry document gốc
    """

    for directory in [
        ACCEPTED_DIR,
        REVIEW_DIR,
        REJECTED_DIR,
    ]:

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        for old_file in directory.glob(
            "DOC*.json"
        ):

            old_file.unlink()


# ============================================================
# FINAL BUCKETS
# ============================================================

def determine_final_buckets(
    document: dict,
):
    """
    Chỉ ACCEPTED documents mới có buckets chính thức.

    suggested_buckets là metadata candidate.
    buckets là metadata được Quality Gate cho phép downstream dùng.
    """

    suggested = set(
        document.get(
            "suggested_buckets"
        )
        or []
    )

    family = document.get(
        "document_family"
    )

    # --------------------------------------------------------
    # Legal documents:
    #
    # Khi chưa Legal Validation thì chưa ACCEPT nên hàm này
    # thường chưa được dùng.
    #
    # Nếu sau này legal document được approve,
    # final bucket chủ yếu là B06.
    # --------------------------------------------------------

    if family in LEGAL_FAMILIES:

        if (
            "B06_PESTICIDE_LEGAL"
            in suggested
        ):

            return [
                "B06_PESTICIDE_LEGAL"
            ]

        return []

    # --------------------------------------------------------
    # Các tài liệu kỹ thuật:
    # giữ các bucket đã được metadata suggest.
    # --------------------------------------------------------

    return sorted(
        suggested
    )


# ============================================================
# CHUNKING STRATEGY
# ============================================================

def determine_chunking_strategy(
    document: dict,
):

    family = document.get(
        "document_family"
    )

    if family in {
        "extension_bulletin",
        "conference_proceedings",
    }:

        return "SECTION_LEVEL"

    if family in {
        "regulation",
        "regulatory_attachment",
    }:

        return "LEGAL_STRUCTURE"

    return "DOCUMENT_STRUCTURE"


# ============================================================
# QUALITY DECISION
# ============================================================

def evaluate_quality(
    document: dict,
    source_config: dict,
):
    """
    Quyết định document-level quality.

    Không dùng LLM.
    Không sửa nội dung.
    Không xóa raw document.

    Output:
        decision
        reasons
        chunking_strategy
    """

    reasons = []

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
            "normalization_status"
        )
    )

    metadata_status = (
        document.get(
            "metadata_status"
        )
    )

    family = (
        document.get(
            "document_family"
        )
    )

    knowledge_scope = (
        document.get(
            "knowledge_scope"
        )
    )

    crop_entities = (
        document.get(
            "crop_entities"
        )
        or []
    )

    source_id = (
        document.get(
            "source_id"
        )
    )

    source_info = (
        source_config.get(
            source_id
        )
    )

    chunking_strategy = (
        determine_chunking_strategy(
            document
        )
    )

    # ========================================================
    # 1. EXTRACTION GATE
    # ========================================================

    if extraction_status != "SUCCESS":

        if (
            extraction_status
            == "OCR_REQUIRED"
        ):

            reasons.append(
                "OCR_REQUIRED"
            )

        else:

            reasons.append(
                "EXTRACTION_NOT_SUCCESS"
            )

        return (
            REVIEW_REQUIRED,
            reasons,
            chunking_strategy,
        )

    # ========================================================
    # 2. NORMALIZATION GATE
    # ========================================================

    if normalization_status != "SUCCESS":

        reasons.append(
            "NORMALIZATION_NOT_SUCCESS"
        )

        return (
            REVIEW_REQUIRED,
            reasons,
            chunking_strategy,
        )

    # ========================================================
    # 3. METADATA GATE
    # ========================================================

    if metadata_status != "SUCCESS":

        reasons.append(
            "METADATA_NOT_SUCCESS"
        )

        return (
            REVIEW_REQUIRED,
            reasons,
            chunking_strategy,
        )

    # ========================================================
    # 4. SOURCE GATE
    # ========================================================

    if not source_info:

        reasons.append(
            "SOURCE_NOT_FOUND_IN_APPROVED_REGISTRY"
        )

        return (
            REVIEW_REQUIRED,
            reasons,
            chunking_strategy,
        )

    if (
        source_info.get("status")
        != "APPROVED"
    ):

        reasons.append(
            "SOURCE_NOT_APPROVED"
        )

        return (
            REVIEW_REQUIRED,
            reasons,
            chunking_strategy,
        )

    # ========================================================
    # 5. SOURCE-EVIDENCE-ONLY DOCUMENT
    #
    # Ví dụ DOC0011:
    # trang giới thiệu cơ quan / bộ môn.
    #
    # Nó chứng minh nguồn có năng lực/chức năng nghiên cứu,
    # nhưng không phải knowledge content chính để retrieval.
    # ========================================================

    if (
        family
        == "institution_profile"
    ):

        reasons.append(
            "SOURCE_EVIDENCE_ONLY_NOT_PRIMARY_RAG_KNOWLEDGE"
        )

        return (
            REJECTED,
            reasons,
            chunking_strategy,
        )

    # ========================================================
    # 6. LEGAL GATE
    #
    # Không cho luật/phụ lục pháp lý vào RAG runtime
    # trước khi kiểm tra hiệu lực / amendment / supersession.
    # ========================================================

    if family in LEGAL_FAMILIES:

        reasons.append(
            "LEGAL_VALIDATION_REQUIRED"
        )

        return (
            REVIEW_REQUIRED,
            reasons,
            chunking_strategy,
        )

    # ========================================================
    # 7. MULTI-TOPIC GATE
    #
    # Bản tin / kỷ yếu dài chứa nhiều chủ đề.
    #
    # Không index nguyên tài liệu.
    # Phải split thành section trước.
    # ========================================================

    if family in MULTI_TOPIC_FAMILIES:

        reasons.append(
            "SECTION_LEVEL_SELECTION_REQUIRED"
        )

        return (
            REVIEW_REQUIRED,
            reasons,
            "SECTION_LEVEL",
        )

    # ========================================================
    # 8. TARGET-CROP RELEVANCE GATE
    #
    # Technical guide nhưng:
    # - không match crop target
    # - scope lại general_agronomy
    #
    # Ví dụ DOC0007 "cải ngọt".
    #
    # Không tự suy cải ngọt = cải xanh.
    # ========================================================

    if (
        family
        == "technical_guide"
        and
        not crop_entities
        and
        knowledge_scope
        == "general_agronomy"
    ):

        reasons.append(
            "TARGET_CROP_SCOPE_UNCLEAR"
        )

        return (
            REVIEW_REQUIRED,
            reasons,
            chunking_strategy,
        )

    # ========================================================
    # 9. REQUIRED METADATA
    # ========================================================

    suggested_buckets = (
        document.get(
            "suggested_buckets"
        )
        or []
    )

    if not suggested_buckets:

        reasons.append(
            "NO_KNOWLEDGE_BUCKET"
        )

        return (
            REVIEW_REQUIRED,
            reasons,
            chunking_strategy,
        )

    if not knowledge_scope:

        reasons.append(
            "KNOWLEDGE_SCOPE_MISSING"
        )

        return (
            REVIEW_REQUIRED,
            reasons,
            chunking_strategy,
        )

    # ========================================================
    # 10. ACCEPT
    # ========================================================

    reasons.append(
        "QUALITY_GATE_PASSED"
    )

    return (
        ACCEPTED,
        reasons,
        chunking_strategy,
    )


# ============================================================
# MANIFEST RECORD
# ============================================================

def build_manifest_record(
    document: dict,
):

    return {
        "document_id":
            document.get(
                "document_id"
            ),

        "source_id":
            document.get(
                "source_id"
            ),

        "url":
            document.get(
                "url"
            ),

        "title":
            document.get(
                "title"
            ),

        "published_date":
            document.get(
                "published_date"
            ),

        "document_family":
            document.get(
                "document_family"
            ),

        "crop_entities":
            document.get(
                "crop_entities"
            )
            or [],

        "buckets":
            document.get(
                "buckets"
            )
            or [],

        "suggested_buckets":
            document.get(
                "suggested_buckets"
            )
            or [],

        "knowledge_scope":
            document.get(
                "knowledge_scope"
            ),

        "region":
            document.get(
                "region"
            ),

        "source_credibility":
            document.get(
                "source_credibility"
            ),

        "local_applicability":
            document.get(
                "local_applicability"
            ),

        "raw_path":
            document.get(
                "raw_path"
            ),

        "extracted_path":
            document.get(
                "extracted_path"
            ),

        "normalized_path":
            document.get(
                "normalized_path"
            ),

        "extraction_status":
            document.get(
                "extraction_status"
            ),

        "normalization_status":
            document.get(
                "normalization_status"
            ),

        "metadata_status":
            document.get(
                "metadata_status"
            ),

        "quality_status":
            document.get(
                "quality_status"
            ),

        "quality_reasons":
            document.get(
                "quality_reasons"
            )
            or [],

        "chunking_strategy":
            document.get(
                "chunking_strategy"
            ),

        "rag_eligible":
            document.get(
                "rag_eligible"
            ),

        "quality_checked_at":
            document.get(
                "quality_checked_at"
            ),
    }


# ============================================================
# QUALITY REPORT CSV
# ============================================================

def write_quality_report(
    rows: list,
):

    fieldnames = [
        "document_id",
        "quality_status",
        "quality_reasons",
        "source_id",
        "document_family",
        "knowledge_scope",
        "crop_entities",
        "buckets",
        "suggested_buckets",
        "region",
        "chunking_strategy",
        "rag_eligible",
        "raw_path",
        "normalized_path",
    ]

    with QUALITY_REPORT_FILE.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for row in rows:

            writer.writerow({
                "document_id":
                    row.get(
                        "document_id"
                    ),

                "quality_status":
                    row.get(
                        "quality_status"
                    ),

                "quality_reasons":
                    " | ".join(
                        row.get(
                            "quality_reasons"
                        )
                        or []
                    ),

                "source_id":
                    row.get(
                        "source_id"
                    ),

                "document_family":
                    row.get(
                        "document_family"
                    ),

                "knowledge_scope":
                    row.get(
                        "knowledge_scope"
                    ),

                "crop_entities":
                    " | ".join(
                        row.get(
                            "crop_entities"
                        )
                        or []
                    ),

                "buckets":
                    " | ".join(
                        row.get(
                            "buckets"
                        )
                        or []
                    ),

                "suggested_buckets":
                    " | ".join(
                        row.get(
                            "suggested_buckets"
                        )
                        or []
                    ),

                "region":
                    row.get(
                        "region"
                    ),

                "chunking_strategy":
                    row.get(
                        "chunking_strategy"
                    ),

                "rag_eligible":
                    row.get(
                        "rag_eligible"
                    ),

                "raw_path":
                    row.get(
                        "raw_path"
                    ),

                "normalized_path":
                    row.get(
                        "normalized_path"
                    ),
            })


# ============================================================
# REVIEW QUEUE CSV
# ============================================================

def write_review_queue(
    rows: list,
):

    fieldnames = [
        "document_id",
        "stage",
        "reasons",
        "source_id",
        "document_family",
        "title",
        "raw_path",
        "normalized_path",
    ]

    with REVIEW_QUEUE_FILE.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for row in rows:

            reasons = (
                row.get(
                    "quality_reasons"
                )
                or []
            )

            # ------------------------------------------------
            # Routing stage
            # ------------------------------------------------

            if (
                "OCR_REQUIRED"
                in reasons
            ):

                stage = "OCR"

            elif (
                "LEGAL_VALIDATION_REQUIRED"
                in reasons
            ):

                stage = (
                    "LEGAL_VALIDATION"
                )

            elif (
                "SECTION_LEVEL_SELECTION_REQUIRED"
                in reasons
            ):

                stage = (
                    "SECTION_SPLITTING"
                )

            elif (
                "TARGET_CROP_SCOPE_UNCLEAR"
                in reasons
            ):

                stage = (
                    "RELEVANCE_VALIDATION"
                )

            else:

                stage = (
                    "QUALITY_REVIEW"
                )

            writer.writerow({
                "document_id":
                    row.get(
                        "document_id"
                    ),

                "stage":
                    stage,

                "reasons":
                    " | ".join(
                        reasons
                    ),

                "source_id":
                    row.get(
                        "source_id"
                    ),

                "document_family":
                    row.get(
                        "document_family"
                    ),

                "title":
                    row.get(
                        "title"
                    ),

                "raw_path":
                    row.get(
                        "raw_path"
                    ),

                "normalized_path":
                    row.get(
                        "normalized_path"
                    ),
            })


# ============================================================
# MAIN
# ============================================================

def main():

    prepare_output_directories()

    source_config = load_yaml(
        SOURCE_CONFIG_FILE
    )

    registry_files = sorted(
        DOCUMENT_DIR.glob(
            "DOC*.json"
        )
    )

    accepted_records = []
    review_records = []
    rejected_records = []
    report_records = []

    accepted_count = 0
    review_count = 0
    rejected_count = 0
    failed_count = 0

    print()
    print("=" * 78)
    print("AGRI RAG - QUALITY GATE")
    print("=" * 78)

    print(
        f"Documents found: "
        f"{len(registry_files)}"
    )

    for index, registry_path in enumerate(
        registry_files,
        start=1,
    ):

        print()
        print("-" * 78)

        print(
            f"[{index}/{len(registry_files)}] "
            f"{registry_path.stem}"
        )

        try:

            document = load_json(
                registry_path
            )

            (
                decision,
                reasons,
                chunking_strategy,
            ) = evaluate_quality(
                document,
                source_config,
            )

            # =================================================
            # Update quality metadata
            # =================================================

            document[
                "quality_status"
            ] = decision

            document[
                "quality_reasons"
            ] = reasons

            document[
                "chunking_strategy"
            ] = chunking_strategy

            document[
                "quality_checked_at"
            ] = datetime.now(
                timezone.utc
            ).isoformat()

            # =================================================
            # ACCEPTED
            # =================================================

            if decision == ACCEPTED:

                final_buckets = (
                    determine_final_buckets(
                        document
                    )
                )

                document[
                    "buckets"
                ] = final_buckets

                document[
                    "rag_eligible"
                ] = True

                accepted_count += 1

            # =================================================
            # REVIEW REQUIRED
            # =================================================

            elif (
                decision
                == REVIEW_REQUIRED
            ):

                # Không cho downstream index
                # khi chưa xử lý review reason.
                document[
                    "buckets"
                ] = []

                document[
                    "rag_eligible"
                ] = False

                review_count += 1

            # =================================================
            # REJECTED
            # =================================================

            else:

                document[
                    "buckets"
                ] = []

                document[
                    "rag_eligible"
                ] = False

                rejected_count += 1

            # =================================================
            # Save master registry
            # =================================================

            save_json(
                registry_path,
                document,
            )

            # =================================================
            # Snapshot
            # =================================================

            snapshot = (
                build_manifest_record(
                    document
                )
            )

            if decision == ACCEPTED:

                accepted_records.append(
                    snapshot
                )

                save_json(
                    ACCEPTED_DIR
                    / (
                        document[
                            "document_id"
                        ]
                        + ".json"
                    ),
                    snapshot,
                )

            elif (
                decision
                == REVIEW_REQUIRED
            ):

                review_records.append(
                    snapshot
                )

                save_json(
                    REVIEW_DIR
                    / (
                        document[
                            "document_id"
                        ]
                        + ".json"
                    ),
                    snapshot,
                )

            else:

                rejected_records.append(
                    snapshot
                )

                save_json(
                    REJECTED_DIR
                    / (
                        document[
                            "document_id"
                        ]
                        + ".json"
                    ),
                    snapshot,
                )

            report_records.append(
                snapshot
            )

            print(
                f"Decision           : "
                f"{decision}"
            )

            print(
                f"Reasons            : "
                f"{reasons}"
            )

            print(
                f"Family             : "
                f"{document.get('document_family')}"
            )

            print(
                f"Crops              : "
                f"{document.get('crop_entities')}"
            )

            print(
                f"Final buckets      : "
                f"{document.get('buckets')}"
            )

            print(
                f"Chunking strategy  : "
                f"{chunking_strategy}"
            )

            print(
                f"RAG eligible       : "
                f"{document.get('rag_eligible')}"
            )

        except Exception as exc:

            failed_count += 1

            print(
                f"[FAILED] {exc}"
            )

    # ========================================================
    # WRITE REPORTS
    # ========================================================

    write_quality_report(
        report_records
    )

    write_review_queue(
        review_records
    )

    write_jsonl(
        ACCEPTED_MANIFEST_FILE,
        accepted_records,
    )

    write_jsonl(
        REVIEW_MANIFEST_FILE,
        review_records,
    )

    write_jsonl(
        REJECTED_MANIFEST_FILE,
        rejected_records,
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print()
    print("=" * 78)
    print("QUALITY GATE SUMMARY")
    print("=" * 78)

    print(
        f"Total documents   : "
        f"{len(registry_files)}"
    )

    print(
        f"ACCEPTED          : "
        f"{accepted_count}"
    )

    print(
        f"REVIEW_REQUIRED   : "
        f"{review_count}"
    )

    print(
        f"REJECTED          : "
        f"{rejected_count}"
    )

    print(
        f"FAILED            : "
        f"{failed_count}"
    )

    print()
    print(
        f"Quality report    : "
        f"{QUALITY_REPORT_FILE}"
    )

    print(
        f"Review queue      : "
        f"{REVIEW_QUEUE_FILE}"
    )

    print(
        f"Accepted manifest : "
        f"{ACCEPTED_MANIFEST_FILE}"
    )

    print(
        f"Review manifest   : "
        f"{REVIEW_MANIFEST_FILE}"
    )

    print(
        f"Rejected manifest : "
        f"{REJECTED_MANIFEST_FILE}"
    )


if __name__ == "__main__":
    main()