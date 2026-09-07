import csv
import json
from pathlib import Path
from collections import Counter

import yaml


# ============================================================
# PATHS
# ============================================================

DOCUMENT_DIR = Path(
    "data/agri_rag/registry/documents"
)

DOWNLOAD_REGISTRY_FILE = Path(
    "data/agri_rag/registry/download_registry.csv"
)

SOURCE_CONFIG_FILE = Path(
    "src/agri_rag/config/approved_sources.yaml"
)

CROP_CONFIG_FILE = Path(
    "src/agri_rag/config/crops.yaml"
)


# ============================================================
# VALID VALUES
# ============================================================

VALID_BUCKETS = {
    "B01_CROP_PROFILE",
    "B02_WATER",
    "B03_NUTRITION",
    "B04_PEST_DISEASE",
    "B05_WEATHER_CARE",
    "B06_PESTICIDE_LEGAL",
    "B07_GAP_SAFETY",
    "B08_LOCAL",
}


VALID_DOCUMENT_FAMILIES = {
    "regulation",
    "regulatory_attachment",
    "technical_document",
    "technical_guide",
    "local_extension_article",
    "extension_bulletin",
    "institution_profile",
    "conference_proceedings",
    "web_document",
}


VALID_KNOWLEDGE_SCOPES = {
    "crop_specific",
    "crop_group",
    "general_agronomy",
    "regulatory",
    "local_context",
    "scientific_external",
}


# ============================================================
# IO
# ============================================================

def load_json(path: Path) -> dict:

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        return json.load(file)


def load_yaml(path: Path) -> dict:

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        return yaml.safe_load(file) or {}


def load_download_registry() -> dict:

    result = {}

    if not DOWNLOAD_REGISTRY_FILE.exists():
        return result

    with DOWNLOAD_REGISTRY_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            document_id = (
                row.get("document_id")
                or ""
            ).strip()

            if document_id:
                result[document_id] = row

    return result


# ============================================================
# HELPERS
# ============================================================

def add_issue(
    issues: list,
    document_id: str,
    reason: str,
    **details,
):

    item = {
        "document_id": document_id,
        "reason": reason,
    }

    item.update(details)

    issues.append(item)


def add_warning(
    warnings: list,
    document_id: str,
    reason: str,
    **details,
):

    item = {
        "document_id": document_id,
        "reason": reason,
    }

    item.update(details)

    warnings.append(item)


# ============================================================
# AUDIT ONE DOCUMENT
# ============================================================

def audit_document(
    document: dict,
    source_config: dict,
    crops_config: dict,
    download_registry: dict,
):

    document_id = document[
        "document_id"
    ]

    issues = []
    warnings = []

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
    # 1. Documents chưa normalize
    # ========================================================

    if normalization_status != "SUCCESS":

        if metadata_status != "SKIPPED":

            add_issue(
                issues,
                document_id,
                "EXPECTED_METADATA_SKIPPED",
                normalization_status=(
                    normalization_status
                ),
                metadata_status=(
                    metadata_status
                ),
            )

        return issues, warnings

    # ========================================================
    # 2. Normalized document phải có metadata result
    # ========================================================

    if metadata_status not in {
        "SUCCESS",
        "REVIEW_REQUIRED",
    }:

        add_issue(
            issues,
            document_id,
            "INVALID_METADATA_STATUS",
            metadata_status=metadata_status,
        )

    # ========================================================
    # 3. Source validation
    # ========================================================

    source_id = (
        document.get("source_id")
    )

    source_info = (
        source_config.get(
            source_id
        )
    )

    if not source_info:

        add_issue(
            issues,
            document_id,
            "SOURCE_NOT_FOUND",
            source_id=source_id,
        )

        return issues, warnings

    source_status = (
        source_info.get("status")
    )

    if source_status != "APPROVED":

        add_issue(
            issues,
            document_id,
            "SOURCE_NOT_APPROVED",
            source_id=source_id,
            source_status=source_status,
        )

    expected_credibility = (
        source_info.get(
            "credibility"
        )
    )

    actual_credibility = (
        document.get(
            "source_credibility"
        )
    )

    if (
        expected_credibility
        != actual_credibility
    ):

        add_issue(
            issues,
            document_id,
            "SOURCE_CREDIBILITY_MISMATCH",
            expected=expected_credibility,
            actual=actual_credibility,
        )

    # ========================================================
    # 4. Download registry + expected bucket
    # ========================================================

    download_row = (
        download_registry.get(
            document_id
        )
    )

    if not download_row:

        add_issue(
            issues,
            document_id,
            "DOWNLOAD_REGISTRY_RECORD_MISSING",
        )

        expected_bucket = None

    else:

        expected_bucket = (
            download_row.get(
                "expected_bucket"
            )
            or ""
        ).strip()

    if not expected_bucket:

        add_issue(
            issues,
            document_id,
            "EXPECTED_BUCKET_MISSING",
        )

    elif (
        expected_bucket
        not in VALID_BUCKETS
    ):

        add_issue(
            issues,
            document_id,
            "EXPECTED_BUCKET_INVALID",
            expected_bucket=expected_bucket,
        )

    else:

        allowed_topics = set(
            source_info.get(
                "allowed_topics"
            )
            or []
        )

        if (
            expected_bucket
            not in allowed_topics
        ):

            add_issue(
                issues,
                document_id,
                "EXPECTED_BUCKET_NOT_ALLOWED_FOR_SOURCE",
                expected_bucket=(
                    expected_bucket
                ),
                source_id=source_id,
            )

    # ========================================================
    # 5. Document family
    # ========================================================

    document_family = (
        document.get(
            "document_family"
        )
    )

    if (
        document_family
        not in VALID_DOCUMENT_FAMILIES
    ):

        add_issue(
            issues,
            document_id,
            "INVALID_DOCUMENT_FAMILY",
            document_family=(
                document_family
            ),
        )

    # ========================================================
    # 6. Knowledge scope
    # ========================================================

    knowledge_scope = (
        document.get(
            "knowledge_scope"
        )
    )

    if (
        knowledge_scope
        not in VALID_KNOWLEDGE_SCOPES
    ):

        add_issue(
            issues,
            document_id,
            "INVALID_KNOWLEDGE_SCOPE",
            knowledge_scope=(
                knowledge_scope
            ),
        )

    # ========================================================
    # 7. Crop entities
    # ========================================================

    crop_entities = (
        document.get(
            "crop_entities"
        )
        or []
    )

    valid_crop_ids = set(
        crops_config.keys()
    )

    invalid_crops = [
        crop
        for crop in crop_entities
        if crop not in valid_crop_ids
    ]

    if invalid_crops:

        add_issue(
            issues,
            document_id,
            "INVALID_CROP_ENTITIES",
            crops=invalid_crops,
        )

    # ========================================================
    # 8. Suggested buckets
    # ========================================================

    suggested_buckets = (
        document.get(
            "suggested_buckets"
        )
        or []
    )

    if not suggested_buckets:

        add_issue(
            issues,
            document_id,
            "NO_SUGGESTED_BUCKET",
        )

    invalid_buckets = [
        bucket
        for bucket in suggested_buckets
        if bucket not in VALID_BUCKETS
    ]

    if invalid_buckets:

        add_issue(
            issues,
            document_id,
            "INVALID_SUGGESTED_BUCKET",
            buckets=invalid_buckets,
        )

    if (
        expected_bucket
        and
        expected_bucket
        not in suggested_buckets
    ):

        add_issue(
            issues,
            document_id,
            "EXPECTED_BUCKET_NOT_IN_SUGGESTIONS",
            expected_bucket=(
                expected_bucket
            ),
            suggested_buckets=(
                suggested_buckets
            ),
        )

    # ========================================================
    # 9. Region
    # ========================================================

    region = (
        document.get(
            "region"
        )
    )

    if not region:

        add_issue(
            issues,
            document_id,
            "REGION_MISSING",
        )

    # ========================================================
    # 10. FAMILY-SPECIFIC INVARIANTS
    # ========================================================

    # --------------------------------------------------------
    # LEGAL
    # --------------------------------------------------------

    if document_family in {
        "regulation",
        "regulatory_attachment",
    }:

        if (
            knowledge_scope
            != "regulatory"
        ):

            add_issue(
                issues,
                document_id,
                "LEGAL_DOCUMENT_NOT_REGULATORY",
            )

        if (
            "B06_PESTICIDE_LEGAL"
            not in suggested_buckets
        ):

            add_issue(
                issues,
                document_id,
                "LEGAL_DOCUMENT_MISSING_B06",
            )

        if region != "VIETNAM":

            add_issue(
                issues,
                document_id,
                "LEGAL_DOCUMENT_REGION_NOT_VIETNAM",
                region=region,
            )

    # --------------------------------------------------------
    # NON-LEGAL không được regulatory
    # --------------------------------------------------------

    else:

        if (
            knowledge_scope
            == "regulatory"
        ):

            add_issue(
                issues,
                document_id,
                "NON_LEGAL_DOCUMENT_MARKED_REGULATORY",
                document_family=(
                    document_family
                ),
            )

    # --------------------------------------------------------
    # EXTENSION BULLETIN
    # --------------------------------------------------------

    if (
        document_family
        == "extension_bulletin"
    ):

        if region != "VIETNAM":

            add_issue(
                issues,
                document_id,
                "BULLETIN_REGION_SHOULD_BE_VIETNAM",
                region=region,
            )

        if (
            knowledge_scope
            != "general_agronomy"
        ):

            add_issue(
                issues,
                document_id,
                "BULLETIN_SCOPE_SHOULD_BE_GENERAL_AGRONOMY",
                knowledge_scope=(
                    knowledge_scope
                ),
            )

        metadata_notes = (
            document.get(
                "metadata_notes"
            )
            or []
        )

        if (
            "MULTI_TOPIC_DOCUMENT_REQUIRES_SECTION_LEVEL_CHUNKING"
            not in metadata_notes
        ):

            add_issue(
                issues,
                document_id,
                "BULLETIN_MISSING_MULTI_TOPIC_NOTE",
            )

    # --------------------------------------------------------
    # INSTITUTION PROFILE
    # --------------------------------------------------------

    if (
        document_family
        == "institution_profile"
    ):

        if (
            knowledge_scope
            != "local_context"
        ):

            add_issue(
                issues,
                document_id,
                "INSTITUTION_PROFILE_SCOPE_INVALID",
            )

        metadata_notes = (
            document.get(
                "metadata_notes"
            )
            or []
        )

        if (
            "SOURCE_EVIDENCE_NOT_PRIMARY_RAG_KNOWLEDGE"
            not in metadata_notes
        ):

            add_issue(
                issues,
                document_id,
                "INSTITUTION_PROFILE_MISSING_SOURCE_EVIDENCE_NOTE",
            )

    # --------------------------------------------------------
    # CONFERENCE PROCEEDINGS
    # --------------------------------------------------------

    if (
        document_family
        == "conference_proceedings"
    ):

        if (
            knowledge_scope
            != "local_context"
        ):

            add_issue(
                issues,
                document_id,
                "CONFERENCE_SCOPE_INVALID",
            )

        if (
            region
            != "SOUTH_CENTRAL_COAST"
        ):

            add_issue(
                issues,
                document_id,
                "CONFERENCE_REGION_INVALID",
                region=region,
            )

        metadata_notes = (
            document.get(
                "metadata_notes"
            )
            or []
        )

        if (
            "MULTI_TOPIC_DOCUMENT_REQUIRES_SECTION_LEVEL_CHUNKING"
            not in metadata_notes
        ):

            add_issue(
                issues,
                document_id,
                "CONFERENCE_MISSING_MULTI_TOPIC_NOTE",
            )

    # --------------------------------------------------------
    # LOCAL ARTICLE
    # --------------------------------------------------------

    if (
        document_family
        == "local_extension_article"
    ):

        if (
            region
            not in {
                "BINH_DINH_LEGACY",
                "GIA_LAI",
            }
        ):

            add_warning(
                warnings,
                document_id,
                "LOCAL_ARTICLE_REGION_NOT_DIRECT_LOCAL",
                region=region,
            )

    # ========================================================
    # 11. Published date
    #
    # Missing date không nhất thiết là lỗi.
    # ========================================================

    published_date = (
        document.get(
            "published_date"
        )
    )

    if not published_date:

        add_warning(
            warnings,
            document_id,
            "PUBLISHED_DATE_NOT_RESOLVED",
        )

    # ========================================================
    # 12. Approved buckets chưa được set ở metadata stage
    # ========================================================

    approved_buckets = (
        document.get(
            "buckets"
        )
        or []
    )

    if approved_buckets:

        add_issue(
            issues,
            document_id,
            "BUCKETS_SHOULD_STILL_BE_EMPTY_BEFORE_QUALITY_GATE",
            buckets=approved_buckets,
        )

    return issues, warnings


# ============================================================
# MAIN
# ============================================================

def main():

    source_config = load_yaml(
        SOURCE_CONFIG_FILE
    )

    crops_config = load_yaml(
        CROP_CONFIG_FILE
    )

    download_registry = (
        load_download_registry()
    )

    registry_files = sorted(
        DOCUMENT_DIR.glob(
            "DOC*.json"
        )
    )

    status_counter = Counter()

    all_issues = []
    all_warnings = []

    print()
    print("=" * 78)
    print("RAG METADATA AUDIT")
    print("=" * 78)

    for registry_path in registry_files:

        document = load_json(
            registry_path
        )

        document_id = (
            document[
                "document_id"
            ]
        )

        metadata_status = (
            document.get(
                "metadata_status",
                "MISSING",
            )
        )

        status_counter[
            metadata_status
        ] += 1

        issues, warnings = (
            audit_document(
                document,
                source_config,
                crops_config,
                download_registry,
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
            f"{document_id}"
        )

        print(
            f"Metadata status : "
            f"{metadata_status}"
        )

        print(
            f"Family          : "
            f"{document.get('document_family')}"
        )

        print(
            f"Scope           : "
            f"{document.get('knowledge_scope')}"
        )

        print(
            f"Region          : "
            f"{document.get('region')}"
        )

        print(
            f"Crops           : "
            f"{document.get('crop_entities')}"
        )

        print(
            f"Suggestions     : "
            f"{document.get('suggested_buckets')}"
        )

        if issues:

            print(
                f"Audit           : REVIEW"
            )

            print(
                f"Issues          : "
                f"{len(issues)}"
            )

        elif (
            metadata_status
            == "SKIPPED"
        ):

            print(
                "Audit           : SKIPPED_OK"
            )

        else:

            print(
                "Audit           : PASS"
            )

        if warnings:

            print(
                f"Warnings        : "
                f"{len(warnings)}"
            )

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print()
    print("=" * 78)
    print("METADATA AUDIT SUMMARY")
    print("=" * 78)

    for status, count in sorted(
        status_counter.items()
    ):

        print(
            f"{status:<20}: "
            f"{count}"
        )

    print()

    print(
        f"Issues found       : "
        f"{len(all_issues)}"
    )

    print(
        f"Warnings found     : "
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
            "No blocking metadata issues detected."
        )


if __name__ == "__main__":
    main()