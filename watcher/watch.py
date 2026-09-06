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


def http_post_json(url, payload, timeout=25):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    if HAS_CURL:
        p = subprocess.run(
            ["curl", "-sSL", "--max-time", str(timeout), "-H",
             "Content-Type: application/json", "-d", "@-", url],
            input=data, capture_output=True, timeout=timeout + 10)
        if p.returncode == 0:
            return p.stdout.decode(errors="replace")
        raise RuntimeError(f"curl rc={p.returncode}: {p.stderr.decode(errors='replace')[:200]}")
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"})
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


def push_ntfy(cfg, title, body):
    # 主题优先取环境变量（GitHub Actions 用 secret 注入，避免写进仓库）
    topic = os.environ.get("NTFY_TOPIC") or cfg["topic"]
    http_post_json(cfg.get("server", "https://ntfy.sh").rstrip("/") + "/",
                   {"topic": topic, "title": title, "message": body,
                    "priority": "high", "tags": ["egg"]})


def push_bark(cfg, title, body):
    url = (f"{cfg.get('server', 'https://api.day.app').rstrip('/')}/{cfg['key']}/"
           + urllib.parse.quote(title, safe="") + "/" + urllib.parse.quote(body, safe=""))
    http_get_plain(url)


def push_serverchan(cfg, title, body):
    http_post_form(f"https://sctapi.ftqq.com/{cfg['key']}.send",
                   {"title": title, "desp": body})


def push_wecom(cfg, title, body):
    http_post_json(cfg["url"], {"msgtype": "markdown",
                                "markdown": {"content": f"**{title}**\n{body}"}})


def push_dingtalk(cfg, title, body):
    http_post_json(cfg["url"], {"msgtype": "markdown",
                                "markdown": {"title": title, "text": f"### {title}\n\n{body}"}})


def deliver_all(title, body):
    channels = load_json(CONFIG_FILE, {}).get("channels", {})
    results = []
    if channels.get("toast", {}).get("enabled"):
        try:
            push_toast(title, body[:220])
            results.append("toast=ok")
        except Exception as e:
            results.append(f"toast=FAIL({type(e).__name__})")
    for ch, fn in (("ntfy", push_ntfy), ("bark", push_bark), ("serverchan", push_serverchan),
                   ("wecom_bot", push_wecom), ("dingtalk_bot", push_dingtalk)):
        cfg = channels.get(ch, {})
        if cfg.get("enabled") and (cfg.get("key") or cfg.get("url") or cfg.get("topic")):
            try:
                fn(cfg, title, body)
                results.append(f"{ch}=ok")
            except Exception as e:
                results.append(f"{ch}=FAIL({type(e).__name__})")
    return results


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
    feed = list(state.get("feed", []))

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
            if hits and not first_run:
                seeded_quiet.append(f"{name}({len(hits)})")
        else:
            for it in hits:
                if it["id"] not in seen:
                    seen[it["id"]] = it["title"]
                    matched.append(it)
        log(f"[源] {name}: 抓到 {len(items)} 条, 命中 {len(hits)} 条 ({time.time()-t0:.1f}s)")

    now = time.strftime("%F %T")
    feed = ([{"t": now, "title": it["title"], "link": it["link"]} for it in matched] + feed)[:60]
    # last_run 等易变时间戳只进 feed.json，不进 state.json（state 进 git，避免每轮提交竞速）
    # sort_keys：内容只取决于数据集合本身，云端/本地产出字节级一致，才能避免无谓 diff
    STATE_FILE.write_text(json.dumps(
        {"seen": dict(list(seen.items())[-5000:]), "sources_ok": sources_ok,
         "feed": feed}, ensure_ascii=False, indent=1, sort_keys=True),
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
    if not matched:
        log("[结果] 0 new")
        return

    for it in matched:
        log(f"[NEW] {it['title']}\n[NEW] -> {it['link']}")

    title = f"🥚 AI福利雷达：{len(matched)} 条新活动"
    body = "\n\n".join(f"{it['title']}\n{it['link']}" for it in matched[:8])
    if len(matched) > 8:
        body += f"\n\n…共 {len(matched)} 条"
    log("[推送] " + " ".join(deliver_all(title, body)))
    log(f"[结果] new={len(matched)}")


if __name__ == "__main__":
    main()
