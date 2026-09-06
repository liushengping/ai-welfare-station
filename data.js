/* ============================================================
 * AI 厂商福利情报站 — 数据文件
 * 更新数据只需改这个文件，页面无需改动。
 *
 * 字段说明：
 *   region: "cn" | "intl"          国内 / 国际
 *   status: "active"               已核实可用
 *           "unverified"           待核实（数字或现状未在官方页面确认）
 *           "dead"                 已失效（进墓场）
 *   deadline: "YYYY-MM-DD"         明确截止日期（会自动算倒计时）
 *           null                   长期有效 / 无固定截止
 *   value:   1~100                 白嫖价值分（用于排序，凭额度粗估）
 *   srcs:    [{label, url}]        信息来源
 * ============================================================ */

const DATA_UPDATED = "2026-09-03";

/* ---------------- 鸡蛋榜：谁在送、送多少、几号过期 ---------------- */
const FREEBIES = [
  {
    vendor: "硅基流动 SiliconFlow", emoji: "🔥", region: "cn", status: "active",
    title: "注册送 2000 万 Token",
    amount: "2000 万 Token",
    who: "所有新用户，注册即到账；填邀请码可再加量",
    note: "平台另有部分限时免费模型可直接调用，不消耗赠送额度；「推荐官」计划邀好友得全平台通用代金券",
    deadline: null, value: 85,
    srcs: [{ label: "官网", url: "https://siliconflow.cn/" }],
  },
  {
    vendor: "智谱 BigModel", emoji: "🧊", region: "cn", status: "active",
    title: "新人 2000 万 Tokens + 邀请双方各 2000 万",
    amount: "新人 2000 万（含 600 万 GLM 系列），有效期 3 个月",
    who: "新用户注册自动发放；邀请 1 位新用户双方各得 2000 万 GLM-4.5-Air（约 58 元），每月可邀 10 人",
    note: "「拼好模」受邀首单 9 折、邀请者得好友首单 10% 赠金可无限叠加；GLM-4.6 资源包低至 4 折",
    deadline: null, value: 90,
    srcs: [
      { label: "活动规则", url: "https://docs.bigmodel.cn/cn/update/promotion" },
      { label: "注册领取", url: "https://bigmodel.cn/" },
    ],
  },
  {
    vendor: "火山引擎·豆包", emoji: "🌋", region: "cn", status: "active",
    title: "每款模型 50 万 Tokens（2 年有效）+ Agent Plan 约 250 元",
    amount: "50 万/模型 × 全系（含 DeepSeek 等第三方）+ Agent Plan 合计约 ¥250",
    who: "新用户，方舟控制台开通模型自动到账，每账号一次",
    note: "Coding Plan 免费版每月额度已升至 100 万 Tokens；Doubao-Seed-2.1-pro 曾有每日 500 万 Tokens 免费活动（截止待核实）",
    deadline: null, value: 80,
    srcs: [
      { label: "免费额度规则", url: "https://www.volcengine.com/docs/82379/1399514" },
      { label: "Agent Plan", url: "https://www.volcengine.com/article/2821158" },
    ],
  },
  {
    vendor: "阿里云百炼", emoji: "☁️", region: "cn", status: "active",
    title: "每款模型 100 万 Tokens × 70+ 款",
    amount: "100 万/款 × 70+ 款（合计可达 7000 万+），有效期 90 天",
    who: "新用户首次进控制台自动发放，无需实名",
    note: "仅华北2（北京）地域在线推理可用；到期/耗尽不补发，同主体重新注册不可再领",
    deadline: null, value: 88,
    srcs: [{ label: "官方文档", url: "https://help.aliyun.com/zh/model-studio/new-free-quota" }],
  },
  {
    vendor: "百度千帆", emoji: "📘", region: "cn", status: "active",
    title: "17 款模型 × 各 100 万 Tokens",
    amount: "17 × 100 万 Tokens（含 ERNIE-4.5-Turbo、DeepSeek-R1、Kimi-K2、Qwen3 等），有效期 3 个月",
    who: "新用户同意协议后自动开通发放（2025-10-24 起政策）",
    note: "仅抵扣在线推理，不含批量推理",
    deadline: null, value: 75,
    srcs: [{ label: "官方文档", url: "https://cloud.baidu.com/doc/qianfan/s/Imi2rpirg" }],
  },
  {
    vendor: "腾讯 TokenHub（混元）", emoji: "🐦", region: "cn", status: "active",
    title: "新人语言 + 多模态各 100 万 Tokens（1 年有效）",
    amount: "语言 100 万 + 多模态 100 万 Tokens + 生视频/3D 积分",
    who: "新用户在控制台模型广场勾选领取，或首次调用自动领取",
    note: "另有微信渠道「混元 2.0 额度 1 亿 Token」大额赠送的报道（是否升级待核实）",
    deadline: "2026-12-31", value: 60,
    srcs: [{ label: "官方文档", url: "https://cloud.tencent.com/document/product/1823/130053" }],
  },
  {
    vendor: "讯飞星火", emoji: "⭐", region: "cn", status: "active",
    title: "注册领 100 万，认证礼包最高 1500 万 Tokens",
    amount: "新注册 100 万；登录+认证礼包最高 1500 万；每款模型另有 20 万体验额度",
    who: "开发者注册 / 完成认证",
    note: "Spark Lite 系列长期免费（政策延续情况待核实）",
    deadline: null, value: 65,
    srcs: [{ label: "星火 API", url: "https://xinghuo.xfyun.cn/sparkapi" }],
  },
  {
    vendor: "Google AI Studio", emoji: "✨", region: "intl", status: "active",
    title: "10+ 款模型免费随便调（Flash 全家 + 2.5 Pro）",
    amount: "Gemini 3.8/3.7/3.6 Flash、3.5/3.1 Flash-Lite、2.5 Pro、Gemma 4 等免费层",
    who: "所有人，AI Studio 全区域免费；代价：数据可能用于改进产品",
    note: "美国大学生可白嫖 12 个月 Google AI Pro（约 $240，需学生认证）；3.1 Pro Preview 无免费层",
    deadline: null, value: 95,
    srcs: [
      { label: "免费层定价", url: "https://ai.google.dev/gemini-api/docs/pricing" },
      { label: "学生_offer", url: "https://gemini.google/students/" },
    ],
  },
  {
    vendor: "OpenRouter", emoji: "🛰️", region: "intl", status: "active",
    title: "免费模型 50 次/天，充 $10（一次性）提到 1000 次/天",
    amount: "50 → 1000 次/天（:free 模型，20 次/分钟）",
    who: "所有人；$10 为终身一次性充值，额度永不过期",
    note: "各家大厂的开源旗舰常挂 :free 端点，是白嫖聚合首选",
    deadline: null, value: 92,
    srcs: [{ label: "限流文档", url: "https://openrouter.ai/docs/api_reference/limits" }],
  },
  {
    vendor: "Cerebras", emoji: "⚡", region: "intl", status: "active",
    title: "每天 100 万 Tokens 免费高速推理",
    amount: "1M tokens/天，无需信用卡",
    who: "注册即用",
    note: "以推理速度著称，免费层速度也是第一梯队；付费 $10 起速率提升 10 倍",
    deadline: null, value: 78,
    srcs: [{ label: "定价页", url: "https://www.cerebras.ai/pricing" }],
  },
  {
    vendor: "Groq", emoji: "🚀", region: "intl", status: "unverified",
    title: "免费层高速推理开源模型",
    amount: "免费层可用 Llama 等开源模型（具体限速待核实）",
    who: "注册即用",
    note: "与 Cerebras 并列免费层吞吐量第一梯队",
    deadline: null, value: 70,
    srcs: [{ label: "控制台", url: "https://console.groq.com/" }],
  },
  {
    vendor: "Mistral", emoji: "🌬️", region: "intl", status: "unverified",
    title: "Experiment 计划：全部模型免费调（约 10 亿 tokens/月）",
    amount: "1 请求/秒，约 1B tokens/月",
    who: "手机号验证账号即可（历史上有数据训练 opt-in 要求）",
    note: "2026 年现行额度待核实，可能已要求绑卡",
    deadline: null, value: 72,
    srcs: [{ label: "Tier 说明", url: "https://docs.mistral.ai/deployment/laplateforme/tier/" }],
  },
  {
    vendor: "Kimi·月之暗面", emoji: "🌙", region: "cn", status: "unverified",
    title: "新用户 15 元体验金 / 500 万 Tokens（两种说法）",
    amount: "≈¥15 或 500 万 Tokens",
    who: "新用户注册 platform.moonshot.cn",
    note: "来源说法不一，以控制台实际到账为准",
    deadline: null, value: 40,
    srcs: [{ label: "开放平台", url: "https://platform.moonshot.cn/" }],
  },
  {
    vendor: "MiniMax", emoji: "🦞", region: "cn", status: "unverified",
    title: "Token Plan 免费额度可领",
    amount: "以官网实际为准",
    who: "新用户",
    note: "M3 旗舰按量价已永久五折（¥2.10/¥8.40 每百万）；编程套餐首月 ¥9.9",
    deadline: null, value: 45,
    srcs: [{ label: "开放平台", url: "https://platform.minimaxi.com/" }],
  },
  {
    vendor: "美团 LongCat", emoji: "🐈", region: "cn", status: "unverified",
    title: "LongCat API 限免（社区报每日数千万 token 免费额度）",
    amount: "社区教程报「每天 5000 万 Token 免费白嫖」，具体以官方为准",
    who: "注册 longcat.ai 开通 API",
    note: "美团 2026 年开源旗舰 LongCat，API 限时免费推广期；额度政策变动快，领取前看官方页",
    deadline: null, value: 70,
    srcs: [{ label: "LongCat 官网", url: "https://longcat.ai" }],
  },
  {
    vendor: "商汤 日日新 SenseNova", emoji: "🏝️", region: "cn", status: "active",
    title: "SenseNova Token Plan 免费开放（每 5 小时 1500 次调用/模型）",
    amount: "免费 OpenAI 兼容 API（token.sensenova.cn/v1），可建 20 个 API Key；付费 Lite/Pro 档即将上线",
    who: "注册 sensenova.cn 即可，无需充值绑卡",
    note: "2026-05 上线，精选 3 款多模态模型；有用户反馈 1500 次额度在灰度放量中未完全生效，以控制台实际为准",
    deadline: null, value: 72,
    srcs: [{ label: "Token Plan 页", url: "https://www.sensenova.cn/token-plan" }],
  },
  {
    vendor: "阶跃星辰 Step", emoji: "🪜", region: "cn", status: "unverified",
    title: "Step Plan 限时免费试用（多轮延期，9 月是否延续待核实）",
    amount: "新用户 15 天 Flash Plan，完成任务+邀请最高 120 天免费；StepClaw 曾放 5 万免费名额（含 5000 万 Tokens）",
    who: "到 platform.stepfun.com/step-plan 看「免费领取」按钮是否还在",
    note: "活动史：7-18 → 7-31 → 8-24 多轮延期，大概率还有下一轮；4 亿 Credits 活动已过期（见墓场）",
    deadline: null, value: 60,
    srcs: [{ label: "Step Plan 页", url: "https://platform.stepfun.com/step-plan" }],
  },
  {
    vendor: "Cohere", emoji: "🧭", region: "intl", status: "active",
    title: "Trial API Key 免费、不限量（限速）",
    amount: "免费调用，限速，禁生产商用",
    who: "注册自动发放",
    note: "适合开发调试；生产需升级 Production key",
    deadline: null, value: 50,
    srcs: [{ label: "定价说明", url: "https://docs.cohere.com/docs/how-does-cohere-pricing-work" }],
  },
];

/* ---------------- 已失效墓场：别再白跑了 ---------------- */
const GRAVEYARD = [
  {
    vendor: "GitHub Models", emoji: "⚰️", region: "intl",
    title: "免费模型 playground / 推理 API",
    was: "曾免费（GPT-4o ~50 次/天等）",
    died: "2026-07-30",
    note: "已全面下线（playground、模型目录、推理 API、BYOK 全部停止），官方指定迁移到 Azure AI Foundry",
    srcs: [{ label: "官方公告", url: "https://github.blog/changelog/2026-07-30-github-models-is-now-retired/" }],
  },
  {
    vendor: "xAI (Grok)", emoji: "⚰️", region: "intl",
    title: "$25 注册赠送 + $150/月数据共享额度",
    was: "新用户 $25、共享数据得 $150/月 API 额度",
    died: "2025-05",
    note: "官方邮件确认项目结束；2026 年部分教程仍称有 $25 新户礼，待核实",
    srcs: [{ label: "API 控制台", url: "https://console.x.ai" }],
  },
  {
    vendor: "OpenAI", emoji: "⚰️", region: "intl",
    title: "新 API 账户 $5 免费额度",
    was: "新账户送 $5（3 个月有效）",
    died: "2025 年中",
    note: "现已取消，新 API 账户不再送任何免费额度",
    srcs: [{ label: "社区确认", url: "https://community.openai.com/t/how-can-i-get-free-trial-credits/26742" }],
  },
  {
    vendor: "讯飞星火", emoji: "⚰️", region: "cn",
    title: "「无限 Token 限时免费」活动",
    was: "免费调用 Qwen3.6-35B-A3B 等模型",
    died: "2026-06-30",
    note: "讯飞 10 亿元押注的限时免单活动已结束",
    srcs: [{ label: "开放平台", url: "https://www.xfyun.cn/" }],
  },
  {
    vendor: "阶跃星辰 Step", emoji: "⚰️", region: "cn",
    title: "新用户 4 亿 Credits 免费领",
    was: "注册后在 Plan 列表点「免费领取」",
    died: "2026-07-31（活动页标注截止）",
    note: "活动标注 7 月 31 日截止，是否延期/重启待核实；Step Plan 订阅仍在（¥49/月起）",
    srcs: [{ label: "开放平台", url: "https://platform.stepfun.com" }],
  },
  {
    vendor: "智谱", emoji: "⚰️", region: "cn",
    title: "「先行者」5 折 API 活动",
    was: "API 全系 5 折",
    died: "2025-11-30",
    note: "智谱 2026 年已多轮涨价（API +20~100%、订阅 +30~60%），活动型折扣要趁早",
    srcs: [{ label: "活动文档", url: "https://docs.bigmodel.cn/cn/update/promotion" }],
  },
];

/* ---------------- 套餐榜：订阅制套餐横评 ---------------- */
const PLANS = [
  {
    vendor: "智谱 GLM Coding Plan", region: "cn", status: "unverified", emoji: "🧊",
    tagline: "国产编码订阅头部，配 Claude Code/Codex/ZCode 等工具",
    price: "Lite ¥118 / Pro ¥538 / Max ¥1078 每月（连续包月）",
    quota: "积分 5h/周：2000/10000 · 12000/60000 · 28000/140000，含 GLM-5.3 与 Flash",
    note: "2026-07 底向海外看齐大涨（旧价 49/149/469），待官方页核实；包季 9 折、包年 8 折，老用户不变；国际版 $12.6~168/月",
    url: "https://bigmodel.cn/glm-coding",
    priceNum: 118,
  },
  {
    vendor: "阿里云 Token Plan（个人版）", region: "cn", status: "active", emoji: "☁️",
    tagline: "7 天滚动额度，可用于 Claude Code/Cursor/Qwen Code 等",
    price: "Lite ¥39 / Standard ¥139 / Pro ¥499 每月（限时价，原 60/180/600）",
    quota: "每 7 天 Credits：2500 / 10000 / 40000；用量包 ¥100=20000 Credits",
    note: "团队版 ¥150/550/1398 每座席每月；限时价截止未注明",
    url: "https://www.aliyun.com/benefit/scene/tokenplan",
    priceNum: 39,
  },
  {
    vendor: "百度千帆 Token Plan", region: "cn", status: "active", emoji: "📘",
    tagline: "门槛最低的正规军套餐，每天 10 点还有五折秒杀",
    price: "Mini ¥9.9（首购 ¥4.9）/ Lite ¥40（首购 ¥19.9）/ Pro ¥200（首购 ¥99.9）/ Max ¥600（首购 ¥299.9）",
    quota: "月额度：1000 万 / 4200 万 / 2.3 亿 / 7 亿 Tokens，文心 + GLM 等主流模型通用",
    note: "首购优惠 + 秒杀叠加，轻量用户 ¥4.9 就能上车",
    url: "https://cloud.baidu.com/product/qianfan_home/token-plan-activity.html",
    priceNum: 9.9,
  },
  {
    vendor: "MiniMax Token Plan", region: "cn", status: "active", emoji: "🦞",
    tagline: "年费制全模态订阅，一个 Key 通吃文字/图像/语音/视频",
    price: "年费 ¥490（原 ¥588）；编程套餐首月 ¥9.9；全模态订阅 ¥29~119/月",
    quota: "旗舰模型 M3 / M2.7 + 图像/语音；Plus 以上赠多模态额度",
    note: "适合做多模态应用的开发者",
    url: "https://platform.minimaxi.com/subscribe/token-plan",
    priceNum: 41,
  },
  {
    vendor: "阶跃星辰 Step Plan", region: "cn", status: "active", emoji: "🪜",
    tagline: "订阅价直调旗舰，全档位统一高速推理",
    price: "Mini ¥49/月（社区限时 ¥25）/ 8000M ¥199 / 40000M ¥699",
    quota: "按档位 8000M、40000M 额度调用旗舰模型",
    note: "年付 ¥1860 / ¥6666",
    url: "https://platform.stepfun.com/step-plan",
    priceNum: 49,
  },
  {
    vendor: "腾讯 Hy Token Plan", region: "cn", status: "unverified", emoji: "🐦",
    tagline: "混元旗舰 Hy3/Hy4 订阅",
    price: "¥28 起，共 4 档",
    quota: "月额度 3500 万 ~ 6.5 亿 Tokens（档位细节待核实）",
    note: "混元按量价本身就是国产旗舰地板价（Hy3 ¥1/¥4），订阅适合稳定用量",
    url: "https://cloud.tencent.com/product/1823",
    priceNum: 28,
  },
  {
    vendor: "讯飞 Astron Token Plan", region: "cn", status: "active", emoji: "⭐",
    tagline: "企业向，错峰积分 0.8 倍",
    price: "标准 ¥200 / 高级 ¥600 / 尊享 ¥2000 每成员每月",
    quota: "月积分 2 万 / 6 万 / 20 万；TPM 200w~500w",
    note: "附赠 ¥168 AstronClaw 会员；工作日 8-22 点外调用积分打 8 折",
    url: "https://www.xfyun.cn/doc/spark/TokenPlan.html",
    priceNum: 200,
  },
  {
    vendor: "ChatGPT（OpenAI）", region: "intl", status: "active", emoji: "🤖",
    tagline: "标杆订阅，Codex/图像/Deep Research 全家桶",
    price: "Go $8 / Plus $20 / Pro $200 每月",
    quota: "Free→Go→Plus 用量递增；Pro 为最大用量 + Pro 模型",
    note: "API 不送免费额度（2025 年中已取消）",
    url: "https://chatgpt.com/pricing/",
    priceNum: 20,
  },
  {
    vendor: "Claude（Anthropic）", region: "intl", status: "active", emoji: "🎭",
    tagline: "编码订阅天花板，Claude Code 全付费档内置",
    price: "Pro $20（年付折合 $17）/ Max $100~200 / Team $20~125 每席",
    quota: "5 小时滚动 + 周限额；Max 5x/20x Pro 用量",
    note: "聊天与终端共用额度池；企业激活活动每用户 $1000 额度（上限 $1000 万/组织）",
    url: "https://claude.com/pricing",
    priceNum: 20,
  },
  {
    vendor: "Google AI Pro / Ultra", region: "intl", status: "active", emoji: "✨",
    tagline: "订阅即全家桶：Gemini + 办公套件 + 大容量网盘",
    price: "Pro $19.99 / Ultra $249.99 每月",
    quota: "Pro：Gemini 3 Pro 4x 用量 + Gmail/Docs 集成 + 2TB；Ultra：最高档 + 20~30TB + YouTube Premium",
    note: "美国学生可免费 12 个月 Pro",
    url: "https://one.google.com/about/google-ai-plans/",
    priceNum: 20,
  },
  {
    vendor: "Perplexity Pro", region: "intl", status: "active", emoji: "🔎",
    tagline: "AI 搜索订阅，学生教育认证半价",
    price: "$20/月（年付约 $17/月）；学生/教师 5 折",
    quota: "Pro 搜索 + 多模型切换",
    note: "不定期有运营商/硬件伙伴送 12 个月 Pro 的活动，值得蹲",
    url: "https://www.perplexity.ai/pro",
    priceNum: 20,
  },
];

/* ---------------- 模型榜：API 每百万 tokens 价格 ----------------
 * price: [输入, 输出]，单位与 currency 一致；ctx 为上下文长度
 * free: true 表示有免费层/免费额度
 */
const MODELS = [
  // ---- 国内（¥ / 百万 tokens）----
  { name: "混元 Hy3", vendor: "腾讯", region: "cn", price: [1, 4], cached: 0.25, ctx: "262K", free: false, note: "国产旗舰地板价，快慢思考融合", status: "active" },
  { name: "MiniMax-M3（≤512K）", vendor: "MiniMax", region: "cn", price: [2.1, 8.4], cached: null, ctx: "1M+", free: false, note: "永久五折价（原 4.2/16.8）", status: "active" },
  { name: "DeepSeek V4-Pro（谷时）", vendor: "DeepSeek", region: "cn", price: [1.5, 4.5], cached: "≈1/10", ctx: "—", free: false, note: "峰时 3.0/9.0；周六日全天谷价；缓存命中约未命中的 1/10", status: "active" },
  { name: "DeepSeek V4-Pro（峰时）", vendor: "DeepSeek", region: "cn", price: [3.0, 9.0], cached: "≈1/10", ctx: "—", free: false, note: "工作日高峰时段；错峰 + 周末可省一半", status: "active" },
  { name: "Step-3（限时）", vendor: "阶跃星辰", region: "cn", price: [1.5, 4], cached: null, ctx: "—", free: false, note: "开源旗舰限时折扣价", status: "active" },
  { name: "星火 X2", vendor: "讯飞", region: "cn", price: [2, 2], cached: null, ctx: "—", free: false, note: "输入输出同价（约 ¥2，待核实）", status: "unverified" },
  { name: "step-3.5-flash", vendor: "阶跃星辰", region: "cn", price: [0.7, 2.1], cached: 0.14, ctx: "—", free: false, note: "轻量快速档", status: "active" },
  { name: "qwen3.8-flash", vendor: "阿里", region: "cn", price: [0.8, 2.7], cached: null, ctx: "1M", free: true, note: "有 100 万 tokens 新人免费额度", status: "active" },
  { name: "GLM-5.3-Flash", vendor: "智谱", region: "cn", price: [0.8, 2.8], cached: 0.23, ctx: "—", free: false, note: "多模态 MIT 开源；国际价 $0.15/$0.5", status: "active" },
  { name: "qwen3.7-plus", vendor: "阿里", region: "cn", price: [2, 8], cached: null, ctx: "256K", free: true, note: "限时 8 折中（1.6/6.4）；>256K 档 6/24", status: "active" },
  { name: "MiniMax-M2.7", vendor: "MiniMax", region: "cn", price: [2.1, 4.2], cached: null, ctx: "—", free: false, note: "$0.30/$0.60，全模态", status: "unverified" },
  { name: "Doubao-Seed-2.1-Pro", vendor: "火山·豆包", region: "cn", price: [6, 30], cached: 1.2, ctx: "256K", free: true, note: "2026-06 旗舰；Agent 场景支持百万级输入", status: "active" },
  { name: "ERNIE 5.0", vendor: "百度", region: "cn", price: [6, 24], cached: null, ctx: "~119K", free: false, note: "≤32K 档价；32-128K 为 10/40", status: "active" },
  { name: "qwen3.8-max", vendor: "阿里", region: "cn", price: [12, 36], cached: null, ctx: "1M", free: true, note: "Qwen 现旗舰（prime 版 24/72 无免费额度）", status: "active" },
  { name: "Kimi K3", vendor: "月之暗面", region: "cn", price: [20, 100], cached: null, ctx: "1M", free: false, note: "2.8 万亿参数，国产最贵档，多模态", status: "active" },

  // ---- 国际（$ / 百万 tokens）----
  { name: "Gemini 3.8 Flash", vendor: "Google", region: "intl", price: [0.75, 3.75], cached: null, ctx: "1M", free: true, note: "促销价至 2026-12-31，之后 1.5/7.5；有免费层", status: "active" },
  { name: "Gemini 3.1 Flash-Lite", vendor: "Google", region: "intl", price: [0.25, 1.5], cached: null, ctx: "1M", free: true, note: "有免费层", status: "active" },
  { name: "Gemini 2.5 Pro", vendor: "Google", region: "intl", price: [1.25, 10], cached: null, ctx: "1M", free: true, note: "老旗舰仍在免费层，白嫖主力", status: "active" },
  { name: "Gemini 3.1 Pro Preview", vendor: "Google", region: "intl", price: [2, 12], cached: null, ctx: "1M", free: false, note: ">200K 档 4/18；无免费层", status: "active" },
  { name: "Mistral Large 3", vendor: "Mistral", region: "intl", price: [0.5, 1.5], cached: null, ctx: "—", free: true, note: "较 Large 2 降约 75%；Experiment 计划可免费调", status: "active" },
  { name: "Grok 4.3", vendor: "xAI", region: "intl", price: [1.25, 2.5], cached: 0.2, ctx: "1M", free: false, note: "<200K 档；≥200K 为 2.5/5", status: "active" },
  { name: "Grok 4.6", vendor: "xAI", region: "intl", price: [2, 6], cached: 0.5, ctx: "500K", free: false, note: "≥200K 档 4/12；批量的 8-9 折", status: "active" },
  { name: "GPT-5.6-luna", vendor: "OpenAI", region: "intl", price: [0.2, 1.2], cached: null, ctx: "400K", free: false, note: "长上下文档 0.4/1.8", status: "active" },
  { name: "GPT-5.6-terra", vendor: "OpenAI", region: "intl", price: [2, 12], cached: null, ctx: "400K", free: false, note: "长上下文档 4/18", status: "active" },
  { name: "GPT-5.6-sol（旗舰）", vendor: "OpenAI", region: "intl", price: [4, 20], cached: 0.4, ctx: "400K", free: false, note: "促销价至少到 2026-11-21；长上下文 8/30；批量 5 折", status: "active" },
  { name: "Claude Haiku 4.5", vendor: "Anthropic", region: "intl", price: [1, 5], cached: null, ctx: "200K", free: false, note: "缓存读 0.1x、写 1.25x", status: "active" },
  { name: "Claude Sonnet 4.5", vendor: "Anthropic", region: "intl", price: [3, 15], cached: null, ctx: "200K(1M beta)", free: false, note: ">200K 档 6/22.5；「Sonnet 5 $2/$10」仅搜索摘要，待核实", status: "active" },
  { name: "Claude Opus 4.5", vendor: "Anthropic", region: "intl", price: [5, 25], cached: null, ctx: "200K", free: false, note: "发布时较 Opus 4.1（15/75）大降价", status: "active" },

  // ---- 免费 / 近免费 ----
  { name: "GLM-4.7-Flash / GLM-4.5-Flash", vendor: "智谱", region: "cn", price: [0, 0], cached: null, ctx: "—", free: true, note: "官方文档确认免费模型", status: "active" },
  { name: "Spark Lite 系列", vendor: "讯飞", region: "cn", price: [0, 0], cached: null, ctx: "—", free: true, note: "长期免费政策（延续情况待核实）", status: "unverified" },
  { name: "OpenRouter :free 端点", vendor: "聚合", region: "intl", price: [0, 0], cached: null, ctx: "—", free: true, note: "50 次/天；充值 $10 提到 1000 次/天", status: "active" },
];

/* ---------------- 情报源雷达：盯新活动的官方入口 ---------------- */
const RADAR = [
  { label: "智谱活动中心", url: "https://docs.bigmodel.cn/cn/update/promotion" },
  { label: "阿里百炼公告", url: "https://help.aliyun.com/zh/model-studio/new-free-quota" },
  { label: "火山方舟文章", url: "https://www.volcengine.com/article" },
  { label: "百度千帆公告", url: "https://cloud.baidu.com/doc/qianfan/s/Imi2rpirg" },
  { label: "腾讯 TokenHub 文档", url: "https://cloud.tencent.com/document/product/1823" },
  { label: "OpenRouter Blog", url: "https://openrouter.ai/blog" },
  { label: "Google AI 定价页", url: "https://ai.google.dev/gemini-api/docs/pricing" },
  { label: "GitHub Changelog", url: "https://github.blog/changelog/" },
];
