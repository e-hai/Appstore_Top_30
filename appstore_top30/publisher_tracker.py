"""20 Top Casual Game Publishers Tracker Module."""

from functools import lru_cache

CASUAL_PUBLISHERS_DATA = [
    # --- 土耳其军团 ---
    {
        "id": "dream_games",
        "name": "Dream Games",
        "region": "turkey",
        "country": "土耳其 🇹🇷",
        "category": "消除新王 (Match-3 King)",
        "desc": "由 Peak 前员工创立，凭《Royal Match》超越《糖果传奇》，成为目前全球最吸金的三消新王。",
        "published_games": [
            {"name": "Royal Match", "icon": "🏰", "release_date": "2021-02", "status": "全球畅销榜 #1", "desc": "全球最赚钱的三消游戏，月流水破 1 亿美元"}
        ],
        "new_games": [
            {"name": "Royal Kingdom", "icon": "👑", "release_date": "2024-11", "status": "爆款测试中", "desc": "《Royal Match》续作，加入攻城防守与公会对抗 PVP 机制"}
        ],
        "upcoming_games": [
            {"name": "Project Royal Puzzle (暂定名)", "icon": "🧩", "expected_date": "2026 Q4", "status": "软发射阶段", "desc": "结合 3D 合成与社交城堡建构的新一代消除实验作品"}
        ]
    },
    {
        "id": "loop_games",
        "name": "Loop Games",
        "region": "turkey",
        "country": "土耳其 🇹🇷",
        "category": "3D消除开拓者",
        "desc": "主攻益智副玩法与超休闲解谜，代表作《Match 3D》开创了 3D 物品寻找消除的潮流。",
        "published_games": [
            {"name": "Match 3D", "icon": "📦", "release_date": "2020-05", "status": "经典爆款", "desc": "开创 3D 杂物堆寻找三消的现象级作品"},
            {"name": "Match Tile 3D", "icon": "🔷", "release_date": "2021-03", "status": "长青运营", "desc": "结合 3D 空间翻转与麻将方块消消乐"}
        ],
        "new_games": [
            {"name": "Match Story 3D", "icon": "📖", "release_date": "2025-08", "status": "稳步上升", "desc": "引入剧情解谜与老宅修复外围的 3D 消除新作"}
        ],
        "upcoming_games": [
            {"name": "Merge Loop 3D", "icon": "🔄", "expected_date": "2026 Q4", "status": "预预约", "desc": "3D 拟真物品合成 + 空间摆放重度变现新品"}
        ]
    },
    {
        "id": "good_job_games",
        "name": "Good Job Games",
        "region": "turkey",
        "country": "土耳其 🇹🇷",
        "category": "魔性物理益智",
        "desc": "擅长将魔性物理机制与休闲益智结合，代表作《Color Fill 3D》、《Paper Fold》。",
        "published_games": [
            {"name": "Color Fill 3D", "icon": "🎨", "release_date": "2019-03", "status": "超 1 亿下载", "desc": "魔性物理填色画线小游戏"},
            {"name": "Paper Fold", "icon": "📜", "release_date": "2021-04", "status": "全球下载榜前列", "desc": "折纸艺术解谜休闲游戏"}
        ],
        "new_games": [
            {"name": "Sort Match 3D", "icon": "🗄️", "release_date": "2025-06", "status": "热播买量中", "desc": "货柜整理与物理推叠消除新品"}
        ],
        "upcoming_games": [
            {"name": "Physics Puzzle Quest", "icon": "⚙️", "expected_date": "2026 Q4", "status": "内部测试", "desc": "结合物理引擎机制的混合休闲（Hybrid Casual）冒险"}
        ]
    },
    {
        "id": "fugo_games",
        "name": "Fugo Games",
        "region": "turkey",
        "country": "土耳其 🇹🇷",
        "category": "文字益智巨头",
        "desc": "文字益智类（Word Games）巨头，其推出的《Words of Wonders》长期横扫多国下载榜。",
        "published_games": [
            {"name": "Words of Wonders: Crossword", "icon": "🔤", "release_date": "2018-04", "status": "全球填字 #1", "desc": "全球数亿玩家的自然地理人文填字巨作"},
            {"name": "Words of Wonders: Guru", "icon": "🎓", "release_date": "2021-09", "status": "长青收割", "desc": "进阶版智力填字谜题"}
        ],
        "new_games": [
            {"name": "Word Travel: Search Puzzle", "icon": "✈️", "release_date": "2025-04", "status": "多国榜单 Top 10", "desc": "结合旅行风景卡牌收集的文字消除"}
        ],
        "upcoming_games": [
            {"name": "Word Merge Trivia", "icon": "💡", "expected_date": "2026 Q4", "status": "加拿大/澳大利亚试软", "desc": "文字拼写 + 词条合成二合一创新变现框架"}
        ]
    },

    # --- 中国出海主力 ---
    {
        "id": "microfun",
        "name": "柠萌互动 (Microfun)",
        "region": "china",
        "country": "中国 🇨🇳",
        "category": "合成+剧情霸主 (Merge-2 King)",
        "desc": "全球“合成+剧情（Merge-2）”赛道当之无愧的霸主，代表作《Gossip Harbor》、《Seaside Escape》。",
        "published_games": [
            {"name": "Gossip Harbor (海滨小镇)", "icon": "⛵", "release_date": "2022-06", "status": "全球 Merge #1", "desc": "豪门八卦 + 餐厅合成，单月流水超 3000 万美元"},
            {"name": "Seaside Escape (海滨消消乐)", "icon": "🏖️", "release_date": "2022-11", "status": "全球畅销榜前列", "desc": "海岛度假村修复 + 物品订单合成"}
        ],
        "new_games": [
            {"name": "Chef Merge: Bistro Story", "icon": "🍳", "release_date": "2025-03", "status": "高买量扩量中", "desc": "主打美食烹饪与环球老街复兴的二合新旗舰"}
        ],
        "upcoming_games": [
            {"name": "Merge Manor Detective (暂定名)", "icon": "🕵️‍♀️", "expected_date": "2026 Q4", "status": "测试预约中", "desc": "悬疑侦探推理解谜 + 豪门合成沉浸式剧情"}
        ]
    },
    {
        "id": "popmart_boke",
        "name": "波克城市 (Pop Mart / Boke)",
        "region": "china",
        "country": "中国 🇨🇳",
        "category": "方块消除大厂 (Tile Match)",
        "desc": "早期凭《宾果消消消》起家，近年来在海外通过《Tile Master》系列在方块消除领域占据巨大份额。",
        "published_games": [
            {"name": "Tile Master", "icon": "🧩", "release_date": "2020-06", "status": "数亿下载", "desc": "3重方块匹配消消乐开山之作"},
            {"name": "Match Tile 3D: Triple Puzzle", "icon": "🀄", "release_date": "2021-08", "status": "出海主力", "desc": "3D麻将图案三连消除"}
        ],
        "new_games": [
            {"name": "Tile Blossom Garden", "icon": "🌸", "release_date": "2025-01", "status": "女性榜单黑马", "desc": "国风唯美花卉收集与连连看消除"}
        ],
        "upcoming_games": [
            {"name": "Tile Tycoon: City Builder", "icon": "🏙️", "expected_date": "2026 Q4", "status": "菲律宾/马来西亚软发射", "desc": "方块消除 + 模拟城市经营大外围"}
        ]
    },
    {
        "id": "three_seven",
        "name": "三七互娱 (37 Interactive)",
        "region": "china",
        "country": "中国 🇨🇳",
        "category": "重度融合开创者 (Match-3 + SLG)",
        "desc": "凭《Puzzles & Survival》（三消+SLG）开创了重度融合流派，用休闲消除外壳吸引欧美玩家。",
        "published_games": [
            {"name": "Puzzles & Survival", "icon": "🧟", "release_date": "2020-08", "status": "累计流水超百亿", "desc": "末日三消 + SLG 策略融合标杆"},
            {"name": "Puzzles & Chaos: Frozen Castle", "icon": "🧊", "release_date": "2023-09", "status": "长青营收", "desc": "冰雪奇幻题材三消 SLG"}
        ],
        "new_games": [
            {"name": "Puzzles & Conquest: Dragon War", "icon": "🐉", "release_date": "2024-12", "status": "欧美宣发爆推", "desc": "魔幻驯龙三消策略"}
        ],
        "upcoming_games": [
            {"name": "Project M3: Mech Wars (暂定名)", "icon": "🤖", "expected_date": "2026 Q4", "status": "欧美全球预预约", "desc": "赛博机甲题材三消 + 基地建设融合大作"}
        ]
    },
    {
        "id": "river_game",
        "name": "江娱互动 (River Game)",
        "region": "china",
        "country": "中国 🇨🇳",
        "category": "合成SLG代表 (Merge + Strategy)",
        "desc": "虽然以策略见长，但其爆款《Top War》（口袋兵团）本质是利用“合成（Merge）”玩法作为核心成长机制。",
        "published_games": [
            {"name": "Top War: Battle Game (口袋兵团)", "icon": "🪖", "release_date": "2019-12", "status": "全球累积破10亿刀", "desc": "拖拽士兵与建筑物即时合成升级的合并 SLG"},
            {"name": "Top Heroes", "icon": "🗡️", "release_date": "2024-01", "status": "畅销榜黑马", "desc": "英雄划屏合成与冒险小队建造"}
        ],
        "new_games": [
            {"name": "Merge Survival: Wasteland", "icon": "☣️", "release_date": "2025-05", "status": "出海飙升榜", "desc": "废土生存与基地设施合成升级"}
        ],
        "upcoming_games": [
            {"name": "Top Galaxy: Fleet Merge", "icon": "🚀", "expected_date": "2026 Q4", "status": "海外软发测数据中", "desc": "星际战舰拖拽合成与银河建造"}
        ]
    },
    {
        "id": "magic_tavern",
        "name": "麦吉太文 (Magic Tavern)",
        "region": "china",
        "country": "中国 🇨🇳",
        "category": "时尚美妆三消颠覆者",
        "desc": "代表作《Project Makeover》，将“三消 + 时尚换装 + 房屋改造”完美融合，一度颠覆欧美市场。",
        "published_games": [
            {"name": "Project Makeover", "icon": "💄", "release_date": "2020-11", "status": "全球爆款", "desc": "素人改造 + 服装美妆 + 室内设计三消巨作"},
            {"name": "Matchington Mansion", "icon": "🏡", "release_date": "2017-10", "status": "老牌经典", "desc": "老宅大逃亡与三消装修"}
        ],
        "new_games": [
            {"name": "Makeover Stories", "icon": "👗", "release_date": "2024-10", "status": "高买量长青", "desc": "好莱坞明星剧组换装与三消挑战"}
        ],
        "upcoming_games": [
            {"name": "Project Style Town", "icon": "👠", "expected_date": "2026 Q4", "status": "欧美全球预预约", "desc": "时尚街区建设 + 服饰合成换装新品"}
        ]
    },

    # --- 欧美老牌及跨国巨头 ---
    {
        "id": "king",
        "name": "King (英国 / 动视暴雪)",
        "region": "western",
        "country": "英国 🇬🇧",
        "category": "三消宗师 (Match-3 Master)",
        "desc": "消除类手游的宗师级企业，《Candy Crush Saga》（糖果传奇）至今仍是全球日活和营收的奇迹。",
        "published_games": [
            {"name": "Candy Crush Saga", "icon": "🍬", "release_date": "2012-11", "status": "日活与流水奇迹", "desc": "全球累计收入突破 200 亿美元的三消宗师"},
            {"name": "Candy Crush Soda Saga", "icon": "🥤", "release_date": "2014-10", "status": "长青高收益", "desc": "汽水与果冻机制经典衍生作品"},
            {"name": "Farm Heroes Saga", "icon": "🚜", "release_date": "2013-03", "status": "老牌常青树", "desc": "农场作物连连看"}
        ],
        "new_games": [
            {"name": "Candy Crush 3D Match", "icon": "🍭", "release_date": "2025-02", "status": "全球推广中", "desc": "糖果传奇官方 3D 物品消除衍生作"}
        ],
        "upcoming_games": [
            {"name": "Candy Crush Adventures", "icon": "🗺️", "expected_date": "2026 Q4", "status": "英国/加拿大封闭测试", "desc": "带外围剧情地图探险与公会做任务的新一代糖果传奇"}
        ]
    },
    {
        "id": "playrix",
        "name": "Playrix (爱尔兰)",
        "region": "western",
        "country": "爱尔兰 🇮🇪",
        "category": "梦幻装扮鼻祖 (Scapes Series)",
        "desc": "开创了“梦幻系列”（《Gardenscapes》、《Homescapes》），将三消与叙事装扮完美结合。",
        "published_games": [
            {"name": "Gardenscapes (梦幻花园)", "icon": "🌷", "release_date": "2016-08", "status": "叙事三消鼻祖", "desc": "管家奥斯汀与花园修复剧情三消"},
            {"name": "Homescapes (梦幻家园)", "icon": "🏠", "release_date": "2017-09", "status": "全球顶级畅销", "desc": "豪宅室内装修与大逃亡买量副玩法"},
            {"name": "Township (梦想小镇)", "icon": "🌾", "release_date": "2013-10", "status": "模拟经营霸主", "desc": "农场小镇建造与消除副副本"}
        ],
        "new_games": [
            {"name": "Mystery Scapes", "icon": "🔍", "release_date": "2024-11", "status": "高增长黑马", "desc": "神秘悬疑古堡寻物与三消装扮"}
        ],
        "upcoming_games": [
            {"name": "Gardenscapes Merge (暂定名)", "icon": "🌺", "expected_date": "2026 Q4", "status": "内部测试", "desc": "经典梦幻花园 IP 转向二合 (Merge-2) 棋盘合成"}
        ]
    },
    {
        "id": "scopely",
        "name": "Scopely (美国 / 萨特Savvy)",
        "region": "western",
        "country": "美国 🇺🇸",
        "category": "强社交博弈与休闲新王",
        "desc": "通过《Monopoly GO!》和《Yahtzee with Buddies》将强社交博弈融入轻度休闲，买量与商业化实力极强。",
        "published_games": [
            {"name": "Monopoly GO!", "icon": "🎲", "release_date": "2023-04", "status": "刷新历史增长纪录", "desc": "上线一年打破全球游戏收入增速纪录，狂揽超 30 亿美金"},
            {"name": "Yahtzee with Buddies", "icon": "🎯", "release_date": "2015-11", "status": "长效高留存", "desc": "经典掷骰子掷骰棋盘社交"}
        ],
        "new_games": [
            {"name": "Bingo GO!", "icon": "🎱", "release_date": "2025-01", "status": "欧美急速升榜", "desc": "融入 Monopoly GO 社交拆家机制的全新宾果游戏"}
        ],
        "upcoming_games": [
            {"name": "Project Board Legends", "icon": "♟️", "expected_date": "2026 Q4", "status": "预预约开测", "desc": "大富翁 + 卡牌桌游强社交即时竞技"}
        ]
    },
    {
        "id": "zynga",
        "name": "Zynga (美国 / Take-Two)",
        "region": "western",
        "country": "美国 🇺🇸",
        "category": "合并益智与农场巨头 (Peak/Gram母公司)",
        "desc": "Peak Games 的母公司。除了 Peak 外，旗下还拥有 Gram Games、Rollic 等超休闲/合并益智工作室。",
        "published_games": [
            {"name": "Merge Dragons!", "icon": "🐉", "release_date": "2017-06", "status": "三合 (Merge-3) 鼻祖", "desc": "Gram Games 打造的三合奇幻巨作"},
            {"name": "Toon Blast (Peak Games)", "icon": "🐻", "release_date": "2017-03", "status": "点消 (Collapse) 巨头", "desc": "极简点消与卡通战队积分赛"},
            {"name": "Toy Blast (Peak Games)", "icon": "🧸", "release_date": "2015-01", "status": "经典老牌", "desc": "玩具消除与闯关"}
        ],
        "new_games": [
            {"name": "Merge Gardens (Re-launch)", "icon": "🏡", "release_date": "2024-09", "status": "流水大幅飙升", "desc": "结合三合与老宅重修的大改版重发"}
        ],
        "upcoming_games": [
            {"name": "FarmVille Merge Tales", "icon": "🌽", "expected_date": "2026 Q4", "status": "北美试软", "desc": "FarmVille 农场 IP 融合二合合成与动物养成"}
        ]
    },
    {
        "id": "applovin_lion",
        "name": "AppLovin / Lion Studios",
        "region": "western",
        "country": "美国 🇺🇸",
        "category": "买量算法与益智爆款厂",
        "desc": "作为移动广告巨头，旗下的游戏工作室利用算法和数据，推出了大量益智买量爆款。",
        "published_games": [
            {"name": "Save the Doge", "icon": "🐶", "release_date": "2022-07", "status": "全网爆款副玩法", "desc": "划线防蜜蜂咬狗头买量神作"},
            {"name": "Match 3D Triple Puzzle", "icon": "🧩", "release_date": "2021-02", "status": "多国下载前列", "desc": "算法驱动的高 ROI 3D 物品消除"}
        ],
        "new_games": [
            {"name": "Screw Jam 3D", "icon": "🔩", "release_date": "2024-12", "status": "螺丝拧固爆款", "desc": "拧螺丝彩色盒分类消除（全网爆火新子品类）"}
        ],
        "upcoming_games": [
            {"name": "Sort & Jam 3D", "icon": "📦", "expected_date": "2026 Q4", "status": "买量投放测试", "desc": "物理杂货整理 + 螺丝解密双重买量机制"}
        ]
    },
    {
        "id": "rovio",
        "name": "Rovio (芬兰 / 世嘉旗下)",
        "region": "western",
        "country": "芬兰 🇫🇮",
        "category": "怒鸟IP与物理弹射",
        "desc": "《愤怒的小鸟》母公司，虽以物理弹射起家，但近年推出了多款小鸟 IP 衍生三消与合并游戏。",
        "published_games": [
            {"name": "Angry Birds Dream Blast", "icon": "🐤", "release_date": "2019-01", "status": "泡泡物理消除巨作", "desc": "物理气泡碰撞与泡泡消除"},
            {"name": "Angry Birds 2", "icon": "🏹", "release_date": "2015-07", "status": "经典弹射", "desc": "经典愤怒的小鸟关卡弹射"}
        ],
        "new_games": [
            {"name": "Angry Birds Match 3D", "icon": "🐥", "release_date": "2025-01", "status": "新IP衍生试发", "desc": "怒鸟角色 3D 收集与消消乐"}
        ],
        "upcoming_games": [
            {"name": "Angry Birds Island Merge", "icon": "🏝️", "expected_date": "2026 Q4", "status": "芬兰/瑞典软发射", "desc": "小鸟大作战 + 猪猪岛二合合成"}
        ]
    },
    {
        "id": "wooga",
        "name": "Wooga (德国 / Playtika旗下)",
        "region": "western",
        "country": "德国 🇩🇪",
        "category": "剧情寻物益智第一 (Hidden Object)",
        "desc": "全球剧情寻物益智（Hidden Object）第一，代表作《June's Journey》深受欧美高龄高付费女性喜爱。",
        "published_games": [
            {"name": "June's Journey (寻物记)", "icon": "🕵️", "release_date": "2017-10", "status": "寻物类全球 #1", "desc": "20世纪20年代名媛复古探案与庄园装饰，高 ARPPU 极高粘性"},
            {"name": "Pearl's Peril", "icon": "💎", "release_date": "2013-03", "status": "经典老牌探案", "desc": "复古寻物解谜与海岛设计"}
        ],
        "new_games": [
            {"name": "Ghost Detective: Hidden Clues", "icon": "👻", "release_date": "2024-08", "status": "好评稳定增长", "desc": "超自然灵异侦探寻物"}
        ],
        "upcoming_games": [
            {"name": "June's Estate Merge", "icon": "🏰", "expected_date": "2026 Q4", "status": "欧洲预预约", "desc": "June's Journey 顶级 IP 结合二合 (Merge-2) 棋盘复原"}
        ]
    },
    {
        "id": "tactile_games",
        "name": "Tactile Games (丹麦)",
        "region": "western",
        "country": "丹麦 🇩🇰",
        "category": "高质感女性向三消 (Lily's Garden)",
        "desc": "高质感女性向三消代表，代表作《Lily's Garden》，其广告剧情营销在业内被广泛模仿。",
        "published_games": [
            {"name": "Lily's Garden", "icon": "🌻", "release_date": "2019-02", "status": "营销剧情标杆", "desc": "莉莉的花园修复与反转八卦剧情广告鼻祖"},
            {"name": "Penny's Pursuit", "icon": "🐕", "release_date": "2021-05", "status": "长青运营", "desc": "探险环球求生与三消"}
        ],
        "new_games": [
            {"name": "Makeover Match", "icon": "💄", "release_date": "2024-06", "status": "高买量推广", "desc": "时尚改造与剧情装扮消除"}
        ],
        "upcoming_games": [
            {"name": "Lily's Secret Manor", "icon": "🔐", "expected_date": "2026 Q4", "status": "丹麦/荷兰封测", "desc": "莉莉系列最新二合合成 (Merge-2) 与秘密庄园解谜"}
        ]
    },

    # --- 日韩及其他地区先锋 ---
    {
        "id": "line_corp",
        "name": "LINE Corporation (日韩)",
        "region": "asia",
        "country": "日本 🇯🇵 / 韩国 🇰🇷",
        "category": "IP泡泡龙与益智消除",
        "desc": "凭借《LINE Puzzle TanTan》、《LINE Bubble 2》等，利用 LINE 家族极具亲和力的角色垄断亚洲泡泡龙与益智消除市场。",
        "published_games": [
            {"name": "LINE Bubble 2", "icon": "🐤", "release_date": "2015-04", "status": "亚洲泡泡龙 #1", "desc": "LINE 布朗熊与可妮兔泡泡发射消除"},
            {"name": "LINE POP2", "icon": "🐻", "release_date": "2014-10", "status": "日本常青树", "desc": "六角形三消方块匹配"}
        ],
        "new_games": [
            {"name": "LINE Chef & Merge", "icon": "🍱", "release_date": "2024-11", "status": "日韩热门榜前列", "desc": "美食烹饪结合 LINE 角色二合合成"}
        ],
        "upcoming_games": [
            {"name": "LINE Friends Puzzle Town", "icon": "🏡", "expected_date": "2026 Q4", "status": "日韩地区预预约中", "desc": "LINE Friends 家族虚拟城镇建造与消除"}
        ]
    },
    {
        "id": "amanotes_vng",
        "name": "Amanotes / VNG Games (越南)",
        "region": "asia",
        "country": "越南 🇻🇳",
        "category": "音乐益智与东南亚巨头",
        "desc": "Amanotes 是全球休闲音乐益智（Magic Tiles 3）的超级大厂；VNG 则通过收购和自研在东南亚复制消除爆款。",
        "published_games": [
            {"name": "Magic Tiles 3: Piano Game", "icon": "🎹", "release_date": "2017-02", "status": "全球数亿下载", "desc": "全球第一音乐节奏消除小游戏"},
            {"name": "Tiles Hop: EDM Rush!", "icon": "🎶", "release_date": "2018-09", "status": "高下载量", "desc": "电音跳跃小球与音乐关卡"}
        ],
        "new_games": [
            {"name": "Duet Cats: Cute Cat Music", "icon": "🐱", "release_date": "2023-08", "status": "萌宠爆款", "desc": "双猫合奏萌宠喂食音乐消除"}
        ],
        "upcoming_games": [
            {"name": "Magic Music Merge 3D", "icon": "🎵", "expected_date": "2026 Q4", "status": "东南亚软发射", "desc": "节奏音游结合 3D 物品合成休闲新品"}
        ]
    },
    {
        "id": "devsisters",
        "name": "Devsisters (韩国)",
        "region": "asia",
        "country": "韩国 🇰🇷",
        "category": "姜饼人IP与高美学消除",
        "desc": "凭借《Cookie Run》（跑跑姜饼人）IP，衍生出了多款高美学的魔女商店、姜饼人三消与益智建造游戏。",
        "published_games": [
            {"name": "Cookie Run: Kingdom", "icon": "🏰", "release_date": "2021-01", "status": "韩国国民级IP", "desc": "姜饼人王国建造 + 冒险卡牌"},
            {"name": "Cookie Run: Puzzle World", "icon": "🍪", "release_date": "2020-01", "status": "经典消除", "desc": "姜饼人果冻消除与城堡设计"}
        ],
        "new_games": [
            {"name": "Cookie Run: Witch's Castle", "icon": "🧹", "release_date": "2024-03", "status": "美学大作", "desc": "魔女城堡逃脱点消 (Tap-to-Blast) 与探索"}
        ],
        "upcoming_games": [
            {"name": "Cookie Run: OvenMerge", "icon": "🔥", "expected_date": "2026 Q4", "status": "韩国预预约开测", "desc": "姜饼人烤箱烘焙二合 (Merge-2) 治愈系新品"}
        ]
    }
]


@lru_cache(maxsize=32)
def get_publisher_portfolio(publisher_id: str | None = None, region: str | None = None) -> list[dict]:
    """Retrieve filtered 20 Top Casual Game Publishers data."""
    results = CASUAL_PUBLISHERS_DATA
    if region and region != "all":
        results = [p for p in results if p["region"] == region]
    if publisher_id:
        results = [p for p in results if p["id"] == publisher_id]
    return results
