#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 福利雷达轮询器：抓源 → 标题关键词过滤 → 去重 → 多渠道推送。
仅用 Python 标准库 + 系统 curl（Windows 10+ 自带）。

用法：
    python watch.py             # 抓一轮，新活动推送到已启用渠道
    python watch.py --seed      # 只记录当前条目为已见，不推送（首次/换源后用）
    python watch.py --test-push # 向所有已启用渠道发一条测试推送

设计说明：
    - 全部 HTTP 走 curl 子进程（对本机的系统代理/TLS 环境更稳，Cloudflare 也放行），
      curl 不可用时回退 urllib。
    - state.json 记录 seen（已见条目）与 sources_ok（各源最近是否成功）。
      某个源断网一段时间后恢复时，期间的积压条目只播种不推送，防止通知轰炸。
"""
import gzip
import json
import os
import re
import subprocess
import sys
import hashlib
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from html import unescape

BJ_TZ = timezone(timedelta(hours=8))

BASE = Path(__file__).resolve().parent
STATE_FILE = BASE / "state.json"
CONFIG_FILE = BASE / "config.json"
SOURCES_FILE = BASE / "sources.json"
FEED_FILE = BASE.parent / "feed.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


def log(msg):
    print(msg, flush=True)


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


# ---------------- 传输层：curl 优先，urllib 兜底 ----------------
def curl_available():
    try:
        subprocess.run(["curl", "--version"], capture_output=True, timeout=10)
        return True
    except Exception:
        return False


HAS_CURL = curl_available()


def http_get(url, timeout=25):
    if HAS_CURL:
        p = subprocess.run(
            ["curl", "-sSL", "--compressed", "--max-time", str(timeout),
             "-A", UA, "-H", "Accept-Language: zh-CN,zh;q=0.9,en;q=0.8", url],
            capture_output=True, timeout=timeout + 10)
        if p.returncode == 0:
            return _decode(p.stdout)
        raise RuntimeError(f"curl rc={p.returncode}: {p.stderr.decode(errors='replace')[:200]}")
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return _decode(resp.read())


def http_post_json(url, payload, timeout=25, headers=None):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    if HAS_CURL:
        cmd = ["curl", "-sSL", "--max-time", str(timeout)]
        for k, v in hdrs.items():
            cmd += ["-H", f"{k}: {v}"]
        cmd += ["-d", "@-", url]
        p = subprocess.run(cmd, input=data, capture_output=True, timeout=timeout + 10)
        if p.returncode == 0:
            return p.stdout.decode(errors="replace")
        raise RuntimeError(f"curl rc={p.returncode}: {p.stderr.decode(errors='replace')[:200]}")
    req = urllib.request.Request(url, data=data, headers=hdrs)
    return urllib.request.urlopen(req, timeout=timeout).read().decode(errors="replace")


def http_post_form(url, fields, timeout=25):
    data = urllib.parse.urlencode(fields).encode()
    if HAS_CURL:
        p = subprocess.run(
            ["curl", "-sSL", "--max-time", str(timeout), "-d", "@-", url],
            input=data, capture_output=True, timeout=timeout + 10)
        if p.returncode == 0:
            return p.stdout.decode(errors="replace")
        raise RuntimeError(f"curl rc={p.returncode}")
    req = urllib.request.Request(url, data=data)
    return urllib.request.urlopen(req, timeout=timeout).read().decode(errors="replace")


def http_get_plain(url, timeout=25):
    """bark 用：GET，URL 已含转义中文。"""
    if HAS_CURL:
        p = subprocess.run(["curl", "-sSL", "--max-time", str(timeout), url],
                           capture_output=True, timeout=timeout + 10)
        if p.returncode == 0:
            return p.stdout.decode(errors="replace")
        raise RuntimeError(f"curl rc={p.returncode}")
    return urllib.request.urlopen(url, timeout=timeout).read().decode(errors="replace")


def _decode(data):
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    for enc in ("utf-8", "gbk"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


# ---------------- 解析层 ----------------
def local_tags(node, name):
    return [c for c in node.iter() if c.tag.rsplit("}", 1)[-1] == name]


def _parse_date(s):
    """RSS 日期 → 北京时间 aware datetime；解析失败返回 None。"""
    s = (s or "").strip()
    if not s:
        return None
    dt = None
    try:
        dt = parsedate_to_datetime(s)           # RFC822: Wed, 11 Sep 2026 10:00:00 +0800
    except Exception:
        pass
    if dt is None:
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(BJ_TZ)


def parse_rss(text):
    items = []
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return items
    for entry in local_tags(root, "item") + local_tags(root, "entry"):
        title, link, date = "", "", ""
        t = local_tags(entry, "title")
        if t and t[0].text:
            title = t[0].text.strip()
        l = local_tags(entry, "link")
        if l:
            link = (l[0].get("href") or (l[0].text or "")).strip()
        for tag in ("pubDate", "published", "updated", "date"):
            d = local_tags(entry, tag)
            if d and (d[0].text or "").strip():
                date = d[0].text.strip()
                break
        if title:
            items.append({"title": unescape(title), "link": link, "date": date})
    return items


ANCHOR_RE = re.compile(r'<a[^>]+href=["\'](https?://[^"\']+)["\'][^>]*>(.*?)</a>',
                       re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")


def parse_html(text):
    items = []
    seen_href = set()
    for href, inner in ANCHOR_RE.findall(text):
        title = unescape(TAG_RE.sub("", inner))
        title = re.sub(r"\s+", " ", title).strip()
        if not (6 <= len(title) <= 120):
            continue
        if href.rstrip("/") in seen_href:
            continue
        seen_href.add(href.rstrip("/"))
        items.append({"title": title, "link": href.split("#")[0]})
    return items


def norm_link(u):
    """链接规范化：去 fragment、去尾斜杠，用于全局跨源去重。"""
    if not u:
        return ""
    return u.split("#")[0].rstrip("/")


def match_keywords(title, keywords, excludes):
    low = title.lower()
    if any(x.lower() in low for x in excludes):
        return False
    return any(k.lower() in low for k in keywords)


def parse_any(text):
    """按内容自动选择解析器（t.me 是 HTML，RSSHub 镜像是 XML）。"""
    head = text[:600].lstrip().lower()
    if head.startswith("<?xml") or "<feed" in head or "<rss" in head:
        items = parse_rss(text)
        if items:
            return items
    return parse_html(text)


# ---------------- 推送层 ----------------
def push_toast(title, body):
    ps1 = BASE / "notify.ps1"
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-File", str(ps1), "-Title", title, "-Body", body],
        timeout=40, capture_output=True)


def push_ntfy(cfg, title, body, click=None, priority="high"):
    # 主题优先取环境变量（GitHub Actions 用 secret 注入，避免写进仓库）
    topic = os.environ.get("NTFY_TOPIC") or cfg["topic"]
    payload = {"topic": topic, "title": title, "message": body,
               "priority": priority, "tags": ["egg"]}
    if click:
        payload["click"] = click   # 点通知直达领取页
    http_post_json(cfg.get("server", "https://ntfy.sh").rstrip("/") + "/", payload)


def push_bark(cfg, title, body):
    url = (f"{cfg.get('server', 'https://api.day.app').rstrip('/')}/{cfg['key']}/"
           + urllib.parse.quote(title, safe="") + "/" + urllib.parse.quote(body, safe=""))
    http_get_plain(url)


def push_serverchan(cfg, title, body):
    key = env_key("SERVERCHAN_KEY") or cfg.get("key")
    if not key:
        raise RuntimeError("SERVERCHAN key missing")
    http_post_form(f"https://sctapi.ftqq.com/{key}.send",
                   {"title": title, "desp": body})


def push_pushplus(cfg, title, body):
    token = env_key("PUSHPLUS_TOKEN") or cfg.get("token")
    if not token:
        raise RuntimeError("PUSHPLUS token missing")
    http_post_json("https://www.pushplus.plus/send",
                   {"token": token, "title": title, "content": body, "template": "txt"})


def push_wecom(cfg, title, body):
    http_post_json(cfg["url"], {"msgtype": "markdown",
                                "markdown": {"content": f"**{title}**\n{body}"}})


def push_dingtalk(cfg, title, body):
    http_post_json(cfg["url"], {"msgtype": "markdown",
                                "markdown": {"title": title, "text": f"### {title}\n\n{body}"}})


def deliver_all(title, body, click=None, priority="high", skip_ntfy=False):
    channels = load_json(CONFIG_FILE, {}).get("channels", {})
    # 各通道就绪条件：本地 config 或环境变量（CI 用 secret 注入）任一有值即可
    ready = {
        "ntfy": bool(os.environ.get("NTFY_TOPIC") or channels.get("ntfy", {}).get("topic")),
        "bark": bool(channels.get("bark", {}).get("key")),
        "serverchan": bool(env_key("SERVERCHAN_KEY") or channels.get("serverchan", {}).get("key")),
        "pushplus": bool(env_key("PUSHPLUS_TOKEN") or channels.get("pushplus", {}).get("token")),
        "wecom_bot": bool(channels.get("wecom_bot", {}).get("url")),
        "dingtalk_bot": bool(channels.get("dingtalk_bot", {}).get("url")),
    }
    results = []
    if channels.get("toast", {}).get("enabled") and priority == "high":
        try:
            push_toast(title, body[:220])
            results.append("toast=ok")
        except Exception as e:
            results.append(f"toast=FAIL({type(e).__name__})")
    for ch, fn in (("ntfy", push_ntfy), ("bark", push_bark), ("serverchan", push_serverchan),
                   ("pushplus", push_pushplus), ("wecom_bot", push_wecom),
                   ("dingtalk_bot", push_dingtalk)):
        if ch == "ntfy" and skip_ntfy:
            continue    # 调用方已逐条单独推过 ntfy
        if channels.get(ch, {}).get("enabled") and ready.get(ch):
            try:
                if ch == "ntfy":
                    fn(channels.get(ch, {}), title, body, click=click, priority=priority)
                else:
                    fn(channels.get(ch, {}), title, body)
                results.append(f"{ch}=ok")
            except Exception as e:
                results.append(f"{ch}=FAIL({type(e).__name__})")
    return results


# ---------------- AI 结构化过滤（GLM 免费模型，未配置 key 时自动跳过） ----------------
def _bigrams(s):
    s = re.sub(r"\s+", "", s.lower())
    return {s[i:i + 2] for i in range(len(s) - 1)} if len(s) > 1 else {s}


VENDOR_FAMILIES = {
    "zhipu": ("zcode", "智谱", "z.ai", "glm", "bigmodel", "chatglm"),
    "moonshot": ("kimi", "月之暗面", "moonshot"),
    "alibaba": ("阿里", "通义", "qwen", "百炼", "aliyun"),
    "tencent": ("腾讯", "混元", "元宝", "hunyuan", "tokenhub"),
    "baidu": ("百度", "文心", "千帆", "ernie"),
    "bytedance": ("字节", "豆包", "doubao", "火山"),
    "deepseek": ("deepseek", "深度求索"),
    "stepfun": ("阶跃", "stepfun", "step-"),
    "sensenova": ("商汤", "sensenova", "日日新"),
    "minimax": ("minimax", "海螺"),
    "xfyun": ("讯飞", "星火", "spark"),
    "meituan": ("美团", "longcat"),
    "openai": ("openai", "gpt", "chatgpt", "codex"),
    "google": ("google", "gemini"),
    "anthropic": ("anthropic", "claude"),
    "xai": ("grok", "xai"),
    "mistral": ("mistral",),
    "siliconflow": ("硅基流动", "siliconflow", "siliconcloud"),
    "cohere": ("cohere",),
    "longcat": ("longcat",),
}


def _vendor_family(text):
    t = text.lower()
    for fam, aliases in VENDOR_FAMILIES.items():
        if any(a in t for a in aliases):
            return fam
    return ""


def _cluster_key(item):
    """同活动聚类键：厂商家族 + 额度量级（如 zhipu+3亿）。不同措辞的同一活动会落进同键。"""
    title = item.get("title", "")
    fam = _vendor_family(title) or _vendor_family(item.get("ai", {}).get("vendor") or "")
    q = re.search(r"\d+\.?\d*\s*[亿万]", title)
    if fam and q:
        return fam + "@" + q.group().replace(" ", "")
    return None


def dedup_similar(items):
    """同一活动多帖合并（双网）：①厂商家族+额度量级聚类键 ②标题二元组 Jaccard ≥ 0.28。
    聚类内保留价值分最高的一条，其余静默归并。"""
    kept, keys_seen = [], []
    for it in sorted(items, key=lambda x: (x.get("ai", {}).get("value") or 0), reverse=True):
        key = _cluster_key(it)
        if key and key in keys_seen:
            continue
        bg = _bigrams(it["title"])
        is_dup = False
        for k in kept:
            kb = _bigrams(k["title"])
            if len(bg & kb) / max(1, len(bg | kb)) >= 0.28:
                is_dup = True
                break
        if is_dup:
            continue
        kept.append(it)
        if key:
            keys_seen.append(key)
    return kept


def env_key(name):
    """密钥来源优先级：环境变量（云端 secret / 已刷新的本机 env）→ apikey.local（gitignore 保护的本机文件，NAME=value 行格式）。"""
    v = os.environ.get(name)
    if v:
        return v.strip()
    f = BASE / "apikey.local"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            if "=" in line and line.split("=", 1)[0].strip() == name:
                return line.split("=", 1)[1].strip()
    return None


def ai_filter(items, config):
    """返回 {index: judgment}；不可用/失败返回 None（fail-open：全部按紧急处理）。"""
    ai = config.get("ai", {})
    if not ai.get("enabled") or not items:
        return None
    key = env_key("ZHIPU_API_KEY")
    if not key:
        return None
    models = ai.get("models") or [ai.get("model", "glm-4.7-flash")]
    api = ai.get("api", "https://open.bigmodel.cn/api/paas/v4/chat/completions")
    chunk_size = ai.get("max_items", 15)
    out = {}
    chunks = [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]
    today_bj = datetime.now(BJ_TZ).strftime("%Y-%m-%d %A")
    wk = "一二三四五六日"
    cal = "；".join(
        (datetime.now(BJ_TZ).date() + timedelta(days=k)).strftime("%Y-%m-%d") + "周" + wk[(datetime.now(BJ_TZ).date() + timedelta(days=k)).weekday()]
        for k in range(-2, 8))
    sys_prompt = (
        "你是AI福利情报审核员。逐条判断下列条目是否为「AI厂商/大模型的免费福利活动」"
        "（送token/额度/积分/会员/免费API/免费模型/限时折扣等）。"
        "忽略：电商优惠券、非AI产品、招聘、纯新闻评论、赌博博彩。"
        f"今天北京时间是 {today_bj}。日期对照表：{cal}。"
        "条目中的相对时间（今晚/明天/本周五/下周一等）必须严格按对照表换算成绝对日期时间。"
        "若多条条目属于同一活动（同厂商同赠送、仅发帖人/措辞不同），只保留信息最完整的一条 rel=true，"
        '其余设 rel=false 并加 "dup":true。'
        '严格只输出JSON数组，不要其它文字：'
        '[{"i":序号,"rel":true或false,"dup":重复时true,"vendor":"厂商名","amount":"额度(20字内)",'
        '"start":"生效开始时间 YYYY-MM-DD HH:MM，条目未提则null","deadline":"结束/到期时间 YYYY-MM-DD HH:MM，未提则null",'
        '"value":1到100价值分,"urgent":限量/先到先得/7天内截止则为true否则false}]'
    )
    for chunk in chunks:
        listing = "\n".join(f'{it["i"]}. {it["title"]} | {it["link"][:80]}' for it in chunk)
        arr = None
        for model in models:   # 免费档降级链：前一个限流/报错时试下一个
            try:
                resp = http_post_json(api, {
                    "model": model, "temperature": 0.1,
                    "messages": [{"role": "system", "content": sys_prompt},
                                 {"role": "user", "content": listing}],
                }, timeout=ai.get("timeout", 40),
                    headers={"Authorization": f"Bearer {key}"}).strip()
            except Exception as e:
                log(f"[AI] {model} 请求失败: {type(e).__name__} {str(e)[:100]}")
                continue
            try:
                body = json.loads(resp)
            except json.JSONDecodeError:
                log(f"[AI] {model} 响应非JSON: {resp[:120]}")
                continue
            if "error" in body:
                log(f"[AI] {model}: {body['error'].get('message', '')[:100]}")
                continue
            txt = body.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            if txt.startswith("```"):
                txt = txt.strip("`").lstrip("json").strip()
            lo, hi = txt.find("["), txt.rfind("]")
            if lo < 0 or hi <= lo:
                log(f"[AI] {model} 输出无JSON数组: {txt[:120]}")
                continue
            try:
                arr = json.loads(txt[lo:hi + 1])
                break
            except json.JSONDecodeError as e:
                log(f"[AI] {model} 数组解析失败: {e}")
        if arr is None:
            return None   # 本轮判定失败，fail-open 保留全部
        for j in arr:
            if isinstance(j, dict) and "i" in j:
                out[j["i"]] = j
    return out


# ---------------- 主流程 ----------------
def main():
    config = load_json(CONFIG_FILE, {})
    sources = load_json(SOURCES_FILE, [])
    keywords = config.get("keywords_any", [])
    excludes = config.get("exclude_any", [])

    if "--test-push" in sys.argv:
        results = deliver_all("🥚 AI福利雷达 · 测试", "推送通道正常。今后有新福利活动会第一时间提醒你。")
        log("[测试推送] " + " ".join(results))
        return

    seed_only = "--seed" in sys.argv
    state = load_json(STATE_FILE, None)
    first_run = state is None
    seen = dict(state["seen"]) if state else {}
    sources_ok = dict(state.get("sources_ok", {}))
    links_seen = dict(state.get("links", {}))   # 全局链接级去重（跨源）
    pending_digest = list(state.get("digest", [])) if state else []   # 日报池
    digest_date = state.get("digest_date", "") if state else ""       # 最近一次日报日期（北京时间）
    feed = list(state.get("feed", []))
    # 历史 feed 去重（修复存量重复，保留最新一条）
    _seen_links = set()
    _clean = []
    for it in feed:
        nl = norm_link(it.get("link", ""))
        if nl and nl in _seen_links:
            continue
        if nl:
            _seen_links.add(nl)
        _clean.append(it)
    feed = _clean

    matched, seeded_quiet = [], []
    stale = 0
    max_age = config.get("max_post_age_days", 3)
    for src in sources:
        name = src["name"]
        t0 = time.time()
        items = []
        urls = src.get("urls") or [src["url"]]   # 多地址自动切换（如 t.me 直连/镜像）
        try:
            last_err = None
            for attempt in (1, 2):          # 间歇性网络抖动重试一次
                for u in urls:
                    try:
                        text = http_get(u, timeout=25)
                        items = parse_any(text)
                        last_err = None
                        break
                    except Exception as e:
                        last_err = e
                if last_err is None:
                    break
                if attempt == 1:
                    time.sleep(3)
            if last_err is not None and not items:
                raise last_err
        except Exception as e:
            log(f"[错误] {name}: {type(e).__name__} {str(e)[:150]}")
            continue
        ever_ok = sources_ok.get(name)
        sources_ok[name] = "1"   # 只存布尔语义（避免时间戳导致每轮 git diff 必变）

        mode = src.get("filter", "keywords")
        for it in items:
            dt = _parse_date(it.get("date", ""))
            it["_age"] = (datetime.now(BJ_TZ) - dt).total_seconds() / 86400 if dt else None
            it["date_str"] = dt.strftime("%m-%d %H:%M") if dt else ""
        hits = []
        for it in items:
            h = hashlib.md5((it["link"] or it["title"]).encode()).hexdigest()[:12]
            it["id"] = f"{name}:{h}"
            if mode == "all" or match_keywords(it["title"], keywords, excludes):
                hits.append(it)

        if first_run or seed_only or not ever_ok:
            # 首次接入/断线恢复：只播种不推送，防通知轰炸
            for it in hits:
                seen[it["id"]] = it["title"]
                nl = norm_link(it.get("link", ""))
                if nl:
                    links_seen[nl] = "1"
            if hits and not first_run:
                seeded_quiet.append(f"{name}({len(hits)})")
        else:
            for it in hits:
                nl = norm_link(it.get("link", ""))
                if nl and nl in links_seen:
                    continue    # 其它源已收录同一链接，跳过（跨源去重）
                if it["id"] not in seen:
                    seen[it["id"]] = it["title"]
                    if nl:
                        links_seen[nl] = "1"
                    if it.get("_age") is not None and it["_age"] > max_age:
                        stale += 1
                        continue    # 旧帖（超 max_age 天）静默入库：旧活动绝不推送
                    matched.append(it)
                elif nl:
                    links_seen[nl] = "1"
        log(f"[源] {name}: 抓到 {len(items)} 条, 命中 {len(hits)} 条 ({time.time()-t0:.1f}s)")

    # ---- AI 结构化过滤（无 key / 失败时 fail-open：全部按紧急放行，等同旧行为） ----
    judgments = None
    if matched:
        judgments = ai_filter([{"i": i, "title": it["title"], "link": it["link"]}
                               for i, it in enumerate(matched)], config)
    relevant, urgent, normal = [], [], []
    rejected = dups = 0
    for i, it in enumerate(matched):
        j = judgments.get(i) if isinstance(judgments, dict) else {"rel": True, "urgent": True}
        if not j.get("rel", True):
            if j.get("dup"):
                dups += 1        # 同活动重复帖：与已收录条目静默合并
            else:
                rejected += 1
            continue          # 已入 seen，静默丢弃，不再打扰
        it["ai"] = {k: j.get(k) for k in ("vendor", "amount", "start", "deadline", "value", "urgent")}
        relevant.append(it)

    before = len(relevant)
    relevant = dedup_similar(relevant)
    dups += before - len(relevant)
    urgent = [it for it in relevant if it["ai"].get("urgent") is True]
    normal = [it for it in relevant if it["ai"].get("urgent") is not True]

    # ---- 分级推送：紧急（限量/临期）直推；常规进日报池，9点后第一轮合并推送 ----
    cfg_digest = config.get("digest", {})
    site_url = "https://liushengping.github.io/ai-welfare-station/"
    now_bj = time.strftime("%m-%d %H:%M", time.gmtime(time.time() + 8 * 3600))

    def fmt_item(it):
        """结构化条目：厂商·额度 + 标题 + 生效/截止 + 发帖时间 + 链接，旧活动一眼可辨。"""
        ai = it.get("ai", {})
        head = "｜".join(x for x in (
            f"[{ai['vendor']}]" if ai.get("vendor") else "",
            str(ai["amount"]) if ai.get("amount") else "",
        ) if x)
        lines = [(head + " " if head else "") + it["title"]]
        when = []
        if ai.get("start"):
            when.append("生效 " + str(ai["start"]))
        if ai.get("deadline"):
            when.append("截止 " + str(ai["deadline"]))
        lines.append("⏰ " + ("，".join(when) if when else "有效期未识别，请点链接核实是否最新一期"))
        if it.get("date_str"):
            lines.append(f"帖发于 {it['date_str']}")
        lines.append(it["link"])
        return "\n".join(lines)

    if urgent:
        # 高价值置顶；ntfy 逐条直达（点通知=领领取页），微信等合并列全（不截断防漏报）
        urgent.sort(key=lambda it: (it["ai"].get("value") or 0), reverse=True)
        ch_cfg = config.get("channels", {}).get("ntfy", {})
        if env_key("NTFY_TOPIC") or ch_cfg.get("topic"):
            for it in urgent[:6]:
                ai = it["ai"]
                parts = [x for x in (ai.get("vendor") or "", ai.get("amount") or "") if x]
                if ai.get("start"):
                    parts.append("生效" + str(ai["start"]))
                if ai.get("deadline"):
                    parts.append("截止" + str(ai["deadline"]))
                if not (ai.get("start") or ai.get("deadline")):
                    parts.append("有效期未识别")
                if it.get("date_str"):
                    parts.append("帖发" + it["date_str"])
                try:
                    push_ntfy(ch_cfg, f"🔥 {it['title'][:60]}",
                              "｜".join(parts) + f"\n{it['link']}",
                              click=it["link"])
                except Exception as e:
                    log(f"[错误] ntfy 单条推送失败: {type(e).__name__} {str(e)[:80]}")
        t = f"🔥 AI福利急报 {now_bj}：{len(urgent)} 条（限量/临期）"
        b = f"（抓取时间 {now_bj} 北京时间，先到先得类请尽快）\n\n" + "\n\n".join(
            f"{'⭐' if (it['ai'].get('value') or 0) >= 80 else '•'} " + fmt_item(it)
            for it in urgent)
        log("[推送] " + " ".join(deliver_all(
            t, b, click=urgent[0]["link"] if len(urgent) == 1 else site_url, skip_ntfy=True)))
    if dups:
        log(f"[合并] {dups} 条同活动重复帖已静默归并")

    bj_hour = int((time.time() + 8 * 3600) // 3600 % 24)
    today_bj = time.strftime("%F", time.gmtime(time.time() + 8 * 3600))
    pool = pending_digest + normal
    # 9 点后第一轮且当天未发过 → 发日报（驻留轮询存在空窗，"恰好9点"条件会永远等不到）
    if (cfg_digest.get("enabled", True) and pool and bj_hour >= cfg_digest.get("beijing_hour", 9)
            and digest_date != today_bj):
        t = f"📋 AI福利日报：{len(pool)} 条常规活动"
        b = "\n".join(f"- {it['title']} {it['link']}" for it in pool) + f"\n\n在线榜：{site_url}"
        log("[日报] " + " ".join(deliver_all(t, b, click=site_url, priority="default")))
        pool = []
        digest_date = today_bj
    else:
        pool = pool[-50:]     # 防膨胀
        if normal:
            log(f"[入报] {len(normal)} 条常规进入日报池（当前池 {len(pool)} 条）")
    if rejected:
        log(f"[AI] 拦截 {rejected} 条非AI福利噪音")

    # ---- 持久化（feed 只收相关条目；digest 池随 state 进 git 实现云端持久） ----
    now = time.strftime("%F %T")
    feed = ([{"t": now, "title": it["title"], "link": it["link"], "ai": it.get("ai", {}),
              "d": it.get("date_str", "")} for it in relevant] + feed)[:60]
    # last_run 等易变时间戳不进 state.json（state 进 git，避免每轮提交竞速）
    # sort_keys：内容只取决于数据集合本身，云端/本地产出字节级一致，才能避免无谓 diff
    links_seen = dict(list(links_seen.items())[-5000:])
    STATE_FILE.write_text(json.dumps(
        {"seen": dict(list(seen.items())[-5000:]), "sources_ok": sources_ok,
         "links": links_seen, "feed": feed, "digest": pool, "digest_date": digest_date},
        ensure_ascii=False, indent=1, sort_keys=True),
        encoding="utf-8")
    try:
        # 不带时间戳字段：feed.json 只有在条目变化时才会产生 git diff
        FEED_FILE.write_text(json.dumps({"items": feed},
                                        ensure_ascii=False, indent=1, sort_keys=True),
                             encoding="utf-8")
    except OSError:
        pass

    if stale:
        log(f"[旧帖] {stale} 条超过 {max_age} 天的旧活动帖已静默入库（未推送）")
    if seeded_quiet:
        log(f"[播种] 断线恢复静默吸收：{', '.join(seeded_quiet)}")
    for it in relevant:
        log(f"[NEW] {it['title']}\n[NEW] -> {it['link']}")
    if relevant:
        log(f"[结果] new={len(relevant)} 急报={len(urgent)} 常规={len(normal)}")
    else:
        log(f"[结果] 0 new（AI拦截 {rejected}）")


if __name__ == "__main__":
    main()
