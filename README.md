# App Store & Google Play Top 30 全球榜单监控系统

每日自动抓取 Apple App Store 与 Google Play 全球 39 国免费榜、付费榜、畅销榜 Top 30 官方榜单数据，并提供直观交互的数据看板与开放可用的标准化 JSON API。

- 🌐 **在线数据看板**：[https://e-hai.github.io/Appstore_Top_30/](https://e-hai.github.io/Appstore_Top_30/)
- 📖 **交互式 API 开发者文档 (Swagger)**：[https://e-hai.github.io/Appstore_Top_30/api-docs.html](https://e-hai.github.io/Appstore_Top_30/api-docs.html)
- ⚙️ **OpenAPI 3.0 规范定义文件**：[https://e-hai.github.io/Appstore_Top_30/api/openapi.json](https://e-hai.github.io/Appstore_Top_30/api/openapi.json)

---

## 目录
- [一、 面板功能 (Dashboard Features)](#一-面板功能-dashboard-features)
  - [1. 双平台与全球 39 国榜单监控](#1-双平台与全球-39-国榜单监控)
  - [2. 跨天历史无缝回溯](#2-跨天历史无缝回溯)
  - [3. 榜单明细与真实排位异动](#3-榜单明细与真实排位异动)
  - [4. 交互增强与开发者产品穿透](#4-交互增强与开发者产品穿透)
  - [5. 应用多日真实排位走势图 (Trend Chart)](#5-应用多日真实排位走势图-trend-chart)
  - [6. 每日异动与品类大盘研判 (抽屉面板)](#6-每日异动与品类大盘研判-抽屉面板)
- [二、 接口功能与调用方式 (API Documentation & Usage)](#二-接口功能与调用方式-api-documentation--usage)
  - [1. 接口特性与接入说明](#1-接口特性与接入说明)
  - [2. 核心 API 端点与规范](#2-核心-api-端点与规范)
    - [① 可用历史日期列表 (`/api/dates.json`)](#-可用历史日期列表-apidatesjson)
    - [② 商店元数据定义 (`/api/meta_{store}.json`)](#-商店元数据定义-apimeta_storejson)
    - [③ Top 30 排行数据 (`/api/rankings/...json`)](#-top-30-排行数据-apirankingsjson)
    - [④ 每日大盘异动与统计摘要 (`/api/summary/...json`)](#-每日大盘异动与统计摘要-apisummaryjson)
    - [⑤ 应用多日排位趋势序列 (`/api/trend/...json`)](#-应用多日排位趋势序列-apitrendjson)
    - [⑥ 全网细分品类宏观趋势 (`/api/category_trends/...json`)](#-全网细分品类宏观趋势-apicategory_trendsjson)
  - [3. 多语言代码调用示例](#3-多语言代码调用示例)
- [三、 本地快速启动与自动化说明](#三-本地快速启动与自动化说明)

---

# 一、 面板功能 (Dashboard Features)

### 1. 双平台与全球 39 国榜单监控
- **双商店数据支持**：全面覆盖 **Apple App Store** 与 **Google Play Store** 官方数据源。
- **全球 39 个主流国家/地区**：
  - **北美区**：美国 (US)、加拿大 (CA)
  - **欧洲区**：英国 (GB)、德国 (DE)、法国 (FR)、意大利 (IT)、西班牙 (ES)
  - **东北亚区**：日本 (JP)、韩国 (KR)、中国香港 (HK)、中国台湾 (TW)、中国澳门 (MO)
  - **东南亚区**：新加坡 (SG)、马来西亚 (MY)、泰国 (TH)、印度尼西亚 (ID)、越南 (VN)、菲律宾 (PH)
  - **拉美区**：巴西 (BR)、墨西哥 (MX)、智利 (CL)、阿根廷 (AR)、秘鲁 (PE)、哥伦比亚 (CO)
  - **中东与北非区**：沙特阿拉伯 (SA)、阿联酋 (AE)、埃及 (EG)、土耳其 (TR)、摩洛哥 (MA)、以色列 (IL)
  - **南亚区**：印度 (IN)、巴基斯坦 (PK)、孟加拉国 (BD)、斯里兰卡 (LK)
  - **大洋洲区**：澳大利亚 (AU)、新西兰 (NZ)
  - **非洲区**：南非 (ZA)、尼日利亚 (NG)、肯尼亚 (KE)
- **三大榜单类型**：畅销榜 (Top Grossing)、免费榜 (Top Free)、付费榜 (Top Paid)。
- **品类维度切换**：支持总榜（Overall）与主要细分品类（如 iOS 游戏总榜 `6014`、Google Play 游戏总榜 `GAME` 及各子品类）。

### 2. 跨天历史无缝回溯
- 收录并支持从 `2026-08-04` 至今的 **87+ 天历史数据**。
- 顶部日期选择器秒级切换，方便复盘任意历史时刻的竞争格局。

### 3. 榜单明细与真实排位异动
- **排位升降角标**：直观展示应用排名较昨日真实数学位次差（`▲ +N` 排名跃升、`▼ -N` 排名下滑、`NEW` 首次新上榜、`—` 排名保持不变）。
- **完整元数据**：展示应用图标、应用全名、分类品类、开发者主体、评分星级、评分人数、价格与本地币种。

### 4. 交互增强与开发者产品穿透
- **实时即时模糊搜索**：在当前榜单中输入应用名或开发者名称，列表瞬间响应过滤。
- **自适应布局切换**：右上角提供「↔ 宽度自适应」与「📋 双栏对照」一键切换，适应不同分辨率屏幕。
- **开发者产品矩阵穿透**：点击榜单中任意开发者的名字，右侧抽屉即可联动展示该开发者在当前市场上架并入榜的所有关联产品。
- **深色/浅色主题**：自适应高对比度黑白双主题。

### 5. 应用多日真实排位走势图 (Trend Chart)
- **真实时间序列**：根据每日真实官方排位绘制走势曲线（数值越小排位越靠前），绝无虚构估算。
- **多产品自由对比**：
  - 默认展示当前榜单 Top 5 应用的大盘走势。
  - 支持在左侧榜单中**任意勾选其他 App**，走势图将实时动态叠加该产品的轨迹曲线，便于竞品排位升降对比。
  - 提供「↺ 重置 Top 5」快捷恢复按钮。

### 6. 每日异动与品类大盘研判 (抽屉面板)
点击顶部 **「📊 异动与品类大盘」** 或趋势图旁的 **「📊 异动分析」** 按钮呼出抽屉：
- **📊 每日应用排位异动榜（纯客观指标）**：
  - 🚀 **今日冲榜爆发 Top 3**：当日排名跃升幅度最大的前 3 款应用。
  - 👑 **最强留存霸榜 Top 3**：高位在榜且排位波动率最低的长青头部产品。
  - 📉 **流量回调下滑 Top 3**：当日名次下滑最明显的产品。
  - 🆕 **今日新上榜 App**：当日新进入 Top 30 的黑马产品清单。
- **📈 全网品类宏观趋势**：
  - 🚀 **最具飙升潜力品类 Top 3**：细分品类中平均名次上升最显著的品类。
  - 📉 **流量回调/衰退品类 Top 3**：平均排名走弱、大盘热度降温的品类。

---

# 二、 接口功能与调用方式 (API Documentation & Usage)

### 1. 接口特性与接入说明
- **基础 URL**：`https://e-hai.github.io/Appstore_Top_30/api/`
- **零服务器成本 & 高可用**：依托 GitHub Pages 全球 CDN 加速节点分发，抗高并发、永不宕机。
- **全量跨域支持 (CORS)**：所有接口响应头默认包含 `Access-Control-Allow-Origin: *`，Web 前端、小程序、移动客户端或后端服务均可直接发起 `GET` 请求。
- **无需鉴权**：零门槛开放访问，免 API Key / Token。
- **在线调试**：第三方开发者可通过 [Swagger UI](https://e-hai.github.io/Appstore_Top_30/api-docs.html) 直接在线发起请求与测试。

---

### 2. 核心 API 端点与规范

#### ① 可用历史日期列表 (`/api/dates.json`)
查询系统当前已收录的所有历史日期及每日的数据量概览。

- **请求方式**：`GET`
- **请求 URL**：`https://e-hai.github.io/Appstore_Top_30/api/dates.json`
- **响应示例**：
  ```json
  {
    "dates": [
      {
        "date": "2026-10-30",
        "countries": 39,
        "snapshots": 10980,
        "entries": 282932,
        "stores": {
          "app_store": { "countries": 39, "snapshots": 5382, "entries": 143465 },
          "play": { "countries": 39, "snapshots": 5598, "entries": 139467 }
        }
      }
    ]
  }
  ```

---

#### ② 商店元数据定义 (`/api/meta_{store}.json`)
获取指定商店下支持的地区分组、国家代码字典与分类清单。

- **请求方式**：`GET`
- **URL 模板**：`https://e-hai.github.io/Appstore_Top_30/api/meta_{store}.json`
- **路径参数**：
  - `store`：应用商店代号，可选 `app_store` 或 `play`。
- **请求示例**：
  `https://e-hai.github.io/Appstore_Top_30/api/meta_app_store.json`
- **响应结构**：包含 `regions`（地区及对应国家代码列表）和 `genres`（全量分类 ID 与分类名称）。

---

#### ③ Top 30 排行数据 (`/api/rankings/...json`)
获取指定国家、榜单、日期维度的 Top 30 完整排行及排位变动。

- **请求方式**：`GET`
- **总榜 URL 模板**：
  `https://e-hai.github.io/Appstore_Top_30/api/rankings/{store}_{country}_{chart}_{date}.json`
- **分类榜 URL 模板**（如游戏总榜）：
  `https://e-hai.github.io/Appstore_Top_30/api/rankings/{store}_{country}_{chart}_{genre_id}_{date}.json`
- **路径参数说明**：
  - `store`：`app_store`（iOS）或 `play`（Google Play）。
  - `country`：ISO 两位小写国家代码，如 `us`, `jp`, `kr`, `gb`, `de` 等。
  - `chart`：榜单代号，`grossing`（畅销榜）、`free`（免费榜）、`paid`（付费榜）。
  - `genre_id`（可选）：分类 ID。iOS 游戏总榜为 `6014`；Google Play 游戏总榜为 `GAME`。
  - `date`：数据日期，格式为 `YYYY-MM-DD`（如 `2026-10-30`）。
- **请求示例**：
  - 查询 iOS 美国畅销总榜：
    `https://e-hai.github.io/Appstore_Top_30/api/rankings/app_store_us_grossing_2026-10-30.json`
  - 查询 iOS 日本游戏畅销榜：
    `https://e-hai.github.io/Appstore_Top_30/api/rankings/app_store_jp_grossing_6014_2026-10-30.json`
- **响应核心字段说明**：
  ```json
  {
    "date": "2026-10-30",
    "country": "us",
    "chart": "grossing",
    "store": "app_store",
    "rows": [
      {
        "rank_no": 1,
        "prev_rank": 1,
        "rank_change": 0,
        "status": "same",
        "app_id": "1195621598",
        "name": "Roblox",
        "developer": "Roblox Corporation",
        "genre_name": "游戏",
        "rating": 4.5,
        "rating_count": 8200000,
        "price_amount": 0.0,
        "currency": "USD"
      }
    ],
    "quant_summary": {
      "avg_volatility": "1.20",
      "spiking_count": 3,
      "stable_count": 3,
      "new_count": 1
    },
    "market_attribution": {
      "exec_summary": "今日大盘异动概况...",
      "rising_apps": [...],
      "falling_apps": [...],
      "stable_apps": [...],
      "new_apps": [...]
    }
  }
  ```

---

#### ④ 每日大盘异动与统计摘要 (`/api/summary/...json`)
查询全天各个国家各榜单的宏观异动指标汇总（新晋上榜数、上升数、下降数、平稳数）。

- **请求方式**：`GET`
- **URL 模板**：`https://e-hai.github.io/Appstore_Top_30/api/summary/{store}_{date}.json`
- **请求示例**：
  `https://e-hai.github.io/Appstore_Top_30/api/summary/app_store_2026-10-30.json`

---

#### ⑤ 应用多日排位趋势序列 (`/api/trend/...json`)
获取指定国家和榜单下，核心在榜应用跨越多个历史日期的真实排名走势点序列。

- **请求方式**：`GET`
- **URL 模板**：`https://e-hai.github.io/Appstore_Top_30/api/trend/{store}_{country}_{chart}.json`
- **请求示例**：
  `https://e-hai.github.io/Appstore_Top_30/api/trend/app_store_us_grossing.json`
- **响应示例**：
  ```json
  {
    "store": "app_store",
    "country": "us",
    "chart": "grossing",
    "trends": {
      "1195621598": [
        { "date": "2026-10-28", "best_rank": 1, "name": "Roblox" },
        { "date": "2026-10-29", "best_rank": 2, "name": "Roblox" },
        { "date": "2026-10-30", "best_rank": 1, "name": "Roblox" }
      ]
    }
  }
  ```

---

#### ⑥ 全网细分品类宏观趋势 (`/api/category_trends/...json`)
获取指定国家细分品类的热度指数与平均排位升降变化。

- **请求方式**：`GET`
- **URL 模板**：`https://e-hai.github.io/Appstore_Top_30/api/category_trends/{store}_{country}.json`
- **请求示例**：
  `https://e-hai.github.io/Appstore_Top_30/api/category_trends/app_store_us.json`

---

### 3. 多语言代码调用示例

#### cURL 命令行
```bash
# 获取最新可用日期列表
curl -s "https://e-hai.github.io/Appstore_Top_30/api/dates.json"

# 获取 2026-10-30 美国 iOS 畅销榜 Top 30
curl -s "https://e-hai.github.io/Appstore_Top_30/api/rankings/app_store_us_grossing_2026-10-30.json"
```

#### Python 示例
```python
import requests

# 1. 查询可用日期
dates_url = "https://e-hai.github.io/Appstore_Top_30/api/dates.json"
dates_res = requests.get(dates_url).json()
latest_date = dates_res["dates"][-1]["date"]
print(f"最新收录日期: {latest_date}")

# 2. 查询指定榜单数据 (如美国 App Store 畅销榜)
rankings_url = f"https://e-hai.github.io/Appstore_Top_30/api/rankings/app_store_us_grossing_{latest_date}.json"
data = requests.get(rankings_url).json()

print(f"\n=== {data['country'].upper()} 畅销榜 Top 5 ===")
for item in data["rows"][:5]:
    change = f"▲+{item['rank_change']}" if item["rank_change"] > 0 else (f"▼{item['rank_change']}" if item["rank_change"] < 0 else "—")
    print(f"#{item['rank_no']} [{change}] {item['name']} ({item['developer']})")
```

#### JavaScript / TypeScript (浏览器前端 & Node.js 18+)
```javascript
async function fetchTopApps() {
  // 1. 获取最新日期
  const datesRes = await fetch("https://e-hai.github.io/Appstore_Top_30/api/dates.json");
  const datesData = await datesRes.json();
  const latestDate = datesData.dates.slice(-1)[0].date;

  // 2. 拉取日本游戏榜畅销 Top 30
  const url = `https://e-hai.github.io/Appstore_Top_30/api/rankings/app_store_jp_grossing_6014_${latestDate}.json`;
  const response = await fetch(url);
  const json = await response.json();

  console.log("今日异动总结:", json.market_attribution.exec_summary);
  json.rows.slice(0, 10).forEach(app => {
    console.log(`#${app.rank_no} ${app.name} - ${app.developer}`);
  });
}

fetchTopApps();
```

---

# 三、 本地快速启动与自动化说明

### 1. 本地一键启动 Web 服务
本项目仅使用 Python 标准库，无任何第三方 pip 依赖：

```bash
# 方式 1：一键运行启动脚本
./start.sh

# 方式 2：使用标准 Python 模块启动
python3 -m appstore_top30 dashboard --host 0.0.0.0 --port 8080
```
启动后在浏览器打开 `http://localhost:8080` 即可浏览。

### 2. 每日数据自动化更新 (CI/CD)
项目通过根目录下的 `.github/workflows/daily_update.yml` 配置了每日定时自动化运行流水线：
- **触发时间**：每天 UTC 00:00（北京时间 08:00）。
- **执行流程**：自动拉取最新官方榜单数据 -> 执行排位差值比对 -> 自动生成全套静态 JSON API -> 部署至 GitHub Pages。
- 全程**无需自建服务器或常驻进程**，完全依托云端完成。
