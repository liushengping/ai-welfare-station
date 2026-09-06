# AI 厂商福利情报站

纯静态单页站点：**🔴 雷达播报**（watcher 抓到的新活动自动上榜）、**鸡蛋榜**（谁在送福利）、**套餐榜**（订阅横评）、**模型榜**（API 每百万 tokens 价格）、**已失效墓场**（别再白跑）。
外加 **🔔 福利雷达**：15 分钟轮询 15 个信息源，新活动推送到 Windows 弹窗 / 手机。

## 使用

- 推荐 `python -m http.server 8765` 后访问 <http://127.0.0.1:8765/index.html>（雷达播报和「安装到手机」需要 http(s) 环境）；直接双击 `index.html` 也能看三张榜，仅雷达流受限。
- **装到手机当 App 用（PWA）**：把本目录部署到任一 https 静态托管（GitHub Pages / 自有服务器 / Cloudflare Pages），手机浏览器访问后「添加到主屏幕」即可全屏运行，配合 ntfy 推送就是完整的 app 体验。
- 支持国内/国际筛选、关键词搜索、模型榜表头排序、截止日自动倒计时。

## 🔔 福利雷达（第一时间推送）

`watcher/` 目录是一个零依赖监控器（Python 标准库 + 系统 curl）：

```
cd watcher
python watch.py             # 抓一轮，新活动推送 + 写入 ../feed.json
python watch.py --test-push # 测试推送通道
python watch.py --seed      # 把当前内容标记为已见（换源后用，防轰炸）
```

- **监控源 15 个**（`sources.json`，2026-09-06 定稿），覆盖策略「官方直盯 + 社区首发兜底」：
  - **官方直盯（新增即报或关键词过滤）**：智谱 BigModel 活动文档、阿里百炼免费额度页、百度千帆额度文档、腾讯 TokenHub 产品页、硅基流动更新公告、ZCode 官网、OpenAI News RSS、GitHub Changelog、Google AI 博客、火山方舟。
  - **社区首发（活动类比官方页更快）**：linux.do 福利羊毛板块 RSS + 全站 latest 兜底（Cloudflare 间歇性拦截，脚本自动重试）；TG 白嫖分享社（pgkj666）、TG 线报台（XianBaoTai）经 `rsshub.rssforever.com` 镜像中转绕开封锁；小众软件论坛。
  - **说明**：DeepSeek / Kimi / MiniMax / 美团 LongCat 的官网为 JS 渲染或无公告区，无法无头抓取，其活动靠 linux.do + TG 社区源首发覆盖（实际速度也更快）。
- **关键词**（`config.json`）：免费/赠送/领取/白嫖/额度/token/credit… 可自行增删。
- **推送渠道**（`config.json` 的 `channels`）：
  - `toast` ✅ 默认开启：Windows 桌面弹窗。
  - `ntfy` ✅ 默认开启：手机装 [ntfy App](https://ntfy.sh)（iOS/Android），订阅主题 `aiwelfare-k7f2m9x4tq` 即可收推送。
  - `bark`（iOS，填你的 key）/ `serverchan`（微信 Server酱）/ `wecom_bot`（企业微信机器人）/ `dingtalk_bot`（钉钉机器人）：填 key/url 并把 `enabled` 改为 `true`。
- **防轰炸**：某源断线恢复后的积压条目只静默入库不推送；新接入的源同样先播种。
- **想要分钟级（真·实时）的做法**：轮询最快也就十几分钟一档，真正秒级靠这两招——
  1. 手机直接加入 TG 频道 [@pgkj666](https://t.me/pgkj666)（白嫖分享社）和 [@XianBaoTai](https://t.me/XianBaoTai)（线报台），活动线报是秒级推的，人肉把关速度最快；
  2. 关注「智谱AI」「ZCode」微信公众号，官方活动图文第一落点；想让它进 RSS 管道可自部署 [wewe-rss](https://github.com/cooderl/wewe-rss)（Docker，微信读书接口转 RSS）。
- **定时调度**（双轨）：
  - **本机**：ZCode 自动化「每15分钟AI福利雷达（8点-23点45）」——电脑开着时生效。
  - **云端（主力，电脑关机也推送）**：GitHub Actions 每 30 分钟（北京时间 8:00–23:30）跑 `welfare-radar.yml`，ntfy 直推手机。已验证跑通。细节：
    - `NTFY_TOPIC` 存在仓库 secret 里；state.json 随运行回写仓库做去重持久化，**只在真有新条目时才产生提交**（易变时间戳已移出 state.json）。
    - TG 源配了双地址自动切换：云端（美国机房）走 t.me 直连，本机（国内）被墙自动切 rssforever 镜像。
    - linux.do 的 Cloudflare 对云机房 IP 可能返回空内容（本机访问正常）——ZCode 活动在云端由智谱官方活动页兜底，本机由 linux.do 首发。
    - 本地改代码后推送前先 `git pull --rebase`，极少数撞上云端新条目提交时，`git checkout --theirs watcher/state.json feed.json` 再 continue 即可。

## 更新榜单数据（只需改一个文件）

所有数据在 `data.js`，字段含：

| 字段 | 说明 |
|---|---|
| `status` | `active` 已核实 / `unverified` 待核实 / `dead` 已失效 |
| `deadline` | `"YYYY-MM-DD"` 自动倒计时；`null` 为长期 |
| `value` | 鸡蛋榜价值分 1~100（快过期的条目自动置顶） |
| `srcs` | 来源链接，方便下次核查 |

维护节奏建议：**每两周核对一轮**。活动过期 → 挪进 `GRAVEYARD`；新活动 → 加进 `FREEBIES` 并附官方来源链接。盯新活动就刷页脚「情报源雷达」里的 8 个官方入口。

## 数据核查日

2026-09-03（价格时效性强，标注「待核实」处请以官方页面为准）。
