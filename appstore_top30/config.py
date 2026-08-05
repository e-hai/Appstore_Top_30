"""Project configuration: regions, charts, and storage paths."""

from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports"
DB_PATH = DATA_DIR / "appstore_top30.db"

TOP_N = 30
FEED_TIMEOUT = 20
FEED_RETRIES = 4
FEED_WORKERS = 4
LOOKUP_WORKERS = 2
LOOKUP_BATCH_SIZE = 100
REQUESTS_PER_SECOND = 4.0

# Region key -> display name and member countries.
REGIONS = {
    "north_america": {
        "name": "北美区",
        "countries": [
            ("us", "美国"),
            ("ca", "加拿大"),
        ],
    },
    "latam": {
        "name": "拉美区",
        "countries": [
            ("mx", "墨西哥"),
            ("br", "巴西"),
            ("ar", "阿根廷"),
            ("cl", "智利"),
            ("co", "哥伦比亚"),
            ("pe", "秘鲁"),
        ],
    },
    "europe": {
        "name": "欧洲区",
        "countries": [
            ("gb", "英国"),
            ("de", "德国"),
            ("fr", "法国"),
            ("it", "意大利"),
            ("es", "西班牙"),
        ],
    },
    "mena": {
        "name": "中东与北非",
        "countries": [
            ("ae", "阿联酋"),
            ("sa", "沙特阿拉伯"),
            ("il", "以色列"),
            ("tr", "土耳其"),
            ("eg", "埃及"),
            ("ma", "摩洛哥"),
        ],
    },
    "east_asia": {
        "name": "东北亚区",
        "countries": [
            ("jp", "日本"),
            ("kr", "韩国"),
            ("tw", "台湾"),
            ("hk", "香港"),
            ("mo", "澳门"),
        ],
    },
    "asean": {
        "name": "东南亚区",
        "countries": [
            ("sg", "新加坡"),
            ("my", "马来西亚"),
            ("th", "泰国"),
            ("id", "印度尼西亚"),
            ("vn", "越南"),
            ("ph", "菲律宾"),
        ],
    },
    "oceania": {
        "name": "大洋洲区",
        "countries": [
            ("au", "澳大利亚"),
            ("nz", "新西兰"),
        ],
    },
    "south_asia": {
        "name": "南亚区",
        "countries": [
            ("in", "印度"),
            ("pk", "巴基斯坦"),
            ("bd", "孟加拉国"),
            ("lk", "斯里兰卡"),
        ],
    },
    "africa": {
        "name": "非洲区",
        "countries": [
            ("za", "南非"),
            ("ng", "尼日利亚"),
            ("ke", "肯尼亚"),
        ],
    },
}

CHART_TYPES = {
    "free": "免费榜",
    "paid": "付费榜",
    "grossing": "畅销榜",
}

GENRE_ROOT_ID = "36"  # App Store root genre id in the iTunes genres endpoint.
GAMES_GENRE_ID = "6014"

# Unified Chinese names for App Store genre ids.
GENRE_NAMES_ZH = {
    "36": "总榜",
    "6000": "商务",
    "6001": "天气",
    "6002": "工具",
    "6003": "旅行",
    "6004": "体育",
    "6005": "社交",
    "6006": "参考",
    "6007": "效率",
    "6008": "摄影与录像",
    "6009": "新闻",
    "6010": "导航",
    "6011": "音乐",
    "6012": "生活",
    "6013": "健康健美",
    "6014": "游戏",
    "6015": "财务",
    "6016": "娱乐",
    "6017": "教育",
    "6018": "图书",
    "6020": "医疗",
    "6021": "报刊杂志",
    "6022": "目录",
    "6023": "美食佳饮",
    "6024": "购物",
    "6025": "贴纸",
    "6026": "开发者工具",
    "6027": "图形与设计",
    "7001": "动作",
    "7002": "冒险",
    "7003": "休闲",
    "7004": "桌面游戏",
    "7005": "卡牌",
    "7006": "赌场",
    "7007": "骰子",
    "7008": "游戏 · 教育",
    "7009": "家庭",
    "7011": "游戏 · 音乐",
    "7012": "解谜",
    "7013": "竞速",
    "7014": "角色扮演",
    "7015": "模拟",
    "7016": "游戏 · 体育",
    "7017": "策略",
    "7018": "问答",
    "7019": "字谜",
    "13001": "新闻与政治",
    "13002": "时尚与风格",
    "13003": "家居与园艺",
    "13004": "户外与自然",
    "13005": "体育与休闲",
    "13006": "汽车",
    "13007": "艺术与摄影",
    "13008": "新娘与婚礼",
    "13009": "商业与投资",
    "13010": "儿童杂志",
    "13011": "计算机与互联网",
    "13012": "烹饪美食饮品",
    "13013": "手工艺与爱好",
    "13014": "电子与音频",
    "13015": "娱乐",
    "13017": "健康身心",
    "13018": "历史",
    "13019": "文学杂志与期刊",
    "13020": "男性兴趣",
    "13021": "电影与音乐",
    "13023": "育儿与家庭",
    "13024": "宠物",
    "13025": "专业与商业",
    "13026": "地区新闻",
    "13027": "科学",
    "13028": "青少年",
    "13029": "旅行与地区",
    "13030": "女性兴趣",
    "16001": "表情与表达",
    "16003": "动物与自然",
    "16005": "艺术",
    "16006": "庆祝活动",
    "16007": "名人",
    "16008": "漫画与卡通",
    "16009": "饮食",
    "16010": "游戏",
    "16014": "电影与电视",
    "16015": "音乐",
    "16017": "人物",
    "16019": "地点与物品",
    "16021": "运动与活动",
    "16025": "儿童与家庭",
    "16026": "时尚",
}

APP_CATEGORY_IDS = sorted(
    genre_id
    for genre_id in GENRE_NAMES_ZH
    if genre_id.startswith("60")
    and genre_id not in {GENRE_ROOT_ID, GAMES_GENRE_ID}
)
GAME_SUBGENRE_IDS = sorted(
    genre_id for genre_id in GENRE_NAMES_ZH if genre_id.startswith("70")
)


def genre_display_name(genre_id: str, original: str | None = None) -> str:
    """Return a unified Chinese genre name when available."""
    return GENRE_NAMES_ZH.get(genre_id, original or genre_id)


@dataclass(frozen=True)
class Country:
    code: str
    name: str
    region: str


def iter_countries() -> list[Country]:
    """Return all configured countries."""
    countries = []
    for region, spec in REGIONS.items():
        for code, name in spec["countries"]:
            countries.append(Country(code=code, name=name, region=region))
    return countries
