# App Store Top 30 每日分析

每天抓取 App Store 与 Google Play 各分类下免费、付费、畅销榜前 30 名应用，保存到 SQLite，并生成 HTML + CSV 每日报告。

## 功能

- 覆盖 39 个国家，按 9 个地区包组织：北美区、拉美区、欧洲区、中东与北非、东北亚区、东南亚区、大洋洲区、南亚区、非洲区
- App Store 覆盖全部一级分类和游戏子分类，Google Play 覆盖全部应用分类和游戏子分类
- 数据均来自官方公开来源：Apple WebObjects charts、iTunes Lookup 和 Google Play 官方榜单页面
- 每日报告包含排名变动、新上榜、跌出榜单、价格与评分变化
- 内置本地交互式看板，支持切换 App Store / Google Play、按日期、地区、国家、榜单、分类筛选，查看历史排名趋势，切换黑白主题
- 支持 GitHub Actions 云端定时采集，可用 Google Drive 或 Cloudflare R2 保存历史数据
- 仅使用 Python 标准库，无需安装第三方依赖

## 一键快捷启动 (推荐)

仅需执行一行命令即可自动完成检测、依赖处理、数据初始化并启动 Web 服务：

```bash
# 首次安装与快速启动
./setup.sh

# 以后日常一键启动看板
./start.sh
```

## 手动安装与运行

环境要求：Python 3.8+（无需任何第三方 pip 依赖，纯标准库）。

```bash
git clone https://github.com/e-hai/Appstore_Top_30.git
cd Appstore_Top_30
python3 -m appstore_top30 init
python3 -m appstore_top30 dashboard --host 0.0.0.0 --port 8080
```
