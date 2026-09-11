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
from pathlib import Path
from html import unescape

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


def parse_rss(text):
    items = []
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return items
    for entry in local_tags(root, "item") + local_tags(root, "entry"):
        title, link = "", ""
        t = local_tags(entry, "title")
        if t and t[0].text:
            title = t[0].text.strip()
        l = local_tags(entry, "link")
        if l:
            link = (l[0].get("href") or (l[0].text or "")).strip()
        if title:
            items.append({"title": unescape(title), "link": link})
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
    key = os.environ.get("SERVERCHAN_KEY") or cfg["key"]
    http_post_form(f"https://sctapi.ftqq.com/{key}.send",
                   {"title": title, "desp": body})


def push_pushplus(cfg, title, body):
    token = os.environ.get("PUSHPLUS_TOKEN") or cfg["token"]
    http_post_json("https://www.pushplus.plus/send",
                   {"token": token, "title": title, "content": body, "template": "txt"})


def push_wecom(cfg, title, body):
    http_post_json(cfg["url"], {"msgtype": "markdown",
                                "markdown": {"content": f"**{title}**\n{body}"}})


def push_dingtalk(cfg, title, body):
    http_post_json(cfg["url"], {"msgtype": "markdown",
                                "markdown": {"title": title, "text": f"### {title}\n\n{body}"}})


def deliver_all(title, body, click=None, priority="high"):
    channels = load_json(CONFIG_FILE, {}).get("channels", {})
    # 各通道就绪条件：本地 config 或环境变量（CI 用 secret 注入）任一有值即可
    ready = {
        "ntfy": bool(os.environ.get("NTFY_TOPIC") or channels.get("ntfy", {}).get("topic")),
        "bark": bool(channels.get("bark", {}).get("key")),
        "serverchan": bool(os.environ.get("SERVERCHAN_KEY") or channels.get("serverchan", {}).get("key")),
        "pushplus": bool(os.environ.get("PUSHPLUS_TOKEN") or channels.get("pushplus", {}).get("token")),
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
def ai_filter(items, config):
    """返回 {index: judgment}；不可用/失败返回 None（fail-open：全部按紧急处理）。"""
    ai = config.get("ai", {})
    if not ai.get("enabled") or not items:
        return None
    key = os.environ.get("ZHIPU_API_KEY")
    if not key:
        return None
    model = ai.get("model", "glm-4.7-flash")
    api = ai.get("api", "https://open.bigmodel.cn/api/paas/v4/chat/completions")
    chunk_size = ai.get("max_items", 15)
    out = {}
    chunks = [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]
    sys_prompt = (
        "你是AI福利情报审核员。逐条判断下列条目是否为「AI厂商/大模型的免费福利活动」"
        "（送token/额度/积分/会员/免费API/免费模型/限时折扣等）。"
        "忽略：电商优惠券、非AI产品、招聘、纯新闻评论、赌博博彩。"
        '严格只输出JSON数组，不要其它文字：'
        '[{"i":条目序号,"rel":true或false,"vendor":"厂商名","amount":"额度简述(20字内)",'
        '"deadline":"YYYY-MM-DD或null","value":1到100价值分,"urgent":限量/先到先得/7天内截止则为true否则false}]'
    )
    for chunk in chunks:
        listing = "\n".join(f'{it["i"]}. {it["title"]} | {it["link"][:80]}' for it in chunk)
        try:
            resp = http_post_json(api, {
                "model": model, "temperature": 0.1,
                "messages": [{"role": "system", "content": sys_prompt},
                             {"role": "user", "content": listing}],
            }, timeout=ai.get("timeout", 40),
                headers={"Authorization": f"Bearer {key}"})
            txt = resp.strip()
            if txt.startswith("```"):
                txt = txt.strip("`").lstrip("json").strip()
            lo, hi = txt.find("["), txt.rfind("]")
            arr = json.loads(txt[lo:hi + 1])
            for j in arr:
                if isinstance(j, dict) and "i" in j:
                    out[j["i"]] = j
        except Exception as e:
            log(f"[AI] 判定失败（fail-open 保留全部）: {type(e).__name__} {str(e)[:120]}")
            return None
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
    rejected = 0
    for i, it in enumerate(matched):
        j = judgments.get(i) if isinstance(judgments, dict) else {"rel": True, "urgent": True}
        if not j.get("rel", True):
            rejected += 1
            continue          # 已入 seen，静默丢弃，不再打扰
        it["ai"] = {k: j.get(k) for k in ("vendor", "amount", "deadline", "value", "urgent")}
        relevant.append(it)
        (urgent if j.get("urgent") is True else normal).append(it)

    # ---- 分级推送：紧急（限量/临期）直推；常规进日报池，北京时间日报点合并推送 ----
    cfg_digest = config.get("digest", {})
    site_url = "https://liushengping.github.io/ai-welfare-station/"
    if urgent:
        t = f"🔥 AI福利急报：{len(urgent)} 条（限量/临期）"
        b = "\n\n".join(f"{it['title']}\n{it['link']}" for it in urgent[:8])
        if len(urgent) > 8:
            b += f"\n\n…共 {len(urgent)} 条"
        log("[推送] " + " ".join(deliver_all(
            t, b, click=urgent[0]["link"] if len(urgent) == 1 else site_url)))

    bj_hour = int((time.time() + 8 * 3600) // 3600 % 24)
    pool = pending_digest + normal
    if cfg_digest.get("enabled", True) and pool and bj_hour == cfg_digest.get("beijing_hour", 9):
        t = f"📋 AI福利日报：{len(pool)} 条常规活动"
        b = "\n\n".join(f"{it['title']}\n{it['link']}" for it in pool[:10])
        if len(pool) > 10:
            b += f"\n\n…共 {len(pool)} 条"
        log("[日报] " + " ".join(deliver_all(t, b, click=site_url, priority="default")))
        pool = []
    else:
        pool = pool[-50:]     # 防膨胀
        if normal:
            log(f"[入报] {len(normal)} 条常规进入日报池（当前池 {len(pool)} 条）")
    if rejected:
        log(f"[AI] 拦截 {rejected} 条非AI福利噪音")

    # ---- 持久化（feed 只收相关条目；digest 池随 state 进 git 实现云端持久） ----
    now = time.strftime("%F %T")
    feed = ([{"t": now, "title": it["title"], "link": it["link"], "ai": it.get("ai", {})}
             for it in relevant] + feed)[:60]
    # last_run 等易变时间戳不进 state.json（state 进 git，避免每轮提交竞速）
    # sort_keys：内容只取决于数据集合本身，云端/本地产出字节级一致，才能避免无谓 diff
    links_seen = dict(list(links_seen.items())[-5000:])
    STATE_FILE.write_text(json.dumps(
        {"seen": dict(list(seen.items())[-5000:]), "sources_ok": sources_ok,
         "links": links_seen, "feed": feed, "digest": pool},
        ensure_ascii=False, indent=1, sort_keys=True),
        encoding="utf-8")
    try:
        # 不带时间戳字段：feed.json 只有在条目变化时才会产生 git diff
        FEED_FILE.write_text(json.dumps({"items": feed},
                                        ensure_ascii=False, indent=1, sort_keys=True),
                             encoding="utf-8")
    except OSError:
        pass

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
