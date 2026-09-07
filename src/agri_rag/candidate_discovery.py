import argparse
import json
import os
import re
import sys
import time
from collections import Counter, OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[2]

QUERY_BANK_JSONL = (
    PROJECT_ROOT
    / "data"
    / "agri_rag"
    / "discovery"
    / "discovery_queries_combined.jsonl"
)

OUTPUT_DIR = PROJECT_ROOT / "data" / "agri_rag" / "candidates"

CANDIDATES_JSONL = OUTPUT_DIR / "candidate_documents.jsonl"
SUMMARY_JSON = OUTPUT_DIR / "candidate_discovery_summary.json"


DEFAULT_SELECTION_LIMIT = 96
DEFAULT_LIVE_QUERY_LIMIT = 8
DEFAULT_RESULTS_PER_QUERY = 5
DEFAULT_TIMEOUT_SECONDS = 20
MIN_QUERY_HIT_RATE = 0.60
PROVIDER_ATTEMPTS = 2
MAX_FALLBACK_SEARCHES_PER_QUERY = 3

VALID_DISCOVERY_CHANNELS = {
    "web",
    "scholarly",
}

VALID_SEARCH_REGIONS = {
    "NONE",
    "VIETNAM",
    "BINH_DINH_LEGACY",
    "GIA_LAI_CURRENT",
    "GLOBAL",
}

WEB_REGION_TERMS = {
    "NONE": "",
    "VIETNAM": "Việt Nam",
    "BINH_DINH_LEGACY": "Bình Định",
    "GIA_LAI_CURRENT": "Gia Lai",
    "GLOBAL": "",
}

TRACKING_QUERY_PARAMETERS = {
    "fbclid",
    "gclid",
    "gclsrc",
    "mc_cid",
    "mc_eid",
    "msclkid",
    "spm",
    "yclid",
}

TRACKING_QUERY_PREFIXES = (
    "utm_",
)

SCENARIO_ORDER = [
    "heavy_rain",
    "prolonged_rain",
    "post_rain",
    "waterlogging",
    "wet_soil",
    "dry_spell",
    "hot_weather",
    "strong_sun",
    "hot_dry_wind",
    "high_humidity",
    "leaf_wetness",
    "strong_wind",
    "rainy_season",
    "cold_weather",
    "weather_change",
]

CORE_ACTIONS = [
    "irrigation",
    "drainage",
    "post_rain_care",
    "field_inspection",
    "disease_monitoring",
    "crop_protection",
    "spray_window",
    "fertilization",
    "planting",
    "shade",
]

CROP_KEYWORDS = {
    "cai_xanh": [
        "cải xanh",
        "cải bẹ xanh",
        "cải canh",
        "brassica juncea",
        "mustard green",
        "mustard greens",
        "leaf mustard",
        "indian mustard",
    ],
    "ngo": [
        "ngò",
        "ngò rí",
        "rau mùi",
        "coriandrum sativum",
        "coriander",
        "cilantro",
    ],
    "cai_cuc": [
        "cải cúc",
        "tần ô",
        "glebionis coronaria",
        "chrysanthemum coronarium",
        "edible chrysanthemum",
        "crown daisy",
        "garland chrysanthemum",
    ],
    "rau_muong": [
        "rau muống",
        "ipomoea aquatica",
        "water spinach",
        "kang kong",
        "kangkong",
    ],
    "xa_lach": [
        "xà lách",
        "rau xà lách",
        "lactuca sativa",
        "lettuce",
    ],
    "leafy_vegetable": [
        "rau ăn lá",
        "leafy vegetable",
        "leafy vegetables",
        "leaf vegetable",
        "leaf vegetables",
    ],
    "herb_vegetable": [
        "rau gia vị",
        "culinary herb",
        "culinary herbs",
        "herb vegetable",
        "herb vegetables",
    ],
    "short_cycle_vegetable": [
        "rau ngắn ngày",
        "rau màu ngắn ngày",
        "short duration vegetable",
        "short duration vegetables",
        "short cycle vegetable",
        "short cycle vegetables",
    ],
    "general_vegetable": [
        "rau",
        "cây rau",
        "rau màu",
        "vegetable crop",
        "vegetable crops",
        "vegetables",
    ],
}

SCENARIO_KEYWORDS = {
    "heavy_rain": [
        "mưa lớn",
        "mưa to",
        "mưa nhiều",
        "mưa bão",
        "ngập",
        "úng",
        "ngập úng",
        "heavy rain",
        "heavy rainfall",
        "rainfall",
        "precipitation",
        "flooding",
        "flood",
        "waterlogging",
        "excess water",
        "excess rainfall",
        "inundation",
        "rainstorm",
    ],
    "prolonged_rain": [
        "mưa kéo dài",
        "mưa liên tục",
        "ẩm kéo dài",
        "ngập úng",
        "độ ẩm cao",
        "prolonged rain",
        "prolonged rainfall",
        "continuous rain",
        "rainfall",
        "flooding",
        "waterlogging",
        "excess moisture",
        "excessive moisture",
        "wet spell",
    ],
    "post_rain": [
        "sau mưa",
        "sau khi mưa",
        "ẩm ướt",
        "thoát nước",
        "bệnh sau mưa",
        "after rain",
        "post-rain",
        "post rain",
        "rainfall",
        "wetness",
        "waterlogging",
        "disease",
        "moisture",
        "wet soil",
    ],
    "waterlogging": [
        "ngập úng",
        "ngập nước",
        "úng nước",
        "đọng nước",
        "thoát nước",
        "waterlogging",
        "waterlogged",
        "flooding",
        "flood",
        "excess water",
        "inundation",
        "soil saturation",
        "saturated soil",
        "anaerobic",
    ],
    "wet_soil": [
        "đất ướt",
        "đất ẩm",
        "ẩm đất",
        "độ ẩm đất",
        "ngập úng",
        "wet soil",
        "soil moisture",
        "moisture",
        "saturated soil",
        "soil water content",
        "waterlogging",
    ],
    "dry_spell": [
        "khô hạn",
        "hạn",
        "thiếu nước",
        "đất khô",
        "mùa khô",
        "dry spell",
        "drought",
        "water deficit",
        "water stress",
        "soil moisture deficit",
        "dry season",
        "limited irrigation",
    ],
    "hot_weather": [
        "nắng nóng",
        "nắng gắt",
        "nhiệt độ cao",
        "sốc nhiệt",
        "stress nhiệt",
        "heat",
        "high temperature",
        "heat stress",
        "thermal stress",
        "temperature stress",
        "hot weather",
    ],
    "strong_sun": [
        "nắng gắt",
        "ánh nắng mạnh",
        "bức xạ mặt trời",
        "che nắng",
        "cháy lá",
        "solar radiation",
        "sunlight",
        "light intensity",
        "shade",
        "shading",
        "photoinhibition",
        "sun scorch",
        "irradiance",
    ],
    "hot_dry_wind": [
        "gió khô nóng",
        "gió nóng",
        "khô nóng",
        "mất nước",
        "bốc thoát hơi",
        "hot dry wind",
        "dry wind",
        "desiccation",
        "evapotranspiration",
        "vapor pressure deficit",
        "wind stress",
        "hot wind",
    ],
    "high_humidity": [
        "độ ẩm cao",
        "ẩm độ cao",
        "ẩm ướt",
        "bệnh",
        "nấm bệnh",
        "thối",
        "humidity",
        "relative humidity",
        "moisture",
        "leaf wetness",
        "disease",
        "fungal",
        "mildew",
        "rot",
    ],
    "leaf_wetness": [
        "ướt lá",
        "lá ướt",
        "ẩm lá",
        "bệnh lá",
        "nấm bệnh",
        "leaf wetness",
        "wet leaves",
        "leaf moisture",
        "humidity",
        "foliar disease",
        "fungal disease",
        "pathogen",
    ],
    "strong_wind": [
        "gió mạnh",
        "gió lớn",
        "đổ ngã",
        "dập lá",
        "mưa bão",
        "wind",
        "strong wind",
        "wind damage",
        "lodging",
        "mechanical damage",
        "storm",
        "typhoon",
    ],
    "rainy_season": [
        "mùa mưa",
        "vụ mưa",
        "mưa mùa",
        "mưa nhiều",
        "ẩm ướt",
        "rainy season",
        "wet season",
        "monsoon",
        "seasonal rainfall",
        "rainfed",
        "rainfall",
    ],
    "cold_weather": [
        "trời lạnh",
        "rét",
        "nhiệt độ thấp",
        "lạnh",
        "sương giá",
        "cold",
        "low temperature",
        "chilling",
        "cold stress",
        "cool temperature",
        "frost",
    ],
    "weather_change": [
        "thời tiết thay đổi",
        "biến động thời tiết",
        "thời tiết thất thường",
        "biến đổi khí hậu",
        "thời tiết cực đoan",
        "weather variability",
        "climate variability",
        "temperature fluctuation",
        "rainfall variability",
        "climate change",
        "extreme weather",
    ],
}

ACTION_KEYWORDS = {
    "NONE": [],
    "irrigation": [
        "tưới",
        "tưới nước",
        "quản lý nước",
        "irrigation",
        "watering",
        "water management",
    ],
    "drainage": [
        "thoát nước",
        "tiêu nước",
        "rút nước",
        "drainage",
        "drain",
        "water removal",
    ],
    "post_rain_care": [
        "sau mưa",
        "chăm sóc sau mưa",
        "xử lý sau mưa",
        "after rain",
        "post-rain",
        "post rain",
        "field management",
    ],
    "field_inspection": [
        "kiểm tra",
        "theo dõi",
        "quan sát",
        "field inspection",
        "monitoring",
        "assessment",
    ],
    "disease_monitoring": [
        "bệnh",
        "nấm bệnh",
        "theo dõi bệnh",
        "disease",
        "pathogen",
        "fungal",
        "monitoring",
    ],
    "crop_protection": [
        "bảo vệ cây",
        "bảo vệ thực vật",
        "phòng trừ",
        "sâu bệnh",
        "crop protection",
        "plant protection",
        "disease management",
        "pest management",
    ],
    "spray_window": [
        "phun thuốc",
        "phun xịt",
        "thời điểm phun",
        "spray",
        "spraying",
        "pesticide application",
        "application timing",
    ],
    "fertilization": [
        "bón phân",
        "phân bón",
        "dinh dưỡng",
        "fertilization",
        "fertilizer",
        "nutrient management",
    ],
    "planting": [
        "gieo",
        "trồng",
        "gieo trồng",
        "planting",
        "sowing",
        "transplanting",
    ],
    "shade": [
        "che nắng",
        "che phủ",
        "lưới che",
        "shade",
        "shading",
        "net house",
    ],
    "soil_moisture_management": [
        "giữ ẩm",
        "ẩm đất",
        "quản lý ẩm",
        "soil moisture",
        "mulch",
        "mulching",
        "water management",
    ],
    "mulching": [
        "phủ luống",
        "che phủ đất",
        "mulch",
        "mulching",
    ],
    "cultivation": [
        "canh tác",
        "kỹ thuật trồng",
        "chăm sóc",
        "cultivation",
        "crop management",
        "agronomy",
    ],
    "disease_management": [
        "phòng bệnh",
        "trị bệnh",
        "quản lý bệnh",
        "disease management",
        "pathogen",
        "fungal disease",
        "control",
    ],
}

AGRONOMIC_EFFECT_KEYWORDS = [
    "héo",
    "vàng lá",
    "cháy lá",
    "thối",
    "bệnh",
    "nấm bệnh",
    "sâu bệnh",
    "úng",
    "ngập",
    "ngập úng",
    "thiếu nước",
    "mất nước",
    "ẩm ướt",
    "dập lá",
    "crop response",
    "crop effect",
    "crop effects",
    "plant response",
    "plant stress",
    "water stress",
    "heat stress",
    "waterlogging",
    "flooding",
    "agronomic effect",
    "agronomic effects",
    "disease",
    "stress",
    "wilting",
    "chlorosis",
    "rot",
]

SCENARIO_GENERAL_WEB_TERMS = {
    "heavy_rain": "mưa ngập úng bệnh",
    "prolonged_rain": "mùa mưa chăm sóc",
    "post_rain": "sau mưa chăm sóc",
    "waterlogging": "ngập úng thoát nước",
    "wet_soil": "đất ẩm thoát nước",
    "dry_spell": "khô hạn tưới nước",
    "hot_weather": "nắng nóng chăm sóc",
    "strong_sun": "nắng gắt che nắng",
    "hot_dry_wind": "gió khô nóng giữ ẩm",
    "high_humidity": "độ ẩm cao bệnh",
    "leaf_wetness": "ướt lá nấm bệnh",
    "strong_wind": "gió mạnh chăm sóc",
    "rainy_season": "mùa mưa chăm sóc",
    "cold_weather": "trời lạnh chăm sóc",
    "weather_change": "thời tiết thay đổi chăm sóc",
}

SCHOLARLY_NOISE_TERMS = [
    "genetic diversity",
    "aflp",
    "marker",
    "molecular marker",
    "microsatellite",
    "population structure",
    "phylogenetic",
    "genome",
    "genetic",
    "row spacing",
    "nitrogen dose",
    "nitrogen rate",
    "storage",
    "postharvest storage",
    "antioxidant",
]


class SearchProviderError(RuntimeError):
    pass


class SearchProviderUnavailable(SearchProviderError):
    pass


@dataclass
class SearchResult:
    url: str
    title: str
    rank: int
    provider: str
    snippet: str = ""
    source_type_hint: str = ""
    doi: str = ""
    abstract: str = ""
    subjects: tuple = ()
    relevance_status: str = "supporting_match"
    relevance_score: int = 0
    relevance_reasons: tuple = ()
    matched_crop_terms: tuple = ()
    matched_scenario_terms: tuple = ()
    matched_action_terms: tuple = ()


def configure_stdout():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def stable_id(text):
    import hashlib

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()[:12].upper()


def utc_now():
    return datetime.now(
        timezone.utc
    ).isoformat()


def load_jsonl(path):
    if not path.exists():
        raise FileNotFoundError(
            f"Missing query bank: {path}. Run python -m src.agri_rag.discovery first."
        )

    rows = []
    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        for line_number, line in enumerate(
            file,
            start=1,
        ):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(
                    json.loads(line)
                )
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid JSONL at {path}:{line_number}: {error}"
                ) from error

    return rows


def write_jsonl(path, rows):
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
                    sort_keys=True,
                )
                + "\n"
            )


def write_json(path, payload):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    with path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            payload,
            file,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )


def count_by(rows, field):
    return dict(
        sorted(
            Counter(
                row.get(field, "")
                for row in rows
            ).items()
        )
    )


def normalize_text(text):
    return " ".join(
        text.casefold().split()
    )


def normalize_query_signature(text):
    normalized = normalize_text(text)
    normalized = re.sub(
        r"[\u201c\u201d\"'`.,;:!?()[\]{}]",
        " ",
        normalized,
    )
    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    )
    return normalized.strip()


def discovery_channel(row):
    channel = row.get(
        "channel",
        "",
    )
    language = row.get(
        "language",
        "",
    )

    if channel == "scholarly":
        return "scholarly"

    if language == "en":
        return "scholarly"

    if channel in {
        "web",
        "public_query",
    }:
        return "web"

    if language == "vi":
        return "web"

    return ""


def effective_priority(row):
    raw_priority = row.get(
        "priority",
        "",
    )

    if raw_priority != "":
        try:
            return int(raw_priority)
        except (TypeError, ValueError):
            pass

    channel = discovery_channel(row)
    scope_type = row.get(
        "scope_type",
        "",
    )
    source_stage = row.get(
        "source_stage",
        "",
    )

    if source_stage == "A2":
        return 1

    if channel == "web" and scope_type == "crop_specific":
        return 1

    if channel == "web" and scope_type == "crop_group":
        return 2

    if channel == "scholarly" and scope_type == "crop_specific":
        return 2

    if channel == "scholarly" and scope_type == "crop_group":
        return 3

    return 9


def annotated_query(row):
    annotated = dict(row)
    annotated["discovery_channel"] = discovery_channel(row)
    annotated["selection_priority"] = effective_priority(row)
    annotated["query_origin_group"] = (
        annotated.get("query_origin")
        or "not_applicable"
    )
    return annotated


def query_sort_key(row):
    channel_rank = {
        "web": 0,
        "scholarly": 1,
    }.get(
        row.get("discovery_channel", ""),
        9,
    )

    stage_rank = {
        "A2": 0,
        "A1": 1,
    }.get(
        row.get("source_stage", ""),
        9,
    )

    kind_rank = {
        "natural_question": 0,
        "action": 1,
        "effect": 2,
    }.get(
        row.get("query_kind", ""),
        9,
    )

    scope_rank = {
        "crop_specific": 0,
        "crop_group": 1,
    }.get(
        row.get("scope_type", ""),
        9,
    )

    web_region_rank = {
        "VIETNAM": 0,
        "BINH_DINH_LEGACY": 1,
        "GIA_LAI_CURRENT": 1,
        "NONE": 2,
    }

    scholarly_region_rank = {
        "GLOBAL": 0,
        "VIETNAM": 1,
    }

    if row.get("discovery_channel") == "scholarly":
        region_rank = scholarly_region_rank.get(
            row.get("search_region", ""),
            9,
        )
    else:
        region_rank = web_region_rank.get(
            row.get("search_region", ""),
            9,
        )

    scenario_rank = {
        scenario: index
        for index, scenario in enumerate(SCENARIO_ORDER)
    }.get(
        row.get("weather_scenario", ""),
        len(SCENARIO_ORDER),
    )

    action_rank = {
        action: index
        for index, action in enumerate(CORE_ACTIONS)
    }.get(
        row.get("action", ""),
        len(CORE_ACTIONS),
    )

    return (
        channel_rank,
        stage_rank,
        row.get("selection_priority", 9),
        kind_rank,
        scope_rank,
        region_rank,
        scenario_rank,
        action_rank,
        row.get("crop_key", ""),
        normalize_query_signature(
            row.get("query_text", "")
        ),
        row.get("combined_query_id", ""),
    )


def near_duplicate_key(row):
    return (
        row.get("discovery_channel", ""),
        row.get("language", ""),
        row.get("source_stage", ""),
        row.get("query_kind", ""),
        row.get("scope_type", ""),
        row.get("crop_key", ""),
        row.get("weather_scenario", ""),
        row.get("action", ""),
        row.get("search_region", ""),
        normalize_query_signature(
            row.get("query_text", "")
        ),
    )


def selection_capacity(selection_limit):
    web_limit = max(
        1,
        (selection_limit * 3) // 4,
    )
    return {
        "discovery_channel": {
            "web": web_limit,
            "scholarly": max(
                1,
                selection_limit - web_limit,
            ),
        },
        "scope_type": {
            "crop_specific": max(
                1,
                (selection_limit * 3) // 4,
            ),
            "crop_group": max(
                1,
                selection_limit // 4,
            ),
        },
        "query_kind": {
            "natural_question": min(
                32,
                max(
                    1,
                    selection_limit // 3,
                ),
            ),
            "effect": min(
                24,
                max(
                    1,
                selection_limit // 4,
                ),
            ),
        },
        "search_region": {
            "VIETNAM": max(
                1,
                (selection_limit * 35) // 100,
            ),
            "BINH_DINH_LEGACY": max(
                1,
                (selection_limit * 15) // 100,
            ),
            "GIA_LAI_CURRENT": max(
                1,
                (selection_limit * 15) // 100,
            ),
            "NONE": max(
                1,
                (selection_limit * 12) // 100,
            ),
            "GLOBAL": max(
                1,
                (selection_limit * 25) // 100,
            ),
        },
    }


def under_soft_capacity(selected, row, capacity):
    channel_counts = Counter(
        item["discovery_channel"]
        for item in selected
    )
    scope_counts = Counter(
        item["scope_type"]
        for item in selected
    )
    kind_counts = Counter(
        item["query_kind"]
        for item in selected
    )
    region_counts = Counter(
        item["search_region"]
        for item in selected
    )
    scenario_counts = Counter(
        item["weather_scenario"]
        for item in selected
    )
    crop_counts = Counter(
        item["crop_key"]
        for item in selected
    )

    channel = row.get(
        "discovery_channel",
        "",
    )
    scope_type = row.get(
        "scope_type",
        "",
    )
    query_kind = row.get(
        "query_kind",
        "",
    )

    if channel_counts[channel] >= capacity["discovery_channel"].get(
        channel,
        len(selected) + 1,
    ):
        return False

    if scope_counts[scope_type] >= capacity["scope_type"].get(
        scope_type,
        len(selected) + 1,
    ):
        return False

    if query_kind in capacity["query_kind"]:
        if kind_counts[query_kind] >= capacity["query_kind"][query_kind]:
            return False

    search_region = row.get(
        "search_region",
        "",
    )
    if search_region in capacity["search_region"]:
        if region_counts[search_region] >= capacity["search_region"][search_region]:
            return False

    scenario_limit = max(
        3,
        len(selected) // max(
            1,
            len(SCENARIO_ORDER),
        )
        + 4,
    )
    if scenario_counts[row.get("weather_scenario", "")] >= scenario_limit:
        return False

    crop_limit = max(
        6,
        len(selected) // 8 + 8,
    )
    if crop_counts[row.get("crop_key", "")] >= crop_limit:
        return False

    return True


def select_queries(rows, selection_limit=DEFAULT_SELECTION_LIMIT):
    annotated_rows = [
        annotated_query(row)
        for row in rows
    ]
    annotated_rows = [
        row
        for row in annotated_rows
        if row.get("discovery_channel") in VALID_DISCOVERY_CHANNELS
    ]
    sorted_rows = sorted(
        annotated_rows,
        key=query_sort_key,
    )

    selected = OrderedDict()
    duplicate_signatures = set()

    def add_best(predicate):
        for row in sorted_rows:
            if not predicate(row):
                continue
            query_id = row.get(
                "combined_query_id",
                "",
            )
            signature = near_duplicate_key(row)
            if query_id in selected:
                return False
            if signature in duplicate_signatures:
                continue
            selected[query_id] = row
            duplicate_signatures.add(signature)
            return True
        return False

    crop_keys = sorted(
        {
            row.get("crop_key", "")
            for row in annotated_rows
            if row.get("scope_type") == "crop_specific"
        }
    )
    crop_group_keys = sorted(
        {
            row.get("crop_key", "")
            for row in annotated_rows
            if row.get("scope_type") == "crop_group"
        }
    )

    for scenario_index, scenario in enumerate(SCENARIO_ORDER):
        preferred_crop = (
            crop_keys[
                scenario_index % len(crop_keys)
            ]
            if crop_keys
            else ""
        )

        added = add_best(
            lambda row, scenario=scenario: (
                row.get("discovery_channel") == "web"
                and row.get("source_stage") == "A2"
                and row.get("query_kind") == "natural_question"
                and row.get("scope_type") == "crop_specific"
                and row.get("crop_key") == preferred_crop
                and row.get("weather_scenario") == scenario
            )
        )
        if not added:
            add_best(
                lambda row, scenario=scenario: (
                    row.get("discovery_channel") == "web"
                    and row.get("source_stage") == "A2"
                    and row.get("query_kind") == "natural_question"
                    and row.get("weather_scenario") == scenario
                )
            )

        added = add_best(
            lambda row, scenario=scenario: (
                row.get("discovery_channel") == "web"
                and row.get("source_stage") == "A1"
                and row.get("scope_type") == "crop_specific"
                and row.get("query_kind") == "effect"
                and row.get("crop_key") == preferred_crop
                and row.get("weather_scenario") == scenario
            )
        )
        if not added:
            add_best(
                lambda row, scenario=scenario: (
                    row.get("discovery_channel") == "web"
                    and row.get("source_stage") == "A1"
                    and row.get("scope_type") == "crop_specific"
                    and row.get("query_kind") == "effect"
                    and row.get("weather_scenario") == scenario
                )
            )

        added = add_best(
            lambda row, scenario=scenario: (
                row.get("discovery_channel") == "scholarly"
                and row.get("source_stage") == "A1"
                and row.get("scope_type") == "crop_specific"
                and row.get("query_kind") == "effect"
                and row.get("crop_key") == preferred_crop
                and row.get("weather_scenario") == scenario
            )
        )
        if not added:
            add_best(
                lambda row, scenario=scenario: (
                    row.get("discovery_channel") == "scholarly"
                    and row.get("source_stage") == "A1"
                    and row.get("scope_type") == "crop_specific"
                    and row.get("query_kind") == "effect"
                    and row.get("weather_scenario") == scenario
                )
            )

    for crop_key in crop_keys:
        add_best(
            lambda row, crop_key=crop_key: (
                row.get("discovery_channel") == "web"
                and row.get("source_stage") == "A1"
                and row.get("scope_type") == "crop_specific"
                and row.get("crop_key") == crop_key
                and row.get("query_kind") == "action"
            )
        )

    for crop_key in crop_group_keys:
        add_best(
            lambda row, crop_key=crop_key: (
                row.get("discovery_channel") == "web"
                and row.get("source_stage") == "A1"
                and row.get("scope_type") == "crop_group"
                and row.get("crop_key") == crop_key
                and row.get("query_kind") == "action"
            )
        )

    for search_region in [
        "VIETNAM",
        "BINH_DINH_LEGACY",
        "GIA_LAI_CURRENT",
        "NONE",
    ]:
        add_best(
            lambda row, search_region=search_region: (
                row.get("discovery_channel") == "web"
                and row.get("source_stage") == "A1"
                and row.get("search_region") == search_region
                and row.get("query_kind") == "action"
            )
        )

    capacity = selection_capacity(selection_limit)

    for row in sorted_rows:
        if len(selected) >= selection_limit:
            break

        query_id = row.get(
            "combined_query_id",
            "",
        )
        signature = near_duplicate_key(row)

        if query_id in selected:
            continue

        if signature in duplicate_signatures:
            continue

        if not under_soft_capacity(
            list(selected.values()),
            row,
            capacity,
        ):
            continue

        selected[query_id] = row
        duplicate_signatures.add(signature)

    selected_rows = list(
        selected.values()
    )[:selection_limit]

    for rank, row in enumerate(
        selected_rows,
        start=1,
    ):
        row["selection_rank"] = rank

    return selected_rows


def selection_summary(rows, selected_rows):
    total = len(rows)
    selected = len(selected_rows)
    return {
        "total_query_bank": total,
        "selected_queries": selected,
        "skipped_queries": total - selected,
        "by_discovery_channel": count_by(
            selected_rows,
            "discovery_channel",
        ),
        "by_language": count_by(
            selected_rows,
            "language",
        ),
        "by_source_stage": count_by(
            selected_rows,
            "source_stage",
        ),
        "by_query_origin": count_by(
            selected_rows,
            "query_origin_group",
        ),
        "by_query_kind": count_by(
            selected_rows,
            "query_kind",
        ),
        "by_crop_scope": count_by(
            selected_rows,
            "scope_type",
        ),
        "by_crop_key": count_by(
            selected_rows,
            "crop_key",
        ),
        "by_weather_scenario": count_by(
            selected_rows,
            "weather_scenario",
        ),
        "by_action": count_by(
            selected_rows,
            "action",
        ),
        "by_search_region": count_by(
            selected_rows,
            "search_region",
        ),
        "by_selection_priority": count_by(
            selected_rows,
            "selection_priority",
        ),
    }


def representative_queries(selected_rows, limit=12):
    representatives = []
    seen_dimensions = set()
    seen_query_ids = set()

    dimensions = [
        "discovery_channel",
        "source_stage",
        "query_kind",
        "scope_type",
        "crop_key",
        "search_region",
    ]

    for field in dimensions:
        for row in selected_rows:
            key = (
                field,
                row.get(field, ""),
            )
            if key in seen_dimensions:
                continue
            if row["combined_query_id"] in seen_query_ids:
                seen_dimensions.add(key)
                continue
            representatives.append(row)
            seen_query_ids.add(
                row["combined_query_id"]
            )
            seen_dimensions.add(key)
            if len(representatives) >= limit:
                return representatives

    for row in selected_rows:
        if row["combined_query_id"] in seen_query_ids:
            continue
        representatives.append(row)
        if len(representatives) >= limit:
            break

    return representatives


def canonicalize_url(url):
    if not url:
        return ""

    parts = urlsplit(
        url.strip()
    )

    if not parts.scheme or not parts.netloc:
        return ""

    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()

    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    elif netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]

    path = parts.path or ""
    if path == "/":
        path = ""
    elif path.endswith("/") and "." not in path.rsplit("/", 1)[-1]:
        path = path.rstrip("/")

    query_pairs = []
    for key, value in parse_qsl(
        parts.query,
        keep_blank_values=True,
    ):
        lowered_key = key.lower()
        if lowered_key in TRACKING_QUERY_PARAMETERS:
            continue
        if any(
            lowered_key.startswith(prefix)
            for prefix in TRACKING_QUERY_PREFIXES
        ):
            continue
        query_pairs.append(
            (
                key,
                value,
            )
        )

    query = urlencode(
        sorted(query_pairs),
        doseq=True,
    )

    return urlunsplit(
        (
            scheme,
            netloc,
            path,
            query,
            "",
        )
    )


def source_domain(url):
    canonical = canonicalize_url(url)
    if not canonical:
        return ""
    return urlsplit(
        canonical
    ).netloc.lower()


def source_type(url, discovery_channel_value, source_type_hint=""):
    path = urlsplit(
        url
    ).path.lower()

    if path.endswith(".pdf"):
        return "pdf"

    if source_type_hint:
        return source_type_hint

    if discovery_channel_value == "scholarly":
        return "scholarly_record"

    if discovery_channel_value == "web":
        return "web_page"

    return "unknown"


def clean_search_text(text):
    if text is None:
        return ""

    cleaned = unescape(
        str(text)
    )
    cleaned = re.sub(
        r"\s+",
        " ",
        cleaned,
    )
    return cleaned.strip()


def clean_crossref_text(text):
    if not text:
        return ""

    cleaned = unescape(
        str(text)
    )
    cleaned = re.sub(
        r"<[^>]+>",
        " ",
        cleaned,
    )
    cleaned = re.sub(
        r"\s+",
        " ",
        cleaned,
    )
    return cleaned.strip()


def metadata_text(result):
    parts = [
        result.title,
        result.snippet,
        result.abstract,
        " ".join(result.subjects),
    ]
    return normalize_text(
        " ".join(
            part
            for part in parts
            if part
        )
    )


def title_subject_text(result):
    return normalize_text(
        " ".join(
            part
            for part in [
                result.title,
                result.snippet,
                " ".join(result.subjects),
            ]
            if part
        )
    )


def matched_terms(text, terms):
    normalized = normalize_text(
        re.sub(
            r"[-_/]+",
            " ",
            text,
        )
    )
    matches = []

    for term in terms:
        normalized_term = normalize_text(
            re.sub(
                r"[-_/]+",
                " ",
                term,
            )
        )
        if not normalized_term:
            continue

        pattern = (
            r"(?<![a-z0-9])"
            + re.escape(normalized_term)
            + r"(?![a-z0-9])"
        )
        if re.search(
            pattern,
            normalized,
        ):
            matches.append(term)

    return tuple(
        sorted(
            set(matches),
            key=lambda value: (
                len(value),
                value,
            ),
            reverse=True,
        )
    )


def crop_terms_for_query(query):
    crop_key = query.get(
        "crop_key",
        "",
    )
    return CROP_KEYWORDS.get(
        crop_key,
        [],
    )


def scenario_terms_for_query(query):
    scenario = query.get(
        "weather_scenario",
        "",
    )
    return SCENARIO_KEYWORDS.get(
        scenario,
        [],
    )


def action_terms_for_query(query):
    action = query.get(
        "action",
        "NONE",
    )
    return ACTION_KEYWORDS.get(
        action,
        [],
    )


def effect_terms_for_query(_query):
    return AGRONOMIC_EFFECT_KEYWORDS


def quote_term(term):
    if not term:
        return ""
    return f'"{term}"'


def first_available(terms, default=""):
    for term in terms:
        if term:
            return term
    return default


def second_available(terms, default=""):
    seen = []
    for term in terms:
        if term and term not in seen:
            seen.append(term)
    if len(seen) >= 2:
        return seen[1]
    return first_available(
        seen,
        default,
    )


def region_fallback_terms(search_region):
    if search_region in {
        "BINH_DINH_LEGACY",
        "GIA_LAI_CURRENT",
    }:
        return [
            "Việt Nam",
            "",
            "",
        ]

    if search_region == "VIETNAM":
        return [
            "Việt Nam",
            "",
            "",
        ]

    return [
        "",
        "",
        "",
    ]


def with_region(text, region_term):
    parts = [
        text,
        region_term,
    ]
    return " ".join(
        part
        for part in parts
        if part
    ).strip()


def make_query_variant(query, search_variant_text, search_variant_type):
    variant = dict(query)
    variant["original_query_id"] = query.get(
        "combined_query_id",
        "",
    )
    variant["original_query_text"] = query.get(
        "query_text",
        "",
    )
    variant["search_text"] = search_variant_text
    variant["search_variant_text"] = search_variant_text
    variant["search_variant_type"] = search_variant_type
    return variant


def web_fallback_variants(query):
    if query.get("discovery_channel") != "web":
        return []

    crop_terms = crop_terms_for_query(query)
    scenario_terms = scenario_terms_for_query(query)
    action_terms = action_terms_for_query(query)
    effect_terms = effect_terms_for_query(query)
    region_terms = region_fallback_terms(
        query.get(
            "search_region",
            "",
        )
    )

    primary_crop = first_available(crop_terms)
    secondary_crop = second_available(
        crop_terms,
        primary_crop,
    )
    primary_scenario = first_available(scenario_terms)
    secondary_scenario = second_available(
        scenario_terms,
        primary_scenario,
    )
    primary_action = first_available(
        action_terms,
        first_available(effect_terms),
    )
    general_weather = SCENARIO_GENERAL_WEB_TERMS.get(
        query.get(
            "weather_scenario",
            "",
        ),
        "thời tiết chăm sóc",
    )

    if not primary_crop or not primary_scenario:
        return []

    fallback_specs = [
        (
            "crop_scenario",
            with_region(
                f"{quote_term(primary_crop)} {quote_term(primary_scenario)}",
                region_terms[0],
            ),
        ),
        (
            "crop_scenario_action",
            with_region(
                f"{quote_term(secondary_crop)} {primary_scenario} {primary_action}".strip(),
                region_terms[1],
            ),
        ),
        (
            "crop_weather_general",
            with_region(
                f"{quote_term(primary_crop)} {secondary_scenario} {general_weather}".strip(),
                region_terms[2],
            ),
        ),
    ]

    variants = []
    seen_texts = set()

    for variant_type, variant_text in fallback_specs:
        normalized = normalize_query_signature(
            variant_text
        )
        if not normalized or normalized in seen_texts:
            continue
        seen_texts.add(normalized)
        variants.append(
            make_query_variant(
                query,
                variant_text,
                variant_type,
            )
        )

    return variants[
        :MAX_FALLBACK_SEARCHES_PER_QUERY
    ]


def search_variants_for_query(query):
    original = make_query_variant(
        query,
        query.get(
            "query_text",
            "",
        ),
        "original",
    )
    return [
        original,
        *web_fallback_variants(query),
    ]


def audit_relevance_rules():
    issues = []

    scenario_terms = {
        normalize_text(term)
        for terms in SCENARIO_KEYWORDS.values()
        for term in terms
    }

    for crop_key, crop_terms in CROP_KEYWORDS.items():
        overlapping_terms = sorted(
            {
                term
                for term in crop_terms
                if normalize_text(term) in scenario_terms
            }
        )
        if overlapping_terms:
            issues.append({
                "type": "A3_CROP_KEYWORD_OVERLAPS_SCENARIO_KEYWORD",
                "crop_key": crop_key,
                "terms": overlapping_terms,
            })

    query = {
        "crop_key": "cai_xanh",
        "scope_type": "crop_specific",
        "weather_scenario": "prolonged_rain",
        "action": "NONE",
        "query_text": '"cải xanh" "mưa kéo dài" ảnh hưởng chăm sóc Việt Nam',
    }
    result = SearchResult(
        url="https://example.com/weather-only",
        title="mưa kéo dài ảnh hưởng chăm sóc Việt Nam",
        snippet="mưa kéo dài, mưa liên tục và ngập úng",
        rank=1,
        provider="self_audit",
    )
    assessment = assess_result_relevance(
        query,
        result,
    )

    if assessment["matched_crop_terms"]:
        issues.append({
            "type": "A3_SCENARIO_TERM_MATCHED_AS_CROP",
            "matched_crop_terms": list(
                assessment["matched_crop_terms"]
            ),
        })

    if assessment["relevance_status"] != "rejected_irrelevant":
        issues.append({
            "type": "A3_WEATHER_ONLY_RESULT_NOT_REJECTED",
            "relevance_status": assessment["relevance_status"],
        })

    return issues


def assess_result_relevance(query, result):
    text = metadata_text(result)
    focused_text = title_subject_text(result)

    crop_matches = matched_terms(
        text,
        crop_terms_for_query(query),
    )
    scenario_matches = matched_terms(
        text,
        scenario_terms_for_query(query),
    )
    action_matches = matched_terms(
        text,
        action_terms_for_query(query),
    )
    effect_matches = matched_terms(
        text,
        effect_terms_for_query(query),
    )
    noise_matches = matched_terms(
        text,
        SCHOLARLY_NOISE_TERMS,
    )
    focused_scenario_matches = matched_terms(
        focused_text,
        scenario_terms_for_query(query),
    )

    score = 0
    reasons = []

    if crop_matches:
        score += 3
        reasons.append(
            "matched crop identity"
        )
    else:
        reasons.append(
            "missing crop identity"
        )

    if scenario_matches:
        score += 4 + min(
            len(scenario_matches) - 1,
            3,
        )
        reasons.append(
            "matched weather scenario terms"
        )
    else:
        reasons.append(
            "missing weather scenario terms"
        )

    if action_matches:
        score += 2 + min(
            len(action_matches) - 1,
            2,
        )
        reasons.append(
            "matched action/effect terms"
        )

    if effect_matches:
        score += 1 + min(
            len(effect_matches) - 1,
            2,
        )
        reasons.append(
            "matched agronomic effect terms"
        )

    if focused_scenario_matches:
        score += 2
        reasons.append(
            "weather scenario appears in title or subject"
        )

    if noise_matches:
        penalty = min(
            len(noise_matches),
            3,
        )
        score -= penalty
        reasons.append(
            "contains crop-only noise terms"
        )

    if not crop_matches:
        status = "rejected_irrelevant"
    elif not scenario_matches:
        if action_matches or effect_matches:
            status = "supporting_match"
        else:
            status = "rejected_irrelevant"
    elif noise_matches and not focused_scenario_matches and not action_matches:
        status = "rejected_irrelevant"
    elif action_matches or effect_matches or focused_scenario_matches or len(scenario_matches) >= 2:
        status = "direct_match"
    else:
        status = "direct_match"

    if status == "rejected_irrelevant":
        score = min(
            score,
            0,
        )

    return {
        "relevance_status": status,
        "relevance_score": score,
        "relevance_reasons": tuple(reasons),
        "matched_crop_terms": crop_matches,
        "matched_scenario_terms": scenario_matches,
        "matched_action_terms": action_matches,
    }


def assess_scholarly_relevance(query, result):
    return assess_result_relevance(
        query,
        result,
    )


def assess_web_relevance(query, result):
    return assess_result_relevance(
        query,
        result,
    )


def apply_relevance(result, assessment):
    result.relevance_status = assessment["relevance_status"]
    result.relevance_score = assessment["relevance_score"]
    result.relevance_reasons = assessment["relevance_reasons"]
    result.matched_crop_terms = assessment["matched_crop_terms"]
    result.matched_scenario_terms = assessment["matched_scenario_terms"]
    result.matched_action_terms = assessment["matched_action_terms"]
    return result


def query_reference(query, result):
    return {
        "query_id": query.get(
            "combined_query_id",
            "",
        ),
        "original_query_id": query.get(
            "original_query_id",
            query.get(
                "combined_query_id",
                "",
            ),
        ),
        "original_query_text": query.get(
            "original_query_text",
            query.get(
                "query_text",
                "",
            ),
        ),
        "search_variant_text": query.get(
            "search_variant_text",
            query.get(
                "search_text",
                query.get(
                    "query_text",
                    "",
                ),
            ),
        ),
        "search_variant_type": query.get(
            "search_variant_type",
            "original",
        ),
        "source_stage": query.get(
            "source_stage",
            "",
        ),
        "source_query_id": query.get(
            "source_query_id",
            "",
        ),
        "query_origin": query.get(
            "query_origin",
            "",
        ),
        "query_text": query.get(
            "query_text",
            "",
        ),
        "language": query.get(
            "language",
            "",
        ),
        "discovery_channel": query.get(
            "discovery_channel",
            "",
        ),
        "query_kind": query.get(
            "query_kind",
            "",
        ),
        "crop_scope": query.get(
            "scope_type",
            "",
        ),
        "crop_key": query.get(
            "crop_key",
            "",
        ),
        "scenario": query.get(
            "weather_scenario",
            "",
        ),
        "action": query.get(
            "action",
            "",
        ),
        "search_region": query.get(
            "search_region",
            "",
        ),
        "result_rank": result.rank,
        "provider": result.provider,
        "relevance_status": result.relevance_status,
        "relevance_score": result.relevance_score,
        "relevance_reasons": list(
            result.relevance_reasons
        ),
        "matched_crop_terms": list(
            result.matched_crop_terms
        ),
        "matched_scenario_terms": list(
            result.matched_scenario_terms
        ),
        "matched_action_terms": list(
            result.matched_action_terms
        ),
    }


def make_candidate(query, result, retrieved_at):
    canonical_url = canonicalize_url(
        result.url
    )
    title = (
        result.title
        or ""
    ).strip()
    title_status = (
        "from_search_result"
        if title
        else "missing_from_search_result"
    )
    reference = query_reference(
        query,
        result,
    )
    discovery_channel_value = query.get(
        "discovery_channel",
        "",
    )

    return {
        "candidate_id": f"CD-{stable_id(canonical_url or result.url)}",
        "url": result.url,
        "canonical_url": canonical_url,
        "title": title,
        "title_status": title_status,
        "snippet": result.snippet,
        "source_domain": source_domain(
            result.url
        ),
        "source_type": source_type(
            result.url,
            discovery_channel_value,
            result.source_type_hint,
        ),
        "doi": result.doi,
        "abstract": result.abstract,
        "subjects": list(
            result.subjects
        ),
        "relevance_status": result.relevance_status,
        "relevance_score": result.relevance_score,
        "relevance_reasons": list(
            result.relevance_reasons
        ),
        "matched_crop_terms": list(
            result.matched_crop_terms
        ),
        "matched_scenario_terms": list(
            result.matched_scenario_terms
        ),
        "matched_action_terms": list(
            result.matched_action_terms
        ),
        "language": query.get(
            "language",
            "",
        ),
        "discovery_channel": discovery_channel_value,
        "query_id": query.get(
            "combined_query_id",
            "",
        ),
        "original_query_id": query.get(
            "original_query_id",
            query.get(
                "combined_query_id",
                "",
            ),
        ),
        "original_query_text": query.get(
            "original_query_text",
            query.get(
                "query_text",
                "",
            ),
        ),
        "search_variant_text": query.get(
            "search_variant_text",
            query.get(
                "search_text",
                query.get(
                    "query_text",
                    "",
                ),
            ),
        ),
        "search_variant_type": query.get(
            "search_variant_type",
            "original",
        ),
        "query_text": query.get(
            "query_text",
            "",
        ),
        "crop_scope": query.get(
            "scope_type",
            "",
        ),
        "crop_key": query.get(
            "crop_key",
            "",
        ),
        "scenario": query.get(
            "weather_scenario",
            "",
        ),
        "action": query.get(
            "action",
            "",
        ),
        "search_region": query.get(
            "search_region",
            "",
        ),
        "retrieved_at": retrieved_at,
        "raw_result_count": 1,
        "discovery_providers": [
            result.provider,
        ],
        "languages": [
            query.get(
                "language",
                "",
            )
        ],
        "discovery_channels": [
            discovery_channel_value,
        ],
        "source_stages": [
            query.get(
                "source_stage",
                "",
            )
        ],
        "query_origins": [
            query.get(
                "query_origin",
                "",
            )
        ],
        "query_references": [
            reference,
        ],
    }


def append_unique(value_list, value):
    if value and value not in value_list:
        value_list.append(value)


def merge_candidate(existing, new_candidate):
    existing["raw_result_count"] += new_candidate["raw_result_count"]
    existing["query_references"].extend(
        new_candidate["query_references"]
    )

    if (
        existing.get("title_status") == "missing_from_search_result"
        and new_candidate.get("title")
    ):
        existing["title"] = new_candidate["title"]
        existing["title_status"] = new_candidate["title_status"]

    for field in [
        "doi",
        "abstract",
        "snippet",
    ]:
        if not existing.get(field) and new_candidate.get(field):
            existing[field] = new_candidate[field]

    if new_candidate.get("relevance_score", 0) > existing.get("relevance_score", 0):
        for field in [
            "relevance_status",
            "relevance_score",
        ]:
            existing[field] = new_candidate[field]

    for field in [
        "discovery_providers",
        "languages",
        "discovery_channels",
        "source_stages",
        "query_origins",
        "subjects",
        "relevance_reasons",
        "matched_crop_terms",
        "matched_scenario_terms",
        "matched_action_terms",
    ]:
        for value in new_candidate.get(
            field,
            [],
        ):
            append_unique(
                existing[field],
                value,
            )


def build_candidates(raw_hits, retrieved_at):
    candidates = OrderedDict()

    for query, result in raw_hits:
        candidate = make_candidate(
            query,
            result,
            retrieved_at,
        )
        canonical_url = candidate["canonical_url"]
        dedup_key = (
            canonical_url
            or f"INVALID:{candidate['url']}"
        )

        if dedup_key in candidates:
            merge_candidate(
                candidates[dedup_key],
                candidate,
            )
        else:
            candidates[dedup_key] = candidate

    return list(
        candidates.values()
    )


def is_valid_url(url):
    parts = urlsplit(url)
    return bool(
        parts.scheme in {
            "http",
            "https",
        }
        and parts.netloc
    )


def audit_candidates(candidates, known_query_ids):
    issues = []
    canonical_urls = set()

    required_fields = [
        "candidate_id",
        "url",
        "canonical_url",
        "title",
        "snippet",
        "source_domain",
        "source_type",
        "doi",
        "abstract",
        "subjects",
        "relevance_status",
        "relevance_score",
        "relevance_reasons",
        "matched_crop_terms",
        "matched_scenario_terms",
        "matched_action_terms",
        "language",
        "discovery_channel",
        "query_id",
        "original_query_id",
        "original_query_text",
        "search_variant_text",
        "search_variant_type",
        "query_text",
        "crop_scope",
        "crop_key",
        "scenario",
        "action",
        "search_region",
        "retrieved_at",
        "query_references",
    ]

    for candidate in candidates:
        candidate_id = candidate.get(
            "candidate_id",
            "",
        )

        for field in required_fields:
            if field not in candidate:
                issues.append({
                    "type": "A3_MISSING_FIELD",
                    "candidate_id": candidate_id,
                    "field": field,
                })

        if not candidate.get("url"):
            issues.append({
                "type": "A3_EMPTY_URL",
                "candidate_id": candidate_id,
            })

        if not is_valid_url(
            candidate.get("url", "")
        ):
            issues.append({
                "type": "A3_MALFORMED_URL",
                "candidate_id": candidate_id,
                "url": candidate.get("url", ""),
            })

        canonical_url = candidate.get(
            "canonical_url",
            "",
        )
        if not canonical_url:
            issues.append({
                "type": "A3_EMPTY_CANONICAL_URL",
                "candidate_id": candidate_id,
            })
        elif not is_valid_url(canonical_url):
            issues.append({
                "type": "A3_MALFORMED_CANONICAL_URL",
                "candidate_id": candidate_id,
                "canonical_url": canonical_url,
            })
        elif canonical_url in canonical_urls:
            issues.append({
                "type": "A3_DUPLICATE_CANONICAL_URL_RECORD",
                "candidate_id": candidate_id,
                "canonical_url": canonical_url,
            })
        else:
            canonical_urls.add(canonical_url)

        if candidate.get("discovery_channel") not in VALID_DISCOVERY_CHANNELS:
            issues.append({
                "type": "A3_INVALID_DISCOVERY_CHANNEL",
                "candidate_id": candidate_id,
                "discovery_channel": candidate.get("discovery_channel", ""),
            })

        if candidate.get("search_region") not in VALID_SEARCH_REGIONS:
            issues.append({
                "type": "A3_INVALID_SEARCH_REGION",
                "candidate_id": candidate_id,
                "search_region": candidate.get("search_region", ""),
            })

        if not candidate.get("source_domain"):
            issues.append({
                "type": "A3_EMPTY_SOURCE_DOMAIN",
                "candidate_id": candidate_id,
            })

        if not candidate.get("query_id"):
            issues.append({
                "type": "A3_MISSING_QUERY_ID",
                "candidate_id": candidate_id,
            })
        elif candidate.get("query_id") not in known_query_ids:
            issues.append({
                "type": "A3_UNKNOWN_QUERY_ID",
                "candidate_id": candidate_id,
                "query_id": candidate.get("query_id"),
            })

        references = candidate.get(
            "query_references",
            [],
        )
        if not references:
            issues.append({
                "type": "A3_MISSING_QUERY_PROVENANCE",
                "candidate_id": candidate_id,
            })

        if candidate.get("raw_result_count") != len(references):
            issues.append({
                "type": "A3_DEDUP_PROVENANCE_LOST",
                "candidate_id": candidate_id,
                "raw_result_count": candidate.get("raw_result_count"),
                "query_reference_count": len(references),
            })

        if not candidate.get("title"):
            if candidate.get("title_status") != "missing_from_search_result":
                issues.append({
                    "type": "A3_EMPTY_TITLE_WITHOUT_STATUS",
                    "candidate_id": candidate_id,
                })

        if candidate.get("title_status") == "fabricated":
            issues.append({
                "type": "A3_FABRICATED_TITLE",
                "candidate_id": candidate_id,
            })

        if candidate.get("relevance_status") not in {
            "direct_match",
            "supporting_match",
            "rejected_irrelevant",
        }:
            issues.append({
                "type": "A3_INVALID_RELEVANCE_STATUS",
                "candidate_id": candidate_id,
                "relevance_status": candidate.get("relevance_status", ""),
            })

        if candidate.get("relevance_status") == "rejected_irrelevant":
            issues.append({
                "type": "A3_REJECTED_CANDIDATE_WRITTEN",
                "candidate_id": candidate_id,
            })

        if not isinstance(
            candidate.get("relevance_score"),
            int,
        ):
            issues.append({
                "type": "A3_INVALID_RELEVANCE_SCORE",
                "candidate_id": candidate_id,
            })

        for reference in references:
            reference_query_id = reference.get(
                "query_id",
                "",
            )
            if not reference_query_id:
                issues.append({
                    "type": "A3_REFERENCE_MISSING_QUERY_ID",
                    "candidate_id": candidate_id,
                })
            elif reference_query_id not in known_query_ids:
                issues.append({
                    "type": "A3_REFERENCE_UNKNOWN_QUERY_ID",
                    "candidate_id": candidate_id,
                    "query_id": reference_query_id,
                })

            if not reference.get("original_query_id"):
                issues.append({
                    "type": "A3_REFERENCE_MISSING_ORIGINAL_QUERY_ID",
                    "candidate_id": candidate_id,
                    "query_id": reference_query_id,
                })

            if not reference.get("original_query_text"):
                issues.append({
                    "type": "A3_REFERENCE_MISSING_ORIGINAL_QUERY_TEXT",
                    "candidate_id": candidate_id,
                    "query_id": reference_query_id,
                })

            if not reference.get("search_variant_text"):
                issues.append({
                    "type": "A3_REFERENCE_MISSING_SEARCH_VARIANT_TEXT",
                    "candidate_id": candidate_id,
                    "query_id": reference_query_id,
                })

            if reference.get("search_variant_type") not in {
                "original",
                "crop_scenario",
                "crop_scenario_action",
                "crop_weather_general",
            }:
                issues.append({
                    "type": "A3_REFERENCE_INVALID_SEARCH_VARIANT_TYPE",
                    "candidate_id": candidate_id,
                    "query_id": reference_query_id,
                    "search_variant_type": reference.get("search_variant_type", ""),
                })

            if reference.get("discovery_channel") not in VALID_DISCOVERY_CHANNELS:
                issues.append({
                    "type": "A3_REFERENCE_INVALID_DISCOVERY_CHANNEL",
                    "candidate_id": candidate_id,
                    "query_id": reference_query_id,
                })

            if not reference.get("source_stage"):
                issues.append({
                    "type": "A3_REFERENCE_MISSING_SOURCE_STAGE",
                    "candidate_id": candidate_id,
                    "query_id": reference_query_id,
                })

            if reference.get("source_stage") == "A2":
                if reference.get("query_origin") not in {
                    "observed",
                    "transformed",
                    "synthetic",
                }:
                    issues.append({
                        "type": "A3_A2_REFERENCE_MISSING_QUERY_ORIGIN",
                        "candidate_id": candidate_id,
                        "query_id": reference_query_id,
                    })

            if reference.get("relevance_status") not in {
                "direct_match",
                "supporting_match",
                "rejected_irrelevant",
            }:
                issues.append({
                    "type": "A3_REFERENCE_INVALID_RELEVANCE_STATUS",
                    "candidate_id": candidate_id,
                    "query_id": reference_query_id,
                })

    return issues


def request_json(url, headers=None, timeout=DEFAULT_TIMEOUT_SECONDS):
    request = Request(
        url,
        headers=headers or {},
    )
    try:
        with urlopen(
            request,
            timeout=timeout,
        ) as response:
            return json.loads(
                response.read().decode("utf-8")
            )
    except HTTPError as error:
        raise SearchProviderError(
            f"HTTP {error.code} while requesting {url}"
        ) from error
    except URLError as error:
        raise SearchProviderError(
            f"Network error while requesting {url}: {error.reason}"
        ) from error


def brave_web_search(query, limit, timeout):
    query_text = query.get(
        "search_text",
        "",
    ) or query.get(
        "query_text",
        "",
    )
    api_key = os.environ.get(
        "BRAVE_SEARCH_API_KEY",
        "",
    )
    if not api_key:
        raise SearchProviderUnavailable(
            "Web search provider 'brave' requires BRAVE_SEARCH_API_KEY."
        )

    params = urlencode({
        "q": query_text,
        "count": max(
            1,
            min(
                20,
                limit,
            ),
        ),
        "search_lang": "vi",
    })
    url = f"https://api.search.brave.com/res/v1/web/search?{params}"
    payload = request_json(
        url,
        headers={
            "Accept": "application/json",
            "X-Subscription-Token": api_key,
            "User-Agent": "KhoaLuan-A3-CandidateDiscovery/1.0",
        },
        timeout=timeout,
    )
    raw_results = payload.get(
        "web",
        {},
    ).get(
        "results",
        [],
    )

    results = []
    for index, item in enumerate(
        raw_results,
        start=1,
    ):
        url = item.get(
            "url",
            "",
        )
        if not url:
            continue

        snippet = (
            item.get("description")
            or item.get("snippet")
            or item.get("body")
            or ""
        )
        result = SearchResult(
            url=url,
            title=clean_search_text(
                item.get("title", "")
            ),
            snippet=clean_search_text(snippet),
            rank=index,
            provider="brave",
        )
        result = apply_relevance(
            result,
            assess_web_relevance(
                query,
                result,
            ),
        )

        if result.relevance_status == "rejected_irrelevant":
            continue

        results.append(result)
        if len(results) >= limit:
            break

    return results, len(raw_results)


def make_ddgs_client(timeout):
    try:
        from ddgs import DDGS
    except ImportError as error:
        raise SearchProviderUnavailable(
            "Web search fallback 'ddgs' is not installed. Install dependencies with pip install -r requirements.txt."
        ) from error

    try:
        return DDGS(
            timeout=timeout
        )
    except TypeError:
        return DDGS()


def ddgs_web_search(query, limit, timeout):
    query_text = query.get(
        "search_text",
        "",
    ) or query.get(
        "query_text",
        "",
    )
    client = make_ddgs_client(
        timeout
    )
    raw_results = []

    try:
        if hasattr(
            client,
            "__enter__",
        ):
            with client as search:
                raw_results = list(
                    search.text(
                        query_text,
                        region="vn-vi",
                        safesearch="moderate",
                        max_results=max(
                            1,
                            limit,
                        ),
                    )
                )
        else:
            raw_results = list(
                client.text(
                    query_text,
                    region="vn-vi",
                    safesearch="moderate",
                    max_results=max(
                        1,
                        limit,
                    ),
                )
            )
    except Exception as error:
        if "no results found" in str(error).casefold():
            return [], 0
        raise SearchProviderError(
            f"DDGS web search failed: {error}"
        ) from error
    finally:
        close = getattr(
            client,
            "close",
            None,
        )
        if callable(close):
            close()

    results = []
    for index, item in enumerate(
        raw_results,
        start=1,
    ):
        url = (
            item.get("href")
            or item.get("url")
            or ""
        )
        snippet = (
            item.get("body")
            or item.get("snippet")
            or item.get("description")
            or ""
        )

        if not url:
            continue

        result = SearchResult(
            url=url,
            title=clean_search_text(
                item.get("title", "")
            ),
            snippet=clean_search_text(snippet),
            rank=index,
            provider="ddgs",
        )
        result = apply_relevance(
            result,
            assess_web_relevance(
                query,
                result,
            ),
        )

        if result.relevance_status == "rejected_irrelevant":
            continue

        results.append(result)
        if len(results) >= limit:
            break

    return results, len(raw_results)


def web_search(query, limit, timeout):
    if os.environ.get(
        "BRAVE_SEARCH_API_KEY",
        "",
    ):
        return brave_web_search(
            query,
            limit,
            timeout,
        )

    return ddgs_web_search(
        query,
        limit,
        timeout,
    )


def crossref_item_to_result(item, rank):
    doi = item.get(
        "DOI",
        "",
    )
    url = item.get(
        "URL",
        "",
    )
    if not url and doi:
        url = f"https://doi.org/{doi}"

    title_values = item.get(
        "title",
        [],
    )
    title = (
        clean_crossref_text(title_values[0])
        if title_values
        else ""
    )
    abstract = clean_crossref_text(
        item.get(
            "abstract",
            "",
        )
    )
    subjects = tuple(
        clean_crossref_text(subject)
        for subject in item.get(
            "subject",
            [],
        )
        if clean_crossref_text(subject)
    )

    if not url:
        return None

    return SearchResult(
        url=url,
        title=title,
        rank=rank,
        provider="crossref",
        source_type_hint=item.get(
            "type",
            "scholarly_record",
        ),
        doi=doi,
        abstract=abstract,
        subjects=subjects,
    )


def scholarly_result_sort_key(result):
    status_rank = {
        "direct_match": 0,
        "supporting_match": 1,
        "rejected_irrelevant": 9,
    }.get(
        result.relevance_status,
        9,
    )
    return (
        status_rank,
        -result.relevance_score,
        result.rank,
    )


def crossref_scholarly_search(query, limit, timeout):
    query_text = query.get(
        "search_text",
        "",
    ) or query.get(
        "query_text",
        "",
    )
    internal_limit = max(
        limit * 2,
        limit + 5,
    )
    params = {
        "query": query_text,
        "rows": max(
            1,
            min(
                20,
                internal_limit,
            ),
        ),
    }
    mailto = os.environ.get(
        "A3_CROSSREF_MAILTO",
        "",
    )
    if mailto:
        params["mailto"] = mailto

    url = (
        "https://api.crossref.org/works?"
        + urlencode(params)
    )
    payload = request_json(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "KhoaLuan-A3-CandidateDiscovery/1.0",
        },
        timeout=timeout,
    )

    items = payload.get(
        "message",
        {},
    ).get(
        "items",
        [],
    )
    results = []

    for index, item in enumerate(
        items,
        start=1,
    ):
        result = crossref_item_to_result(
            item,
            index,
        )
        if result is None:
            continue

        assessment = assess_scholarly_relevance(
            query,
            result,
        )
        result = apply_relevance(
            result,
            assessment,
        )

        if result.relevance_status == "rejected_irrelevant":
            continue

        results.append(result)

    filtered_results = sorted(
        results,
        key=scholarly_result_sort_key,
    )[:limit]
    return filtered_results, len(items)


def search_query(query, results_per_query, timeout):
    channel = query.get(
        "discovery_channel",
        "",
    )

    if channel == "web":
        return web_search(
            query,
            results_per_query,
            timeout,
        )

    if channel == "scholarly":
        return crossref_scholarly_search(
            query,
            results_per_query,
            timeout,
        )

    raise SearchProviderUnavailable(
        f"No search provider for discovery_channel={channel!r}."
    )


def provider_name_for_query(query):
    channel = query.get(
        "discovery_channel",
        "",
    )

    if channel == "web":
        if os.environ.get(
            "BRAVE_SEARCH_API_KEY",
            "",
        ):
            return "brave"
        return "ddgs"

    if channel == "scholarly":
        return "crossref"

    return channel or "unknown"


def search_variant_with_retries(
    variant,
    *,
    results_per_query,
    timeout,
    attempts,
):
    last_error = None

    for attempt in range(
        1,
        attempts + 1,
    ):
        try:
            results, raw_provider_results = search_query(
                variant,
                results_per_query,
                timeout,
            )
            return results, raw_provider_results, None
        except SearchProviderError as error:
            last_error = error
            if attempt < attempts:
                time.sleep(0.5)

    return [], 0, {
        "original_query_id": variant.get(
            "original_query_id",
            variant.get(
                "combined_query_id",
                "",
            ),
        ),
        "original_query_text": variant.get(
            "original_query_text",
            variant.get(
                "query_text",
                "",
            ),
        ),
        "search_variant_text": variant.get(
            "search_variant_text",
            variant.get(
                "search_text",
                "",
            ),
        ),
        "search_variant_type": variant.get(
            "search_variant_type",
            "original",
        ),
        "provider": provider_name_for_query(
            variant
        ),
        "attempts": attempts,
        "error": str(last_error),
    }


def execute_live_search(
    selected_rows,
    *,
    query_limit,
    results_per_query,
    timeout,
    channels,
    sleep_seconds,
):
    channel_set = set(channels)
    executable_queries = [
        row
        for row in selected_rows
        if row.get("discovery_channel") in channel_set
    ][:query_limit]

    raw_hits = []
    raw_provider_results = 0
    query_result_counts = {}
    executed_search_requests = 0
    provider_errors = []
    provider_error_query_ids = set()
    zero_result_query_ids = set()
    recovered_by_fallback_query_ids = set()
    successful_original_query_ids = set()

    for index, query in enumerate(
        executable_queries,
        start=1,
    ):
        original_query_id = query.get(
            "combined_query_id",
            "",
        )
        query_result_counts[original_query_id] = 0
        query_raw_provider_results = 0
        original_variant_relevant = False

        for variant in search_variants_for_query(query):
            executed_search_requests += 1
            (
                results,
                provider_result_count,
                provider_error,
            ) = search_variant_with_retries(
                variant,
                results_per_query=results_per_query,
                timeout=timeout,
                attempts=PROVIDER_ATTEMPTS,
            )

            if provider_error:
                provider_errors.append(provider_error)
                provider_error_query_ids.add(original_query_id)
                continue

            successful_original_query_ids.add(original_query_id)
            raw_provider_results += provider_result_count
            query_raw_provider_results += provider_result_count

            if (
                variant.get("search_variant_type") == "original"
                and results
            ):
                original_variant_relevant = True

            if (
                variant.get("search_variant_type") != "original"
                and results
                and not original_variant_relevant
            ):
                recovered_by_fallback_query_ids.add(original_query_id)

            query_result_counts[original_query_id] += len(results)

            for result in results:
                raw_hits.append(
                    (
                        variant,
                        result,
                    )
                )

            if results:
                break

        if (
            query_raw_provider_results == 0
            and original_query_id not in provider_error_query_ids
        ):
            zero_result_query_ids.add(original_query_id)

        if index < len(executable_queries) and sleep_seconds:
            time.sleep(sleep_seconds)

    search_stats = {
        "executed_search_requests": executed_search_requests,
        "provider_errors": provider_errors,
        "queries_with_provider_error": len(provider_error_query_ids),
        "queries_with_zero_results": len(zero_result_query_ids),
        "original_queries_succeeded": len(successful_original_query_ids),
        "queries_recovered_by_fallback": len(recovered_by_fallback_query_ids),
    }

    return (
        executable_queries,
        raw_hits,
        raw_provider_results,
        query_result_counts,
        search_stats,
    )


def domain_breakdown(candidates):
    return dict(
        Counter(
            candidate.get(
                "source_domain",
                "",
            )
            for candidate in candidates
            if candidate.get("source_domain")
        ).most_common()
    )


def query_coverage_summary(executed_queries, query_result_counts):
    executed_count = len(executed_queries)
    queries_with_relevant_results = sum(
        1
        for query in executed_queries
        if query_result_counts.get(
            query.get(
                "combined_query_id",
                "",
            ),
            0,
        )
        > 0
    )
    queries_without_relevant_results = (
        executed_count
        -
        queries_with_relevant_results
    )
    query_hit_rate = (
        queries_with_relevant_results / executed_count
        if executed_count
        else 0.0
    )

    return {
        "executed_queries": executed_count,
        "queries_with_relevant_results": queries_with_relevant_results,
        "queries_without_relevant_results": queries_without_relevant_results,
        "query_hit_rate": round(
            query_hit_rate,
            4,
        ),
    }


def build_run_summary(
    *,
    mode,
    query_bank_rows,
    selected_rows,
    executed_queries,
    query_result_counts,
    search_stats,
    raw_provider_results,
    raw_results,
    candidates,
    audit_issues,
    status,
    errors=None,
    candidate_output_path=CANDIDATES_JSONL,
    summary_output_path=SUMMARY_JSON,
):
    coverage = query_coverage_summary(
        executed_queries,
        query_result_counts,
    )
    stats = search_stats or {}

    return {
        "generated_at": utc_now(),
        "stage": "A3",
        "mode": mode,
        "status": status,
        "total_query_bank": len(query_bank_rows),
        "selected_queries": len(selected_rows),
        "skipped_queries": len(query_bank_rows) - len(selected_rows),
        "executed_queries": coverage["executed_queries"],
        "executed_original_queries": coverage["executed_queries"],
        "executed_search_requests": stats.get(
            "executed_search_requests",
            coverage["executed_queries"],
        ),
        "queries_with_relevant_results": coverage["queries_with_relevant_results"],
        "queries_without_relevant_results": coverage["queries_without_relevant_results"],
        "query_hit_rate": coverage["query_hit_rate"],
        "minimum_query_hit_rate": MIN_QUERY_HIT_RATE,
        "original_queries_succeeded": stats.get(
            "original_queries_succeeded",
            coverage["executed_queries"],
        ),
        "queries_recovered_by_fallback": stats.get(
            "queries_recovered_by_fallback",
            0,
        ),
        "provider_errors": stats.get(
            "provider_errors",
            [],
        ),
        "queries_with_provider_error": stats.get(
            "queries_with_provider_error",
            0,
        ),
        "queries_with_zero_results": stats.get(
            "queries_with_zero_results",
            0,
        ),
        "raw_provider_results": raw_provider_results,
        "raw_results": raw_results,
        "relevant_results": raw_results,
        "relevant_results_kept": raw_results,
        "irrelevant_results_filtered": raw_provider_results - raw_results,
        "irrelevant_filtered": raw_provider_results - raw_results,
        "unique_candidates": len(candidates),
        "duplicate_urls_removed": raw_results - len(candidates),
        "selection": selection_summary(
            query_bank_rows,
            selected_rows,
        ),
        "by_channel": count_by(
            selected_rows,
            "discovery_channel",
        ),
        "by_language": count_by(
            selected_rows,
            "language",
        ),
        "by_domain": domain_breakdown(
            candidates
        ),
        "by_search_region": count_by(
            selected_rows,
            "search_region",
        ),
        "audit": {
            "issue_count": len(audit_issues),
            "issues": audit_issues,
        },
        "errors": errors or [],
        "outputs": {
            "candidate_documents_jsonl": str(candidate_output_path),
            "candidate_discovery_summary_json": str(summary_output_path),
        },
    }


def print_counter(title, values):
    print()
    print(title)
    for key, value in values.items():
        print(
            f"  {str(key):<24} {value}"
        )


def print_selection_report(summary, selected_rows):
    print()
    print("Query selector:")
    print(
        f"  total    : {summary['total_query_bank']}"
    )
    print(
        f"  selected : {summary['selected_queries']}"
    )
    print(
        f"  skipped  : {summary['skipped_queries']}"
    )

    print_counter(
        "Selection by discovery channel:",
        summary["selection"]["by_discovery_channel"],
    )
    print_counter(
        "Selection by language:",
        summary["selection"]["by_language"],
    )
    print_counter(
        "Selection by source stage:",
        summary["selection"]["by_source_stage"],
    )
    print_counter(
        "Selection by query origin:",
        summary["selection"]["by_query_origin"],
    )
    print_counter(
        "Selection by query kind:",
        summary["selection"]["by_query_kind"],
    )
    print_counter(
        "Selection by crop scope:",
        summary["selection"]["by_crop_scope"],
    )
    print_counter(
        "Selection by crop key:",
        summary["selection"]["by_crop_key"],
    )
    print_counter(
        "Selection by search region:",
        summary["selection"]["by_search_region"],
    )

    print()
    print("Representative selected queries:")
    for row in representative_queries(
        selected_rows
    ):
        print()
        print(
            f"{row['selection_rank']:02d}. "
            f"[{row['combined_query_id']}] "
            f"{row.get('discovery_channel')} | "
            f"{row.get('source_stage')} | "
            f"{row.get('query_origin') or 'A1'} | "
            f"{row.get('query_kind')} | "
            f"{row.get('scope_type')} | "
            f"{row.get('crop_key')} | "
            f"{row.get('weather_scenario')} | "
            f"{row.get('action')} | "
            f"{row.get('search_region')}"
        )
        print(
            f"    {row.get('query_text', '')}"
        )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Stage A3 candidate document discovery."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Select and report queries without external search.",
    )
    mode.add_argument(
        "--live",
        action="store_true",
        help="Execute a small live discovery run.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=QUERY_BANK_JSONL,
        help="Combined A1/A2 discovery query bank JSONL.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=CANDIDATES_JSONL,
        help="Candidate document registry JSONL for live runs.",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=SUMMARY_JSON,
        help="Candidate discovery summary JSON for live runs.",
    )
    parser.add_argument(
        "--selection-limit",
        type=int,
        default=DEFAULT_SELECTION_LIMIT,
        help="Maximum representative query subset selected from the full bank.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIVE_QUERY_LIMIT,
        help="Maximum selected queries to execute in live mode.",
    )
    parser.add_argument(
        "--results-per-query",
        type=int,
        default=DEFAULT_RESULTS_PER_QUERY,
        help="Maximum search results to keep per live query.",
    )
    parser.add_argument(
        "--channels",
        nargs="+",
        choices=sorted(VALID_DISCOVERY_CHANNELS),
        default=sorted(VALID_DISCOVERY_CHANNELS),
        help="Logical discovery channels allowed for live search.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="HTTP timeout in seconds for live provider requests.",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=1.0,
        help="Pause between live search requests.",
    )
    return parser.parse_args()


def main():
    configure_stdout()
    args = parse_args()

    if args.selection_limit < 1:
        raise SystemExit(
            "--selection-limit must be at least 1."
        )
    if args.limit < 1:
        raise SystemExit(
            "--limit must be at least 1."
        )
    if args.results_per_query < 1:
        raise SystemExit(
            "--results-per-query must be at least 1."
        )

    mode = (
        "live"
        if args.live
        else "dry_run"
    )

    query_bank_rows = load_jsonl(
        args.input
    )
    selected_rows = select_queries(
        query_bank_rows,
        args.selection_limit,
    )
    relevance_rule_issues = audit_relevance_rules()

    if mode == "dry_run":
        dry_run_status = (
            "DRY_RUN_READY"
            if not relevance_rule_issues
            else "NEEDS_A3_REVIEW"
        )
        summary = build_run_summary(
            mode=mode,
            query_bank_rows=query_bank_rows,
            selected_rows=selected_rows,
            executed_queries=[],
            query_result_counts={},
            search_stats={},
            raw_provider_results=0,
            raw_results=0,
            candidates=[],
            audit_issues=relevance_rule_issues,
            status=dry_run_status,
            candidate_output_path=args.output,
            summary_output_path=args.summary,
        )
        print("=" * 80)
        print("AGRI RAG - A3 CANDIDATE DOCUMENT DISCOVERY / DRY RUN")
        print("=" * 80)
        print_selection_report(
            summary,
            selected_rows,
        )
        print()
        print("Live search executed: no")
        print(f"Audit status        : {dry_run_status}")
        print(f"Audit issues        : {len(relevance_rule_issues)}")
        return

    print("=" * 80)
    print("AGRI RAG - A3 CANDIDATE DOCUMENT DISCOVERY / LIVE")
    print("=" * 80)

    try:
        (
            executed_queries,
            raw_hits,
            raw_provider_results,
            query_result_counts,
            search_stats,
        ) = execute_live_search(
            selected_rows,
            query_limit=args.limit,
            results_per_query=args.results_per_query,
            timeout=args.timeout,
            channels=args.channels,
            sleep_seconds=args.sleep_seconds,
        )
    except SearchProviderError as error:
        error_status = (
            "SEARCH_PROVIDER_UNAVAILABLE"
            if isinstance(
                error,
                SearchProviderUnavailable,
            )
            else
            "SEARCH_PROVIDER_ERROR"
        )
        summary = build_run_summary(
            mode=mode,
            query_bank_rows=query_bank_rows,
            selected_rows=selected_rows,
            executed_queries=[],
            query_result_counts={},
            search_stats={},
            raw_provider_results=0,
            raw_results=0,
            candidates=[],
            audit_issues=relevance_rule_issues,
            status=error_status,
            errors=[
                str(error),
            ],
            candidate_output_path=args.output,
            summary_output_path=args.summary,
        )
        write_json(
            args.summary,
            summary,
        )
        print_selection_report(
            summary,
            selected_rows,
        )
        print()
        print("Live search executed: no")
        print(f"Search status       : {error_status}")
        print(f"Search error        : {error}")
        print(f"Summary             : {args.summary}")
        raise SystemExit(2) from error

    retrieved_at = utc_now()
    candidates = build_candidates(
        raw_hits,
        retrieved_at,
    )
    known_query_ids = {
        row.get(
            "combined_query_id",
            "",
        )
        for row in query_bank_rows
    }
    audit_issues = relevance_rule_issues + audit_candidates(
        candidates,
        known_query_ids,
    )
    coverage = query_coverage_summary(
        executed_queries,
        query_result_counts,
    )
    provider_unusable = (
        bool(executed_queries)
        and search_stats.get(
            "queries_with_provider_error",
            0,
        )
        == len(executed_queries)
        and not candidates
    )
    if audit_issues:
        status = "NEEDS_A3_REVIEW"
    elif provider_unusable:
        status = "SEARCH_PROVIDER_ERROR"
    elif candidates and coverage["query_hit_rate"] >= MIN_QUERY_HIT_RATE:
        status = "READY_FOR_A4"
    else:
        status = "A3_LOW_COVERAGE"

    write_jsonl(
        args.output,
        candidates,
    )
    summary = build_run_summary(
        mode=mode,
        query_bank_rows=query_bank_rows,
        selected_rows=selected_rows,
        executed_queries=executed_queries,
        query_result_counts=query_result_counts,
        search_stats=search_stats,
        raw_provider_results=raw_provider_results,
        raw_results=len(raw_hits),
        candidates=candidates,
        audit_issues=audit_issues,
        status=status,
        candidate_output_path=args.output,
        summary_output_path=args.summary,
    )
    write_json(
        args.summary,
        summary,
    )

    print_selection_report(
        summary,
        selected_rows,
    )
    print()
    print(f"Executed queries        : {len(executed_queries)}")
    print(
        "Executed search requests: "
        f"{search_stats['executed_search_requests']}"
    )
    print(
        "Queries with relevant  : "
        f"{coverage['queries_with_relevant_results']}"
    )
    print(
        "Queries without        : "
        f"{coverage['queries_without_relevant_results']}"
    )
    print(
        "Query hit rate         : "
        f"{coverage['query_hit_rate']:.2%}"
    )
    print(
        "Queries recovered      : "
        f"{search_stats['queries_recovered_by_fallback']}"
    )
    print(
        "Provider error queries : "
        f"{search_stats['queries_with_provider_error']}"
    )
    print(
        "Zero-result queries    : "
        f"{search_stats['queries_with_zero_results']}"
    )
    print(f"Raw provider results    : {raw_provider_results}")
    print(f"Relevant results kept   : {len(raw_hits)}")
    print(f"Irrelevant filtered     : {raw_provider_results - len(raw_hits)}")
    print(f"Raw results             : {len(raw_hits)}")
    print(f"Unique canonical URLs   : {len(candidates)}")
    print(f"Duplicates removed      : {len(raw_hits) - len(candidates)}")
    print(f"Audit status            : {status}")
    print(f"Audit issues            : {len(audit_issues)}")
    print(f"Candidate registry      : {args.output}")
    print(f"Summary                 : {args.summary}")


if __name__ == "__main__":
    main()
