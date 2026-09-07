import csv
import json
from collections import Counter
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

DOCUMENT_DIR = Path(
    "data/agri_rag/registry/documents"
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
# VALID VALUES
# ============================================================

VALID_QUALITY_STATUSES = {
    "ACCEPTED",
    "REVIEW_REQUIRED",
    "REJECTED",
}


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


def load_jsonl(
    path: Path,
) -> list:

    if not path.exists():
        return []

    records = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        for line in file:

            line = line.strip()

            if not line:
                continue

            records.append(
                json.loads(line)
            )

    return records


def load_csv(
    path: Path,
) -> list:

    if not path.exists():
        return []

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        return list(
            csv.DictReader(file)
        )


# ============================================================
# ISSUE HELPERS
# ============================================================

def add_issue(
    issues: list,
    document_id: str,
    reason: str,
    **details,
):

    item = {
        "document_id":
            document_id,

        "reason":
            reason,
    }

    item.update(
        details
    )

    issues.append(
        item
    )


def add_warning(
    warnings: list,
    document_id: str,
    reason: str,
    **details,
):

    item = {
        "document_id":
            document_id,

        "reason":
            reason,
    }

    item.update(
        details
    )

    warnings.append(
        item
    )


# ============================================================
# EXPECTED REVIEW ROUTING
# ============================================================

def expected_review_stage(
    reasons: list,
):

    if (
        "OCR_REQUIRED"
        in reasons
    ):
        return "OCR"

    if (
        "LEGAL_VALIDATION_REQUIRED"
        in reasons
    ):
        return "LEGAL_VALIDATION"

    if (
        "SECTION_LEVEL_SELECTION_REQUIRED"
        in reasons
    ):
        return "SECTION_SPLITTING"

    if (
        "TARGET_CROP_SCOPE_UNCLEAR"
        in reasons
    ):
        return "RELEVANCE_VALIDATION"

    return "QUALITY_REVIEW"


# ============================================================
# AUDIT MASTER DOCUMENT
# ============================================================

def audit_document(
    document: dict,
):

    issues = []
    warnings = []

    document_id = (
        document.get(
            "document_id"
        )
    )

    quality_status = (
        document.get(
            "quality_status"
        )
    )

    reasons = (
        document.get(
            "quality_reasons"
        )
        or []
    )

    family = (
        document.get(
            "document_family"
        )
    )

    rag_eligible = (
        document.get(
            "rag_eligible"
        )
    )

    buckets = (
        document.get(
            "buckets"
        )
        or []
    )

    suggested_buckets = (
        document.get(
            "suggested_buckets"
        )
        or []
    )

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

    # ========================================================
    # 1. Quality status
    # ========================================================

    if (
        quality_status
        not in VALID_QUALITY_STATUSES
    ):

        add_issue(
            issues,
            document_id,
            "INVALID_QUALITY_STATUS",
            quality_status=quality_status,
        )

        return issues, warnings

    if not reasons:

        add_issue(
            issues,
            document_id,
            "QUALITY_REASONS_MISSING",
        )

    # ========================================================
    # 2. ACCEPTED invariants
    # ========================================================

    if quality_status == "ACCEPTED":

        if rag_eligible is not True:

            add_issue(
                issues,
                document_id,
                "ACCEPTED_DOCUMENT_NOT_RAG_ELIGIBLE",
            )

        if not buckets:

            add_issue(
                issues,
                document_id,
                "ACCEPTED_DOCUMENT_HAS_NO_FINAL_BUCKETS",
            )

        if (
            reasons
            != ["QUALITY_GATE_PASSED"]
        ):

            add_issue(
                issues,
                document_id,
                "ACCEPTED_DOCUMENT_INVALID_REASON",
                reasons=reasons,
            )

        if (
            extraction_status
            != "SUCCESS"
        ):

            add_issue(
                issues,
                document_id,
                "ACCEPTED_EXTRACTION_NOT_SUCCESS",
            )

        if (
            normalization_status
            != "SUCCESS"
        ):

            add_issue(
                issues,
                document_id,
                "ACCEPTED_NORMALIZATION_NOT_SUCCESS",
            )

        if (
            metadata_status
            != "SUCCESS"
        ):

            add_issue(
                issues,
                document_id,
                "ACCEPTED_METADATA_NOT_SUCCESS",
            )

        normalized_path_value = (
            document.get(
                "normalized_path"
            )
        )

        if not normalized_path_value:

            add_issue(
                issues,
                document_id,
                "ACCEPTED_NORMALIZED_PATH_MISSING",
            )

        else:

            normalized_path = Path(
                normalized_path_value
            )

            if not normalized_path.exists():

                add_issue(
                    issues,
                    document_id,
                    "ACCEPTED_NORMALIZED_FILE_NOT_FOUND",
                )

        if (
            family
            in LEGAL_FAMILIES
        ):

            add_issue(
                issues,
                document_id,
                "LEGAL_DOCUMENT_ACCEPTED_BEFORE_LEGAL_VALIDATION",
            )

        if (
            family
            in MULTI_TOPIC_FAMILIES
        ):

            add_issue(
                issues,
                document_id,
                "MULTI_TOPIC_DOCUMENT_ACCEPTED_BEFORE_SECTION_SPLITTING",
            )

        if (
            family
            == "institution_profile"
        ):

            add_issue(
                issues,
                document_id,
                "INSTITUTION_PROFILE_ACCEPTED_AS_RAG_KNOWLEDGE",
            )

    # ========================================================
    # 3. REVIEW invariants
    # ========================================================

    elif (
        quality_status
        == "REVIEW_REQUIRED"
    ):

        if rag_eligible is not False:

            add_issue(
                issues,
                document_id,
                "REVIEW_DOCUMENT_RAG_ELIGIBLE",
            )

        if buckets:

            add_issue(
                issues,
                document_id,
                "REVIEW_DOCUMENT_HAS_FINAL_BUCKETS",
                buckets=buckets,
            )

        if (
            "QUALITY_GATE_PASSED"
            in reasons
        ):

            add_issue(
                issues,
                document_id,
                "REVIEW_DOCUMENT_MARKED_GATE_PASSED",
            )

    # ========================================================
    # 4. REJECTED invariants
    # ========================================================

    elif (
        quality_status
        == "REJECTED"
    ):

        if rag_eligible is not False:

            add_issue(
                issues,
                document_id,
                "REJECTED_DOCUMENT_RAG_ELIGIBLE",
            )

        if buckets:

            add_issue(
                issues,
                document_id,
                "REJECTED_DOCUMENT_HAS_FINAL_BUCKETS",
                buckets=buckets,
            )

    # ========================================================
    # 5. Legal rules
    # ========================================================

    if family in LEGAL_FAMILIES:

        if (
            quality_status
            != "REVIEW_REQUIRED"
        ):

            add_issue(
                issues,
                document_id,
                "LEGAL_DOCUMENT_NOT_IN_REVIEW",
                quality_status=quality_status,
            )

        if (
            "LEGAL_VALIDATION_REQUIRED"
            not in reasons
        ):

            add_issue(
                issues,
                document_id,
                "LEGAL_VALIDATION_REASON_MISSING",
            )

    # ========================================================
    # 6. OCR rules
    # ========================================================

    if (
        extraction_status
        == "OCR_REQUIRED"
    ):

        if (
            quality_status
            != "REVIEW_REQUIRED"
        ):

            add_issue(
                issues,
                document_id,
                "OCR_DOCUMENT_NOT_IN_REVIEW",
            )

        if (
            "OCR_REQUIRED"
            not in reasons
        ):

            add_issue(
                issues,
                document_id,
                "OCR_REASON_MISSING",
            )

    # ========================================================
    # 7. Multi-topic rules
    # ========================================================

    if family in MULTI_TOPIC_FAMILIES:

        if (
            quality_status
            != "REVIEW_REQUIRED"
        ):

            add_issue(
                issues,
                document_id,
                "MULTI_TOPIC_DOCUMENT_NOT_IN_REVIEW",
            )

        if (
            "SECTION_LEVEL_SELECTION_REQUIRED"
            not in reasons
        ):

            add_issue(
                issues,
                document_id,
                "SECTION_LEVEL_REASON_MISSING",
            )

        if (
            document.get(
                "chunking_strategy"
            )
            != "SECTION_LEVEL"
        ):

            add_issue(
                issues,
                document_id,
                "MULTI_TOPIC_CHUNKING_STRATEGY_INVALID",
            )

    # ========================================================
    # 8. Institution profile
    # ========================================================

    if (
        family
        == "institution_profile"
    ):

        if (
            quality_status
            != "REJECTED"
        ):

            add_issue(
                issues,
                document_id,
                "INSTITUTION_PROFILE_NOT_REJECTED",
            )

        if (
            "SOURCE_EVIDENCE_ONLY_NOT_PRIMARY_RAG_KNOWLEDGE"
            not in reasons
        ):

            add_issue(
                issues,
                document_id,
                "INSTITUTION_PROFILE_REASON_MISSING",
            )

    # ========================================================
    # 9. Final buckets must originate from suggestions
    # ========================================================

    invalid_promoted_buckets = [
        bucket
        for bucket in buckets
        if (
            bucket
            not in suggested_buckets
        )
    ]

    if invalid_promoted_buckets:

        add_issue(
            issues,
            document_id,
            "FINAL_BUCKET_NOT_IN_SUGGESTIONS",
            buckets=invalid_promoted_buckets,
        )

    # ========================================================
    # 10. Preserve raw evidence
    # ========================================================

    raw_path_value = (
        document.get(
            "raw_path"
        )
    )

    if not raw_path_value:

        add_issue(
            issues,
            document_id,
            "RAW_PATH_MISSING",
        )

    else:

        raw_path = Path(
            raw_path_value
        )

        if not raw_path.exists():

            add_issue(
                issues,
                document_id,
                "RAW_FILE_NOT_FOUND",
                raw_path=raw_path_value,
            )

    # ========================================================
    # 11. Quality timestamp
    # ========================================================

    if not document.get(
        "quality_checked_at"
    ):

        add_warning(
            warnings,
            document_id,
            "QUALITY_CHECK_TIMESTAMP_MISSING",
        )

    return issues, warnings


# ============================================================
# CROSS-FILE CONSISTENCY
# ============================================================

def audit_cross_file_consistency(
    documents: dict,
    accepted_manifest: list,
    review_manifest: list,
    rejected_manifest: list,
    quality_report: list,
    review_queue: list,
):

    issues = []

    accepted_master = {
        document_id
        for document_id, document
        in documents.items()
        if (
            document.get(
                "quality_status"
            )
            == "ACCEPTED"
        )
    }

    review_master = {
        document_id
        for document_id, document
        in documents.items()
        if (
            document.get(
                "quality_status"
            )
            == "REVIEW_REQUIRED"
        )
    }

    rejected_master = {
        document_id
        for document_id, document
        in documents.items()
        if (
            document.get(
                "quality_status"
            )
            == "REJECTED"
        )
    }

    # ========================================================
    # Manifest IDs
    # ========================================================

    accepted_manifest_ids = {
        row.get(
            "document_id"
        )
        for row in accepted_manifest
    }

    review_manifest_ids = {
        row.get(
            "document_id"
        )
        for row in review_manifest
    }

    rejected_manifest_ids = {
        row.get(
            "document_id"
        )
        for row in rejected_manifest
    }

    if (
        accepted_master
        != accepted_manifest_ids
    ):

        add_issue(
            issues,
            "__GLOBAL__",
            "ACCEPTED_MANIFEST_MISMATCH",
            expected=sorted(
                accepted_master
            ),
            actual=sorted(
                accepted_manifest_ids
            ),
        )

    if (
        review_master
        != review_manifest_ids
    ):

        add_issue(
            issues,
            "__GLOBAL__",
            "REVIEW_MANIFEST_MISMATCH",
            expected=sorted(
                review_master
            ),
            actual=sorted(
                review_manifest_ids
            ),
        )

    if (
        rejected_master
        != rejected_manifest_ids
    ):

        add_issue(
            issues,
            "__GLOBAL__",
            "REJECTED_MANIFEST_MISMATCH",
            expected=sorted(
                rejected_master
            ),
            actual=sorted(
                rejected_manifest_ids
            ),
        )

    # ========================================================
    # Snapshot directories
    # ========================================================

    accepted_snapshot_ids = {
        path.stem
        for path in (
            ACCEPTED_DIR.glob(
                "DOC*.json"
            )
        )
    }

    review_snapshot_ids = {
        path.stem
        for path in (
            REVIEW_DIR.glob(
                "DOC*.json"
            )
        )
    }

    rejected_snapshot_ids = {
        path.stem
        for path in (
            REJECTED_DIR.glob(
                "DOC*.json"
            )
        )
    }

    if (
        accepted_snapshot_ids
        != accepted_master
    ):

        add_issue(
            issues,
            "__GLOBAL__",
            "ACCEPTED_DIRECTORY_MISMATCH",
            expected=sorted(
                accepted_master
            ),
            actual=sorted(
                accepted_snapshot_ids
            ),
        )

    if (
        review_snapshot_ids
        != review_master
    ):

        add_issue(
            issues,
            "__GLOBAL__",
            "REVIEW_DIRECTORY_MISMATCH",
            expected=sorted(
                review_master
            ),
            actual=sorted(
                review_snapshot_ids
            ),
        )

    if (
        rejected_snapshot_ids
        != rejected_master
    ):

        add_issue(
            issues,
            "__GLOBAL__",
            "REJECTED_DIRECTORY_MISMATCH",
            expected=sorted(
                rejected_master
            ),
            actual=sorted(
                rejected_snapshot_ids
            ),
        )

    # ========================================================
    # Quality report must contain every document exactly once
    # ========================================================

    report_ids = [
        row.get(
            "document_id"
        )
        for row in quality_report
    ]

    if len(report_ids) != len(
        set(report_ids)
    ):

        add_issue(
            issues,
            "__GLOBAL__",
            "QUALITY_REPORT_DUPLICATE_DOCUMENT_ID",
        )

    if (
        set(report_ids)
        != set(
            documents.keys()
        )
    ):

        add_issue(
            issues,
            "__GLOBAL__",
            "QUALITY_REPORT_DOCUMENT_SET_MISMATCH",
            expected=sorted(
                documents.keys()
            ),
            actual=sorted(
                set(report_ids)
            ),
        )

    # ========================================================
    # Review queue
    # ========================================================

    review_queue_ids = [
        row.get(
            "document_id"
        )
        for row in review_queue
    ]

    if len(
        review_queue_ids
    ) != len(
        set(review_queue_ids)
    ):

        add_issue(
            issues,
            "__GLOBAL__",
            "REVIEW_QUEUE_DUPLICATE_DOCUMENT_ID",
        )

    if (
        set(review_queue_ids)
        != review_master
    ):

        add_issue(
            issues,
            "__GLOBAL__",
            "REVIEW_QUEUE_DOCUMENT_SET_MISMATCH",
            expected=sorted(
                review_master
            ),
            actual=sorted(
                set(review_queue_ids)
            ),
        )

    # ========================================================
    # Review queue routing
    # ========================================================

    for row in review_queue:

        document_id = (
            row.get(
                "document_id"
            )
        )

        document = (
            documents.get(
                document_id
            )
        )

        if not document:
            continue

        reasons = (
            document.get(
                "quality_reasons"
            )
            or []
        )

        expected_stage = (
            expected_review_stage(
                reasons
            )
        )

        actual_stage = (
            row.get(
                "stage"
            )
        )

        if (
            actual_stage
            != expected_stage
        ):

            add_issue(
                issues,
                document_id,
                "REVIEW_QUEUE_STAGE_MISMATCH",
                expected=(
                    expected_stage
                ),
                actual=(
                    actual_stage
                ),
            )

    # ========================================================
    # No document may appear in multiple destinations
    # ========================================================

    overlap_ar = (
        accepted_master
        & review_master
    )

    overlap_aj = (
        accepted_master
        & rejected_master
    )

    overlap_rj = (
        review_master
        & rejected_master
    )

    if overlap_ar:

        add_issue(
            issues,
            "__GLOBAL__",
            "ACCEPTED_REVIEW_OVERLAP",
            document_ids=sorted(
                overlap_ar
            ),
        )

    if overlap_aj:

        add_issue(
            issues,
            "__GLOBAL__",
            "ACCEPTED_REJECTED_OVERLAP",
            document_ids=sorted(
                overlap_aj
            ),
        )

    if overlap_rj:

        add_issue(
            issues,
            "__GLOBAL__",
            "REVIEW_REJECTED_OVERLAP",
            document_ids=sorted(
                overlap_rj
            ),
        )

    return issues


# ============================================================
# MAIN
# ============================================================

def main():

    registry_files = sorted(
        DOCUMENT_DIR.glob(
            "DOC*.json"
        )
    )

    documents = {}

    all_issues = []
    all_warnings = []

    status_counter = Counter()

    print()
    print("=" * 78)
    print("RAG QUALITY GATE AUDIT")
    print("=" * 78)

    # ========================================================
    # Audit master registry
    # ========================================================

    for registry_path in registry_files:

        document = load_json(
            registry_path
        )

        document_id = (
            document[
                "document_id"
            ]
        )

        documents[
            document_id
        ] = document

        quality_status = (
            document.get(
                "quality_status",
                "MISSING",
            )
        )

        status_counter[
            quality_status
        ] += 1

        issues, warnings = (
            audit_document(
                document
            )
        )

        all_issues.extend(
            issues
        )

        all_warnings.extend(
            warnings
        )

        print()
        print("-" * 78)

        print(
            document_id
        )

        print(
            "Quality status   : "
            f"{quality_status}"
        )

        print(
            "Reasons          : "
            f"{document.get('quality_reasons')}"
        )

        print(
            "RAG eligible     : "
            f"{document.get('rag_eligible')}"
        )

        print(
            "Buckets          : "
            f"{document.get('buckets')}"
        )

        print(
            "Chunking         : "
            f"{document.get('chunking_strategy')}"
        )

        if issues:

            print(
                "Audit            : REVIEW"
            )

            print(
                "Issues           : "
                f"{len(issues)}"
            )

        else:

            print(
                "Audit            : PASS"
            )

        if warnings:

            print(
                "Warnings         : "
                f"{len(warnings)}"
            )

    # ========================================================
    # Load generated reports/manifests
    # ========================================================

    accepted_manifest = (
        load_jsonl(
            ACCEPTED_MANIFEST_FILE
        )
    )

    review_manifest = (
        load_jsonl(
            REVIEW_MANIFEST_FILE
        )
    )

    rejected_manifest = (
        load_jsonl(
            REJECTED_MANIFEST_FILE
        )
    )

    quality_report = (
        load_csv(
            QUALITY_REPORT_FILE
        )
    )

    review_queue = (
        load_csv(
            REVIEW_QUEUE_FILE
        )
    )

    # ========================================================
    # Cross-file audit
    # ========================================================

    cross_issues = (
        audit_cross_file_consistency(
            documents,
            accepted_manifest,
            review_manifest,
            rejected_manifest,
            quality_report,
            review_queue,
        )
    )

    all_issues.extend(
        cross_issues
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print()
    print("=" * 78)
    print("QUALITY GATE AUDIT SUMMARY")
    print("=" * 78)

    print(
        f"Total documents   : "
        f"{len(documents)}"
    )

    for status in [
        "ACCEPTED",
        "REVIEW_REQUIRED",
        "REJECTED",
    ]:

        print(
            f"{status:<18}: "
            f"{status_counter.get(status, 0)}"
        )

    print()

    print(
        f"Accepted manifest : "
        f"{len(accepted_manifest)}"
    )

    print(
        f"Review manifest   : "
        f"{len(review_manifest)}"
    )

    print(
        f"Rejected manifest : "
        f"{len(rejected_manifest)}"
    )

    print(
        f"Quality report    : "
        f"{len(quality_report)}"
    )

    print(
        f"Review queue      : "
        f"{len(review_queue)}"
    )

    print()

    print(
        f"Issues found      : "
        f"{len(all_issues)}"
    )

    print(
        f"Warnings found    : "
        f"{len(all_warnings)}"
    )

    if all_issues:

        print()
        print("ISSUES")
        print("-" * 78)

        print(
            json.dumps(
                all_issues,
                ensure_ascii=False,
                indent=2,
            )
        )

    if all_warnings:

        print()
        print("WARNINGS")
        print("-" * 78)

        print(
            json.dumps(
                all_warnings,
                ensure_ascii=False,
                indent=2,
            )
        )

    if not all_issues:

        print()
        print(
            "No blocking quality gate issues detected."
        )


if __name__ == "__main__":
    main()