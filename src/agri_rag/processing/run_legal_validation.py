import csv
import json
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml


# ============================================================
# PATHS
# ============================================================

DOCUMENT_DIR = Path(
    "data/agri_rag/registry/documents"
)

LEGAL_REGISTRY_FILE = Path(
    "src/agri_rag/config/legal_registry.yaml"
)

REVIEW_QUEUE_FILE = Path(
    "data/agri_rag/registry/review_queue.csv"
)

LEGAL_REPORT_FILE = Path(
    "data/agri_rag/registry/legal_validation_report.csv"
)

LEGAL_MANIFEST_FILE = Path(
    "data/agri_rag/registry/legal_validated_manifest.jsonl"
)


# ============================================================
# IO
# ============================================================

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


def load_yaml(path: Path) -> dict:

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        return yaml.safe_load(file) or {}


def load_review_queue() -> list:

    if not REVIEW_QUEUE_FILE.exists():
        return []

    with REVIEW_QUEUE_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        return list(
            csv.DictReader(file)
        )


# ============================================================
# DATE
# ============================================================

def parse_date(
    value,
):

    if not value:
        return None

    return datetime.strptime(
        value,
        "%Y-%m-%d",
    ).date()


# ============================================================
# REGISTRY INDEX
# ============================================================

def build_document_legal_index(
    legal_registry: dict,
) -> dict:

    result = {}

    roles = (
        legal_registry.get(
            "document_roles"
        )
        or {}
    )

    instruments = (
        legal_registry.get(
            "legal_instruments"
        )
        or {}
    )

    for document_id, role_info in (
        roles.items()
    ):

        instrument_key = (
            role_info.get(
                "legal_instrument"
            )
        )

        instrument = (
            instruments.get(
                instrument_key
            )
        )

        if not instrument:
            continue

        result[document_id] = {
            "instrument_key":
                instrument_key,

            "legal_role":
                role_info.get(
                    "legal_role"
                ),

            "instrument":
                instrument,
        }

    return result


# ============================================================
# VERIFY ONE DOCUMENT
# ============================================================

def validate_legal_document(
    document: dict,
    legal_info: dict,
    legal_registry: dict,
) -> dict:

    document_id = (
        document["document_id"]
    )

    instrument = (
        legal_info["instrument"]
    )

    verified_on = parse_date(
        legal_registry.get(
            "verified_on"
        )
    )

    recheck_days = (
        legal_registry
        .get(
            "verification_policy",
            {}
        )
        .get(
            "recheck_after_days",
            30,
        )
    )

    today = date.today()

    # ========================================================
    # 1. Registry itself must have verification date
    # ========================================================

    if not verified_on:

        return {
            "document_id":
                document_id,

            "status":
                "REVIEW_REQUIRED",

            "reason":
                "LEGAL_REGISTRY_VERIFICATION_DATE_MISSING",
        }

    # ========================================================
    # 2. Registry freshness
    # ========================================================

    expires_on = (
        verified_on
        + timedelta(
            days=recheck_days
        )
    )

    if today > expires_on:

        return {
            "document_id":
                document_id,

            "status":
                "REVERIFICATION_REQUIRED",

            "reason":
                "LEGAL_REGISTRY_STALE",

            "verified_on":
                verified_on.isoformat(),

            "reverify_after":
                expires_on.isoformat(),
        }

    # ========================================================
    # 3. Source / family checks
    # ========================================================

    if (
        document.get(
            "source_id"
        )
        != "S01_PPD"
    ):

        return {
            "document_id":
                document_id,

            "status":
                "REVIEW_REQUIRED",

            "reason":
                "LEGAL_DOCUMENT_SOURCE_UNEXPECTED",
        }

    if (
        document.get(
            "document_family"
        )
        not in {
            "regulation",
            "regulatory_attachment",
        }
    ):

        return {
            "document_id":
                document_id,

            "status":
                "REVIEW_REQUIRED",

            "reason":
                "LEGAL_DOCUMENT_FAMILY_INVALID",
        }

    if (
        document.get(
            "extraction_status"
        )
        != "SUCCESS"
    ):

        return {
            "document_id":
                document_id,

            "status":
                "REVIEW_REQUIRED",

            "reason":
                "LEGAL_EXTRACTION_NOT_SUCCESS",
        }

    if (
        document.get(
            "normalization_status"
        )
        != "SUCCESS"
    ):

        return {
            "document_id":
                document_id,

            "status":
                "REVIEW_REQUIRED",

            "reason":
                "LEGAL_NORMALIZATION_NOT_SUCCESS",
        }

    if (
        document.get(
            "metadata_status"
        )
        != "SUCCESS"
    ):

        return {
            "document_id":
                document_id,

            "status":
                "REVIEW_REQUIRED",

            "reason":
                "LEGAL_METADATA_NOT_SUCCESS",
        }

    # ========================================================
    # 4. Effective date
    # ========================================================

    effective_date = parse_date(
        instrument.get(
            "effective_date"
        )
    )

    if not effective_date:

        return {
            "document_id":
                document_id,

            "status":
                "REVIEW_REQUIRED",

            "reason":
                "LEGAL_EFFECTIVE_DATE_MISSING",
        }

    if today < effective_date:

        return {
            "document_id":
                document_id,

            "status":
                "NOT_YET_EFFECTIVE",

            "reason":
                "LEGAL_DOCUMENT_NOT_YET_EFFECTIVE",
        }

    # ========================================================
    # 5. Official sources must exist in registry
    # ========================================================

    official_sources = (
        instrument.get(
            "official_sources"
        )
        or []
    )

    if not official_sources:

        return {
            "document_id":
                document_id,

            "status":
                "REVIEW_REQUIRED",

            "reason":
                "OFFICIAL_LEGAL_SOURCE_MISSING",
        }

    # ========================================================
    # 6. Current legal status
    # ========================================================

    legal_status = (
        instrument.get(
            "legal_status"
        )
    )

    if legal_status not in {
        "EFFECTIVE",
        "EFFECTIVE_AS_AMENDED",
    }:

        return {
            "document_id":
                document_id,

            "status":
                "REVIEW_REQUIRED",

            "reason":
                "LEGAL_STATUS_NOT_ACCEPTABLE",

            "legal_status":
                legal_status,
        }

    usage_policy = (
        instrument.get(
            "usage_policy"
        )
        or {}
    )

    # ========================================================
    # 7. Successful legal validation
    # ========================================================

    return {
        "document_id":
            document_id,

        "status":
            "VERIFIED",

        "reason":
            "LEGAL_STATUS_VERIFIED",

        "legal_identifier":
            instrument.get(
                "identifier"
            ),

        "legal_role":
            legal_info.get(
                "legal_role"
            ),

        "legal_status":
            legal_status,

        "issued_date":
            instrument.get(
                "issued_date"
            ),

        "effective_date":
            instrument.get(
                "effective_date"
            ),

        "supersedes":
            instrument.get(
                "supersedes"
            )
            or [],

        "amended_by":
            instrument.get(
                "amended_by"
            )
            or [],

        "amends":
            instrument.get(
                "amends"
            )
            or [],

        "companion_documents":
            instrument.get(
                "companion_documents"
            )
            or [],

        "requires_legal_bundle":
            bool(
                usage_policy.get(
                    "requires_legal_bundle"
                )
            ),

        "legal_bundle_id":
            usage_policy.get(
                "bundle_id"
            ),

        "standalone_current_source":
            bool(
                usage_policy.get(
                    "standalone_current_source"
                )
            ),

        "official_sources":
            official_sources,

        "registry_verified_on":
            verified_on.isoformat(),

        "registry_reverify_after":
            expires_on.isoformat(),
    }


# ============================================================
# SAVE REPORT
# ============================================================

def write_report(
    results: list,
):

    fieldnames = [
        "document_id",
        "status",
        "reason",
        "legal_identifier",
        "legal_role",
        "legal_status",
        "issued_date",
        "effective_date",
        "legal_bundle_id",
        "requires_legal_bundle",
        "standalone_current_source",
        "registry_verified_on",
        "registry_reverify_after",
    ]

    with LEGAL_REPORT_FILE.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for result in results:

            writer.writerow({
                field:
                    result.get(field)
                for field in fieldnames
            })


def write_manifest(
    results: list,
):

    with LEGAL_MANIFEST_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        for result in results:

            file.write(
                json.dumps(
                    result,
                    ensure_ascii=False,
                )
            )

            file.write("\n")


# ============================================================
# MAIN
# ============================================================

def main():

    legal_registry = load_yaml(
        LEGAL_REGISTRY_FILE
    )

    legal_index = (
        build_document_legal_index(
            legal_registry
        )
    )

    review_queue = (
        load_review_queue()
    )

    legal_queue = [
        row
        for row in review_queue
        if (
            row.get("stage")
            == "LEGAL_VALIDATION"
        )
    ]

    print()
    print("=" * 78)
    print("AGRI RAG - LEGAL VALIDATION")
    print("=" * 78)

    print(
        f"Legal documents queued: "
        f"{len(legal_queue)}"
    )

    verified_count = 0
    review_count = 0
    reverification_count = 0
    failed_count = 0

    results = []

    for index, queue_row in enumerate(
        legal_queue,
        start=1,
    ):

        document_id = (
            queue_row[
                "document_id"
            ]
        )

        print()
        print("-" * 78)

        print(
            f"[{index}/{len(legal_queue)}] "
            f"{document_id}"
        )

        registry_path = (
            DOCUMENT_DIR
            / f"{document_id}.json"
        )

        try:

            if not registry_path.exists():

                result = {
                    "document_id":
                        document_id,

                    "status":
                        "REVIEW_REQUIRED",

                    "reason":
                        "DOCUMENT_REGISTRY_FILE_NOT_FOUND",
                }

            elif (
                document_id
                not in legal_index
            ):

                result = {
                    "document_id":
                        document_id,

                    "status":
                        "REVIEW_REQUIRED",

                    "reason":
                        "DOCUMENT_NOT_FOUND_IN_LEGAL_REGISTRY",
                }

            else:

                document = load_json(
                    registry_path
                )

                result = (
                    validate_legal_document(
                        document,
                        legal_index[
                            document_id
                        ],
                        legal_registry,
                    )
                )

                # =============================================
                # Update master document with legal metadata
                # =============================================

                document[
                    "legal_validation_status"
                ] = result.get(
                    "status"
                )

                document[
                    "legal_validation_reason"
                ] = result.get(
                    "reason"
                )

                if (
                    result.get(
                        "status"
                    )
                    == "VERIFIED"
                ):

                    document[
                        "legal_identifier"
                    ] = result.get(
                        "legal_identifier"
                    )

                    document[
                        "legal_role"
                    ] = result.get(
                        "legal_role"
                    )

                    document[
                        "legal_status"
                    ] = result.get(
                        "legal_status"
                    )

                    document[
                        "effective_date"
                    ] = result.get(
                        "effective_date"
                    )

                    document[
                        "supersedes"
                    ] = result.get(
                        "supersedes"
                    )

                    document[
                        "amended_by"
                    ] = result.get(
                        "amended_by"
                    )

                    document[
                        "legal_amends"
                    ] = result.get(
                        "amends"
                    )

                    document[
                        "legal_companion_documents"
                    ] = result.get(
                        "companion_documents"
                    )

                    document[
                        "legal_bundle_id"
                    ] = result.get(
                        "legal_bundle_id"
                    )

                    document[
                        "requires_legal_bundle"
                    ] = result.get(
                        "requires_legal_bundle"
                    )

                    document[
                        "standalone_current_source"
                    ] = result.get(
                        "standalone_current_source"
                    )

                    document[
                        "legal_official_sources"
                    ] = result.get(
                        "official_sources"
                    )

                    document[
                        "legal_verified_on"
                    ] = result.get(
                        "registry_verified_on"
                    )

                    document[
                        "legal_reverify_after"
                    ] = result.get(
                        "registry_reverify_after"
                    )

                save_json(
                    registry_path,
                    document,
                )

            results.append(
                result
            )

            status = result.get(
                "status"
            )

            print(
                f"Status              : "
                f"{status}"
            )

            print(
                f"Reason              : "
                f"{result.get('reason')}"
            )

            if status == "VERIFIED":

                verified_count += 1

                print(
                    f"Legal identifier    : "
                    f"{result.get('legal_identifier')}"
                )

                print(
                    f"Legal role          : "
                    f"{result.get('legal_role')}"
                )

                print(
                    f"Legal status        : "
                    f"{result.get('legal_status')}"
                )

                print(
                    f"Effective date      : "
                    f"{result.get('effective_date')}"
                )

                print(
                    f"Bundle              : "
                    f"{result.get('legal_bundle_id')}"
                )

                print(
                    f"Requires bundle     : "
                    f"{result.get('requires_legal_bundle')}"
                )

                print(
                    f"Standalone current  : "
                    f"{result.get('standalone_current_source')}"
                )

            elif (
                status
                == "REVERIFICATION_REQUIRED"
            ):

                reverification_count += 1

            else:

                review_count += 1

        except Exception as exc:

            failed_count += 1

            result = {
                "document_id":
                    document_id,

                "status":
                    "FAILED",

                "reason":
                    str(exc),
            }

            results.append(
                result
            )

            print(
                f"[FAILED] {exc}"
            )

    # ========================================================
    # Reports
    # ========================================================

    write_report(
        results
    )

    write_manifest(
        results
    )

    # ========================================================
    # Summary
    # ========================================================

    print()
    print()
    print("=" * 78)
    print("LEGAL VALIDATION SUMMARY")
    print("=" * 78)

    print(
        f"Queued documents        : "
        f"{len(legal_queue)}"
    )

    print(
        f"VERIFIED                : "
        f"{verified_count}"
    )

    print(
        f"REVERIFICATION_REQUIRED : "
        f"{reverification_count}"
    )

    print(
        f"REVIEW_REQUIRED         : "
        f"{review_count}"
    )

    print(
        f"FAILED                  : "
        f"{failed_count}"
    )

    print()
    print(
        f"Report                   : "
        f"{LEGAL_REPORT_FILE}"
    )

    print(
        f"Manifest                 : "
        f"{LEGAL_MANIFEST_FILE}"
    )


if __name__ == "__main__":
    main()