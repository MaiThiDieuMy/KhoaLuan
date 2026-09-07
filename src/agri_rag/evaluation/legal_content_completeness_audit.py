import csv
import json
import re
import unicodedata
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

REPORT_FILE = Path(
    "data/agri_rag/registry/"
    "legal_content_completeness_report.csv"
)

READINESS_FILE = Path(
    "data/agri_rag/registry/"
    "legal_bundle_readiness.json"
)


# ============================================================
# BUNDLE
# ============================================================

BUNDLE_ID = (
    "PESTICIDE_LIST_VN_CURRENT"
)


# ============================================================
# REQUIRED LEGAL CONTENT
#
# 5 tài liệu nội dung chính để xây bundle hiện hành.
#
# DOC0001 và DOC0002 là HTML notice/provenance,
# không thay thế các PDF/phụ lục.
#
# expected_identifier:
#   giúp chống gắn nhầm document vào TT75/TT28.
#
# expected_family:
#   kiểm tra metadata classification.
#
# required_all:
#   tất cả cụm phải có.
#
# required_any_groups:
#   với mỗi group, ít nhất một cách diễn đạt phải có.
# ============================================================

REQUIRED_CONTENT_ROLES = {

    "BASE_INSTRUMENT_PDF": {

        "expected_document_id":
            "DOC0013",

        "expected_identifier":
            "75/2025/TT-BNNMT",

        "expected_family":
            "regulation",

        "required_all": [
            "THÔNG TƯ",
            "Danh mục thuốc bảo vệ thực vật",
        ],

        "required_any_groups": [
            [
                "được phép sử dụng tại Việt Nam",
                "được phép sử dụng",
            ],

            [
                "cấm sử dụng tại Việt Nam",
                "cấm sử dụng",
            ],
        ],
    },


    "BASE_ALLOWED_LIST": {

        "expected_document_id":
            "DOC0003",

        "expected_identifier":
            "75/2025/TT-BNNMT",

        "expected_family":
            "regulatory_attachment",

        "required_all": [
            "Phụ lục I",
            "DANH MỤC THUỐC BẢO VỆ THỰC VẬT",
        ],

        "required_any_groups": [
            [
                "ĐƯỢC PHÉP SỬ DỤNG TẠI VIỆT NAM",
                "được phép sử dụng tại Việt Nam",
            ],

            [
                "HOẠT CHẤT",
                "COMMON NAME",
            ],
        ],
    },


    "BASE_BANNED_LIST": {

        "expected_document_id":
            "DOC0014",

        "expected_identifier":
            "75/2025/TT-BNNMT",

        "expected_family":
            "regulatory_attachment",

        "required_all": [
            "Phụ lục II",
            "DANH MỤC THUỐC BẢO VỆ THỰC VẬT",
        ],

        "required_any_groups": [
            [
                "CẤM SỬ DỤNG TẠI VIỆT NAM",
                "cấm sử dụng tại Việt Nam",
            ],

            [
                "HOẠT CHẤT",
                "COMMON NAME",
            ],
        ],
    },


    "AMENDMENT_INSTRUMENT_PDF": {

        "expected_document_id":
            "DOC0015",

        "expected_identifier":
            "28/2026/TT-BNNMT",

        "expected_family":
            "regulation",

        "required_all": [
            "THÔNG TƯ",
            "75/2025/TT-BNNMT",
        ],

        "required_any_groups": [
            [
                "Sửa đổi, bổ sung",
                "sửa đổi bổ sung",
                "sửa đổi, bổ sung Thông tư",
            ],
        ],
    },


    "AMENDMENT_APPENDICES": {

        "expected_document_id":
            "DOC0016",

        "expected_identifier":
            "28/2026/TT-BNNMT",

        "expected_family":
            "regulatory_attachment",

        # ----------------------------------------------------
        # TT28 official attachment contains:
        #
        # Appendix I:
        #   - registration/applicant information changes
        #   - active ingredient information changes
        #   - voluntary withdrawals
        #
        # Appendix II:
        #   - pesticides registered into the allowed list
        #
        # Không bắt exact phrase "đăng ký bổ sung"
        # vì official PDF dùng tiêu đề
        # "ĐĂNG KÝ VÀO DANH MỤC..."
        # ----------------------------------------------------

        "required_all": [
            "Phụ lục I",
            "thay đổi thông tin",
            "Phụ lục II",
            "THUỐC BẢO VỆ THỰC VẬT",
        ],

        "required_any_groups": [

            # -----------------------------------------------
            # Withdrawal section
            # -----------------------------------------------

            [
                "tự nguyện rút khỏi Danh mục",
                "rút khỏi Danh mục thuốc bảo vệ thực vật được phép sử dụng",
                "tự nguyện rút khỏi",
            ],

            # -----------------------------------------------
            # Appendix II additions
            # -----------------------------------------------

            [
                "ĐĂNG KÝ VÀO DANH MỤC THUỐC BẢO VỆ THỰC VẬT ĐƯỢC PHÉP SỬ DỤNG",
                "đăng ký vào Danh mục thuốc bảo vệ thực vật được phép sử dụng",
                "đăng ký vào danh mục",
                "đăng ký bổ sung vào Danh mục",
            ],
        ],
    },
}


# ============================================================
# PROVENANCE DOCUMENTS
# ============================================================

PROVENANCE_ROLES = {
    "BASE_INSTRUMENT_NOTICE",
    "AMENDMENT_INSTRUMENT_NOTICE",
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


# ============================================================
# TEXT NORMALIZATION FOR AUDIT
# ============================================================

def normalize_for_search(
    text: str,
) -> str:
    """
    Chỉ dùng cho content audit.

    Không thay đổi normalized corpus.

    Mục đích:
    - Unicode NFC
    - case-insensitive
    - NBSP -> normal space
    - mọi newline/tab/multiple spaces -> single space

    Việc collapse whitespace rất quan trọng với PDF,
    vì tiêu đề có thể bị extract thành nhiều dòng.
    """

    if not text:
        return ""

    value = unicodedata.normalize(
        "NFC",
        text,
    )

    value = value.replace(
        "\u00a0",
        " ",
    )

    value = value.casefold()

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def phrase_present(
    searchable_text: str,
    phrase: str,
) -> bool:

    normalized_phrase = (
        normalize_for_search(
            phrase
        )
    )

    return (
        normalized_phrase
        in searchable_text
    )


# ============================================================
# LEGAL ROLE INDEX
# ============================================================

def build_legal_role_index(
    legal_registry: dict,
) -> dict:

    result = {}

    document_roles = (
        legal_registry.get(
            "document_roles"
        )
        or {}
    )

    for document_id, role_info in (
        document_roles.items()
    ):

        role = (
            role_info.get(
                "legal_role"
            )
        )

        if not role:
            continue

        result.setdefault(
            role,
            [],
        )

        result[role].append(
            document_id
        )

    return result


# ============================================================
# AUDIT REQUIRED DOCUMENT
# ============================================================

def audit_required_document(
    role: str,
    rule: dict,
    role_index: dict,
):

    expected_document_id = (
        rule[
            "expected_document_id"
        ]
    )

    result = {

        "role":
            role,

        "document_id":
            expected_document_id,

        "status":
            "PASS",

        "issues":
            [],

        "warnings":
            [],
    }

    # ========================================================
    # 1. LEGAL REGISTRY ROLE
    # ========================================================

    registered_ids = (
        role_index.get(
            role,
            []
        )
    )

    if not registered_ids:

        result["issues"].append(
            "ROLE_MISSING_FROM_LEGAL_REGISTRY"
        )

        result["status"] = (
            "FAIL"
        )

        return result

    if (
        expected_document_id
        not in registered_ids
    ):

        result["issues"].append(
            "EXPECTED_DOCUMENT_NOT_REGISTERED_FOR_ROLE"
        )

    if len(
        registered_ids
    ) > 1:

        result["warnings"].append(
            "MULTIPLE_DOCUMENTS_REGISTERED_FOR_ROLE"
        )

    # ========================================================
    # 2. MASTER DOCUMENT RECORD
    # ========================================================

    registry_path = (
        DOCUMENT_DIR
        / f"{expected_document_id}.json"
    )

    if not registry_path.exists():

        result["issues"].append(
            "DOCUMENT_REGISTRY_FILE_NOT_FOUND"
        )

        result["status"] = (
            "FAIL"
        )

        return result

    document = load_json(
        registry_path
    )

    # ========================================================
    # 3. SOURCE
    # ========================================================

    if (
        document.get(
            "source_id"
        )
        != "S01_PPD"
    ):

        result["issues"].append(
            "LEGAL_SOURCE_NOT_PPD"
        )

    # ========================================================
    # 4. LEGAL VALIDATION
    # ========================================================

    if (
        document.get(
            "legal_validation_status"
        )
        != "VERIFIED"
    ):

        result["issues"].append(
            "LEGAL_VALIDATION_NOT_VERIFIED"
        )

    actual_role = (
        document.get(
            "legal_role"
        )
        or
        document.get(
            "legal_role_hint"
        )
    )

    if actual_role != role:

        result["issues"].append(
            "LEGAL_ROLE_MISMATCH"
        )

    # ========================================================
    # 5. LEGAL IDENTIFIER
    # ========================================================

    expected_identifier = (
        rule.get(
            "expected_identifier"
        )
    )

    actual_identifier = (
        document.get(
            "legal_identifier"
        )
        or
        document.get(
            "legal_identifier_hint"
        )
    )

    if (
        expected_identifier
        and
        actual_identifier
        != expected_identifier
    ):

        result["issues"].append(
            "LEGAL_IDENTIFIER_MISMATCH"
        )

    # ========================================================
    # 6. BUNDLE
    # ========================================================

    bundle_id = (
        document.get(
            "legal_bundle_id"
        )
    )

    if (
        bundle_id
        and
        bundle_id != BUNDLE_ID
    ):

        result["issues"].append(
            "LEGAL_BUNDLE_ID_MISMATCH"
        )

    # ========================================================
    # 7. METADATA
    # ========================================================

    if (
        document.get(
            "metadata_status"
        )
        != "SUCCESS"
    ):

        result["issues"].append(
            "METADATA_NOT_SUCCESS"
        )

    expected_family = (
        rule.get(
            "expected_family"
        )
    )

    if (
        expected_family
        and
        document.get(
            "document_family"
        )
        != expected_family
    ):

        result["issues"].append(
            "DOCUMENT_FAMILY_MISMATCH"
        )

    if (
        document.get(
            "knowledge_scope"
        )
        != "regulatory"
    ):

        result["issues"].append(
            "LEGAL_KNOWLEDGE_SCOPE_INVALID"
        )

    suggested_buckets = (
        document.get(
            "suggested_buckets"
        )
        or []
    )

    if suggested_buckets != [
        "B06_PESTICIDE_LEGAL"
    ]:

        result["issues"].append(
            "LEGAL_BUCKET_SCOPE_INVALID"
        )

    # ========================================================
    # 8. EXTRACTION
    # ========================================================

    if (
        document.get(
            "extraction_status"
        )
        != "SUCCESS"
    ):

        result["issues"].append(
            "EXTRACTION_NOT_SUCCESS"
        )

    # ========================================================
    # 9. NORMALIZATION
    # ========================================================

    if (
        document.get(
            "normalization_status"
        )
        != "SUCCESS"
    ):

        result["issues"].append(
            "NORMALIZATION_NOT_SUCCESS"
        )

    normalized_path_value = (
        document.get(
            "normalized_path"
        )
    )

    if not normalized_path_value:

        result["issues"].append(
            "NORMALIZED_PATH_MISSING"
        )

        result["status"] = (
            "FAIL"
        )

        return result

    normalized_path = Path(
        normalized_path_value
    )

    if not normalized_path.exists():

        result["issues"].append(
            "NORMALIZED_FILE_NOT_FOUND"
        )

        result["status"] = (
            "FAIL"
        )

        return result

    # ========================================================
    # 10. LOAD CONTENT
    # ========================================================

    text = normalized_path.read_text(
        encoding="utf-8"
    )

    result[
        "char_count"
    ] = len(text)

    if len(text) < 200:

        result["issues"].append(
            "LEGAL_CONTENT_TOO_SHORT"
        )

    searchable = (
        normalize_for_search(
            text
        )
    )

    # ========================================================
    # 11. REQUIRED ALL
    # ========================================================

    missing_required = []

    for phrase in (
        rule.get(
            "required_all"
        )
        or []
    ):

        if not phrase_present(
            searchable,
            phrase,
        ):

            missing_required.append(
                phrase
            )

    if missing_required:

        result["issues"].append(
            "REQUIRED_CONTENT_MISSING"
        )

        result[
            "missing_required_phrases"
        ] = (
            missing_required
        )

    # ========================================================
    # 12. REQUIRED ANY GROUPS
    #
    # Mỗi group đại diện cho một semantic requirement.
    #
    # Ví dụ amendment appendix:
    #
    # group 1 = withdrawal content
    # group 2 = addition/registration content
    #
    # Chỉ cần một cách diễn đạt chính thức trong mỗi group.
    # ========================================================

    failed_groups = []

    matched_groups = []

    for group in (
        rule.get(
            "required_any_groups"
        )
        or []
    ):

        matched_phrase = None

        for phrase in group:

            if phrase_present(
                searchable,
                phrase,
            ):

                matched_phrase = (
                    phrase
                )

                break

        if matched_phrase:

            matched_groups.append(
                matched_phrase
            )

        else:

            failed_groups.append(
                group
            )

    result[
        "matched_content_groups"
    ] = matched_groups

    if failed_groups:

        result["issues"].append(
            "EXPECTED_CONTENT_GROUP_MISSING"
        )

        result[
            "missing_content_groups"
        ] = failed_groups

    # ========================================================
    # FINAL STATUS
    # ========================================================

    if result["issues"]:

        result["status"] = (
            "FAIL"
        )

    return result


# ============================================================
# AUDIT PROVENANCE DOCUMENTS
# ============================================================

def audit_provenance_documents(
    role_index: dict,
):

    results = []

    for role in sorted(
        PROVENANCE_ROLES
    ):

        document_ids = (
            role_index.get(
                role,
                []
            )
        )

        for document_id in (
            document_ids
        ):

            result = {

                "role":
                    role,

                "document_id":
                    document_id,

                "status":
                    "PASS",

                "issues":
                    [],

                "warnings":
                    [],
            }

            registry_path = (
                DOCUMENT_DIR
                / f"{document_id}.json"
            )

            if not registry_path.exists():

                result[
                    "issues"
                ].append(
                    "DOCUMENT_REGISTRY_FILE_NOT_FOUND"
                )

                result[
                    "status"
                ] = "FAIL"

                results.append(
                    result
                )

                continue

            document = load_json(
                registry_path
            )

            if (
                document.get(
                    "legal_validation_status"
                )
                != "VERIFIED"
            ):

                result[
                    "issues"
                ].append(
                    "LEGAL_VALIDATION_NOT_VERIFIED"
                )

            if (
                document.get(
                    "extraction_status"
                )
                != "SUCCESS"
            ):

                result[
                    "issues"
                ].append(
                    "EXTRACTION_NOT_SUCCESS"
                )

            if (
                document.get(
                    "normalization_status"
                )
                != "SUCCESS"
            ):

                result[
                    "issues"
                ].append(
                    "NORMALIZATION_NOT_SUCCESS"
                )

            if (
                document.get(
                    "metadata_status"
                )
                != "SUCCESS"
            ):

                result[
                    "issues"
                ].append(
                    "METADATA_NOT_SUCCESS"
                )

            if result[
                "issues"
            ]:

                result[
                    "status"
                ] = "FAIL"

            results.append(
                result
            )

    return results


# ============================================================
# WRITE REPORT
# ============================================================

def write_report(
    results: list,
):

    fieldnames = [
        "role",
        "document_id",
        "status",
        "char_count",
        "issues",
        "warnings",
        "matched_content_groups",
    ]

    with REPORT_FILE.open(
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

                "role":
                    result.get(
                        "role"
                    ),

                "document_id":
                    result.get(
                        "document_id"
                    ),

                "status":
                    result.get(
                        "status"
                    ),

                "char_count":
                    result.get(
                        "char_count"
                    ),

                "issues":
                    " | ".join(
                        result.get(
                            "issues"
                        )
                        or []
                    ),

                "warnings":
                    " | ".join(
                        result.get(
                            "warnings"
                        )
                        or []
                    ),

                "matched_content_groups":
                    " | ".join(
                        result.get(
                            "matched_content_groups"
                        )
                        or []
                    ),
            })


# ============================================================
# MAIN
# ============================================================

def main():

    legal_registry = load_yaml(
        LEGAL_REGISTRY_FILE
    )

    role_index = (
        build_legal_role_index(
            legal_registry
        )
    )

    print()
    print("=" * 78)
    print(
        "RAG LEGAL CONTENT COMPLETENESS AUDIT V2"
    )
    print("=" * 78)

    print(
        f"Bundle ID: "
        f"{BUNDLE_ID}"
    )

    print(
        f"Required content roles: "
        f"{len(REQUIRED_CONTENT_ROLES)}"
    )

    print()

    required_results = []

    # ========================================================
    # REQUIRED DOCUMENTS
    # ========================================================

    for index, (
        role,
        rule,
    ) in enumerate(
        REQUIRED_CONTENT_ROLES.items(),
        start=1,
    ):

        result = (
            audit_required_document(
                role,
                rule,
                role_index,
            )
        )

        required_results.append(
            result
        )

        print("-" * 78)

        print(
            f"[{index}/"
            f"{len(REQUIRED_CONTENT_ROLES)}] "
            f"{role}"
        )

        print(
            f"Document       : "
            f"{result['document_id']}"
        )

        print(
            f"Status         : "
            f"{result['status']}"
        )

        print(
            f"Characters     : "
            f"{result.get('char_count')}"
        )

        print(
            f"Issues         : "
            f"{result.get('issues')}"
        )

        print(
            f"Warnings       : "
            f"{result.get('warnings')}"
        )

        print(
            f"Matched groups : "
            f"{result.get('matched_content_groups')}"
        )

        if result.get(
            "missing_required_phrases"
        ):

            print(
                "Missing text   : "
                f"{result['missing_required_phrases']}"
            )

        if result.get(
            "missing_content_groups"
        ):

            print(
                "Missing groups : "
                f"{result['missing_content_groups']}"
            )

    # ========================================================
    # PROVENANCE
    # ========================================================

    provenance_results = (
        audit_provenance_documents(
            role_index
        )
    )

    all_results = (
        required_results
        + provenance_results
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    required_pass = sum(
        1
        for result in required_results
        if (
            result[
                "status"
            ]
            == "PASS"
        )
    )

    required_fail = (
        len(
            required_results
        )
        - required_pass
    )

    provenance_pass = sum(
        1
        for result in provenance_results
        if (
            result[
                "status"
            ]
            == "PASS"
        )
    )

    provenance_fail = (
        len(
            provenance_results
        )
        - provenance_pass
    )

    blocking_issues = sum(
        len(
            result.get(
                "issues"
            )
            or []
        )
        for result in required_results
    )

    warnings = sum(
        len(
            result.get(
                "warnings"
            )
            or []
        )
        for result in all_results
    )

    # ========================================================
    # READY means:
    #
    # - all five required content documents passed
    # - provenance documents passed
    # - no blocking content issue
    #
    # READY DOES NOT mean:
    # current pesticide records have been consolidated.
    # ========================================================

    bundle_ready = (
        required_fail == 0
        and
        provenance_fail == 0
        and
        blocking_issues == 0
    )

    readiness = {

        "bundle_id":
            BUNDLE_ID,

        "audit_version":
            "LEGAL_CONTENT_COMPLETENESS_V2",

        "status":
            (
                "READY"
                if bundle_ready
                else "NOT_READY"
            ),

        "required_roles":
            len(
                REQUIRED_CONTENT_ROLES
            ),

        "required_pass":
            required_pass,

        "required_fail":
            required_fail,

        "provenance_documents":
            len(
                provenance_results
            ),

        "provenance_pass":
            provenance_pass,

        "provenance_fail":
            provenance_fail,

        "blocking_issues":
            blocking_issues,

        "warnings":
            warnings,

        "required_documents": [

            {
                "role":
                    result[
                        "role"
                    ],

                "document_id":
                    result[
                        "document_id"
                    ],

                "status":
                    result[
                        "status"
                    ],

                "matched_content_groups":
                    result.get(
                        "matched_content_groups"
                    )
                    or [],
            }

            for result
            in required_results
        ],

        "important_note": (
            "READY means all required legal source "
            "documents are present, structurally "
            "validated, and legally verified. "
            "It does not mean the pesticide lists "
            "have already been consolidated into "
            "current legal records."
        ),
    }

    # ========================================================
    # OUTPUT
    # ========================================================

    write_report(
        all_results
    )

    save_json(
        READINESS_FILE,
        readiness,
    )

    print()
    print()
    print("=" * 78)
    print(
        "LEGAL CONTENT COMPLETENESS SUMMARY"
    )
    print("=" * 78)

    print(
        f"Required roles       : "
        f"{len(REQUIRED_CONTENT_ROLES)}"
    )

    print(
        f"Required PASS        : "
        f"{required_pass}"
    )

    print(
        f"Required FAIL        : "
        f"{required_fail}"
    )

    print(
        f"Provenance documents : "
        f"{len(provenance_results)}"
    )

    print(
        f"Provenance PASS      : "
        f"{provenance_pass}"
    )

    print(
        f"Provenance FAIL      : "
        f"{provenance_fail}"
    )

    print(
        f"Blocking issues      : "
        f"{blocking_issues}"
    )

    print(
        f"Warnings             : "
        f"{warnings}"
    )

    print(
        f"Bundle readiness     : "
        f"{readiness['status']}"
    )

    print()

    print(
        f"Report               : "
        f"{REPORT_FILE}"
    )

    print(
        f"Readiness            : "
        f"{READINESS_FILE}"
    )

    print()

    if bundle_ready:

        print(
            "Legal source corpus is complete "
            "for bundle construction."
        )

        print(
            "NOTE: Current pesticide records "
            "have NOT yet been consolidated."
        )

    else:

        print(
            "Legal source corpus is NOT ready "
            "for bundle construction."
        )


if __name__ == "__main__":
    main()