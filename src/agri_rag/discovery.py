import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CROP_CONFIG = PROJECT_ROOT / "config" / "crops.yaml"

OUTPUT_DIR = PROJECT_ROOT / "data" / "agri_rag" / "discovery"

QUERY_CSV = OUTPUT_DIR / "query_bank.csv"
QUERY_JSONL = OUTPUT_DIR / "query_bank.jsonl"
SUMMARY_JSON = OUTPUT_DIR / "query_bank_summary.json"

A2_QUERY_CSV = OUTPUT_DIR / "a2_public_queries.csv"
A2_QUERY_JSONL = OUTPUT_DIR / "a2_public_queries.jsonl"
COMBINED_QUERY_JSONL = OUTPUT_DIR / "discovery_queries_combined.jsonl"


# ============================================================
# ROUND 1 SEARCH REGIONS
#
# Đây là SEARCH CONTEXT, không phải region thật của document.
# ============================================================

VI_SEARCH_REGIONS = [
    {
        "id": "NONE",
        "text": "",
        "priority": 1,
    },
    {
        "id": "VIETNAM",
        "text": "Việt Nam",
        "priority": 1,
    },
    {
        "id": "BINH_DINH_LEGACY",
        "text": "Bình Định",
        "priority": 1,
    },
    {
        "id": "GIA_LAI_CURRENT",
        "text": "Gia Lai",
        "priority": 1,
    },
]

EN_SEARCH_REGIONS = [
    {
        "id": "GLOBAL",
        "text": "",
        "priority": 2,
    },
    {
        "id": "VIETNAM",
        "text": "Vietnam",
        "priority": 2,
    },
]


# ============================================================
# ROUND 2 / GAP-FILL REGIONS
#
# CHƯA sinh query ở Stage A1.
# Chỉ dùng sau Coverage Audit nếu thiếu evidence.
# ============================================================

REGIONAL_FALLBACKS = [
    "SOUTH_CENTRAL_COAST",
    "MEKONG_DELTA",
    "SOUTHEAST_VIETNAM",
    "CENTRAL_HIGHLANDS",
    "NORTH_CENTRAL_VIETNAM",
    "RED_RIVER_DELTA",
    "SOUTHEAST_ASIA",
    "TROPICAL",
    "GLOBAL",
]

TARGET_CROP_IDS = {
    "cai_xanh",
    "ngo",
    "cai_cuc",
    "rau_muong",
    "xa_lach",
}

NO_ACTION = "NONE"

REQUIRED_FIELDS = [
    "query_id",
    "search_round",
    "language",
    "channel",
    "priority",
    "query_kind",
    "scope_type",
    "crop_id",
    "crop_name",
    "crop_group",
    "crop_term",
    "weather_scenario",
    "weather_factor",
    "weather_term",
    "effects",
    "action",
    "search_region",
    "search_region_term",
    "query",
]

A2_REQUIRED_FIELDS = [
    "query_id",
    "query_text",
    "language",
    "stage",
    "query_origin",
    "intent",
    "scenario",
    "action",
    "crop_scope",
    "crop_key",
    "search_region",
    "search_region_term",
    "source_url",
    "source_title",
    "parent_query_id",
]

VALID_LANGUAGES = {
    "vi",
    "en",
}

VALID_CHANNELS = {
    "vi": "web",
    "en": "scholarly",
}

VALID_QUERY_KINDS = {
    "effect",
    "action",
}

VALID_SCOPE_TYPES = {
    "crop_specific",
    "crop_group",
}

ROUND_1_SEARCH_REGIONS = {
    "vi": VI_SEARCH_REGIONS,
    "en": EN_SEARCH_REGIONS,
}

A2_STAGE = "A2"

A2_SEARCH_REGIONS = {
    "NONE": "",
    "VIETNAM": "Việt Nam",
    "BINH_DINH_LEGACY": "Bình Định",
    "GIA_LAI_CURRENT": "Gia Lai",
}

A2_QUERY_ORIGINS = {
    "observed",
    "transformed",
    "synthetic",
}

A2_QUERY_ORIGIN_ORDER = [
    "observed",
    "transformed",
    "synthetic",
]

A2_REVIEW_CHANGES = [
    "Changed A2 region text from direct 'ở <region>' suffix to search-keyword suffix.",
    "Changed awkward leaf-wetness group wording to '<crop> bị ướt lá lâu...'.",
    "Changed heat impact wording from 'có nặng không' to 'thế nào'.",
    "Changed hot-weather planting wording to 'có nên trồng'.",
    "Changed cold-weather planting wording to 'có được không'.",
    "Changed weather-change recovery wording to 'chăm <crop> thế nào'.",
    "Changed heavy-rain mortality wording to 'có bị chết không'.",
]

A2_INTENTS = {
    "irrigation_water",
    "rain_effect",
    "heat_sunlight",
    "humidity_disease",
    "fertilizer_weather",
    "spraying_weather",
    "planting_weather",
    "weather_recovery",
}

# No real public-query dataset exists in the repository yet.
# Future observed entries must include source_url and source_title.
OBSERVED_PUBLIC_QUERY_SEEDS = []

# Future transformed entries must point to an observed parent_query_id.
TRANSFORMED_PUBLIC_QUERY_SEEDS = []


def specific_crop_keys():
    return [
        "cai_xanh",
        "ngo",
        "cai_cuc",
        "rau_muong",
        "xa_lach",
    ]


PUBLIC_INTENT_PATTERNS = {
    "irrigation_water": [
        {
            "template": "hôm nay có cần tưới {crop} không",
            "scenario": "dry_spell",
            "action": "irrigation",
            "crop_scope": "crop_group",
            "crop_keys": [
                "general_vegetable",
                "leafy_vegetable",
            ],
            "search_regions": [
                "NONE",
                "VIETNAM",
            ],
        },
        {
            "template": "mưa rồi có cần tưới {crop} nữa không",
            "scenario": "post_rain",
            "action": "irrigation",
            "crop_scope": "crop_specific",
            "crop_keys": specific_crop_keys(),
            "search_regions": [
                "NONE",
                "VIETNAM",
            ],
        },
        {
            "template": "đất còn ướt có tưới {crop} được không",
            "scenario": "wet_soil",
            "action": "irrigation",
            "crop_scope": "crop_specific",
            "crop_keys": [
                "cai_xanh",
                "cai_cuc",
                "xa_lach",
                "rau_muong",
            ],
            "search_regions": [
                "NONE",
                "BINH_DINH_LEGACY",
            ],
        },
        {
            "template": "nắng quá nên tưới {crop} lúc nào",
            "scenario": "hot_weather",
            "action": "irrigation",
            "crop_scope": "crop_specific",
            "crop_keys": specific_crop_keys(),
            "search_regions": [
                "NONE",
                "GIA_LAI_CURRENT",
            ],
        },
        {
            "template": "{crop} bị úng sau mưa phải làm sao",
            "scenario": "waterlogging",
            "action": "drainage",
            "crop_scope": "crop_specific",
            "crop_keys": [
                "cai_xanh",
                "cai_cuc",
                "xa_lach",
                "rau_muong",
            ],
            "search_regions": [
                "NONE",
                "VIETNAM",
            ],
        },
        {
            "template": "mưa liên tục mấy ngày {crop} có bị úng không",
            "scenario": "prolonged_rain",
            "action": "drainage",
            "crop_scope": "crop_group",
            "crop_keys": [
                "general_vegetable",
                "leafy_vegetable",
            ],
            "search_regions": [
                "NONE",
                "BINH_DINH_LEGACY",
            ],
        },
    ],

    "rain_effect": [
        {
            "template": "mưa nhiều {crop} bị vàng lá phải làm sao",
            "scenario": "prolonged_rain",
            "action": "field_inspection",
            "crop_scope": "crop_specific",
            "crop_keys": [
                "cai_xanh",
                "cai_cuc",
                "xa_lach",
            ],
            "search_regions": [
                "NONE",
                "VIETNAM",
            ],
        },
        {
            "template": "mưa lớn {crop} có bị chết không",
            "scenario": "heavy_rain",
            "action": "crop_protection",
            "crop_scope": "crop_specific",
            "crop_keys": specific_crop_keys(),
            "search_regions": [
                "NONE",
            ],
        },
        {
            "template": "{crop} mới trồng gặp mưa lớn thì làm sao",
            "scenario": "heavy_rain",
            "action": "crop_protection",
            "crop_scope": "crop_specific",
            "crop_keys": [
                "cai_xanh",
                "cai_cuc",
                "xa_lach",
                "ngo",
            ],
            "search_regions": [
                "NONE",
                "BINH_DINH_LEGACY",
            ],
        },
        {
            "template": "sau mưa nên chăm {crop} thế nào",
            "scenario": "post_rain",
            "action": "post_rain_care",
            "crop_scope": "crop_group",
            "crop_keys": [
                "general_vegetable",
                "short_cycle_vegetable",
            ],
            "search_regions": [
                "NONE",
                "GIA_LAI_CURRENT",
            ],
        },
        {
            "template": "mưa kéo dài ảnh hưởng {crop} thế nào",
            "scenario": "prolonged_rain",
            "action": NO_ACTION,
            "crop_scope": "crop_group",
            "crop_keys": [
                "leafy_vegetable",
                "herb_vegetable",
            ],
            "search_regions": [
                "NONE",
                "VIETNAM",
            ],
        },
    ],

    "heat_sunlight": [
        {
            "template": "trời nắng nóng {crop} bị héo phải làm sao",
            "scenario": "hot_weather",
            "action": "irrigation",
            "crop_scope": "crop_specific",
            "crop_keys": specific_crop_keys(),
            "search_regions": [
                "NONE",
                "VIETNAM",
            ],
        },
        {
            "template": "nắng gắt có nên tưới {crop} giữa trưa không",
            "scenario": "strong_sun",
            "action": "irrigation",
            "crop_scope": "crop_group",
            "crop_keys": [
                "leafy_vegetable",
                "general_vegetable",
            ],
            "search_regions": [
                "NONE",
                "BINH_DINH_LEGACY",
            ],
        },
        {
            "template": "{crop} bị cháy lá do nắng xử lý sao",
            "scenario": "strong_sun",
            "action": "crop_protection",
            "crop_scope": "crop_specific",
            "crop_keys": [
                "cai_xanh",
                "cai_cuc",
                "xa_lach",
            ],
            "search_regions": [
                "NONE",
                "GIA_LAI_CURRENT",
            ],
        },
        {
            "template": "nắng nóng có cần che lưới cho {crop} không",
            "scenario": "hot_weather",
            "action": "shade",
            "crop_scope": "crop_specific",
            "crop_keys": [
                "cai_xanh",
                "cai_cuc",
                "xa_lach",
                "ngo",
            ],
            "search_regions": [
                "NONE",
                "VIETNAM",
            ],
        },
        {
            "template": "nắng kéo dài ảnh hưởng {crop} thế nào",
            "scenario": "hot_weather",
            "action": NO_ACTION,
            "crop_scope": "crop_group",
            "crop_keys": [
                "leafy_vegetable",
                "short_cycle_vegetable",
            ],
            "search_regions": [
                "NONE",
                "GIA_LAI_CURRENT",
            ],
        },
    ],

    "humidity_disease": [
        {
            "template": "trời ẩm {crop} dễ bị bệnh gì",
            "scenario": "high_humidity",
            "action": "disease_monitoring",
            "crop_scope": "crop_specific",
            "crop_keys": specific_crop_keys(),
            "search_regions": [
                "NONE",
                "VIETNAM",
            ],
        },
        {
            "template": "mưa nhiều {crop} bị nấm phải làm sao",
            "scenario": "prolonged_rain",
            "action": "disease_management",
            "crop_scope": "crop_specific",
            "crop_keys": [
                "cai_xanh",
                "cai_cuc",
                "xa_lach",
                "ngo",
            ],
            "search_regions": [
                "NONE",
                "BINH_DINH_LEGACY",
            ],
        },
        {
            "template": "độ ẩm cao có làm {crop} bị thối không",
            "scenario": "high_humidity",
            "action": "disease_monitoring",
            "crop_scope": "crop_group",
            "crop_keys": [
                "leafy_vegetable",
                "general_vegetable",
            ],
            "search_regions": [
                "NONE",
                "GIA_LAI_CURRENT",
            ],
        },
        {
            "template": "sau mưa {crop} dễ bị sâu bệnh gì",
            "scenario": "post_rain",
            "action": "disease_monitoring",
            "crop_scope": "crop_specific",
            "crop_keys": specific_crop_keys(),
            "search_regions": [
                "NONE",
                "VIETNAM",
            ],
        },
        {
            "template": "{crop} bị ướt lá lâu có dễ bị bệnh không",
            "scenario": "leaf_wetness",
            "action": "disease_monitoring",
            "crop_scope": "crop_group",
            "crop_keys": [
                "leafy_vegetable",
                "herb_vegetable",
            ],
            "search_regions": [
                "NONE",
            ],
        },
    ],

    "fertilizer_weather": [
        {
            "template": "mưa xong có bón phân cho {crop} được không",
            "scenario": "post_rain",
            "action": "fertilization",
            "crop_scope": "crop_specific",
            "crop_keys": specific_crop_keys(),
            "search_regions": [
                "NONE",
                "VIETNAM",
            ],
        },
        {
            "template": "bón phân cho {crop} trước khi mưa có bị trôi không",
            "scenario": "heavy_rain",
            "action": "fertilization",
            "crop_scope": "crop_group",
            "crop_keys": [
                "general_vegetable",
                "short_cycle_vegetable",
            ],
            "search_regions": [
                "NONE",
                "BINH_DINH_LEGACY",
            ],
        },
        {
            "template": "sau mưa bao lâu thì bón phân cho {crop}",
            "scenario": "post_rain",
            "action": "fertilization",
            "crop_scope": "crop_specific",
            "crop_keys": [
                "cai_xanh",
                "cai_cuc",
                "xa_lach",
                "rau_muong",
            ],
            "search_regions": [
                "NONE",
                "GIA_LAI_CURRENT",
            ],
        },
        {
            "template": "trời nắng nóng có nên bón phân cho {crop} không",
            "scenario": "hot_weather",
            "action": "fertilization",
            "crop_scope": "crop_group",
            "crop_keys": [
                "leafy_vegetable",
                "herb_vegetable",
            ],
            "search_regions": [
                "NONE",
                "VIETNAM",
            ],
        },
    ],

    "spraying_weather": [
        {
            "template": "sắp mưa có nên phun thuốc cho {crop} không",
            "scenario": "heavy_rain",
            "action": "spray_window",
            "crop_scope": "crop_group",
            "crop_keys": [
                "general_vegetable",
                "leafy_vegetable",
            ],
            "search_regions": [
                "NONE",
                "VIETNAM",
            ],
        },
        {
            "template": "phun thuốc xong gặp mưa có cần phun lại cho {crop} không",
            "scenario": "post_rain",
            "action": "spray_window",
            "crop_scope": "crop_specific",
            "crop_keys": [
                "cai_xanh",
                "cai_cuc",
                "xa_lach",
            ],
            "search_regions": [
                "NONE",
                "BINH_DINH_LEGACY",
            ],
        },
        {
            "template": "sau mưa bao lâu thì phun thuốc cho {crop}",
            "scenario": "post_rain",
            "action": "spray_window",
            "crop_scope": "crop_group",
            "crop_keys": [
                "general_vegetable",
                "short_cycle_vegetable",
            ],
            "search_regions": [
                "NONE",
                "GIA_LAI_CURRENT",
            ],
        },
        {
            "template": "trời gió có phun thuốc cho {crop} được không",
            "scenario": "strong_wind",
            "action": "spray_window",
            "crop_scope": "crop_group",
            "crop_keys": [
                "general_vegetable",
                "leafy_vegetable",
            ],
            "search_regions": [
                "NONE",
                "VIETNAM",
            ],
        },
        {
            "template": "trời ẩm có nên phun thuốc phòng bệnh cho {crop} không",
            "scenario": "high_humidity",
            "action": "spray_window",
            "crop_scope": "crop_specific",
            "crop_keys": [
                "cai_xanh",
                "cai_cuc",
                "xa_lach",
                "ngo",
            ],
            "search_regions": [
                "NONE",
            ],
        },
    ],

    "planting_weather": [
        {
            "template": "tháng này trồng {crop} có phù hợp không",
            "scenario": "weather_change",
            "action": "planting",
            "crop_scope": "crop_specific",
            "crop_keys": specific_crop_keys(),
            "search_regions": [
                "NONE",
                "VIETNAM",
            ],
        },
        {
            "template": "mưa nhiều có nên xuống giống {crop} không",
            "scenario": "prolonged_rain",
            "action": "planting",
            "crop_scope": "crop_group",
            "crop_keys": [
                "general_vegetable",
                "short_cycle_vegetable",
            ],
            "search_regions": [
                "NONE",
                "BINH_DINH_LEGACY",
            ],
        },
        {
            "template": "trời nóng quá có nên trồng {crop} không",
            "scenario": "hot_weather",
            "action": "planting",
            "crop_scope": "crop_specific",
            "crop_keys": [
                "xa_lach",
                "cai_xanh",
                "cai_cuc",
                "ngo",
            ],
            "search_regions": [
                "NONE",
                "GIA_LAI_CURRENT",
            ],
        },
        {
            "template": "mùa mưa nên trồng {crop} thế nào",
            "scenario": "rainy_season",
            "action": "planting",
            "crop_scope": "crop_group",
            "crop_keys": [
                "leafy_vegetable",
                "herb_vegetable",
            ],
            "search_regions": [
                "NONE",
                "VIETNAM",
            ],
        },
        {
            "template": "trời lạnh gieo {crop} có được không",
            "scenario": "cold_weather",
            "action": "planting",
            "crop_scope": "crop_specific",
            "crop_keys": [
                "cai_xanh",
                "cai_cuc",
                "xa_lach",
                "ngo",
            ],
            "search_regions": [
                "NONE",
            ],
        },
    ],

    "weather_recovery": [
        {
            "template": "{crop} bị ngập nước phải xử lý sao",
            "scenario": "waterlogging",
            "action": "drainage",
            "crop_scope": "crop_specific",
            "crop_keys": [
                "cai_xanh",
                "cai_cuc",
                "xa_lach",
                "rau_muong",
            ],
            "search_regions": [
                "NONE",
                "VIETNAM",
            ],
        },
        {
            "template": "{crop} bị héo sau nắng nóng phải làm gì",
            "scenario": "hot_weather",
            "action": "irrigation",
            "crop_scope": "crop_specific",
            "crop_keys": specific_crop_keys(),
            "search_regions": [
                "NONE",
                "GIA_LAI_CURRENT",
            ],
        },
        {
            "template": "sau mưa lớn cần làm gì cho {crop}",
            "scenario": "heavy_rain",
            "action": "post_rain_care",
            "crop_scope": "crop_group",
            "crop_keys": [
                "general_vegetable",
                "short_cycle_vegetable",
            ],
            "search_regions": [
                "NONE",
                "BINH_DINH_LEGACY",
            ],
        },
        {
            "template": "{crop} bị đổ do gió có cứu được không",
            "scenario": "strong_wind",
            "action": "crop_protection",
            "crop_scope": "crop_group",
            "crop_keys": [
                "general_vegetable",
                "leafy_vegetable",
            ],
            "search_regions": [
                "NONE",
                "VIETNAM",
            ],
        },
        {
            "template": "thời tiết thay đổi đột ngột chăm {crop} thế nào",
            "scenario": "weather_change",
            "action": "field_inspection",
            "crop_scope": "crop_specific",
            "crop_keys": specific_crop_keys(),
            "search_regions": [
                "NONE",
            ],
        },
    ],
}


# ============================================================
# AGRICULTURAL ACTIONS
# ============================================================

ACTIONS = {
    "cultivation": {
        "vi": "chăm sóc",
        "en": "crop management",
    },
    "irrigation": {
        "vi": "tưới nước",
        "en": "irrigation",
    },
    "drainage": {
        "vi": "thoát nước",
        "en": "drainage",
    },
    "fertilization": {
        "vi": "bón phân",
        "en": "fertilization",
    },
    "disease_management": {
        "vi": "sâu bệnh",
        "en": "disease management",
    },
    "disease_monitoring": {
        "vi": "theo dõi bệnh",
        "en": "disease monitoring",
    },
    "shade": {
        "vi": "che nắng",
        "en": "shade management",
    },
    "crop_protection": {
        "vi": "bảo vệ cây",
        "en": "crop protection",
    },
    "mulching": {
        "vi": "phủ đất giữ ẩm",
        "en": "mulching",
    },
    "soil_moisture_management": {
        "vi": "quản lý độ ẩm đất",
        "en": "soil moisture management",
    },
    "field_inspection": {
        "vi": "kiểm tra cây",
        "en": "field inspection",
    },
    "post_rain_care": {
        "vi": "chăm sóc sau mưa",
        "en": "post rain care",
    },
    "spray_window": {
        "vi": "thời điểm phun",
        "en": "spray timing",
    },
    "planting": {
        "vi": "gieo trồng",
        "en": "planting",
    },
}


# ============================================================
# WEATHER / AGRO-WEATHER TAXONOMY
#
# Đây chỉ dùng cho DATA DISCOVERY.
# Không phải threshold của Decision Engine.
# ============================================================

SCENARIOS = {
    "heavy_rain": {
        "factor": "rainfall",
        "vi": "mưa lớn",
        "en": "heavy rainfall",
        "effects": [
            "excess_water",
            "nutrient_loss",
            "physical_damage",
            "disease_risk",
        ],
        "actions": [
            "irrigation",
            "drainage",
            "fertilization",
            "disease_management",
            "crop_protection",
            "spray_window",
        ],
    },

    "prolonged_rain": {
        "factor": "rainfall",
        "vi": "mưa kéo dài",
        "en": "prolonged rainfall",
        "effects": [
            "waterlogging",
            "root_stress",
            "nutrient_loss",
            "disease_risk",
        ],
        "actions": [
            "irrigation",
            "drainage",
            "fertilization",
            "disease_management",
            "disease_monitoring",
            "post_rain_care",
        ],
    },

    "rainy_season": {
        "factor": "rainfall",
        "vi": "mùa mưa",
        "en": "rainy season",
        "effects": [
            "excess_water",
            "disease_risk",
        ],
        "actions": [
            "cultivation",
            "drainage",
            "fertilization",
            "disease_management",
            "crop_protection",
        ],
    },

    "post_rain": {
        "factor": "rainfall",
        "vi": "sau mưa",
        "en": "after heavy rain",
        "effects": [
            "wet_soil",
            "nutrient_loss",
            "root_stress",
            "disease_risk",
        ],
        "actions": [
            "irrigation",
            "drainage",
            "fertilization",
            "field_inspection",
            "disease_monitoring",
            "post_rain_care",
        ],
    },

    "hot_weather": {
        "factor": "temperature",
        "vi": "nắng nóng",
        "en": "heat stress",
        "effects": [
            "heat_stress",
            "water_loss",
            "wilting",
            "leaf_damage",
        ],
        "actions": [
            "irrigation",
            "shade",
            "mulching",
            "fertilization",
            "crop_protection",
            "field_inspection",
        ],
    },

    "strong_sun": {
        "factor": "solar_radiation",
        "vi": "nắng gắt",
        "en": "intense sunlight",
        "effects": [
            "leaf_heat",
            "water_loss",
            "leaf_damage",
        ],
        "actions": [
            "irrigation",
            "shade",
            "mulching",
            "crop_protection",
        ],
    },

    "dry_spell": {
        "factor": "rainfall",
        "vi": "nhiều ngày không mưa",
        "en": "dry spell",
        "effects": [
            "soil_dryness",
            "water_stress",
            "wilting",
        ],
        "actions": [
            "irrigation",
            "mulching",
            "soil_moisture_management",
            "field_inspection",
        ],
    },

    "high_humidity": {
        "factor": "relative_humidity",
        "vi": "độ ẩm cao",
        "en": "high humidity",
        "effects": [
            "leaf_wetness",
            "disease_risk",
        ],
        "actions": [
            "disease_management",
            "disease_monitoring",
            "field_inspection",
            "spray_window",
        ],
    },

    "leaf_wetness": {
        "factor": "leaf_wetness",
        "vi": "lá ướt lâu",
        "en": "prolonged leaf wetness",
        "effects": [
            "leaf_wetness",
            "disease_risk",
        ],
        "actions": [
            "disease_management",
            "disease_monitoring",
            "field_inspection",
        ],
    },

    "cold_weather": {
        "factor": "temperature",
        "vi": "trời lạnh",
        "en": "cold weather",
        "effects": [
            "cold_stress",
            "slow_growth",
        ],
        "actions": [
            "irrigation",
            "crop_protection",
            "planting",
            "field_inspection",
        ],
    },

    "strong_wind": {
        "factor": "wind",
        "vi": "gió mạnh",
        "en": "strong wind",
        "effects": [
            "physical_damage",
            "water_loss",
        ],
        "actions": [
            "irrigation",
            "crop_protection",
            "field_inspection",
            "spray_window",
        ],
    },

    "hot_dry_wind": {
        "factor": "wind",
        "vi": "gió nóng khô",
        "en": "hot dry wind",
        "effects": [
            "water_loss",
            "plant_stress",
            "flower_damage",
        ],
        "actions": [
            "irrigation",
            "crop_protection",
            "field_inspection",
        ],
    },

    "waterlogging": {
        "factor": "soil_water",
        "vi": "ngập úng",
        "en": "waterlogging",
        "effects": [
            "root_stress",
            "root_rot_risk",
            "oxygen_stress",
        ],
        "actions": [
            "irrigation",
            "drainage",
            "fertilization",
            "disease_management",
            "field_inspection",
        ],
    },

    "wet_soil": {
        "factor": "soil_water",
        "vi": "đất quá ướt",
        "en": "excess soil moisture",
        "effects": [
            "excess_water",
            "root_stress",
            "disease_risk",
        ],
        "actions": [
            "irrigation",
            "drainage",
            "fertilization",
            "disease_monitoring",
        ],
    },

    "weather_change": {
        "factor": "weather_transition",
        "vi": "thời tiết thay đổi đột ngột",
        "en": "sudden weather change",
        "effects": [
            "plant_stress",
            "disease_risk",
        ],
        "actions": [
            "irrigation",
            "crop_protection",
            "disease_monitoring",
            "field_inspection",
        ],
    },
}

A2_COMPATIBLE_ACTIONS = {
    scenario_id:
        set(scenario["actions"])
    for scenario_id, scenario
    in SCENARIOS.items()
}

A2_COMPATIBLE_ACTIONS["prolonged_rain"].add(
    "planting"
)
A2_COMPATIBLE_ACTIONS["prolonged_rain"].add(
    "field_inspection"
)
A2_COMPATIBLE_ACTIONS["rainy_season"].add(
    "planting"
)
A2_COMPATIBLE_ACTIONS["hot_weather"].add(
    "planting"
)
A2_COMPATIBLE_ACTIONS["weather_change"].add(
    "planting"
)
A2_COMPATIBLE_ACTIONS["heavy_rain"].add(
    "post_rain_care"
)
A2_COMPATIBLE_ACTIONS["post_rain"].add(
    "spray_window"
)


# ============================================================
# CONFIG
# ============================================================

def load_config():
    with CROP_CONFIG.open(
        "r",
        encoding="utf-8",
    ) as file:
        config = yaml.safe_load(file)

    if not config.get("crops"):
        raise ValueError(
            "config/crops.yaml contains no crops."
        )

    return config


# ============================================================
# QUERY HELPERS
# ============================================================

def configure_stdout():

    if hasattr(
        sys.stdout,
        "reconfigure",
    ):
        sys.stdout.reconfigure(
            encoding="utf-8",
        )


def normalize(text):
    return " ".join(
        text.casefold().split()
    )


def stable_id(text):
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()[:12].upper()


def build_vi_query(
    crop_term,
    weather_term,
    extra_term,
    region,
):
    query = (
        f'"{crop_term}" '
        f'"{weather_term}" '
        f'{extra_term}'
    )

    if region:
        query += f" {region}"

    return query.strip()


def build_en_query(
    crop_term,
    weather_term,
    extra_term,
    region,
):
    parts = [
        crop_term,
        weather_term,
        extra_term,
    ]

    if region:
        parts.append(region)

    return " ".join(parts)


def normalize_public_query(text):
    punctuation = "\"'“”‘’.,;:!?()[]{}"
    translated = "".join(
        " "
        if character in punctuation
        else character
        for character in text
    )

    return normalize(translated)


def a2_region_phrase(search_region):
    return A2_SEARCH_REGIONS[
        search_region
    ]


def build_a2_query(
    template,
    crop_term,
    search_region,
):
    query = template.format(
        crop=crop_term
    )

    region_phrase = a2_region_phrase(
        search_region
    )

    if region_phrase:
        query = f"{query} {region_phrase}"

    return query.strip()


def config_crop_maps(config):
    crops = {
        crop["id"]:
            crop
        for crop in config.get(
            "crops",
            [],
        )
    }

    crop_groups = config.get(
        "crop_groups",
        {},
    )

    return crops, crop_groups


def a2_crop_term(
    config,
    crop_scope,
    crop_key,
):
    crops, crop_groups = config_crop_maps(
        config
    )

    if crop_scope == "crop_specific":
        return crops[crop_key]["aliases_vi"][0]

    if crop_scope == "crop_group":
        return crop_groups[crop_key]["aliases_vi"][0]

    raise ValueError(
        f"Unknown crop_scope: {crop_scope}"
    )


def add_a2_query(
    rows,
    seen,
    *,
    query_text,
    query_origin,
    intent,
    scenario,
    action,
    crop_scope,
    crop_key,
    search_region,
    source_url="",
    source_title="",
    parent_query_id="",
):
    normalized = normalize_public_query(
        query_text
    )

    if normalized in seen:
        return

    seen.add(normalized)

    rows.append({
        "query_id":
            f"A2Q-{stable_id(A2_STAGE + '|' + normalized)}",

        "query_text":
            query_text,

        "language":
            "vi",

        "stage":
            A2_STAGE,

        "query_origin":
            query_origin,

        "intent":
            intent,

        "scenario":
            scenario,

        "action":
            action,

        "crop_scope":
            crop_scope,

        "crop_key":
            crop_key,

        "search_region":
            search_region,

        "search_region_term":
            a2_region_phrase(
                search_region
            ),

        "source_url":
            source_url,

        "source_title":
            source_title,

        "parent_query_id":
            parent_query_id,
    })


def add_query(
    rows,
    seen,
    *,
    language,
    channel,
    scope_type,
    crop_id,
    crop_name,
    crop_group,
    crop_term,
    scenario_id,
    query_kind,
    action,
    search_region,
    search_region_term,
    priority,
    query,
):
    normalized = normalize(query)

    if normalized in seen:
        return

    seen.add(normalized)

    scenario = SCENARIOS[scenario_id]

    rows.append({
        "query_id":
            f"DQ-{stable_id(normalized)}",

        "search_round":
            1,

        "language":
            language,

        "channel":
            channel,

        "priority":
            priority,

        "query_kind":
            query_kind,

        "scope_type":
            scope_type,

        "crop_id":
            crop_id or "",

        "crop_name":
            crop_name or "",

        "crop_group":
            crop_group or "",

        "crop_term":
            crop_term,

        "weather_scenario":
            scenario_id,

        "weather_factor":
            scenario["factor"],

        "weather_term":
            (
                scenario["vi"]
                if language == "vi"
                else scenario["en"]
            ),

        "effects":
            "|".join(
                scenario["effects"]
            ),

        "action":
            action or NO_ACTION,

        "search_region":
            search_region,

        "search_region_term":
            search_region_term,

        "query":
            query,
    })


# ============================================================
# GENERATION
# ============================================================

def generate_crop_queries(
    config,
    rows,
    seen,
):
    for crop in config["crops"]:

        crop_id = crop["id"]
        crop_name = crop["name_vi"]

        # Round 1 intentionally uses one canonical Vietnamese term.
        vi_crop = crop["aliases_vi"][0]

        # Scientific name gives good scholarly precision.
        en_crop = crop["scientific_name"]

        for scenario_id, scenario in SCENARIOS.items():

            # ------------------------------------------------
            # Vietnamese effect discovery
            # ------------------------------------------------

            for region in VI_SEARCH_REGIONS:

                query = build_vi_query(
                    vi_crop,
                    scenario["vi"],
                    "ảnh hưởng chăm sóc",
                    region["text"],
                )

                add_query(
                    rows,
                    seen,
                    language="vi",
                    channel="web",
                    scope_type="crop_specific",
                    crop_id=crop_id,
                    crop_name=crop_name,
                    crop_group="",
                    crop_term=vi_crop,
                    scenario_id=scenario_id,
                    query_kind="effect",
                    action="",
                    search_region=region["id"],
                    search_region_term=region["text"],
                    priority=region["priority"],
                    query=query,
                )

            # ------------------------------------------------
            # Vietnamese action discovery
            # ------------------------------------------------

            for action_id in scenario["actions"]:

                action_term = ACTIONS[action_id]["vi"]

                for region in VI_SEARCH_REGIONS:

                    query = build_vi_query(
                        vi_crop,
                        scenario["vi"],
                        action_term,
                        region["text"],
                    )

                    add_query(
                        rows,
                        seen,
                        language="vi",
                        channel="web",
                        scope_type="crop_specific",
                        crop_id=crop_id,
                        crop_name=crop_name,
                        crop_group="",
                        crop_term=vi_crop,
                        scenario_id=scenario_id,
                        query_kind="action",
                        action=action_id,
                        search_region=region["id"],
                        search_region_term=region["text"],
                        priority=region["priority"],
                        query=query,
                    )

            # ------------------------------------------------
            # English scholarly effect discovery
            # ------------------------------------------------

            for region in EN_SEARCH_REGIONS:

                query = build_en_query(
                    en_crop,
                    scenario["en"],
                    "agronomic effects management",
                    region["text"],
                )

                add_query(
                    rows,
                    seen,
                    language="en",
                    channel="scholarly",
                    scope_type="crop_specific",
                    crop_id=crop_id,
                    crop_name=crop_name,
                    crop_group="",
                    crop_term=en_crop,
                    scenario_id=scenario_id,
                    query_kind="effect",
                    action="",
                    search_region=region["id"],
                    search_region_term=region["text"],
                    priority=region["priority"],
                    query=query,
                )

            # ------------------------------------------------
            # English scholarly action discovery
            # ------------------------------------------------

            for action_id in scenario["actions"]:

                action_term = ACTIONS[action_id]["en"]

                for region in EN_SEARCH_REGIONS:

                    query = build_en_query(
                        en_crop,
                        scenario["en"],
                        action_term,
                        region["text"],
                    )

                    add_query(
                        rows,
                        seen,
                        language="en",
                        channel="scholarly",
                        scope_type="crop_specific",
                        crop_id=crop_id,
                        crop_name=crop_name,
                        crop_group="",
                        crop_term=en_crop,
                        scenario_id=scenario_id,
                        query_kind="action",
                        action=action_id,
                        search_region=region["id"],
                        search_region_term=region["text"],
                        priority=region["priority"],
                        query=query,
                    )


def generate_group_queries(
    config,
    rows,
    seen,
):
    groups = config.get(
        "crop_groups",
        {},
    )

    # Group fallback does not need local query explosion.
    group_vi_regions = [
        VI_SEARCH_REGIONS[0],  # NONE
        VI_SEARCH_REGIONS[1],  # VIETNAM
    ]

    for group_id, group in groups.items():

        vi_crop = group["aliases_vi"][0]
        en_crop = group["aliases_en"][0]

        for scenario_id, scenario in SCENARIOS.items():

            # Generic effect query.
            for region in group_vi_regions:

                query = build_vi_query(
                    vi_crop,
                    scenario["vi"],
                    "ảnh hưởng chăm sóc",
                    region["text"],
                )

                add_query(
                    rows,
                    seen,
                    language="vi",
                    channel="web",
                    scope_type="crop_group",
                    crop_id="",
                    crop_name="",
                    crop_group=group_id,
                    crop_term=vi_crop,
                    scenario_id=scenario_id,
                    query_kind="effect",
                    action="",
                    search_region=region["id"],
                    search_region_term=region["text"],
                    priority=2,
                    query=query,
                )

            for action_id in scenario["actions"]:

                action_term = ACTIONS[action_id]["vi"]

                for region in group_vi_regions:

                    query = build_vi_query(
                        vi_crop,
                        scenario["vi"],
                        action_term,
                        region["text"],
                    )

                    add_query(
                        rows,
                        seen,
                        language="vi",
                        channel="web",
                        scope_type="crop_group",
                        crop_id="",
                        crop_name="",
                        crop_group=group_id,
                        crop_term=vi_crop,
                        scenario_id=scenario_id,
                        query_kind="action",
                        action=action_id,
                        search_region=region["id"],
                        search_region_term=region["text"],
                        priority=2,
                        query=query,
                    )

            # English group fallback: GLOBAL only.
            global_region = EN_SEARCH_REGIONS[0]

            query = build_en_query(
                en_crop,
                scenario["en"],
                "agronomic effects management",
                "",
            )

            add_query(
                rows,
                seen,
                language="en",
                channel="scholarly",
                scope_type="crop_group",
                crop_id="",
                crop_name="",
                crop_group=group_id,
                crop_term=en_crop,
                scenario_id=scenario_id,
                query_kind="effect",
                action="",
                search_region="GLOBAL",
                search_region_term="",
                priority=3,
                query=query,
            )

            for action_id in scenario["actions"]:

                query = build_en_query(
                    en_crop,
                    scenario["en"],
                    ACTIONS[action_id]["en"],
                    "",
                )

                add_query(
                    rows,
                    seen,
                    language="en",
                    channel="scholarly",
                    scope_type="crop_group",
                    crop_id="",
                    crop_name="",
                    crop_group=group_id,
                    crop_term=en_crop,
                    scenario_id=scenario_id,
                    query_kind="action",
                    action=action_id,
                    search_region="GLOBAL",
                    search_region_term="",
                    priority=3,
                    query=query,
                )


# ============================================================
# A2 PUBLIC / FARMER-STYLE QUERY MINING
# ============================================================

def generate_observed_a2_queries(
    rows,
    seen,
):
    for seed in OBSERVED_PUBLIC_QUERY_SEEDS:
        add_a2_query(
            rows,
            seen,
            query_text=seed["query_text"],
            query_origin="observed",
            intent=seed["intent"],
            scenario=seed["scenario"],
            action=seed.get(
                "action",
                NO_ACTION,
            ),
            crop_scope=seed["crop_scope"],
            crop_key=seed["crop_key"],
            search_region=seed.get(
                "search_region",
                "NONE",
            ),
            source_url=seed.get(
                "source_url",
                "",
            ),
            source_title=seed.get(
                "source_title",
                "",
            ),
            parent_query_id="",
        )


def generate_transformed_a2_queries(
    rows,
    seen,
):
    parent_rows = {
        row["query_id"]:
            row
        for row in rows
    }

    for seed in TRANSFORMED_PUBLIC_QUERY_SEEDS:
        parent_query_id = seed.get(
            "parent_query_id",
            "",
        )
        parent = parent_rows.get(
            parent_query_id,
            {},
        )

        add_a2_query(
            rows,
            seen,
            query_text=seed["query_text"],
            query_origin="transformed",
            intent=seed["intent"],
            scenario=seed["scenario"],
            action=seed.get(
                "action",
                NO_ACTION,
            ),
            crop_scope=seed["crop_scope"],
            crop_key=seed["crop_key"],
            search_region=seed.get(
                "search_region",
                "NONE",
            ),
            source_url=(
                seed.get(
                    "source_url",
                    "",
                )
                or
                parent.get(
                    "source_url",
                    "",
                )
            ),
            source_title=(
                seed.get(
                    "source_title",
                    "",
                )
                or
                parent.get(
                    "source_title",
                    "",
                )
            ),
            parent_query_id=parent_query_id,
        )


def generate_synthetic_a2_queries(
    config,
    rows,
    seen,
):
    for intent, patterns in (
        PUBLIC_INTENT_PATTERNS.items()
    ):

        for pattern in patterns:
            crop_scope = pattern[
                "crop_scope"
            ]

            for crop_key in pattern[
                "crop_keys"
            ]:
                crop_term = a2_crop_term(
                    config,
                    crop_scope,
                    crop_key,
                )

                for search_region in pattern[
                    "search_regions"
                ]:
                    query_text = build_a2_query(
                        pattern["template"],
                        crop_term,
                        search_region,
                    )

                    add_a2_query(
                        rows,
                        seen,
                        query_text=query_text,
                        query_origin="synthetic",
                        intent=intent,
                        scenario=pattern[
                            "scenario"
                        ],
                        action=pattern.get(
                            "action",
                            NO_ACTION,
                        ),
                        crop_scope=crop_scope,
                        crop_key=crop_key,
                        search_region=search_region,
                    )


def generate_a2_queries(config):
    rows = []
    seen = set()

    generate_observed_a2_queries(
        rows,
        seen,
    )

    generate_transformed_a2_queries(
        rows,
        seen,
    )

    generate_synthetic_a2_queries(
        config,
        rows,
        seen,
    )

    rows.sort(
        key=lambda row: (
            row["query_origin"],
            row["intent"],
            row["crop_scope"],
            row["crop_key"],
            row["scenario"],
            row["action"],
            row["search_region"],
            row["query_text"],
        )
    )

    return rows


# ============================================================
# AUDIT
# ============================================================

def audit(
    rows,
    config,
):
    issues = []

    ids = set()
    queries = set()

    crop_scenarios = defaultdict(set)
    config_crops = config.get(
        "crops",
        [],
    )
    config_crop_ids = {
        crop.get("id")
        for crop in config_crops
    }
    config_crop_names = {
        crop.get("id"):
            crop.get("name_vi", "")
        for crop in config_crops
    }
    config_crop_groups = set(
        config.get(
            "crop_groups",
            {},
        )
    )
    valid_search_regions = {
        language: {
            region["id"]:
                region["text"]
            for region in regions
        }
        for language, regions
        in ROUND_1_SEARCH_REGIONS.items()
    }

    missing_target_crops = (
        TARGET_CROP_IDS
        -
        config_crop_ids
    )

    if missing_target_crops:
        issues.append({
            "type":
                "MISSING_TARGET_CROPS",

            "missing":
                sorted(missing_target_crops),
        })

    for scenario_id, scenario in SCENARIOS.items():

        for key in [
            "factor",
            "vi",
            "en",
            "effects",
            "actions",
        ]:

            if key not in scenario:
                issues.append({
                    "type":
                        "INVALID_SCENARIO",

                    "weather_scenario":
                        scenario_id,

                    "missing_field":
                        key,
                })

        for action_id in scenario.get(
            "actions",
            [],
        ):

            if action_id not in ACTIONS:
                issues.append({
                    "type":
                        "UNKNOWN_SCENARIO_ACTION",

                    "weather_scenario":
                        scenario_id,

                    "action":
                        action_id,
                })

    for row in rows:

        for field in REQUIRED_FIELDS:

            if field not in row:
                issues.append({
                    "type":
                        "MISSING_FIELD",

                    "field":
                        field,

                    "row":
                        row,
                })

        query_id = row.get(
            "query_id",
            "",
        )

        if not query_id:
            issues.append({
                "type":
                    "EMPTY_QUERY_ID",

                "row":
                    row,
            })

        elif query_id in ids:
            issues.append({
                "type": "DUPLICATE_QUERY_ID",
                "query_id": query_id,
            })

        ids.add(
            query_id
        )

        normalized = normalize(
            row.get(
                "query",
                "",
            )
        )

        if not normalized:
            issues.append({
                "type":
                    "EMPTY_QUERY",

                "query_id":
                    query_id,
            })

        elif normalized in queries:
            issues.append({
                "type": "DUPLICATE_QUERY",
                "query": row.get("query", ""),
            })

        queries.add(normalized)

        language = row.get("language")
        channel = row.get("channel")
        query_kind = row.get("query_kind")
        scope_type = row.get("scope_type")
        crop_id = row.get("crop_id", "")
        crop_group = row.get("crop_group", "")
        scenario_id = row.get("weather_scenario")
        action_id = row.get("action")
        search_region = row.get("search_region")

        if row.get("search_round") != 1:
            issues.append({
                "type":
                    "INVALID_SEARCH_ROUND",

                "query_id":
                    query_id,
            })

        if language not in VALID_LANGUAGES:
            issues.append({
                "type":
                    "INVALID_LANGUAGE",

                "query_id":
                    query_id,

                "language":
                    language,
            })

        elif channel != VALID_CHANNELS[language]:
            issues.append({
                "type":
                    "INVALID_CHANNEL",

                "query_id":
                    query_id,

                "language":
                    language,

                "channel":
                    channel,
            })

        if query_kind not in VALID_QUERY_KINDS:
            issues.append({
                "type":
                    "INVALID_QUERY_KIND",

                "query_id":
                    query_id,

                "query_kind":
                    query_kind,
            })

        if scope_type not in VALID_SCOPE_TYPES:
            issues.append({
                "type":
                    "INVALID_SCOPE_TYPE",

                "query_id":
                    query_id,

                "scope_type":
                    scope_type,
            })

        elif scope_type == "crop_specific":

            if crop_id not in config_crop_ids:
                issues.append({
                    "type":
                        "INVALID_CROP_ID",

                    "query_id":
                        query_id,

                    "crop_id":
                        crop_id,
                })

            if not row.get("crop_name"):
                issues.append({
                    "type":
                        "MISSING_CROP_NAME",

                    "query_id":
                        query_id,
                })

            elif (
                crop_id in config_crop_names
                and
                row["crop_name"] != config_crop_names[crop_id]
            ):
                issues.append({
                    "type":
                        "CROP_NAME_MISMATCH",

                    "query_id":
                        query_id,

                    "crop_id":
                        crop_id,
                })

            if crop_group:
                issues.append({
                    "type":
                        "UNEXPECTED_CROP_GROUP",

                    "query_id":
                        query_id,
                })

        elif scope_type == "crop_group":

            if crop_id or row.get("crop_name"):
                issues.append({
                    "type":
                        "UNEXPECTED_CROP_FIELDS",

                    "query_id":
                        query_id,
                })

            if crop_group not in config_crop_groups:
                issues.append({
                    "type":
                        "INVALID_CROP_GROUP",

                    "query_id":
                        query_id,

                    "crop_group":
                        crop_group,
                })

        if not row.get("crop_term"):
            issues.append({
                "type":
                    "EMPTY_CROP_TERM",

                "query_id":
                    query_id,
            })

        if scenario_id not in SCENARIOS:
            issues.append({
                "type":
                    "INVALID_WEATHER_SCENARIO",

                "query_id":
                    query_id,

                "weather_scenario":
                    scenario_id,
            })

        else:
            scenario = SCENARIOS[scenario_id]
            expected_weather_term = (
                scenario["vi"]
                if language == "vi"
                else scenario["en"]
            )

            if row.get("weather_factor") != scenario["factor"]:
                issues.append({
                    "type":
                        "WEATHER_FACTOR_MISMATCH",

                    "query_id":
                        query_id,
                })

            if row.get("weather_term") != expected_weather_term:
                issues.append({
                    "type":
                        "WEATHER_TERM_MISMATCH",

                    "query_id":
                        query_id,
                })

            if row.get("effects") != "|".join(scenario["effects"]):
                issues.append({
                    "type":
                        "EFFECTS_MISMATCH",

                    "query_id":
                        query_id,
                })

        if query_kind == "effect":

            if action_id != NO_ACTION:
                issues.append({
                    "type":
                        "EFFECT_QUERY_HAS_ACTION",

                    "query_id":
                        query_id,

                    "action":
                        action_id,
                })

        elif query_kind == "action":

            if action_id not in ACTIONS:
                issues.append({
                    "type":
                        "INVALID_ROW_ACTION",

                    "query_id":
                        query_id,

                    "action":
                        action_id,
                })

        if language in valid_search_regions:
            expected_term = valid_search_regions[
                language
            ].get(
                search_region
            )

            if expected_term is None:
                issues.append({
                    "type":
                        "INVALID_SEARCH_REGION",

                    "query_id":
                        query_id,

                    "language":
                        language,

                    "search_region":
                        search_region,
                })

            elif row.get("search_region_term", "") != expected_term:
                issues.append({
                    "type":
                        "SEARCH_REGION_TERM_MISMATCH",

                    "query_id":
                        query_id,

                    "search_region":
                        search_region,
                })

        if crop_id:
            crop_scenarios[
                crop_id
            ].add(
                scenario_id
            )

    expected = set(
        SCENARIOS.keys()
    )

    for crop in config_crops:

        missing = (
            expected
            -
            crop_scenarios[
                crop["id"]
            ]
        )

        if missing:
            issues.append({
                "type":
                    "MISSING_WEATHER_SCENARIO",

                "crop_id":
                    crop["id"],

                "missing":
                    sorted(missing),
            })

    return issues


def audit_a2(
    rows,
    config,
):
    issues = []
    ids = set()
    normalized_queries = set()

    crops, crop_groups = config_crop_maps(
        config
    )

    for row in rows:

        for field in A2_REQUIRED_FIELDS:

            if field not in row:
                issues.append({
                    "type":
                        "A2_MISSING_FIELD",

                    "field":
                        field,

                    "row":
                        row,
                })

        query_id = row.get(
            "query_id",
            "",
        )
        query_text = row.get(
            "query_text",
            "",
        )
        normalized = normalize_public_query(
            query_text
        )

        if not query_id:
            issues.append({
                "type":
                    "A2_EMPTY_QUERY_ID",

                "row":
                    row,
            })

        elif query_id in ids:
            issues.append({
                "type":
                    "A2_DUPLICATE_QUERY_ID",

                "query_id":
                    query_id,
            })

        ids.add(query_id)

        if not normalized:
            issues.append({
                "type":
                    "A2_EMPTY_QUERY_TEXT",

                "query_id":
                    query_id,
            })

        elif normalized in normalized_queries:
            issues.append({
                "type":
                    "A2_DUPLICATE_NORMALIZED_QUERY",

                "query_id":
                    query_id,

                "query_text":
                    query_text,
            })

        normalized_queries.add(normalized)

    all_ids = {
        row.get("query_id")
        for row in rows
    }

    for row in rows:
        query_id = row.get(
            "query_id",
            "",
        )
        origin = row.get(
            "query_origin",
            "",
        )
        stage = row.get(
            "stage",
            "",
        )
        intent = row.get(
            "intent",
            "",
        )
        scenario = row.get(
            "scenario",
            "",
        )
        action = row.get(
            "action",
            NO_ACTION,
        )
        crop_scope = row.get(
            "crop_scope",
            "",
        )
        crop_key = row.get(
            "crop_key",
            "",
        )
        search_region = row.get(
            "search_region",
            "",
        )
        source_url = row.get(
            "source_url",
            "",
        )
        source_title = row.get(
            "source_title",
            "",
        )
        parent_query_id = row.get(
            "parent_query_id",
            "",
        )

        if stage != A2_STAGE:
            issues.append({
                "type":
                    "A2_MALFORMED_STAGE",

                "query_id":
                    query_id,

                "stage":
                    stage,
            })

        if row.get("language") != "vi":
            issues.append({
                "type":
                    "A2_INVALID_LANGUAGE",

                "query_id":
                    query_id,

                "language":
                    row.get("language"),
            })

        if origin not in A2_QUERY_ORIGINS:
            issues.append({
                "type":
                    "A2_INVALID_QUERY_ORIGIN",

                "query_id":
                    query_id,

                "query_origin":
                    origin,
            })

        if intent not in A2_INTENTS:
            issues.append({
                "type":
                    "A2_INVALID_INTENT",

                "query_id":
                    query_id,

                "intent":
                    intent,
            })

        if origin == "observed" and not source_url:
            issues.append({
                "type":
                    "A2_OBSERVED_WITHOUT_SOURCE_URL",

                "query_id":
                    query_id,
            })

        if origin == "transformed":

            if not parent_query_id:
                issues.append({
                    "type":
                        "A2_TRANSFORMED_WITHOUT_PARENT_QUERY_ID",

                    "query_id":
                        query_id,
                })

            elif parent_query_id not in all_ids:
                issues.append({
                    "type":
                        "A2_TRANSFORMED_PARENT_NOT_FOUND",

                    "query_id":
                        query_id,

                    "parent_query_id":
                        parent_query_id,
                })

        if origin == "synthetic" and (
            source_url
            or
            source_title
            or
            parent_query_id
        ):
            issues.append({
                "type":
                    "A2_SYNTHETIC_HAS_FAKE_PROVENANCE",

                "query_id":
                    query_id,
            })

        if crop_scope == "crop_specific":

            if crop_key not in crops:
                issues.append({
                    "type":
                        "A2_UNKNOWN_CROP_KEY",

                    "query_id":
                        query_id,

                    "crop_key":
                        crop_key,
                })

        elif crop_scope == "crop_group":

            if crop_key not in crop_groups:
                issues.append({
                    "type":
                        "A2_UNKNOWN_CROP_GROUP_KEY",

                    "query_id":
                        query_id,

                    "crop_key":
                        crop_key,
                })

        else:
            issues.append({
                "type":
                    "A2_INVALID_CROP_SCOPE",

                "query_id":
                    query_id,

                "crop_scope":
                    crop_scope,
            })

        if search_region not in A2_SEARCH_REGIONS:
            issues.append({
                "type":
                    "A2_INVALID_SEARCH_REGION",

                "query_id":
                    query_id,

                "search_region":
                    search_region,
            })

        elif row.get(
            "search_region_term",
            "",
        ) != a2_region_phrase(search_region):
            issues.append({
                "type":
                    "A2_SEARCH_REGION_TERM_MISMATCH",

                "query_id":
                    query_id,

                "search_region":
                    search_region,
            })

        if scenario not in SCENARIOS:
            issues.append({
                "type":
                    "A2_UNKNOWN_SCENARIO",

                "query_id":
                    query_id,

                "scenario":
                    scenario,
            })

        if (
            action != NO_ACTION
            and
            action not in ACTIONS
        ):
            issues.append({
                "type":
                    "A2_UNKNOWN_ACTION",

                "query_id":
                    query_id,

                "action":
                    action,
            })

        if (
            scenario in A2_COMPATIBLE_ACTIONS
            and
            action != NO_ACTION
            and
            action not in A2_COMPATIBLE_ACTIONS[scenario]
        ):
            issues.append({
                "type":
                    "A2_INCOMPATIBLE_ACTION_SCENARIO",

                "query_id":
                    query_id,

                "scenario":
                    scenario,

                "action":
                    action,
            })

    return issues


# ============================================================
# REPORTING
# ============================================================

def count_by(
    rows,
    field,
):
    counts = Counter(
        row[field]
        for row in rows
    )

    return dict(
        sorted(
            counts.items()
        )
    )


def count_by_with_defaults(
    rows,
    field,
    keys,
):
    counts = Counter(
        row[field]
        for row in rows
    )

    return {
        key:
            counts.get(
                key,
                0,
            )
        for key in keys
    }


def print_counter(
    title,
    values,
):
    print()
    print(title)

    for key, value in values.items():
        print(
            f"  {key:<24} {value}"
        )


def row_matches(
    row,
    criteria,
):
    for key, value in criteria.items():

        if row.get(key) != value:
            return False

    return True


def representative_queries(
    rows,
    limit=20,
):
    criteria = [
        {
            "language": "vi",
            "scope_type": "crop_specific",
            "crop_id": "cai_xanh",
            "weather_scenario": "heavy_rain",
            "query_kind": "action",
            "action": "irrigation",
            "search_region": "NONE",
        },
        {
            "language": "vi",
            "scope_type": "crop_specific",
            "crop_id": "cai_xanh",
            "weather_scenario": "heavy_rain",
            "query_kind": "action",
            "action": "irrigation",
            "search_region": "VIETNAM",
        },
        {
            "language": "vi",
            "scope_type": "crop_specific",
            "crop_id": "xa_lach",
            "weather_scenario": "hot_weather",
            "query_kind": "action",
            "action": "shade",
            "search_region": "BINH_DINH_LEGACY",
        },
        {
            "language": "vi",
            "scope_type": "crop_specific",
            "crop_id": "ngo",
            "weather_scenario": "high_humidity",
            "query_kind": "action",
            "action": "disease_management",
            "search_region": "GIA_LAI_CURRENT",
        },
        {
            "language": "vi",
            "scope_type": "crop_specific",
            "crop_id": "cai_cuc",
            "weather_scenario": "prolonged_rain",
            "query_kind": "action",
            "action": "drainage",
            "search_region": "VIETNAM",
        },
        {
            "language": "vi",
            "scope_type": "crop_specific",
            "crop_id": "rau_muong",
            "weather_scenario": "wet_soil",
            "query_kind": "effect",
            "action": NO_ACTION,
            "search_region": "NONE",
        },
        {
            "language": "vi",
            "scope_type": "crop_specific",
            "crop_id": "xa_lach",
            "weather_scenario": "strong_sun",
            "query_kind": "effect",
            "action": NO_ACTION,
            "search_region": "BINH_DINH_LEGACY",
        },
        {
            "language": "vi",
            "scope_type": "crop_specific",
            "crop_id": "cai_xanh",
            "weather_scenario": "waterlogging",
            "query_kind": "action",
            "action": "drainage",
            "search_region": "GIA_LAI_CURRENT",
        },
        {
            "language": "en",
            "scope_type": "crop_specific",
            "crop_id": "xa_lach",
            "weather_scenario": "hot_weather",
            "query_kind": "action",
            "action": "irrigation",
            "search_region": "GLOBAL",
        },
        {
            "language": "en",
            "scope_type": "crop_specific",
            "crop_id": "ngo",
            "weather_scenario": "high_humidity",
            "query_kind": "action",
            "action": "disease_management",
            "search_region": "VIETNAM",
        },
        {
            "language": "en",
            "scope_type": "crop_specific",
            "crop_id": "cai_cuc",
            "weather_scenario": "prolonged_rain",
            "query_kind": "effect",
            "action": NO_ACTION,
            "search_region": "GLOBAL",
        },
        {
            "language": "en",
            "scope_type": "crop_specific",
            "crop_id": "rau_muong",
            "weather_scenario": "waterlogging",
            "query_kind": "action",
            "action": "drainage",
            "search_region": "VIETNAM",
        },
        {
            "language": "vi",
            "scope_type": "crop_group",
            "crop_group": "leafy_vegetable",
            "weather_scenario": "rainy_season",
            "query_kind": "action",
            "action": "cultivation",
            "search_region": "VIETNAM",
        },
        {
            "language": "vi",
            "scope_type": "crop_group",
            "crop_group": "herb_vegetable",
            "weather_scenario": "hot_weather",
            "query_kind": "action",
            "action": "shade",
            "search_region": "NONE",
        },
        {
            "language": "en",
            "scope_type": "crop_group",
            "crop_group": "short_cycle_vegetable",
            "weather_scenario": "heavy_rain",
            "query_kind": "effect",
            "action": NO_ACTION,
            "search_region": "GLOBAL",
        },
        {
            "language": "en",
            "scope_type": "crop_group",
            "crop_group": "general_vegetable",
            "weather_scenario": "dry_spell",
            "query_kind": "action",
            "action": "irrigation",
            "search_region": "GLOBAL",
        },
        {
            "language": "vi",
            "scope_type": "crop_specific",
            "crop_id": "xa_lach",
            "weather_scenario": "dry_spell",
            "query_kind": "action",
            "action": "soil_moisture_management",
            "search_region": "GIA_LAI_CURRENT",
        },
        {
            "language": "vi",
            "scope_type": "crop_specific",
            "crop_id": "ngo",
            "weather_scenario": "cold_weather",
            "query_kind": "action",
            "action": "planting",
            "search_region": "VIETNAM",
        },
        {
            "language": "en",
            "scope_type": "crop_specific",
            "crop_id": "cai_xanh",
            "weather_scenario": "strong_wind",
            "query_kind": "action",
            "action": "crop_protection",
            "search_region": "GLOBAL",
        },
        {
            "language": "vi",
            "scope_type": "crop_group",
            "crop_group": "general_vegetable",
            "weather_scenario": "post_rain",
            "query_kind": "action",
            "action": "post_rain_care",
            "search_region": "VIETNAM",
        },
    ]

    selected = []
    selected_ids = set()

    for item in criteria:

        for row in rows:

            if (
                row["query_id"] not in selected_ids
                and
                row_matches(row, item)
            ):
                selected.append(row)
                selected_ids.add(row["query_id"])
                break

    for row in rows:

        if len(selected) >= limit:
            break

        if row["query_id"] in selected_ids:
            continue

        selected.append(row)
        selected_ids.add(row["query_id"])

    return selected[:limit]


def representative_a2_queries(
    rows,
    limit=24,
):
    criteria = [
        {
            "intent": "irrigation_water",
            "crop_scope": "crop_group",
            "crop_key": "general_vegetable",
            "search_region": "NONE",
        },
        {
            "intent": "irrigation_water",
            "crop_scope": "crop_specific",
            "crop_key": "cai_xanh",
            "search_region": "VIETNAM",
        },
        {
            "intent": "irrigation_water",
            "crop_scope": "crop_specific",
            "crop_key": "xa_lach",
            "search_region": "BINH_DINH_LEGACY",
        },
        {
            "intent": "rain_effect",
            "crop_scope": "crop_specific",
            "crop_key": "cai_cuc",
            "search_region": "NONE",
        },
        {
            "intent": "rain_effect",
            "crop_scope": "crop_group",
            "crop_key": "short_cycle_vegetable",
            "search_region": "GIA_LAI_CURRENT",
        },
        {
            "intent": "rain_effect",
            "crop_scope": "crop_specific",
            "crop_key": "cai_xanh",
            "search_region": "VIETNAM",
        },
        {
            "intent": "heat_sunlight",
            "crop_scope": "crop_specific",
            "crop_key": "xa_lach",
            "search_region": "VIETNAM",
        },
        {
            "intent": "heat_sunlight",
            "crop_scope": "crop_group",
            "crop_key": "leafy_vegetable",
            "search_region": "BINH_DINH_LEGACY",
        },
        {
            "intent": "heat_sunlight",
            "crop_scope": "crop_specific",
            "crop_key": "cai_cuc",
            "search_region": "GIA_LAI_CURRENT",
        },
        {
            "intent": "humidity_disease",
            "crop_scope": "crop_specific",
            "crop_key": "ngo",
            "search_region": "VIETNAM",
        },
        {
            "intent": "humidity_disease",
            "crop_scope": "crop_group",
            "crop_key": "general_vegetable",
            "search_region": "GIA_LAI_CURRENT",
        },
        {
            "intent": "fertilizer_weather",
            "crop_scope": "crop_specific",
            "crop_key": "rau_muong",
            "search_region": "NONE",
        },
        {
            "intent": "fertilizer_weather",
            "crop_scope": "crop_group",
            "crop_key": "short_cycle_vegetable",
            "search_region": "BINH_DINH_LEGACY",
        },
        {
            "intent": "fertilizer_weather",
            "crop_scope": "crop_group",
            "crop_key": "leafy_vegetable",
            "search_region": "VIETNAM",
        },
        {
            "intent": "spraying_weather",
            "crop_scope": "crop_group",
            "crop_key": "general_vegetable",
            "search_region": "VIETNAM",
        },
        {
            "intent": "spraying_weather",
            "crop_scope": "crop_specific",
            "crop_key": "cai_xanh",
            "search_region": "BINH_DINH_LEGACY",
        },
        {
            "intent": "spraying_weather",
            "crop_scope": "crop_group",
            "crop_key": "leafy_vegetable",
            "search_region": "NONE",
        },
        {
            "intent": "planting_weather",
            "crop_scope": "crop_specific",
            "crop_key": "xa_lach",
            "search_region": "GIA_LAI_CURRENT",
        },
        {
            "intent": "planting_weather",
            "crop_scope": "crop_group",
            "crop_key": "leafy_vegetable",
            "search_region": "VIETNAM",
        },
        {
            "intent": "planting_weather",
            "crop_scope": "crop_specific",
            "crop_key": "ngo",
            "search_region": "NONE",
        },
        {
            "intent": "weather_recovery",
            "crop_scope": "crop_specific",
            "crop_key": "cai_xanh",
            "search_region": "VIETNAM",
        },
        {
            "intent": "weather_recovery",
            "crop_scope": "crop_specific",
            "crop_key": "ngo",
            "search_region": "GIA_LAI_CURRENT",
        },
        {
            "intent": "weather_recovery",
            "crop_scope": "crop_group",
            "crop_key": "general_vegetable",
            "search_region": "BINH_DINH_LEGACY",
        },
        {
            "intent": "weather_recovery",
            "crop_scope": "crop_group",
            "crop_key": "leafy_vegetable",
            "search_region": "VIETNAM",
        },
    ]

    selected = []
    selected_ids = set()

    for item in criteria:

        for row in rows:

            if (
                row["query_id"] not in selected_ids
                and
                row_matches(row, item)
            ):
                selected.append(row)
                selected_ids.add(row["query_id"])
                break

    for row in rows:

        if len(selected) >= limit:
            break

        if row["query_id"] in selected_ids:
            continue

        selected.append(row)
        selected_ids.add(row["query_id"])

    return selected[:limit]


def combined_from_a1(row):
    query_text = row["query"]
    normalized = normalize_public_query(
        query_text
    )

    return {
        "combined_query_id":
            f"CQ-{stable_id(normalized)}",

        "source_stage":
            "A1",

        "source_query_id":
            row["query_id"],

        "query_text":
            query_text,

        "language":
            row["language"],

        "channel":
            row["channel"],

        "query_kind":
            row["query_kind"],

        "scope_type":
            row["scope_type"],

        "crop_key":
            row["crop_id"]
            or
            row["crop_group"],

        "weather_scenario":
            row["weather_scenario"],

        "action":
            row["action"],

        "search_region":
            row["search_region"],

        "query_origin":
            "",
    }


def combined_from_a2(row):
    query_text = row["query_text"]
    normalized = normalize_public_query(
        query_text
    )

    return {
        "combined_query_id":
            f"CQ-{stable_id(normalized)}",

        "source_stage":
            row["stage"],

        "source_query_id":
            row["query_id"],

        "query_text":
            query_text,

        "language":
            row["language"],

        "channel":
            "public_query",

        "query_kind":
            "natural_question",

        "scope_type":
            row["crop_scope"],

        "crop_key":
            row["crop_key"],

        "weather_scenario":
            row["scenario"],

        "action":
            row["action"],

        "search_region":
            row["search_region"],

        "query_origin":
            row["query_origin"],
    }


def build_combined_queries(
    a1_rows,
    a2_rows,
):
    combined = []
    seen = set()

    for row in a1_rows:
        normalized = normalize_public_query(
            row["query"]
        )

        if normalized in seen:
            continue

        seen.add(normalized)
        combined.append(
            combined_from_a1(row)
        )

    for row in a2_rows:
        normalized = normalize_public_query(
            row["query_text"]
        )

        if normalized in seen:
            continue

        seen.add(normalized)
        combined.append(
            combined_from_a2(row)
        )

    return combined


# ============================================================
# OUTPUT
# ============================================================

def write_outputs(
    a1_rows,
    a1_issues,
    a2_rows,
    a2_issues,
    combined_rows,
    config,
):
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with QUERY_CSV.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=list(
                a1_rows[0].keys()
            ),
        )

        writer.writeheader()
        writer.writerows(a1_rows)

    with QUERY_JSONL.open(
        "w",
        encoding="utf-8",
    ) as file:

        for row in a1_rows:
            file.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                )
                + "\n"
            )

    with A2_QUERY_CSV.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=A2_REQUIRED_FIELDS,
        )

        writer.writeheader()
        writer.writerows(a2_rows)

    with A2_QUERY_JSONL.open(
        "w",
        encoding="utf-8",
    ) as file:

        for row in a2_rows:
            file.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                )
                + "\n"
            )

    with COMBINED_QUERY_JSONL.open(
        "w",
        encoding="utf-8",
    ) as file:

        for row in combined_rows:
            file.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                )
                + "\n"
            )

    all_issues = (
        [
            {
                "stage": "A1",
                **issue,
            }
            for issue in a1_issues
        ]
        +
        [
            {
                "stage": "A2",
                **issue,
            }
            for issue in a2_issues
        ]
    )

    summary = {
        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "version":
            "discovery_query_bank_v2_round1_a2",

        "status":
            (
                "READY_FOR_A3"
                if not all_issues
                else
                "NEEDS_REVIEW"
            ),

        "strategy":
            "a1_systematic_coverage_plus_a2_natural_public_questions",

        "a1_query_count":
            len(a1_rows),

        "a2_query_count":
            len(a2_rows),

        "combined_unique_query_count":
            len(combined_rows),

        "crop_count":
            len(config["crops"]),

        "weather_scenario_count":
            len(SCENARIOS),

        "action_count":
            len(ACTIONS),

        "round_1_search_regions":
            {
                language: [
                    region["id"]
                    for region in regions
                ]
                for language, regions
                in ROUND_1_SEARCH_REGIONS.items()
            },

        "future_gap_fill_regions":
            REGIONAL_FALLBACKS,

        "a1": {
            "status":
                (
                    "READY_FOR_DISCOVERY"
                    if not a1_issues
                    else
                    "REVIEW_REQUIRED"
                ),

            "query_count":
                len(a1_rows),

            "by_language":
                count_by(
                    a1_rows,
                    "language",
                ),

            "by_channel":
                count_by(
                    a1_rows,
                    "channel",
                ),

            "by_scope":
                count_by(
                    a1_rows,
                    "scope_type",
                ),

            "by_query_kind":
                count_by(
                    a1_rows,
                    "query_kind",
                ),

            "by_search_region":
                count_by(
                    a1_rows,
                    "search_region",
                ),

            "by_weather_scenario":
                count_by(
                    a1_rows,
                    "weather_scenario",
                ),

            "audit": {
                "issue_count":
                    len(a1_issues),

                "issues":
                    a1_issues,
            },
        },

        "a2": {
            "status":
                (
                    "READY_FOR_A3"
                    if not a2_issues
                    else
                    "NEEDS_REVIEW"
                ),

            "query_count":
                len(a2_rows),

            "queries_with_region":
                sum(
                    1
                    for row in a2_rows
                    if row["search_region"] != "NONE"
                ),

            "queries_without_region":
                sum(
                    1
                    for row in a2_rows
                    if row["search_region"] == "NONE"
                ),

            "review_changes":
                A2_REVIEW_CHANGES,

            "by_query_origin":
                count_by_with_defaults(
                    a2_rows,
                    "query_origin",
                    A2_QUERY_ORIGIN_ORDER,
                ),

            "by_intent":
                count_by(
                    a2_rows,
                    "intent",
                ),

            "by_crop_scope":
                count_by(
                    a2_rows,
                    "crop_scope",
                ),

            "by_search_region":
                count_by(
                    a2_rows,
                    "search_region",
                ),

            "audit": {
                "issue_count":
                    len(a2_issues),

                "issues":
                    a2_issues,
            },
        },

        "audit": {
            "issue_count":
                len(all_issues),

            "issues":
                all_issues,
        },

        "outputs": {
            "a1_csv":
                str(QUERY_CSV),

            "a1_jsonl":
                str(QUERY_JSONL),

            "a2_csv":
                str(A2_QUERY_CSV),

            "a2_jsonl":
                str(A2_QUERY_JSONL),

            "combined_jsonl":
                str(COMBINED_QUERY_JSONL),

            "summary_json":
                str(SUMMARY_JSON),
        },
    }

    with SUMMARY_JSON.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            summary,
            file,
            ensure_ascii=False,
            indent=2,
        )

    return summary


# ============================================================
# MAIN
# ============================================================

def main():

    configure_stdout()

    print("=" * 80)
    print("AGRI RAG - DISCOVERY QUERY BANK V2 / ROUND 1 + A2")
    print("=" * 80)

    config = load_config()

    a1_rows = []
    seen = set()

    generate_crop_queries(
        config,
        a1_rows,
        seen,
    )

    generate_group_queries(
        config,
        a1_rows,
        seen,
    )

    a1_rows.sort(
        key=lambda row: (
            row["priority"],
            row["language"],
            row["scope_type"],
            row["crop_id"],
            row["crop_group"],
            row["weather_scenario"],
            row["query_kind"],
            row["action"],
            row["search_region"],
        )
    )

    a1_issues = audit(
        a1_rows,
        config,
    )

    a2_rows = generate_a2_queries(
        config
    )

    a2_issues = audit_a2(
        a2_rows,
        config,
    )

    combined_rows = build_combined_queries(
        a1_rows,
        a2_rows,
    )

    summary = write_outputs(
        a1_rows,
        a1_issues,
        a2_rows,
        a2_issues,
        combined_rows,
        config,
    )

    print()
    print(
        f"A1 queries              : "
        f"{summary['a1_query_count']}"
    )

    print(
        f"A2 queries              : "
        f"{summary['a2_query_count']}"
    )

    print(
        f"Combined unique queries : "
        f"{summary['combined_unique_query_count']}"
    )

    print(
        f"Scenarios               : "
        f"{summary['weather_scenario_count']}"
    )

    print(
        f"Actions                 : "
        f"{summary['action_count']}"
    )

    print(
        f"Status                  : "
        f"{summary['status']}"
    )

    print(
        f"Issues                  : "
        f"{summary['audit']['issue_count']}"
    )

    print_counter(
        "A1 by language:",
        summary["a1"]["by_language"],
    )

    print_counter(
        "A1 by query kind:",
        summary["a1"]["by_query_kind"],
    )

    print_counter(
        "A1 by scope:",
        summary["a1"]["by_scope"],
    )

    print_counter(
        "A1 by search region:",
        summary["a1"]["by_search_region"],
    )

    print_counter(
        "A1 by weather scenario:",
        summary["a1"]["by_weather_scenario"],
    )

    print_counter(
        "A2 by query origin:",
        summary["a2"]["by_query_origin"],
    )

    print_counter(
        "A2 by intent:",
        summary["a2"]["by_intent"],
    )

    print_counter(
        "A2 by crop scope:",
        summary["a2"]["by_crop_scope"],
    )

    print_counter(
        "A2 by search region:",
        summary["a2"]["by_search_region"],
    )

    print()
    print(
        "A2 queries with region    : "
        f"{summary['a2']['queries_with_region']}"
    )
    print(
        "A2 queries without region : "
        f"{summary['a2']['queries_without_region']}"
    )

    print()
    print("A2 review changes:")

    for change in summary["a2"]["review_changes"]:
        print(
            f"  - {change}"
        )

    print()
    print("Round 1 regions:")

    for language, regions in (
        summary[
            "round_1_search_regions"
        ].items()
    ):

        print(
            f"  {language:<2}: "
            f"{', '.join(regions)}"
        )

    print()
    print("Regional fallback is NOT searched yet:")
    print(
        ", ".join(
            summary["future_gap_fill_regions"]
        )
    )

    print()
    print("Audit issues:")

    if summary["audit"]["issues"]:

        for issue in summary["audit"]["issues"][:20]:
            print(
                f"  {issue}"
            )

    else:
        print("  none")

    print()
    print("Representative A2 queries:")

    for index, row in enumerate(
        representative_a2_queries(a2_rows),
        start=1,
    ):

        print()
        print(
            f"{index:02d}. [{row['query_id']}] "
            f"{row['query_origin']} | "
            f"{row['intent']} | "
            f"{row['crop_scope']} | "
            f"{row['crop_key']} | "
            f"{row['scenario']} | "
            f"{row['action']} | "
            f"{row['search_region']}"
        )

        print(
            f"    {row['query_text']}"
        )

    print()
    print(f"A1 CSV        : {QUERY_CSV}")
    print(f"A1 JSONL      : {QUERY_JSONL}")
    print(f"A2 CSV        : {A2_QUERY_CSV}")
    print(f"A2 JSONL      : {A2_QUERY_JSONL}")
    print(f"Combined JSONL: {COMBINED_QUERY_JSONL}")
    print(f"Summary       : {SUMMARY_JSON}")


if __name__ == "__main__":
    main()
