"""Category Trend Intelligence & Commercial Feasibility Report Generator."""

from functools import lru_cache


@lru_cache(maxsize=16)
def get_merge_games_report() -> dict:
    return {
        "category": "合成类游戏 (Merge Games)",
        "timeframe": "2026 Q1 - Q3 至今",
        "market_performance": {
            "surge_summary": "自 2026 年第一季度以来，合成类游戏（Merge 2 / Merge 3）在 iOS App Store 与 Google Play 全球游戏免费榜与畅销榜中的席位增幅超过 38%。代表产品（如 Gossip Harbor、Travel Town、Merge Mansion、Merge Gardens）月流水相继突破数千万美元大关。",
            "top_markets": [
                {"country": "🇺🇸 美国 (US)", "share": "42%", "notes": "全球第一大营收来源，女性中重度玩家比例高，付费意愿强"},
                {"country": "🇩🇪 德国 (DE) / 🇬🇧 英国 (UK)", "share": "22%", "notes": "欧洲核心高 ARPU 市场，长期留存表现突出"},
                {"country": "🇯🇵 日本 (JP) / 🇰🇷 韩国 (KR)", "share": "15%", "notes": "东亚增速最快，通过轻度剧情与萌系画风快速渗透"},
                {"country": "其他（澳大利亚/加拿大/东南亚）", "share": "21%", "notes": "稳步增长的辅助流失与买量扩容市场"}
            ],
            "revenue_benchmark": "头部 Merge 2 游戏单月全球流水处于 1,500万 - 3,500万美元 区间，30日留存率 (D30 Retention) 可达 8%-12%，ARPPU 处于 $25-$45。"
        },
        "growth_drivers": [
            {
                "title": "1. 极低门槛 + 高频正向反馈",
                "detail": "滑动棋盘两两合成的“二合 (Merge 2)”玩法操作极简，认知负荷极低，能给玩家提供秒级的解压感与正向心理反馈。"
            },
            {
                "title": "2. 剧情/装修副玩法（Meta-Game）深度结合",
                "detail": "融合了“狗血八卦剧情”或“老宅装修解锁”，利用悬念故事线（如“老公出轨/破产修大宅”）大幅拉升女性玩家的 D7/D30 长期留存。"
            },
            {
                "title": "3. 三消 (Match-3) 大盘受众的吸纳转移",
                "detail": "传统三消（如 Candy Crush）玩家出现审美疲劳，Merge 游戏凭借更有掌控感的棋盘空间管理与长线经营线，吸纳了大量原三消高价值用户。"
            }
        ],
        "monetization_model": {
            "model_type": "混合变现 (Hybrid Monetization: IAP 85% + IAA 15%)",
            "iap_components": [
                "体力/能量购买（Energy Refill）：核心消耗项，体力耗尽是触发付费的第一卡点",
                "棋盘空间与格子扩展（Board Expansion）：棋盘满格时购买额外存储位",
                "道具/高级生成器（Toolbox & Speed-up）：加速高阶物品合成周期",
                "赛季通行证（Battle Pass / Event Pass）：限时主题活动专属奖励线"
            ],
            "iaa_components": [
                "激励视频广告（Rewarded Ads）：观看广告获得 +15 体力或清除气泡（Bubble Pop）",
                "插屏广告（仅在中低 ARPU 地区少量开启，避免损害留存）"
            ]
        },
        "core_gameplay_loop": "棋盘合成 (Merge Grid) ──> 订单交付 (Task Order) ──> 获得代币/星币 (Currency) ──> 解锁剧情/装修大宅 (Meta Story & Decoration) ──> 开启限时赛季活动 (LiveOps Event)",
        "rd_investment_recommendation": {
            "verdict": "💡 建议跟进，但需采取【差异化题材 + 快速敏捷试软】策略，避免硬碰硬。",
            "team_requirement": "核心团队 8-15 人（1个数值策划、2个主美术/动画、3个客户端、2个后端、1个买量/LiveOps 运营），研发周期约 4-6 个月。",
            "differentiation_paths": [
                "题材差异化：避开同质化的“老宅装修/抓奸”，尝试“美食餐厅/奇幻探险/宠物养殖/侦探解谜”。",
                "数值与商业化微创新：引入限时积分赛 (Leaderboard) 与公会互送体力机制 (Guild System)。",
                "买量素材驱动：将热门副玩法（短视频热点）作为副副本直接植入游戏前 10 分钟体验。"
            ],
            "key_risks": [
                "买量成本 (CPI) 攀升：北美 iOS CPI 较 2025 年上升约 25%，必须保证 LTV(D90) > CPI 才能实现回收。",
                "数值平衡与内容消耗极快：需要准备至少 6 个月以上的剧情与限时活动关卡储备。"
            ]
        }
    }
