import argparse
import hashlib
import json
import re
import unicodedata
from copy import deepcopy
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:
    import fitz


# ============================================================
# PATHS
# ============================================================

DATA_DIR = Path("data/agri_rag")
REGISTRY_DIR = DATA_DIR / "registry"
DOCUMENT_DIR = REGISTRY_DIR / "documents"

LEGAL_BUNDLE_DIR = (
    DATA_DIR
    / "legal_bundles"
    / "PESTICIDE_LIST_VN_CURRENT"
)

MANIFEST_FILE = LEGAL_BUNDLE_DIR / "manifest.json"

CURRENT_RECORDS_FILE = (
    LEGAL_BUNDLE_DIR
    / "current_legal_records.jsonl"
)

CONSOLIDATION_REPORT_FILE = (
    LEGAL_BUNDLE_DIR
    / "legal_consolidation_report.json"
)


# ============================================================
# LEGAL SOURCES
# ============================================================

BASE_DOC = "DOC0003"
AMENDMENT_DOC = "DOC0016"

BASE_EFFECTIVE_DATE = "2026-02-10"
AMENDMENT_EFFECTIVE_DATE = "2026-08-15"


# ============================================================
# TARGET CROPS
# ============================================================

CROPS = {
    "cai_xanh": {
        "crop_name": "Cải xanh",
        "aliases": [
            "cải xanh",
            "cải bẹ xanh",
        ],
    },

    "ngo": {
        "crop_name": "Ngò / ngò rí",
        "aliases": [
            "rau mùi",
            "ngò rí",
            "ngò",
        ],
    },

    "cai_cuc": {
        "crop_name": "Cải cúc / tần ô",
        "aliases": [
            "cải cúc",
            "tần ô",
        ],
    },

    "rau_muong": {
        "crop_name": "Rau muống",
        "aliases": [
            "rau muống",
        ],
    },

    "xa_lach": {
        "crop_name": "Xà lách",
        "aliases": [
            "xà lách",
        ],
    },
}


# ============================================================
# IO
# ============================================================

def load_json(path: Path):

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        return json.load(file)


def save_json(path: Path, data):

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

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


def write_jsonl(path: Path, rows: list):

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:

        for row in rows:

            file.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                )
            )

            file.write("\n")


# ============================================================
# TEXT HELPERS
# ============================================================

def clean_cell(value):

    if value is None:
        return ""

    value = unicodedata.normalize(
        "NFC",
        str(value),
    )

    value = value.replace(
        "\u00a0",
        " ",
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def ascii_fold(value):

    value = clean_cell(
        value
    ).casefold()

    value = unicodedata.normalize(
        "NFD",
        value,
    )

    value = "".join(
        character
        for character in value
        if not unicodedata.combining(character)
    )

    return value


def canonical_key(value):

    return re.sub(
        r"[^a-z0-9]+",
        "",
        ascii_fold(value),
    )


def sha256_text(value):

    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def normalize_row(row):

    result = [
        clean_cell(cell)
        for cell in row
    ]

    if len(result) < 5:

        result.extend(
            [""] * (5 - len(result))
        )

    return result[:5]


def is_numeric_row_id(value):

    return bool(
        re.fullmatch(
            r"\d+\.?",
            clean_cell(value),
        )
    )


def append_cell_text(old, new):

    old = clean_cell(old)
    new = clean_cell(new)

    if not old:
        return new

    if not new:
        return old

    if new in old:
        return old

    return f"{old} {new}"


# ============================================================
# PDF
# ============================================================

def load_document_registry(document_id):

    path = (
        DOCUMENT_DIR
        / f"{document_id}.json"
    )

    if not path.exists():

        raise RuntimeError(
            f"{document_id}: registry missing."
        )

    return load_json(path)


def open_pdf(document_id):

    record = load_document_registry(
        document_id
    )

    if (
        record.get("extraction_status")
        != "SUCCESS"
    ):

        raise RuntimeError(
            f"{document_id}: extraction is not SUCCESS."
        )

    raw_path = Path(
        record["raw_path"]
    )

    if not raw_path.exists():

        raise RuntimeError(
            f"{document_id}: raw PDF missing."
        )

    return fitz.open(raw_path)


def find_tables(page):

    if not hasattr(
        page,
        "find_tables",
    ):

        raise RuntimeError(
            "PyMuPDF find_tables() unavailable."
        )

    return list(
        page.find_tables().tables
    )


# ============================================================
# CROP MATCH
# ============================================================

def alias_regex(alias):

    alias = (
        unicodedata.normalize(
            "NFC",
            alias,
        )
        .casefold()
    )

    return re.compile(
        rf"(?<!\w)"
        rf"{re.escape(alias)}"
        rf"(?!\w)",
        re.UNICODE,
    )


def crop_matches_for_text(text):

    searchable = (
        unicodedata.normalize(
            "NFC",
            text or "",
        )
        .casefold()
    )

    result = []

    for crop_id, crop_info in CROPS.items():

        aliases = []

        for alias in crop_info["aliases"]:

            if alias_regex(alias).search(
                searchable
            ):

                aliases.append(alias)

        if aliases:

            result.append({
                "crop_id":
                    crop_id,

                "crop_name":
                    crop_info["crop_name"],

                "aliases":
                    sorted(set(aliases)),
            })

    return result


# ============================================================
# TARGET PEST PARSER
#
# Example 1:
#
# sâu xanh bướm trắng, bọ nhảy, rệp/cải xanh
#
# -> sâu xanh bướm trắng | bọ nhảy | rệp
#
#
# Example 2:
#
# rỉ sắt/đậu đũa, rỉ trắng/rau muống
#
# -> rỉ trắng
#
#
# Example 3:
#
# cỏ/lạc, ngô, rau mùi, rau muống
#
# -> cỏ
# ============================================================

def extract_pests_for_crop(
    clause,
    crop_id,
):

    segments = [
        clean_cell(item)
        for item in re.split(
            r"\s*,\s*",
            clause,
        )
        if clean_cell(item)
    ]

    crop_info = CROPS[
        crop_id
    ]

    target_indices = []

    for index, segment in enumerate(
        segments
    ):

        searchable = (
            unicodedata.normalize(
                "NFC",
                segment,
            )
            .casefold()
        )

        if any(
            alias_regex(alias).search(
                searchable
            )
            for alias in crop_info["aliases"]
        ):

            target_indices.append(index)

    pests = []

    for target_index in target_indices:

        slash_index = None

        for index in range(
            target_index,
            -1,
            -1,
        ):

            if "/" in segments[index]:

                slash_index = index
                break

        if slash_index is None:
            continue

        slash_segment = (
            segments[
                slash_index
            ]
        )

        left = clean_cell(
            slash_segment.split(
                "/",
                1,
            )[0]
        )

        group_start = (
            slash_index
        )

        while group_start > 0:

            previous = (
                segments[
                    group_start - 1
                ]
            )

            if "/" in previous:
                break

            group_start -= 1

        prefix_pests = []

        for index in range(
            group_start,
            slash_index,
        ):

            value = clean_cell(
                segments[index]
            )

            if value:
                prefix_pests.append(value)

        if left:
            prefix_pests.append(left)

        pests.extend(
            prefix_pests
        )

    return sorted(
        set(
            clean_cell(item)
            for item in pests
            if clean_cell(item)
        )
    )


def crop_match_details(
    pest_crop_text,
):

    crop_matches = (
        crop_matches_for_text(
            pest_crop_text
        )
    )

    if not crop_matches:
        return []

    semicolon_clauses = [
        clean_cell(item)
        for item in re.split(
            r"\s*;\s*",
            pest_crop_text,
        )
        if clean_cell(item)
    ]

    result = []

    for crop_match in crop_matches:

        crop_id = (
            crop_match[
                "crop_id"
            ]
        )

        matched_clauses = []
        target_pests = []

        for clause in semicolon_clauses:

            if not any(
                item["crop_id"] == crop_id
                for item in crop_matches_for_text(
                    clause
                )
            ):

                continue

            matched_clauses.append(
                clause
            )

            target_pests.extend(
                extract_pests_for_crop(
                    clause,
                    crop_id,
                )
            )

        result.append({
            "crop_id":
                crop_id,

            "crop_name":
                crop_match[
                    "crop_name"
                ],

            "aliases":
                crop_match[
                    "aliases"
                ],

            "matched_clauses":
                matched_clauses,

            "target_pests":
                sorted(
                    set(
                        target_pests
                    )
                ),

            "target_pest_text":
                " | ".join(
                    sorted(
                        set(
                            target_pests
                        )
                    )
                ),

            "target_pest_parse_status":
                (
                    "PARSED"
                    if target_pests
                    else "CLAUSE_ONLY"
                ),
        })

    return result


# ============================================================
# TABLE HEADER DETECTION
# ============================================================

def row_is_registration_header(row):

    text = ascii_fold(
        " ".join(
            normalize_row(row)
        )
    )

    marker_count = sum(
        marker in text
        for marker in [
            "hoat chat",
            "common name",
            "ten thuong pham",
            "trade name",
            "doi tuong phong tru",
            "pest/crop",
            "to chuc de nghi dang ky",
            "applicant",
        ]
    )

    return marker_count >= 2


def looks_like_category_row(
    row,
):

    cells = normalize_row(row)

    joined = ascii_fold(
        " ".join(cells)
    )

    if (
        "thuoc tru sau"
        in joined
        or
        "thuoc tru benh"
        in joined
        or
        "thuoc tru co"
        in joined
        or
        "thuoc dieu hoa sinh truong"
        in joined
        or
        "chat dan du"
        in joined
    ):

        if not any(
            cells[index]
            for index in [
                2,
                3,
                4,
            ]
        ):

            return True

    return False


# ============================================================
# REGISTRATION TABLE PARSER
#
# Used for:
# DOC0003 TT75 BASE
# DOC0016 TT28 ADD
#
# KEY CHANGE:
# TT75 is parsed sequentially from page 1 → 355.
# We no longer parse only selected pages.
#
# That preserves active ingredient / applicant context across
# page boundaries.
# ============================================================

def parse_registration_pages(
    pdf,
    page_numbers,
    document_id,
    legal_action,
):

    records = []

    current_active = ""
    current_row_number = ""

    last_record = None

    table_crop_hit_pages = {
        crop_id: set()
        for crop_id in CROPS
    }

    previous_page = None

    for page_number in page_numbers:

        # ----------------------------------------------------
        # Do not carry context over an intentional page gap.
        # ----------------------------------------------------

        if (
            previous_page is not None
            and
            page_number
            != previous_page + 1
        ):

            current_active = ""
            current_row_number = ""
            last_record = None

        previous_page = page_number

        # Tracks the first real registration row on this page.
        # Used to safely detect a row continued from the
        # previous PDF page.
        page_has_registration_row = False

        page = pdf[
            page_number - 1
        ]

        tables = find_tables(
            page
        )

        for table in tables:

            data = table.extract()

            for raw_row in data:

                if len(raw_row) < 5:
                    continue

                if row_is_registration_header(
                    raw_row
                ):
                    continue

                if looks_like_category_row(
                    raw_row
                ):

                    current_active = ""
                    current_row_number = ""
                    last_record = None

                    continue

                (
                    number,
                    active,
                    trade,
                    pest_crop,
                    applicant,
                ) = normalize_row(
                    raw_row
                )

                # Ignore completely empty rows.
                if not any([
                    number,
                    active,
                    trade,
                    pest_crop,
                    applicant,
                ]):
                    continue

                # ------------------------------------------------
                # Observe official table cells containing exact
                # crop aliases before any reconstruction.
                # ------------------------------------------------

                for crop_match in (
                    crop_matches_for_text(
                        pest_crop
                    )
                ):

                    table_crop_hit_pages[
                        crop_match[
                            "crop_id"
                        ]
                    ].add(
                        page_number
                    )

                # =================================================
                # CROSS-PAGE CONTINUATION
                #
                # Example verified in DOC0003:
                #
                # PAGE 77:
                #   TT 540
                #   Dinotefuran ...
                #   <trade name starts here>
                #   applicant present
                #
                # PAGE 78 first row:
                #   TT=""
                #   active=""
                #   trade="1GR, 20WP, 20SG, 100SL"
                #   pest_crop="..."
                #   applicant=""
                #
                # This is not a new legal registration.
                # It continues the last row from page 77.
                # =================================================

                is_cross_page_continuation = (
                    not page_has_registration_row
                    and
                    last_record is not None
                    and
                    bool(
                        last_record.get(
                            "source_pages"
                        )
                    )
                    and
                    page_number
                    != last_record[
                        "source_pages"
                    ][-1]
                    and
                    not number
                    and
                    not active
                    and
                    bool(trade)
                    and
                    not applicant
                )

                if is_cross_page_continuation:

                    if (
                        page_number
                        not in last_record[
                            "source_pages"
                        ]
                    ):

                        last_record[
                            "source_pages"
                        ].append(
                            page_number
                        )

                    last_record[
                        "trade_name"
                    ] = append_cell_text(
                        last_record[
                            "trade_name"
                        ],
                        trade,
                    )

                    if pest_crop:

                        last_record[
                            "pest_crop"
                        ] = append_cell_text(
                            last_record[
                                "pest_crop"
                            ],
                            pest_crop,
                        )

                    last_record.setdefault(
                        "parser_notes",
                        [],
                    ).append({
                        "type":
                            "CROSS_PAGE_CONTINUATION",

                        "source_page":
                            page_number,
                    })

                    page_has_registration_row = True

                    continue

                # From this point the row is a normal
                # registration/sub-registration row.
                page_has_registration_row = True

                # ------------------------------------------------
                # New numbered active-ingredient group.
                # ------------------------------------------------

                if is_numeric_row_id(
                    number
                ):

                    current_row_number = (
                        number.rstrip(".")
                    )

                    if active:
                        current_active = active

                elif active:

                    # Some PDF table sub-entries repeat an active
                    # ingredient without repeating the TT value.
                    current_active = active

                effective_active = (
                    active
                    or
                    current_active
                )

                # ------------------------------------------------
                # A trade-name cell normally indicates a distinct
                # product registration.
                #
                # Blank TT / blank active is valid here because
                # multiple trade names may share one active
                # ingredient.
                # ------------------------------------------------

                if trade:

                    record = {
                        "source_document_id":
                            document_id,

                        "source_pages": [
                            page_number
                        ],

                        "source_row_number":
                            current_row_number,

                        "legal_action":
                            legal_action,

                        "active_ingredient":
                            effective_active,

                        "trade_name":
                            trade,

                        "pest_crop":
                            pest_crop,

                        "applicant":
                            applicant,
                    }

                    records.append(
                        record
                    )

                    last_record = record

                    continue

                # ------------------------------------------------
                # Same-page continuation row.
                # ------------------------------------------------

                if last_record is None:
                    continue

                if not any([
                    active,
                    pest_crop,
                    applicant,
                ]):
                    continue

                if (
                    page_number
                    not in last_record[
                        "source_pages"
                    ]
                ):

                    last_record[
                        "source_pages"
                    ].append(
                        page_number
                    )

                if (
                    active
                    and
                    not last_record[
                        "active_ingredient"
                    ]
                ):

                    last_record[
                        "active_ingredient"
                    ] = active

                if pest_crop:

                    last_record[
                        "pest_crop"
                    ] = append_cell_text(
                        last_record[
                            "pest_crop"
                        ],
                        pest_crop,
                    )

                if applicant:

                    last_record[
                        "applicant"
                    ] = append_cell_text(
                        last_record[
                            "applicant"
                        ],
                        applicant,
                    )

    return (
        records,
        {
            crop_id:
                sorted(pages)

            for crop_id, pages
            in table_crop_hit_pages.items()
        },
    )
# ============================================================
# DEDUPLICATE RAW REGISTRATION ROWS
# ============================================================

def registration_fingerprint(
    row,
):

    return sha256_text(
        "|".join([
            row[
                "source_document_id"
            ],
            row[
                "legal_action"
            ],
            canonical_key(
                row[
                    "active_ingredient"
                ]
            ),
            canonical_key(
                row[
                    "trade_name"
                ]
            ),
            canonical_key(
                row[
                    "pest_crop"
                ]
            ),
            canonical_key(
                row[
                    "applicant"
                ]
            ),
        ])
    )


def deduplicate_registration_rows(
    rows,
):

    result = []
    seen = set()

    duplicate_count = 0

    for row in rows:

        fingerprint = (
            registration_fingerprint(
                row
            )
        )

        if fingerprint in seen:

            duplicate_count += 1
            continue

        seen.add(
            fingerprint
        )

        row[
            "row_fingerprint"
        ] = fingerprint

        result.append(row)

    return (
        result,
        duplicate_count,
    )


# ============================================================
# TARGET RECORD BUILDER
# ============================================================

def build_target_records(
    rows,
    effective_date,
):

    result = []

    for row in rows:

        matches = (
            crop_match_details(
                row["pest_crop"]
            )
        )

        if not matches:
            continue

        record = deepcopy(row)

        record[
            "crop_matches"
        ] = matches

        record[
            "effective_from"
        ] = effective_date

        record[
            "current_legal_status"
        ] = "ACTIVE"

        record[
            "safe_for_runtime"
        ] = False

        record[
            "amendment_history"
        ] = []

        record_key = "|".join([
            row["source_document_id"],
            row["legal_action"],
            canonical_key(
                row["active_ingredient"]
            ),
            canonical_key(
                row["trade_name"]
            ),
            canonical_key(
                row["pest_crop"]
            ),
            canonical_key(
                row["applicant"]
            ),
        ])

        record[
            "legal_record_id"
        ] = (
            "LR-"
            +
            sha256_text(
                record_key
            )[:16]
        )

        result.append(record)

    return result


# ============================================================
# TT28 EXPLICIT TABLE PARSING
#
# Verified official structure:
#
# PAGE 1
# table 1 = CHANGE applicant rows 1–17
#
# PAGE 2
# table 1 = CHANGE applicant rows 18–20
# table 2 = CHANGE active ingredient rows 1–2
# table 3 = WITHDRAW rows 1–5
#
# No heuristic table classification is used here.
# ============================================================

def data_rows_without_header(
    data,
):

    rows = []

    for raw_row in data:

        if len(raw_row) < 5:
            continue

        if row_is_registration_header(
            raw_row
        ):
            continue

        cells = normalize_row(
            raw_row
        )

        if not is_numeric_row_id(
            cells[0]
        ):
            continue

        rows.append(cells)

    return rows


def parse_change_applicant_rows(
    data,
    page_number,
):

    result = []

    for (
        number,
        active,
        trade,
        old_value,
        new_value,
    ) in data_rows_without_header(
        data
    ):

        result.append({
            "source_document_id":
                AMENDMENT_DOC,

            "source_page":
                page_number,

            "source_row_number":
                number.rstrip("."),

            "change_type":
                "APPLICANT",

            "active_ingredient":
                active,

            "trade_name":
                trade,

            "old_value":
                old_value,

            "new_value":
                new_value,
        })

    return result


def parse_change_active_rows(
    data,
    page_number,
):

    result = []

    for (
        number,
        applicant,
        trade,
        old_value,
        new_value,
    ) in data_rows_without_header(
        data
    ):

        result.append({
            "source_document_id":
                AMENDMENT_DOC,

            "source_page":
                page_number,

            "source_row_number":
                number.rstrip("."),

            "change_type":
                "ACTIVE_INGREDIENT",

            "applicant":
                applicant,

            "trade_name":
                trade,

            "old_value":
                old_value,

            "new_value":
                new_value,
        })

    return result


def parse_withdraw_rows(
    data,
    page_number,
):

    result = []

    for (
        number,
        active,
        trade,
        pest_crop,
        applicant,
    ) in data_rows_without_header(
        data
    ):

        result.append({
            "source_document_id":
                AMENDMENT_DOC,

            "source_page":
                page_number,

            "source_row_number":
                number.rstrip("."),

            "legal_action":
                "WITHDRAW",

            "active_ingredient":
                active,

            "trade_name":
                trade,

            "pest_crop":
                pest_crop,

            "applicant":
                applicant,
        })

    return result


def parse_tt28_changes_and_withdrawals(
    pdf,
):

    page1_tables = find_tables(
        pdf[0]
    )

    page2_tables = find_tables(
        pdf[1]
    )

    if len(page1_tables) < 1:

        raise RuntimeError(
            "DOC0016 page 1 table 1 missing."
        )

    if len(page2_tables) < 3:

        raise RuntimeError(
            "DOC0016 page 2 expected 3 tables, "
            f"found {len(page2_tables)}."
        )

    change_applicant = []

    # Page 1 rows 1–17.
    change_applicant.extend(
        parse_change_applicant_rows(
            page1_tables[0].extract(),
            1,
        )
    )

    # Page 2 rows 18–20.
    change_applicant.extend(
        parse_change_applicant_rows(
            page2_tables[0].extract(),
            2,
        )
    )

    # Page 2 second table: change active ingredient.
    change_active = (
        parse_change_active_rows(
            page2_tables[1].extract(),
            2,
        )
    )

    # Page 2 third table: voluntary withdrawal.
    withdrawals = (
        parse_withdraw_rows(
            page2_tables[2].extract(),
            2,
        )
    )

    return (
        change_applicant,
        change_active,
        withdrawals,
    )


# ============================================================
# AMENDMENT MATCHING
# ============================================================

def trade_key(row):

    return canonical_key(
        row.get(
            "trade_name",
            ""
        )
    )


def active_key(row):

    return canonical_key(
        row.get(
            "active_ingredient",
            ""
        )
    )


def applicant_key(row):

    return canonical_key(
        row.get(
            "applicant",
            ""
        )
    )


def find_change_applicant_matches(
    records,
    change,
):

    active = canonical_key(
        change[
            "active_ingredient"
        ]
    )

    trade = canonical_key(
        change[
            "trade_name"
        ]
    )

    exact = [
        record
        for record in records
        if (
            trade_key(record)
            == trade
            and
            active_key(record)
            == active
        )
    ]

    if exact:

        return (
            exact,
            "ACTIVE_AND_TRADE_EXACT",
        )

    trade_only = [
        record
        for record in records
        if trade_key(record) == trade
    ]

    if len(trade_only) == 1:

        return (
            trade_only,
            "UNIQUE_TRADE_FALLBACK",
        )

    return (
        [],
        "NO_TARGET_MATCH",
    )


def find_change_active_matches(
    records,
    change,
):

    trade = canonical_key(
        change[
            "trade_name"
        ]
    )

    applicant = canonical_key(
        change[
            "applicant"
        ]
    )

    exact = [
        record
        for record in records
        if (
            trade_key(record)
            == trade
            and
            applicant_key(record)
            == applicant
        )
    ]

    if exact:

        return (
            exact,
            "TRADE_AND_APPLICANT_EXACT",
        )

    trade_only = [
        record
        for record in records
        if trade_key(record) == trade
    ]

    if len(trade_only) == 1:

        return (
            trade_only,
            "UNIQUE_TRADE_FALLBACK",
        )

    return (
        [],
        "NO_TARGET_MATCH",
    )


def find_withdraw_matches(
    records,
    withdrawal,
):

    trade = canonical_key(
        withdrawal[
            "trade_name"
        ]
    )

    active = canonical_key(
        withdrawal[
            "active_ingredient"
        ]
    )

    exact = [
        record
        for record in records
        if (
            trade_key(record)
            == trade
            and
            active_key(record)
            == active
        )
    ]

    if exact:

        return (
            exact,
            "ACTIVE_AND_TRADE_EXACT",
        )

    trade_only = [
        record
        for record in records
        if trade_key(record) == trade
    ]

    if len(trade_only) == 1:

        return (
            trade_only,
            "UNIQUE_TRADE_FALLBACK",
        )

    return (
        [],
        "NO_TARGET_MATCH",
    )


def suspicious_trade_overlap(
    records,
    trade_name,
):

    needle = canonical_key(
        trade_name
    )

    if not needle:
        return []

    result = []

    for record in records:

        candidate = trade_key(
            record
        )

        if not candidate:
            continue

        if (
            needle in candidate
            or
            candidate in needle
        ):

            result.append(
                record[
                    "legal_record_id"
                ]
            )

    return sorted(
        set(result)
    )


# ============================================================
# APPLY TT28
# ============================================================

def apply_amendments(
    base_records,
    change_applicant,
    change_active,
    withdrawals,
):

    records = deepcopy(
        base_records
    )

    audit = {
        "change_applicant": [],
        "change_active_ingredient": [],
        "withdrawals": [],
        "blocking_suspicious_matches": [],
    }

    # --------------------------------------------------------
    # CHANGE APPLICANT
    # --------------------------------------------------------

    for change in change_applicant:

        (
            matches,
            method,
        ) = find_change_applicant_matches(
            records,
            change,
        )

        for record in matches:

            old_value = (
                record[
                    "applicant"
                ]
            )

            record[
                "applicant"
            ] = change[
                "new_value"
            ]

            record[
                "amendment_history"
            ].append({
                "action":
                    "CHANGE_APPLICANT",

                "source_document_id":
                    AMENDMENT_DOC,

                "source_page":
                    change[
                        "source_page"
                    ],

                "source_row_number":
                    change[
                        "source_row_number"
                    ],

                "old_value":
                    old_value,

                "new_value":
                    change[
                        "new_value"
                    ],

                "match_method":
                    method,

                "effective_from":
                    AMENDMENT_EFFECTIVE_DATE,
            })

        if not matches:

            suspicious = (
                suspicious_trade_overlap(
                    records,
                    change[
                        "trade_name"
                    ],
                )
            )

            if suspicious:

                audit[
                    "blocking_suspicious_matches"
                ].append({
                    "type":
                        "CHANGE_APPLICANT",

                    "trade_name":
                        change[
                            "trade_name"
                        ],

                    "candidate_records":
                        suspicious,
                })

        audit[
            "change_applicant"
        ].append({
            **change,

            "target_match_count":
                len(matches),

            "match_method":
                method,
        })

    # --------------------------------------------------------
    # CHANGE ACTIVE INGREDIENT
    # --------------------------------------------------------

    for change in change_active:

        (
            matches,
            method,
        ) = find_change_active_matches(
            records,
            change,
        )

        for record in matches:

            old_value = (
                record[
                    "active_ingredient"
                ]
            )

            record[
                "active_ingredient"
            ] = change[
                "new_value"
            ]

            record[
                "amendment_history"
            ].append({
                "action":
                    "CHANGE_ACTIVE_INGREDIENT",

                "source_document_id":
                    AMENDMENT_DOC,

                "source_page":
                    change[
                        "source_page"
                    ],

                "source_row_number":
                    change[
                        "source_row_number"
                    ],

                "old_value":
                    old_value,

                "new_value":
                    change[
                        "new_value"
                    ],

                "match_method":
                    method,

                "effective_from":
                    AMENDMENT_EFFECTIVE_DATE,
            })

        if not matches:

            suspicious = (
                suspicious_trade_overlap(
                    records,
                    change[
                        "trade_name"
                    ],
                )
            )

            if suspicious:

                audit[
                    "blocking_suspicious_matches"
                ].append({
                    "type":
                        "CHANGE_ACTIVE_INGREDIENT",

                    "trade_name":
                        change[
                            "trade_name"
                        ],

                    "candidate_records":
                        suspicious,
                })

        audit[
            "change_active_ingredient"
        ].append({
            **change,

            "target_match_count":
                len(matches),

            "match_method":
                method,
        })

    # --------------------------------------------------------
    # WITHDRAW
    # --------------------------------------------------------

    for withdrawal in withdrawals:

        (
            matches,
            method,
        ) = find_withdraw_matches(
            records,
            withdrawal,
        )

        for record in matches:

            record[
                "current_legal_status"
            ] = "WITHDRAWN"

            record[
                "amendment_history"
            ].append({
                "action":
                    "WITHDRAW",

                "source_document_id":
                    AMENDMENT_DOC,

                "source_page":
                    withdrawal[
                        "source_page"
                    ],

                "source_row_number":
                    withdrawal[
                        "source_row_number"
                    ],

                "match_method":
                    method,

                "effective_from":
                    AMENDMENT_EFFECTIVE_DATE,
            })

        if not matches:

            suspicious = (
                suspicious_trade_overlap(
                    records,
                    withdrawal[
                        "trade_name"
                    ],
                )
            )

            if suspicious:

                audit[
                    "blocking_suspicious_matches"
                ].append({
                    "type":
                        "WITHDRAW",

                    "trade_name":
                        withdrawal[
                            "trade_name"
                        ],

                    "candidate_records":
                        suspicious,
                })

        audit[
            "withdrawals"
        ].append({
            **withdrawal,

            "target_match_count":
                len(matches),

            "match_method":
                method,
        })

    return (
        records,
        audit,
    )


# ============================================================
# COMPLETENESS
# ============================================================

def record_completeness_issues(
    records,
):

    issues = []

    for record in records:

        missing = []

        for field in [
            "active_ingredient",
            "trade_name",
            "pest_crop",
            "applicant",
        ]:

            if not clean_cell(
                record.get(field)
            ):

                missing.append(field)

        if missing:

            issues.append({
                "legal_record_id":
                    record[
                        "legal_record_id"
                    ],

                "missing_fields":
                    missing,

                "source_document_id":
                    record[
                        "source_document_id"
                    ],

                "source_pages":
                    record[
                        "source_pages"
                    ],
            })

    return issues


# ============================================================
# TARGET PAGE COVERAGE
# ============================================================

def parsed_crop_pages(records):

    result = {
        crop_id: set()
        for crop_id in CROPS
    }

    for record in records:

        for crop_match in (
            record[
                "crop_matches"
            ]
        ):

            crop_id = (
                crop_match[
                    "crop_id"
                ]
            )

            for page in (
                record[
                    "source_pages"
                ]
            ):

                result[
                    crop_id
                ].add(page)

    return {
        crop_id:
            sorted(pages)
        for crop_id, pages
        in result.items()
    }


def build_page_coverage(
    table_hit_pages,
    target_records,
):

    parsed_pages = (
        parsed_crop_pages(
            target_records
        )
    )

    result = {}

    for crop_id in CROPS:

        expected = sorted(
            set(
                table_hit_pages[
                    crop_id
                ]
            )
        )

        actual = sorted(
            set(
                parsed_pages[
                    crop_id
                ]
            )
        )

        missing = sorted(
            set(expected)
            -
            set(actual)
        )

        result[
            crop_id
        ] = {
            "table_exact_match_pages":
                expected,

            "parsed_record_pages":
                actual,

            "missing_pages":
                missing,

            "passed":
                len(missing) == 0,
        }

    return result


# ============================================================
# FINAL RECORD FINGERPRINT
# ============================================================

def finalize_records(records):

    result = []

    for record in records:

        record[
            "current_state_fingerprint"
        ] = sha256_text(
            "|".join([
                canonical_key(
                    record[
                        "active_ingredient"
                    ]
                ),
                canonical_key(
                    record[
                        "trade_name"
                    ]
                ),
                canonical_key(
                    record[
                        "pest_crop"
                    ]
                ),
                canonical_key(
                    record[
                        "applicant"
                    ]
                ),
                record[
                    "current_legal_status"
                ],
            ])
        )

        result.append(record)

    return result


# ============================================================
# SUMMARY
# ============================================================

def summarize_records(records):

    result = {}

    for crop_id, crop_info in (
        CROPS.items()
    ):

        crop_records = [
            record
            for record in records
            if any(
                match[
                    "crop_id"
                ]
                == crop_id
                for match in
                record[
                    "crop_matches"
                ]
            )
        ]

        base_records = [
            record
            for record in crop_records
            if (
                record[
                    "legal_action"
                ]
                == "BASE"
            )
        ]

        add_records = [
            record
            for record in crop_records
            if (
                record[
                    "legal_action"
                ]
                == "ADD"
            )
        ]

        active_records = [
            record
            for record in crop_records
            if (
                record[
                    "current_legal_status"
                ]
                == "ACTIVE"
            )
        ]

        withdrawn_records = [
            record
            for record in crop_records
            if (
                record[
                    "current_legal_status"
                ]
                == "WITHDRAWN"
            )
        ]

        result[
            crop_id
        ] = {
            "crop_name":
                crop_info[
                    "crop_name"
                ],

            "lookup_status":
                (
                    "EXACT_MATCH_RECORDS_FOUND"
                    if crop_records
                    else "NO_EXACT_MATCH_FOUND"
                ),

            "total_records":
                len(crop_records),

            "base_records":
                len(base_records),

            "add_records":
                len(add_records),

            "active_records":
                len(active_records),

            "withdrawn_records":
                len(
                    withdrawn_records
                ),
        }

    return result


# ============================================================
# PRINT SAMPLES
# ============================================================

def print_samples(records):

    print()
    print("=" * 110)
    print(
        "CURRENT LEGAL RECORD SAMPLES"
    )
    print("=" * 110)

    for crop_id, crop_info in (
        CROPS.items()
    ):

        matching = [
            record
            for record in records
            if any(
                item[
                    "crop_id"
                ]
                == crop_id
                for item in
                record[
                    "crop_matches"
                ]
            )
        ]

        print()
        print(
            f"{crop_info['crop_name']} "
            f"({crop_id})"
        )

        if not matching:

            print(
                "  NO_EXACT_MATCH_FOUND"
            )
            continue

        for record in matching[:3]:

            detail = next(
                item
                for item in
                record[
                    "crop_matches"
                ]
                if (
                    item[
                        "crop_id"
                    ]
                    == crop_id
                )
            )

            print(
                f"  "
                f"[{record['current_legal_status']}] "
                f"[{record['legal_action']}] "
                f"{record['active_ingredient']}"
            )

            print(
                f"      Trade    : "
                f"{record['trade_name']}"
            )

            print(
                f"      Pest/crop: "
                f"{record['pest_crop']}"
            )

            print(
                f"      Target   : "
                f"{detail['target_pest_text']}"
            )

            print(
                f"      Pest parse: "
                f"{detail['target_pest_parse_status']}"
            )

            print(
                f"      Applicant: "
                f"{record['applicant']}"
            )

            print(
                f"      Source   : "
                f"{record['source_document_id']} "
                f"pages={record['source_pages']}"
            )


# ============================================================
# MANIFEST
# ============================================================

def update_manifest(
    structural_pass,
    approved,
    report,
):

    if not MANIFEST_FILE.exists():

        raise RuntimeError(
            "Legal bundle manifest is missing."
        )

    manifest = load_json(
        MANIFEST_FILE
    )

    current_ready = bool(
        structural_pass
        and
        approved
    )

    if not structural_pass:

        status = (
            "REVIEW_REQUIRED"
        )

        current_record_status = (
            "NOT_READY"
        )

    elif current_ready:

        status = (
            "COMPLETED"
        )

        current_record_status = (
            "READY_FOR_RUNTIME"
        )

    else:

        status = (
            "PENDING_HUMAN_APPROVAL"
        )

        current_record_status = (
            "PENDING_APPROVAL"
        )

    # --------------------------------------------------------
    # IMPORTANT LEGAL SAFETY SEMANTICS
    #
    # Raw TT75 / TT28 source bundle must NEVER become an
    # ordinary RAG corpus.
    #
    # Runtime legal lookup uses only consolidated,
    # human-approved structured current records.
    # --------------------------------------------------------

    manifest[
        "consolidation_status"
    ] = status

    manifest[
        "rag_eligible"
    ] = False

    manifest[
        "legal_current_ready"
    ] = current_ready

    manifest[
        "current_records_runtime_eligible"
    ] = current_ready

    manifest[
        "consolidation"
    ] = {
        "status":
            status,

        "structural_audit_passed":
            structural_pass,

        "human_approved":
            current_ready,

        "current_records_ready":
            current_ready,

        "runtime_eligible":
            current_ready,

        "raw_bundle_rag_eligible":
            False,

        "record_count":
            report[
                "record_count"
            ],

        "active_record_count":
            report[
                "active_record_count"
            ],

        "withdrawn_record_count":
            report[
                "withdrawn_record_count"
            ],

        "effective_through":
            AMENDMENT_EFFECTIVE_DATE,

        "output":
            str(
                CURRENT_RECORDS_FILE
            ),

        "audit_report":
            str(
                CONSOLIDATION_REPORT_FILE
            ),
    }

    manifest[
        "current_legal_records"
    ] = {
        "status":
            current_record_status,

        "runtime_eligible":
            current_ready,

        "record_count":
            report[
                "record_count"
            ],

        "active_record_count":
            report[
                "active_record_count"
            ],

        "withdrawn_record_count":
            report[
                "withdrawn_record_count"
            ],

        "effective_through":
            AMENDMENT_EFFECTIVE_DATE,

        "path":
            str(
                CURRENT_RECORDS_FILE
            ),
    }

    save_json(
        MANIFEST_FILE,
        manifest,
    )

    return status
# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--approve",
        action="store_true",
    )

    args = parser.parse_args()

    approved = args.approve

    LEGAL_BUNDLE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 110)
    print(
        "AGRI RAG - LEGAL CONSOLIDATION V2"
    )
    print("=" * 110)

    print(
        "Mode : "
        + (
            "APPROVAL"
            if approved
            else "DRY RUN / STRUCTURAL AUDIT"
        )
    )

    base_pdf = open_pdf(
        BASE_DOC
    )

    amendment_pdf = open_pdf(
        AMENDMENT_DOC
    )

    # ========================================================
    # TT75
    #
    # Parse ALL 355 pages sequentially.
    # ========================================================

    print()
    print(
        f"Parsing TT75 sequentially: "
        f"{len(base_pdf)} pages"
    )

    (
        base_rows,
        base_table_hit_pages,
    ) = parse_registration_pages(
        base_pdf,
        list(
            range(
                1,
                len(base_pdf) + 1,
            )
        ),
        BASE_DOC,
        "BASE",
    )

    (
        base_rows,
        base_duplicate_count,
    ) = deduplicate_registration_rows(
        base_rows
    )

    base_records = (
        build_target_records(
            base_rows,
            BASE_EFFECTIVE_DATE,
        )
    )

    # ========================================================
    # TT28 CHANGE + WITHDRAW
    # ========================================================

    (
        change_applicant,
        change_active,
        withdrawals,
    ) = (
        parse_tt28_changes_and_withdrawals(
            amendment_pdf
        )
    )

    # ========================================================
    # TT28 ADD
    # ========================================================

    (
        add_rows,
        add_table_hit_pages,
    ) = parse_registration_pages(
        amendment_pdf,
        list(
            range(
                3,
                len(amendment_pdf) + 1,
            )
        ),
        AMENDMENT_DOC,
        "ADD",
    )

    (
        add_rows,
        add_duplicate_count,
    ) = deduplicate_registration_rows(
        add_rows
    )

    add_records = (
        build_target_records(
            add_rows,
            AMENDMENT_EFFECTIVE_DATE,
        )
    )

    base_pdf.close()
    amendment_pdf.close()

    # ========================================================
    # APPLY TT28
    # ========================================================

    (
        amended_base_records,
        amendment_audit,
    ) = apply_amendments(
        base_records,
        change_applicant,
        change_active,
        withdrawals,
    )

    records = (
        amended_base_records
        +
        add_records
    )

    records = finalize_records(
        records
    )

    # ========================================================
    # PAGE COVERAGE
    # ========================================================

    base_page_coverage = (
        build_page_coverage(
            base_table_hit_pages,
            base_records,
        )
    )

    add_page_coverage = (
        build_page_coverage(
            add_table_hit_pages,
            add_records,
        )
    )

    # ========================================================
    # STRUCTURAL AUDIT
    # ========================================================

    blocking_issues = []

    if len(
        change_applicant
    ) != 20:

        blocking_issues.append({
            "code":
                "TT28_CHANGE_APPLICANT_ROW_COUNT",

            "expected":
                20,

            "actual":
                len(
                    change_applicant
                ),
        })

    if len(
        change_active
    ) != 2:

        blocking_issues.append({
            "code":
                "TT28_CHANGE_ACTIVE_ROW_COUNT",

            "expected":
                2,

            "actual":
                len(
                    change_active
                ),
        })

    if len(
        withdrawals
    ) != 5:

        blocking_issues.append({
            "code":
                "TT28_WITHDRAW_ROW_COUNT",

            "expected":
                5,

            "actual":
                len(
                    withdrawals
                ),
        })

    completeness_issues = (
        record_completeness_issues(
            records
        )
    )

    if completeness_issues:

        blocking_issues.append({
            "code":
                "TARGET_RECORD_FIELD_COMPLETENESS",

            "count":
                len(
                    completeness_issues
                ),

            "details":
                completeness_issues[:20],
        })

    for crop_id, info in (
        base_page_coverage.items()
    ):

        if not info[
            "passed"
        ]:

            blocking_issues.append({
                "code":
                    "TT75_TABLE_TARGET_PAGE_NOT_PARSED",

                "crop_id":
                    crop_id,

                "missing_pages":
                    info[
                        "missing_pages"
                    ],
            })

    for crop_id, info in (
        add_page_coverage.items()
    ):

        if not info[
            "passed"
        ]:

            blocking_issues.append({
                "code":
                    "TT28_ADD_TABLE_TARGET_PAGE_NOT_PARSED",

                "crop_id":
                    crop_id,

                "missing_pages":
                    info[
                        "missing_pages"
                    ],
            })

    suspicious = (
        amendment_audit[
            "blocking_suspicious_matches"
        ]
    )

    if suspicious:

        blocking_issues.append({
            "code":
                "SUSPICIOUS_AMENDMENT_TARGET_MATCH",

            "count":
                len(suspicious),

            "details":
                suspicious,
        })

    per_crop = summarize_records(
        records
    )

    # All 5 crops are now expected to have an
    # exact legal table record after native-table parsing.
    for crop_id in CROPS:

        if (
            per_crop[
                crop_id
            ][
                "total_records"
            ]
            == 0
        ):

            blocking_issues.append({
                "code":
                    "TARGET_CROP_HAS_NO_EXACT_LEGAL_RECORD",

                "crop_id":
                    crop_id,
            })

    structural_pass = (
        len(
            blocking_issues
        )
        == 0
    )

    runtime_allowed = (
        structural_pass
        and approved
    )

    for record in records:

        record[
            "safe_for_runtime"
        ] = (
            runtime_allowed
            and
            record[
                "current_legal_status"
            ]
            == "ACTIVE"
        )

    # ========================================================
    # REPORT
    # ========================================================

    active_count = sum(
        1
        for record in records
        if (
            record[
                "current_legal_status"
            ]
            == "ACTIVE"
        )
    )

    withdrawn_count = sum(
        1
        for record in records
        if (
            record[
                "current_legal_status"
            ]
            == "WITHDRAWN"
        )
    )

    report = {
        "bundle_id":
            "PESTICIDE_LIST_VN_CURRENT",

        "base_document":
            BASE_DOC,

        "amendment_document":
            AMENDMENT_DOC,

        "base_effective_date":
            BASE_EFFECTIVE_DATE,

        "amendment_effective_date":
            AMENDMENT_EFFECTIVE_DATE,

        "structural_audit_passed":
            structural_pass,

        "human_approval_requested":
            approved,

        "runtime_allowed":
            runtime_allowed,

        "base_raw_registration_rows":
            len(base_rows),

        "add_raw_registration_rows":
            len(add_rows),

        "base_target_record_count":
            len(base_records),

        "add_target_record_count":
            len(add_records),

        "record_count":
            len(records),

        "active_record_count":
            active_count,

        "withdrawn_record_count":
            withdrawn_count,

        "base_duplicate_rows_removed":
            base_duplicate_count,

        "add_duplicate_rows_removed":
            add_duplicate_count,

        "tt28": {
            "change_applicant_rows":
                len(
                    change_applicant
                ),

            "change_active_ingredient_rows":
                len(
                    change_active
                ),

            "withdraw_rows":
                len(
                    withdrawals
                ),

            "change_applicant_target_matches":
                sum(
                    row[
                        "target_match_count"
                    ]
                    for row in
                    amendment_audit[
                        "change_applicant"
                    ]
                ),

            "change_active_target_matches":
                sum(
                    row[
                        "target_match_count"
                    ]
                    for row in
                    amendment_audit[
                        "change_active_ingredient"
                    ]
                ),

            "withdraw_target_matches":
                sum(
                    row[
                        "target_match_count"
                    ]
                    for row in
                    amendment_audit[
                        "withdrawals"
                    ]
                ),
        },

        "per_crop":
            per_crop,

        "base_page_coverage":
            base_page_coverage,

        "add_page_coverage":
            add_page_coverage,

        "blocking_issues":
            blocking_issues,

        "amendment_audit":
            amendment_audit,
    }

    write_jsonl(
        CURRENT_RECORDS_FILE,
        records,
    )

    save_json(
        CONSOLIDATION_REPORT_FILE,
        report,
    )

    manifest_status = (
        update_manifest(
            structural_pass,
            approved,
            report,
        )
    )

    # ========================================================
    # OUTPUT
    # ========================================================

    print()
    print("=" * 110)
    print(
        "TT28 PARSER SUMMARY"
    )
    print("=" * 110)

    print(
        f"CHANGE applicant rows          : "
        f"{len(change_applicant)}"
    )

    print(
        f"CHANGE active ingredient rows  : "
        f"{len(change_active)}"
    )

    print(
        f"WITHDRAW rows                  : "
        f"{len(withdrawals)}"
    )

    print()
    print(
        f"TT75 parsed registration rows  : "
        f"{len(base_rows)}"
    )

    print(
        f"TT75 target records            : "
        f"{len(base_records)}"
    )

    print(
        f"TT28 ADD target records        : "
        f"{len(add_records)}"
    )

    print(
        f"Consolidated records           : "
        f"{len(records)}"
    )

    print(
        f"ACTIVE records                 : "
        f"{active_count}"
    )

    print(
        f"WITHDRAWN records              : "
        f"{withdrawn_count}"
    )

    print()
    print("=" * 110)
    print(
        "PER-CROP CURRENT LEGAL COVERAGE"
    )
    print("=" * 110)

    print(
        f"{'Crop':<24}"
        f"{'Total':>8}"
        f"{'BASE':>8}"
        f"{'ADD':>8}"
        f"{'ACTIVE':>10}"
        f"{'WITHDRAWN':>12}"
        f"{'Status':>30}"
    )

    print("-" * 110)

    for crop_id in CROPS:

        info = (
            per_crop[
                crop_id
            ]
        )

        print(
            f"{info['crop_name']:<24}"
            f"{info['total_records']:>8}"
            f"{info['base_records']:>8}"
            f"{info['add_records']:>8}"
            f"{info['active_records']:>10}"
            f"{info['withdrawn_records']:>12}"
            f"{info['lookup_status']:>30}"
        )

    print()
    print("=" * 110)
    print(
        "NATIVE TABLE PAGE COVERAGE"
    )
    print("=" * 110)

    print()
    print("TT75 BASE")

    for crop_id in CROPS:

        info = (
            base_page_coverage[
                crop_id
            ]
        )

        print(
            f"  {crop_id:<15} "
            f"table_pages="
            f"{len(info['table_exact_match_pages']):<4} "
            f"missing="
            f"{info['missing_pages']}"
        )

    print()
    print("TT28 ADD")

    for crop_id in CROPS:

        info = (
            add_page_coverage[
                crop_id
            ]
        )

        print(
            f"  {crop_id:<15} "
            f"table_pages="
            f"{len(info['table_exact_match_pages']):<4} "
            f"missing="
            f"{info['missing_pages']}"
        )

    print_samples(
        records
    )

    print()
    print("=" * 110)
    print(
        "LEGAL CONSOLIDATION AUDIT"
    )
    print("=" * 110)

    print(
        "Structural audit : "
        + (
            "PASS"
            if structural_pass
            else "FAIL"
        )
    )

    print(
        f"Blocking issues  : "
        f"{len(blocking_issues)}"
    )

    if blocking_issues:

        for issue in (
            blocking_issues
        ):

            print(
                f"- {issue}"
            )

    print()
    print(
        f"Manifest status  : "
        f"{manifest_status}"
    )

    print(
        f"RAG eligible     : "
        f"{runtime_allowed}"
    )

    print()
    print("=" * 110)
    print("OUTPUT")
    print("=" * 110)

    print(
        f"Current records : "
        f"{CURRENT_RECORDS_FILE}"
    )

    print(
        f"Audit report    : "
        f"{CONSOLIDATION_REPORT_FILE}"
    )

    print(
        f"Bundle manifest : "
        f"{MANIFEST_FILE}"
    )

    print()

    if (
        structural_pass
        and
        not approved
    ):

        print(
            "STRUCTURAL AUDIT PASSED."
        )

        print(
            "Review the samples before running --approve."
        )

    elif runtime_allowed:

        print(
            "LEGAL CONSOLIDATION COMPLETED."
        )

        print(
            "B06 may transition to LEGAL."
        )

    else:

        print(
            "LEGAL CONSOLIDATION REQUIRES REVIEW."
        )

        print(
            "Do not run --approve."
        )


if __name__ == "__main__":
    main()