# App Store Top 30 每日分析

每天抓取 App Store 各分类下免费、付费、畅销榜前 30 名应用，保存到 SQLite，并生成 HTML + CSV 每日报告，包含排名变动、新上榜、跌出榜单、价格和评分变化。

## 支持的地区与榜单

- 北美区：美国、加拿大
- 拉美区：墨西哥、巴西、阿根廷、智利、哥伦比亚、秘鲁
- 欧洲区：英国、德国、法国、意大利、西班牙
- 中东与北非：阿联酋、沙特阿拉伯、以色列、土耳其、埃及、摩洛哥
- 东北亚区：日本、韩国、台湾、香港、澳门
- 东南亚区：新加坡、马来西亚、泰国、印度尼西亚、越南、菲律宾
- 大洋洲区：澳大利亚、新西兰
- 南亚区：印度、巴基斯坦、孟加拉国、斯里兰卡
- 非洲区：南非、尼日利亚、肯尼亚

每个国家抓取免费榜、付费榜、畅销榜，覆盖 App Store 全部一级分类，并包含游戏子分类。

地区列表、榜单类型、分类范围、并发数都可在 `appstore_top30/config.py` 中修改。

## 快速开始

环境要求：Python 3.9+，仅使用标准库，无需安装依赖。

```bash
python3 -m appstore_top30 init
python3 -m appstore_top30 run -d 2026-08-04
```

`run` 会先抓取当天数据，再生成报告。也可以分步执行：

```bash
python3 -m appstore_top30 fetch -d 2026-08-04
python3 -m appstore_top30 report -d 2026-08-04
```

常用参数：

```bash
# 只抓指定地区和榜单
python3 -m appstore_top30 fetch --regions us,japan --charts free,grossing

# 抓取少量数据用于测试
python3 -m appstore_top30 run --regions japan --charts free --top-n 5
```

## 交互式数据看板

除了每日 HTML/CSV 报告，项目还内置一个本地交互式看板：

```bash
python3 -m appstore_top30 dashboard
```

默认在 `http://127.0.0.1:8000` 打开，支持：

- 按日期、地区、国家、榜单、分类筛选
- 分类按“应用 / 游戏”大分类逐层展开，游戏下再细分动作、卡牌等子分类
- 查看榜单明细、排名变化、价格与评分
- 分类分布汇总
- 点击任意应用查看历史排名趋势
- 黑白两种主题可切换：默认浅色、深色，选择会自动保存

界面参考 Android Material Design 3 与 iOS HIG：Material 语义色、状态层、层级与圆角，配合 iOS 大标题、毛玻璃材质和分组面板，黑白主题下保持一致的设计语言。

自定义端口：

```bash
python3 -m appstore_top30 dashboard --port 9000 --no-open
```

## 输出

- 数据库：`data/appstore_top30.db`
- 报告目录：`reports/YYYY-MM-DD/`
  - `report_YYYY-MM-DD.html`：每日分析报告
  - `rankings_{country}_{chart}.csv`：完整榜单快照
  - `changes_{country}_{chart}.csv`：日环比变化
  - `summary.csv`：各国家/榜单汇总

报告包含排名变动 Top 15、新上榜 Top 15、跌出榜单 Top 15、评分变化 Top 10，以及各国家、各榜单的汇总卡片。

## 每日定时运行

项目内置 `run_daily.sh`，默认抓取当天数据并生成报告，日志写入 `logs/daily.log`。

```bash
chmod +x run_daily.sh
```

crontab 示例（每天 09:00 执行）：

```cron
0 9 * * * cd /Users/a/Develop/project/chrome && ./run_daily.sh
```

macOS 也可改用 launchd。注意 Apple 公开接口有频率限制，不建议把并发调得过高。

项目已附带 launchd 配置 `com.user.appstore-top30.plist`，默认每天 09:00 自动运行 `run_daily.sh`：

```bash
# 安装到当前用户
cp com.user.appstore-top30.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.user.appstore-top30.plist

# 查看任务状态
launchctl print gui/$(id -u)/com.user.appstore-top30

# 卸载任务
launchctl bootout gui/$(id -u)/com.user.appstore-top30
```

运行日志写入 `logs/daily.log`，launchd 自身日志在 `logs/launchd.out.log` 和 `logs/launchd.err.log`。

## GitHub Actions 云端每日采集

如果电脑不常开，可以把每日采集放到 GitHub Actions 上，由云端定时执行，每天 09:00（北京时间）自动运行：

1. 把项目推到 GitHub 仓库
2. 在 Cloudflare R2 建一个 Bucket（免费额度 10GB），创建 API Token
3. 在仓库 `Settings -> Secrets and variables -> Actions` 添加：
   - `R2_ACCESS_KEY_ID`
   - `R2_SECRET_ACCESS_KEY`
   - `R2_BUCKET`（Bucket 名称）
   - `R2_ENDPOINT`（形如 `https://<account-id>.r2.cloudflarestorage.com`）

`.github/workflows/daily.yml` 会自动：

- 每天 01:00 UTC（北京时间 09:00）跑完整 Top 30 采集
- 先把上次的 SQLite 数据库从 R2 下载下来继续追加，再上传回去，历史数据不丢失
- 把每日 HTML/CSV 报告同步到 R2
- 另外上传一份最近 30 天的报告到 GitHub Actions Artifacts

没有 R2 时工作流也能运行，但 GitHub Actions 的运行环境是临时的，历史数据库不会保留，只能拿到每天的报告文件。

### 用 Google Drive 做备份盘

如果你有 Google One，可以把 Google Drive 作为历史数据的长期备份盘。Google One 本身不能定时运行脚本，计算仍然由 GitHub Actions 完成，Drive 只负责存数据。

一次性配置：

```bash
# 本地安装 rclone
brew install rclone

# 创建名为 gdrive 的远程配置，授权 Google Drive
rclone config

# 将 rclone 配置转成 Base64，加到 GitHub Secrets，变量名 RCLONE_CONFIG_B64
base64 < ~/.config/rclone/rclone.conf
```

配置后，云端工作流每天会：

- 从 Google Drive 下载上次的 SQLite 数据库继续追加
- 抓取当天数据后，把数据库和报告上传回 `appstore-top30/data` 与 `appstore-top30/reports`

如果希望完全用 Google 生态，也可以改用 Google Cloud 的 Cloud Scheduler + Cloud Run，但 Google One 并不包含这些计算资源，需要单独的 GCP 免费额度或付费项目。

### GitHub Actions 定时没有触发时的兜底

GitHub 对个人账号的 `schedule` 触发不保证准点，也出现过整段不触发的情况；手动 `workflow_dispatch` 不受影响。仓库是公开、未归档且 workflow 为 `active` 时，一般不是配置问题，可以先用以下方式确认：

```bash
# 查看是否有 schedule 事件触发的运行
curl -sS "https://api.github.com/repos/e-hai/Appstore_Top_30/actions/runs?event=schedule"

# 查看 workflow 状态
curl -sS "https://api.github.com/repos/e-hai/Appstore_Top_30/actions/workflows/daily.yml"
```

临时补一次数据可以到仓库 `Actions -> daily-appstore-top30 -> Run workflow` 手动运行，或本地执行：

```bash
GITHUB_PAT=<你的 PAT> ./scripts/trigger_workflow.sh
```

需要创建一个 GitHub Personal Access Token，权限勾选 `workflow`。长期兜底建议用外部定时服务（如 cron-job.org、Google Apps Script 的每日触发器）每天调用同一个 `workflow_dispatch` 接口：

```text
POST https://api.github.com/repos/e-hai/Appstore_Top_30/actions/workflows/daily.yml/dispatches
Authorization: Bearer <PAT>
Content-Type: application/json

{"ref":"main"}
```

另外，公开仓库的定时工作流在 60 天没有任何运行后会被 GitHub 自动停用，需要手动去 Actions 页面重新启用。

## 数据说明

- 榜单数据来自 Apple 的 WebObjects charts 接口：`itunes.apple.com/WebObjects/MZStoreServices.woa/ws/charts?cc=...&g=...&name=...`
- 应用名称、价格、评分和评分人数来自 iTunes Lookup 接口，按国家批量查询
- 分类树来自 Apple 的 genres 接口，分类名为各国家本地化名称
- 数据为公开接口快照，可能与 App Store 客户端展示存在时差或差异，仅用于个人分析

默认配置下全量抓取约 1500 个榜单接口，并启用了全局限速（默认 4 请求/秒）和失败重试，单次完整运行约 10-20 分钟。如被 Apple 临时限流，缺失的榜单会记录到日志并在报告 CSV 中跳过。

## 测试

```bash
python3 -m unittest discover -s tests -v
```
