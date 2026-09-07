import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


# ============================================================
# OUTPUT
# ============================================================

ROOT = Path("data/agri_rag")

DISCOVERY_DIR = (
    ROOT
    / "discovery"
)

QUERY_BANK_JSONL = (
    DISCOVERY_DIR
    / "query_bank.jsonl"
)

QUERY_BANK_CSV = (
    DISCOVERY_DIR
    / "query_bank.csv"
)

QUERY_BANK_SUMMARY = (
    DISCOVERY_DIR
    / "query_bank_summary.json"
)


# ============================================================
# TARGET CROPS
#
# Không chỉ dùng tên tiếng Việt chính.
# Alias giúp search bắt được cách viết khác nhau của tài liệu.
# ============================================================

CROPS = {
    "cai_xanh": {
        "name":
            "Cải xanh",

        "vi": [
            "cải xanh",
            "cải bẹ xanh",
            "cải canh",
        ],

        "en": [
            "mustard greens",
            "Brassica juncea",
        ],

        "groups": [
            "leafy_vegetable",
            "short_cycle_vegetable",
        ],
    },

    "ngo": {
        "name":
            "Ngò / ngò rí",

        "vi": [
            "ngò rí",
            "rau mùi",
            "ngò",
        ],

        "en": [
            "coriander",
            "Coriandrum sativum",
            "cilantro",
        ],

        "groups": [
            "herb_vegetable",
            "short_cycle_vegetable",
        ],
    },

    "cai_cuc": {
        "name":
            "Cải cúc / tần ô",

        "vi": [
            "cải cúc",
            "tần ô",
        ],

        "en": [
            "edible chrysanthemum",
            "Glebionis coronaria",
            "crown daisy",
        ],

        "groups": [
            "leafy_vegetable",
            "short_cycle_vegetable",
        ],
    },

    "rau_muong": {
        "name":
            "Rau muống",

        "vi": [
            "rau muống",
        ],

        "en": [
            "water spinach",
            "Ipomoea aquatica",
        ],

        "groups": [
            "leafy_vegetable",
            "short_cycle_vegetable",
        ],
    },

    "xa_lach": {
        "name":
            "Xà lách",

        "vi": [
            "xà lách",
        ],

        "en": [
            "lettuce",
            "Lactuca sativa",
        ],

        "groups": [
            "leafy_vegetable",
            "short_cycle_vegetable",
        ],
    },
}


# ============================================================
# GROUP FALLBACK
#
# Nếu không có tài liệu riêng cây:
#
# crop specific
#     ↓
# crop group
#     ↓
# general vegetable
#
# ============================================================

CROP_GROUPS = {
    "leafy_vegetable": {
        "name":
            "Rau ăn lá",

        "vi": [
            "rau ăn lá",
        ],

        "en": [
            "leafy vegetables",
        ],
    },

    "herb_vegetable": {
        "name":
            "Rau gia vị",

        "vi": [
            "rau gia vị",
        ],

        "en": [
            "culinary herbs",
            "herb vegetables",
        ],
    },

    "short_cycle_vegetable": {
        "name":
            "Rau ngắn ngày",

        "vi": [
            "rau ngắn ngày",
            "rau màu ngắn ngày",
        ],

        "en": [
            "short cycle vegetables",
            "short duration vegetables",
        ],
    },

    "general_vegetable": {
        "name":
            "Rau",

        "vi": [
            "rau",
            "cây rau",
        ],

        "en": [
            "vegetables",
            "vegetable crops",
        ],
    },
}


# ============================================================
# AGRICULTURAL ACTIONS
# ============================================================

ACTIONS = {
    "irrigation": {
        "vi": [
            "tưới nước",
            "có nên tưới",
        ],

        "en": [
            "irrigation",
            "watering",
        ],
    },

    "drainage": {
        "vi": [
            "thoát nước",
            "khơi rãnh",
        ],

        "en": [
            "drainage",
            "drain excess water",
        ],
    },

    "fertilization": {
        "vi": [
            "bón phân",
            "bón thúc",
        ],

        "en": [
            "fertilization",
            "fertilizer application",
        ],
    },

    "disease_management": {
        "vi": [
            "sâu bệnh",
            "bệnh nấm",
        ],

        "en": [
            "disease management",
            "pest and disease",
        ],
    },

    "disease_monitoring": {
        "vi": [
            "theo dõi bệnh",
            "kiểm tra sâu bệnh",
        ],

        "en": [
            "disease monitoring",
            "crop disease monitoring",
        ],
    },

    "shade": {
        "vi": [
            "che nắng",
            "che phủ",
        ],

        "en": [
            "shade management",
            "shade protection",
        ],
    },

    "crop_protection": {
        "vi": [
            "bảo vệ cây",
            "che chắn cây",
        ],

        "en": [
            "crop protection",
            "protect plants",
        ],
    },

    "mulching": {
        "vi": [
            "phủ đất giữ ẩm",
            "giữ ẩm đất",
        ],

        "en": [
            "mulching",
            "soil moisture conservation",
        ],
    },

    "field_inspection": {
        "vi": [
            "kiểm tra đồng ruộng",
            "theo dõi cây",
        ],

        "en": [
            "field inspection",
            "crop monitoring",
        ],
    },

    "post_rain_care": {
        "vi": [
            "chăm sóc sau mưa",
            "phục hồi sau mưa",
        ],

        "en": [
            "post rain care",
            "crop recovery after rain",
        ],
    },

    "spray_window": {
        "vi": [
            "thời điểm phun thuốc",
            "phun thuốc trước mưa",
        ],

        "en": [
            "spray timing",
            "pesticide application timing",
        ],
    },

    "planting": {
        "vi": [
            "gieo trồng",
            "trồng cây con",
        ],

        "en": [
            "planting",
            "transplanting",
        ],
    },

    "harvest": {
        "vi": [
            "thu hoạch",
            "thời điểm thu hoạch",
        ],

        "en": [
            "harvest timing",
            "harvesting",
        ],
    },
}


# ============================================================
# WEATHER / ENVIRONMENT SCENARIOS
#
# Mỗi scenario chỉ kết hợp với những action có ý nghĩa.
# Không lấy Cartesian product toàn bộ để tránh query rác.
# ============================================================

SCENARIOS = {
    "heavy_rain": {
        "factor":
            "rainfall",

        "vi": [
            "mưa lớn",
            "mưa to",
        ],

        "en": [
            "heavy rain",
            "excess rainfall",
        ],

        "effects": [
            "excess_water",
            "nutrient_loss",
            "disease_risk",
        ],

        "actions": [
            "irrigation",
            "drainage",
            "fertilization",
            "disease_management",
            "spray_window",
            "harvest",
        ],
    },

    "prolonged_rain": {
        "factor":
            "rainfall",

        "vi": [
            "mưa kéo dài",
            "mưa liên tục nhiều ngày",
        ],

        "en": [
            "prolonged rainfall",
            "consecutive rainy days",
        ],

        "effects": [
            "waterlogging",
            "root_stress",
            "disease_risk",
        ],

        "actions": [
            "drainage",
            "fertilization",
            "disease_management",
            "disease_monitoring",
            "post_rain_care",
        ],
    },

    "post_rain": {
        "factor":
            "rainfall",

        "vi": [
            "sau mưa",
            "sau mưa lớn",
        ],

        "en": [
            "after heavy rain",
            "post rain",
        ],

        "effects": [
            "wet_soil",
            "disease_risk",
            "nutrient_loss",
        ],

        "actions": [
            "post_rain_care",
            "field_inspection",
            "irrigation",
            "fertilization",
            "disease_monitoring",
        ],
    },

    "hot_weather": {
        "factor":
            "temperature",

        "vi": [
            "nắng nóng",
            "nhiệt độ cao",
        ],

        "en": [
            "hot weather",
            "heat stress",
        ],

        "effects": [
            "heat_stress",
            "water_loss",
        ],

        "actions": [
            "irrigation",
            "shade",
            "mulching",
            "crop_protection",
            "field_inspection",
        ],
    },

    "intense_sun": {
        "factor":
            "solar_radiation",

        "vi": [
            "nắng gắt",
            "nắng mạnh",
        ],

        "en": [
            "intense sunlight",
            "high solar radiation",
        ],

        "effects": [
            "leaf_heat",
            "water_loss",
        ],

        "actions": [
            "shade",
            "irrigation",
            "crop_protection",
        ],
    },

    "dry_spell": {
        "factor":
            "rainfall",

        "vi": [
            "khô hạn",
            "nhiều ngày không mưa",
        ],

        "en": [
            "dry spell",
            "drought stress",
        ],

        "effects": [
            "soil_dryness",
            "water_stress",
        ],

        "actions": [
            "irrigation",
            "mulching",
            "field_inspection",
        ],
    },

    "high_humidity": {
        "factor":
            "humidity",

        "vi": [
            "độ ẩm cao",
            "trời ẩm",
        ],

        "en": [
            "high humidity",
            "humid conditions",
        ],

        "effects": [
            "disease_risk",
            "leaf_wetness",
        ],

        "actions": [
            "disease_management",
            "disease_monitoring",
            "spray_window",
            "field_inspection",
        ],
    },

    "leaf_wetness": {
        "factor":
            "humidity",

        "vi": [
            "lá ướt lâu",
            "sương nhiều",
        ],

        "en": [
            "leaf wetness",
            "heavy dew",
        ],

        "effects": [
            "leaf_wetness",
            "disease_risk",
        ],

        "actions": [
            "disease_monitoring",
            "disease_management",
            "field_inspection",
        ],
    },

    "cold_weather": {
        "factor":
            "temperature",

        "vi": [
            "rét",
            "nhiệt độ thấp",
        ],

        "en": [
            "cold weather",
            "low temperature",
        ],

        "effects": [
            "cold_stress",
            "slow_growth",
        ],

        "actions": [
            "crop_protection",
            "irrigation",
            "planting",
            "field_inspection",
        ],
    },

    "strong_wind": {
        "factor":
            "wind",

        "vi": [
            "gió mạnh",
            "gió lớn",
        ],

        "en": [
            "strong wind",
            "high wind",
        ],

        "effects": [
            "physical_damage",
            "water_loss",
        ],

        "actions": [
            "crop_protection",
            "irrigation",
            "field_inspection",
            "spray_window",
        ],
    },

    "hot_dry_wind": {
        "factor":
            "wind",

        "vi": [
            "gió nóng khô",
            "gió khô nóng",
        ],

        "en": [
            "hot dry wind",
            "dry hot wind",
        ],

        "effects": [
            "water_loss",
            "flower_damage",
        ],

        "actions": [
            "irrigation",
            "crop_protection",
            "field_inspection",
        ],
    },

    "waterlogging": {
        "factor":
            "soil_water",

        "vi": [
            "ngập úng",
            "đất bị úng",
        ],

        "en": [
            "waterlogging",
            "waterlogged soil",
        ],

        "effects": [
            "root_stress",
            "root_rot_risk",
        ],

        "actions": [
            "drainage",
            "disease_management",
            "fertilization",
            "field_inspection",
        ],
    },

    "wet_soil": {
        "factor":
            "soil_water",

        "vi": [
            "đất quá ướt",
            "đất còn ướt",
        ],

        "en": [
            "wet soil",
            "excess soil moisture",
        ],

        "effects": [
            "excess_water",
            "root_stress",
        ],

        "actions": [
            "irrigation",
            "fertilization",
            "disease_monitoring",
            "field_inspection",
        ],
    },

    "weather_transition": {
        "factor":
            "weather_transition",

        "vi": [
            "sau mưa gặp nắng",
            "thời tiết thay đổi đột ngột",
        ],

        "en": [
            "rain to heat transition",
            "sudden weather change",
        ],

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


# ============================================================
# GEOGRAPHIC PRIORITY
#
# Discovery vẫn toàn web.
# Region chỉ giúp sinh query ưu tiên.
# ============================================================

VI_REGIONS = [
    {
        "region_id":
            "VIETNAM",

        "query_text":
            "Việt Nam",

        "priority":
            1,
    },

    {
        "region_id":
            "BINH_DINH_LEGACY",

        "query_text":
            "Bình Định",

        "priority":
            1,
    },

    {
        "region_id":
            "GIA_LAI_CURRENT",

        "query_text":
            "Gia Lai",

        "priority":
            1,
    },

    {
        "region_id":
            "SOUTH_CENTRAL_COAST",

        "query_text":
            "Nam Trung Bộ",

        "priority":
            2,
    },
]


EN_REGIONS = [
    {
        "region_id":
            "VIETNAM",

        "query_text":
            "Vietnam",

        "priority":
            2,
    },

    {
        "region_id":
            "SOUTHEAST_ASIA",

        "query_text":
            "Southeast Asia",

        "priority":
            3,
    },

    {
        "region_id":
            "TROPICAL",

        "query_text":
            "tropical",

        "priority":
            3,
    },
]


# ============================================================
# HELPERS
# ============================================================

def stable_id(text):

    digest = hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()

    return digest[:12]


def write_jsonl(
    path,
    rows,
):

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


def write_csv(
    path,
    rows,
):

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not rows:
        return

    fieldnames = list(
        rows[0].keys()
    )

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


def save_json(
    path,
    data,
):

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


# ============================================================
# QUERY BUILDERS
# ============================================================

def make_vi_query(
    crop_term,
    weather_term,
    action_term,
    region_term,
):

    return (
        f'"{crop_term}" '
        f'"{weather_term}" '
        f'"{action_term}" '
        f'{region_term}'
    ).strip()


def make_en_query(
    crop_term,
    weather_term,
    action_term,
    region_term,
):

    return (
        f'{crop_term} '
        f'{weather_term} '
        f'{action_term} '
        f'{region_term}'
    ).strip()


def add_query(
    rows,
    seen_queries,
    *,
    language,
    channel,
    scope_type,
    crop_id,
    crop_name,
    crop_group,
    crop_term,
    scenario_id,
    scenario,
    weather_term,
    action_id,
    action_term,
    region_id,
    region_term,
    priority,
    query,
):

    normalized = (
        " ".join(
            query.casefold().split()
        )
    )

    if normalized in seen_queries:
        return

    seen_queries.add(
        normalized
    )

    query_id = (
        "DQ-"
        +
        stable_id(
            normalized
        ).upper()
    )

    rows.append({
        "query_id":
            query_id,

        "language":
            language,

        "channel":
            channel,

        "priority":
            priority,

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
            scenario[
                "factor"
            ],

        "weather_term":
            weather_term,

        "effects":
            "|".join(
                scenario[
                    "effects"
                ]
            ),

        "action":
            action_id,

        "action_term":
            action_term,

        "region_id":
            region_id,

        "region_term":
            region_term,

        "query":
            query,
    })


# ============================================================
# GENERATE CROP-SPECIFIC QUERIES
# ============================================================

def generate_crop_queries(
    rows,
    seen_queries,
):

    for crop_id, crop in (
        CROPS.items()
    ):

        # --------------------------------------------
        # Vietnamese discovery.
        # Use up to two strong aliases per crop.
        # --------------------------------------------

        vi_crop_terms = (
            crop[
                "vi"
            ][:2]
        )

        for (
            scenario_id,
            scenario,
        ) in SCENARIOS.items():

            for action_id in (
                scenario[
                    "actions"
                ]
            ):

                action = (
                    ACTIONS[
                        action_id
                    ]
                )

                # Keep query bank broad but controlled:
                # first 2 weather phrases × first 1 action phrase.
                for crop_term in (
                    vi_crop_terms
                ):

                    for weather_term in (
                        scenario[
                            "vi"
                        ][:2]
                    ):

                        action_term = (
                            action[
                                "vi"
                            ][0]
                        )

                        # Query without forced locality.
                        query = (
                            make_vi_query(
                                crop_term,
                                weather_term,
                                action_term,
                                "",
                            )
                        )

                        add_query(
                            rows,
                            seen_queries,
                            language="vi",
                            channel="web",
                            scope_type="crop_specific",
                            crop_id=crop_id,
                            crop_name=crop["name"],
                            crop_group="",
                            crop_term=crop_term,
                            scenario_id=scenario_id,
                            scenario=scenario,
                            weather_term=weather_term,
                            action_id=action_id,
                            action_term=action_term,
                            region_id="ANY",
                            region_term="",
                            priority=1,
                            query=query,
                        )

                        # Geography-aware query.
                        for region in (
                            VI_REGIONS
                        ):

                            query = (
                                make_vi_query(
                                    crop_term,
                                    weather_term,
                                    action_term,
                                    region[
                                        "query_text"
                                    ],
                                )
                            )

                            add_query(
                                rows,
                                seen_queries,
                                language="vi",
                                channel="web",
                                scope_type="crop_specific",
                                crop_id=crop_id,
                                crop_name=crop["name"],
                                crop_group="",
                                crop_term=crop_term,
                                scenario_id=scenario_id,
                                scenario=scenario,
                                weather_term=weather_term,
                                action_id=action_id,
                                action_term=action_term,
                                region_id=region["region_id"],
                                region_term=region["query_text"],
                                priority=region["priority"],
                                query=query,
                            )

        # --------------------------------------------
        # English / scholarly gap-fill.
        # --------------------------------------------

        en_crop_terms = (
            crop[
                "en"
            ][:2]
        )

        for (
            scenario_id,
            scenario,
        ) in SCENARIOS.items():

            for action_id in (
                scenario[
                    "actions"
                ]
            ):

                action = (
                    ACTIONS[
                        action_id
                    ]
                )

                crop_term = (
                    en_crop_terms[-1]
                )

                weather_term = (
                    scenario[
                        "en"
                    ][0]
                )

                action_term = (
                    action[
                        "en"
                    ][0]
                )

                # No region = global paper discovery.
                query = make_en_query(
                    crop_term,
                    weather_term,
                    action_term,
                    "",
                )

                add_query(
                    rows,
                    seen_queries,
                    language="en",
                    channel="scholarly",
                    scope_type="crop_specific",
                    crop_id=crop_id,
                    crop_name=crop["name"],
                    crop_group="",
                    crop_term=crop_term,
                    scenario_id=scenario_id,
                    scenario=scenario,
                    weather_term=weather_term,
                    action_id=action_id,
                    action_term=action_term,
                    region_id="GLOBAL",
                    region_term="",
                    priority=3,
                    query=query,
                )

                for region in (
                    EN_REGIONS
                ):

                    query = (
                        make_en_query(
                            crop_term,
                            weather_term,
                            action_term,
                            region[
                                "query_text"
                            ],
                        )
                    )

                    add_query(
                        rows,
                        seen_queries,
                        language="en",
                        channel="scholarly",
                        scope_type="crop_specific",
                        crop_id=crop_id,
                        crop_name=crop["name"],
                        crop_group="",
                        crop_term=crop_term,
                        scenario_id=scenario_id,
                        scenario=scenario,
                        weather_term=weather_term,
                        action_id=action_id,
                        action_term=action_term,
                        region_id=region["region_id"],
                        region_term=region["query_text"],
                        priority=region["priority"],
                        query=query,
                    )


# ============================================================
# GENERATE CROP-GROUP FALLBACK QUERIES
# ============================================================

def generate_group_queries(
    rows,
    seen_queries,
):

    for (
        group_id,
        group,
    ) in CROP_GROUPS.items():

        vi_group_term = (
            group[
                "vi"
            ][0]
        )

        en_group_term = (
            group[
                "en"
            ][0]
        )

        for (
            scenario_id,
            scenario,
        ) in SCENARIOS.items():

            for action_id in (
                scenario[
                    "actions"
                ]
            ):

                action = (
                    ACTIONS[
                        action_id
                    ]
                )

                weather_vi = (
                    scenario[
                        "vi"
                    ][0]
                )

                action_vi = (
                    action[
                        "vi"
                    ][0]
                )

                # General Vietnam query.
                query = (
                    make_vi_query(
                        vi_group_term,
                        weather_vi,
                        action_vi,
                        "Việt Nam",
                    )
                )

                add_query(
                    rows,
                    seen_queries,
                    language="vi",
                    channel="web",
                    scope_type="crop_group",
                    crop_id="",
                    crop_name="",
                    crop_group=group_id,
                    crop_term=vi_group_term,
                    scenario_id=scenario_id,
                    scenario=scenario,
                    weather_term=weather_vi,
                    action_id=action_id,
                    action_term=action_vi,
                    region_id="VIETNAM",
                    region_term="Việt Nam",
                    priority=2,
                    query=query,
                )

                # Local group search.
                for region in (
                    VI_REGIONS[1:]
                ):

                    query = (
                        make_vi_query(
                            vi_group_term,
                            weather_vi,
                            action_vi,
                            region[
                                "query_text"
                            ],
                        )
                    )

                    add_query(
                        rows,
                        seen_queries,
                        language="vi",
                        channel="web",
                        scope_type="crop_group",
                        crop_id="",
                        crop_name="",
                        crop_group=group_id,
                        crop_term=vi_group_term,
                        scenario_id=scenario_id,
                        scenario=scenario,
                        weather_term=weather_vi,
                        action_id=action_id,
                        action_term=action_vi,
                        region_id=region["region_id"],
                        region_term=region["query_text"],
                        priority=region["priority"],
                        query=query,
                    )

                # English fallback.
                query = (
                    make_en_query(
                        en_group_term,
                        scenario[
                            "en"
                        ][0],
                        action[
                            "en"
                        ][0],
                        "tropical",
                    )
                )

                add_query(
                    rows,
                    seen_queries,
                    language="en",
                    channel="scholarly",
                    scope_type="crop_group",
                    crop_id="",
                    crop_name="",
                    crop_group=group_id,
                    crop_term=en_group_term,
                    scenario_id=scenario_id,
                    scenario=scenario,
                    weather_term=scenario["en"][0],
                    action_id=action_id,
                    action_term=action["en"][0],
                    region_id="TROPICAL",
                    region_term="tropical",
                    priority=3,
                    query=query,
                )


# ============================================================
# AUDIT
# ============================================================

def count_field(
    rows,
    field,
):

    counter = Counter()

    for row in rows:

        value = (
            row.get(
                field
            )
            or ""
        )

        counter[
            value
        ] += 1

    return dict(
        sorted(
            counter.items()
        )
    )


def audit(
    rows,
):

    issues = []

    required = [
        "query_id",
        "language",
        "channel",
        "scope_type",
        "weather_scenario",
        "weather_factor",
        "action",
        "query",
    ]

    ids = set()
    queries = set()

    for row in rows:

        for field in required:

            if not row.get(
                field
            ):

                issues.append({
                    "code":
                        "MISSING_REQUIRED_FIELD",

                    "query_id":
                        row.get(
                            "query_id"
                        ),

                    "field":
                        field,
                })

        query_id = (
            row[
                "query_id"
            ]
        )

        if query_id in ids:

            issues.append({
                "code":
                    "DUPLICATE_QUERY_ID",

                "query_id":
                    query_id,
            })

        ids.add(
            query_id
        )

        normalized = (
            " ".join(
                row[
                    "query"
                ].casefold().split()
            )
        )

        if normalized in queries:

            issues.append({
                "code":
                    "DUPLICATE_QUERY",

                "query_id":
                    query_id,

                "query":
                    row[
                        "query"
                    ],
            })

        queries.add(
            normalized
        )

    return issues


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 110)
    print(
        "AGRI RAG - DISCOVERY QUERY BANK V1"
    )
    print("=" * 110)

    print(
        "Strategy: DISCOVERY FIRST -> "
        "CONTENT RELEVANCE -> SOURCE VALIDATION"
    )

    print(
        "No source/domain whitelist is used "
        "in this query bank."
    )

    rows = []
    seen_queries = set()

    generate_crop_queries(
        rows,
        seen_queries,
    )

    generate_group_queries(
        rows,
        seen_queries,
    )

    # Stable output ordering.
    rows.sort(
        key=lambda row: (
            row[
                "priority"
            ],
            row[
                "language"
            ],
            row[
                "scope_type"
            ],
            row[
                "crop_id"
            ],
            row[
                "crop_group"
            ],
            row[
                "weather_scenario"
            ],
            row[
                "action"
            ],
            row[
                "query"
            ],
        )
    )

    issues = audit(
        rows
    )

    status = (
        "READY_FOR_DISCOVERY"
        if not issues
        else
        "REVIEW_REQUIRED"
    )

    write_jsonl(
        QUERY_BANK_JSONL,
        rows,
    )

    write_csv(
        QUERY_BANK_CSV,
        rows,
    )

    summary = {
        "status":
            status,

        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "strategy":
            (
                "discovery_first_"
                "validation_second"
            ),

        "query_count":
            len(
                rows
            ),

        "crops":
            list(
                CROPS.keys()
            ),

        "crop_groups":
            list(
                CROP_GROUPS.keys()
            ),

        "weather_scenarios":
            list(
                SCENARIOS.keys()
            ),

        "actions":
            list(
                ACTIONS.keys()
            ),

        "by_language":
            count_field(
                rows,
                "language",
            ),

        "by_channel":
            count_field(
                rows,
                "channel",
            ),

        "by_scope_type":
            count_field(
                rows,
                "scope_type",
            ),

        "by_crop":
            count_field(
                rows,
                "crop_id",
            ),

        "by_crop_group":
            count_field(
                rows,
                "crop_group",
            ),

        "by_weather_scenario":
            count_field(
                rows,
                "weather_scenario",
            ),

        "by_action":
            count_field(
                rows,
                "action",
            ),

        "by_region":
            count_field(
                rows,
                "region_id",
            ),

        "audit": {
            "issue_count":
                len(
                    issues
                ),

            "issues":
                issues,
        },

        "outputs": {
            "jsonl":
                str(
                    QUERY_BANK_JSONL
                ),

            "csv":
                str(
                    QUERY_BANK_CSV
                ),
        },
    }

    save_json(
        QUERY_BANK_SUMMARY,
        summary,
    )

    print()
    print("=" * 110)
    print("QUERY BANK SUMMARY")
    print("=" * 110)

    print(
        f"Queries generated       : "
        f"{len(rows)}"
    )

    print(
        f"Target crops            : "
        f"{len(CROPS)}"
    )

    print(
        f"Crop fallback groups    : "
        f"{len(CROP_GROUPS)}"
    )

    print(
        f"Weather scenarios       : "
        f"{len(SCENARIOS)}"
    )

    print(
        f"Agricultural actions    : "
        f"{len(ACTIONS)}"
    )

    print()
    print(
        "By language:"
    )

    for key, value in (
        count_field(
            rows,
            "language",
        ).items()
    ):

        print(
            f"  {key:<20}: "
            f"{value}"
        )

    print()
    print(
        "By channel:"
    )

    for key, value in (
        count_field(
            rows,
            "channel",
        ).items()
    ):

        print(
            f"  {key:<20}: "
            f"{value}"
        )

    print()
    print("=" * 110)
    print("WEATHER SCENARIO COVERAGE")
    print("=" * 110)

    for key, value in (
        count_field(
            rows,
            "weather_scenario",
        ).items()
    ):

        print(
            f"{key:<28}: "
            f"{value}"
        )

    print()
    print("=" * 110)
    print("ACTION COVERAGE")
    print("=" * 110)

    for key, value in (
        count_field(
            rows,
            "action",
        ).items()
    ):

        print(
            f"{key:<28}: "
            f"{value}"
        )

    print()
    print("=" * 110)
    print("QUERY SAMPLES")
    print("=" * 110)

    sample_indices = [
        0,
        len(rows) // 5,
        (len(rows) * 2) // 5,
        (len(rows) * 3) // 5,
        (len(rows) * 4) // 5,
    ]

    used = set()

    for index in sample_indices:

        if (
            index < 0
            or
            index >= len(rows)
            or
            index in used
        ):
            continue

        used.add(
            index
        )

        row = (
            rows[
                index
            ]
        )

        print()
        print(
            f"{row['query_id']}"
        )

        print(
            f"  priority : "
            f"{row['priority']}"
        )

        print(
            f"  language : "
            f"{row['language']}"
        )

        print(
            f"  scope    : "
            f"{row['scope_type']}"
        )

        print(
            f"  crop     : "
            f"{row['crop_id'] or row['crop_group']}"
        )

        print(
            f"  weather  : "
            f"{row['weather_scenario']}"
        )

        print(
            f"  action   : "
            f"{row['action']}"
        )

        print(
            f"  region   : "
            f"{row['region_id']}"
        )

        print(
            f"  query    : "
            f"{row['query']}"
        )

    print()
    print("=" * 110)
    print("AUDIT")
    print("=" * 110)

    print(
        f"Status : {status}"
    )

    print(
        f"Issues : {len(issues)}"
    )

    if issues:

        for issue in (
            issues[:20]
        ):

            print(
                f"  - {issue}"
            )

    print()
    print("=" * 110)
    print("OUTPUT")
    print("=" * 110)

    print(
        "Query bank JSONL : "
        f"{QUERY_BANK_JSONL}"
    )

    print(
        "Query bank CSV   : "
        f"{QUERY_BANK_CSV}"
    )

    print(
        "Summary          : "
        f"{QUERY_BANK_SUMMARY}"
    )

    print()

    if status == (
        "READY_FOR_DISCOVERY"
    ):

        print(
            "QUERY BANK PASSED."
        )

        print(
            "NEXT: discover candidate "
            "documents across the whole web "
            "and scholarly indexes."
        )

    else:

        print(
            "QUERY BANK REQUIRES REVIEW."
        )


if __name__ == "__main__":
    main()