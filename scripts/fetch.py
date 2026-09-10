#!/usr/bin/env python3
"""Daily aggregator. Fetch -> merge into per-source JSON -> write status.

Design rules (do not break these):
  * One source failing must never affect another. Every fetch is isolated.
  * On failure the previous JSON is left exactly as it was; only status.json changes.
  * Items accumulate, so a short feed (Apple ML carries 10 items = 13 days) still
    fills a 30-day view after a few days of runs.
  * No ranking, no scoring, no cross-source dedup, no summarisation. Fetch and store.
"""
import html, json, os, re, sys, time, urllib.request, urllib.error
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sources import FEEDS, HF_DAILY, HF_PAPER, KEEP_DAYS_PAPERS, KEEP_DAYS_ARTICLES

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
FEED_DIR = os.path.join(DATA, "feeds")
UA = {"User-Agent": "ml-radar/1.0 (personal daily aggregator)"}
ATOM = "{http://www.w3.org/2005/Atom}"
NOW = datetime.now(timezone.utc)
TIMEOUT = 30


def http_get(url, timeout=TIMEOUT):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def parse_dt(s):
    if not s:
        return None
    s = s.strip()
    try:
        d = parsedate_to_datetime(s)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        pass
    for f in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z",
              "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d"):
        try:
            d = datetime.strptime(s, f)
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except Exception:
            pass
    return None


def read_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write_json(path, obj):
    """Atomic: never leave a half-written file if the runner dies mid-write."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, path)


def merge(old_items, new_items, keep_days, key="link"):
    """Accumulate. New wins on conflict. Drop anything past the retention window."""
    by_key = {}
    for it in old_items + new_items:
        k = it.get(key) or it.get("title")
        if k:
            by_key[k] = it
    cutoff = NOW - timedelta(days=keep_days)
    out = []
    for it in by_key.values():
        d = parse_dt(it.get("date"))
        if d and d < cutoff:
            continue
        out.append(it)
    out.sort(key=lambda x: x.get("date") or "", reverse=True)
    return out



MEDIA = "{http://search.yahoo.com/mrss/}"
CONTENT = "{http://purl.org/rss/1.0/modules/content/}"
IMG_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)', re.I)
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
# 1x1 trackers, share buttons and other junk we never want to render
BAD_IMG = re.compile(r"(pixel|track|beacon|badge|button|icon|avatar|emoji|/p/\d+\.gif)", re.I)
SUMMARY_MAX = 220


def clean_text(raw, limit=SUMMARY_MAX):
    if not raw:
        return None
    t = WS_RE.sub(" ", html.unescape(TAG_RE.sub(" ", raw))).strip()
    if len(t) < 25:
        return None
    if len(t) > limit:
        cut = t[:limit]
        sp = cut.rfind(" ")
        t = (cut[:sp] if sp > limit * 0.6 else cut).rstrip(" ,.;:-") + "\u2026"
    return t


def pick_image(el, body):
    """media:content -> media:thumbnail -> image enclosure -> first <img> in body."""
    for tag in (MEDIA + "content", MEDIA + "thumbnail"):
        for m in el.findall(tag):
            u = m.get("url")
            if u and not BAD_IMG.search(u):
                return u
    for e in el.findall("enclosure"):
        if "image" in (e.get("type") or "") and e.get("url") and not BAD_IMG.search(e.get("url")):
            return e.get("url")
    if body:
        for m in IMG_RE.finditer(body):
            u = html.unescape(m.group(1))
            if u.startswith("http") and not BAD_IMG.search(u):
                return u
    return None


# ---------------------------------------------------------------- RSS / Atom
def parse_feed(raw):
    root = ET.fromstring(raw)
    out = []
    if root.find("channel") is not None or root.tag.endswith("rss"):
        for it in root.findall(".//item"):
            link = (it.findtext("link") or "").strip()
            if not link:
                g = it.findtext("guid")
                link = (g or "").strip()
            d = parse_dt(it.findtext("pubDate") or it.findtext(
                "{http://purl.org/dc/elements/1.1/}date"))
            body = (it.findtext("description") or "") + (it.findtext(CONTENT + "encoded") or "")
            out.append({"title": html.unescape((it.findtext("title") or "").strip()),
                        "link": link,
                        "date": d.isoformat() if d else None,
                        "image": pick_image(it, body),
                        "summary": clean_text(body)})
    else:
        for it in root.findall(f"{ATOM}entry"):
            href = ""
            for l in it.findall(f"{ATOM}link"):
                if l.get("rel") in (None, "alternate"):
                    href = l.get("href") or ""
                    break
            d = parse_dt(it.findtext(f"{ATOM}published") or it.findtext(f"{ATOM}updated"))
            body = (it.findtext(f"{ATOM}content") or "") + (it.findtext(f"{ATOM}summary") or "")
            out.append({"title": html.unescape((it.findtext(f"{ATOM}title") or "").strip()),
                        "link": href.strip(),
                        "date": d.isoformat() if d else None,
                        "image": pick_image(it, body),
                        "summary": clean_text(body)})
    return [x for x in out if x["title"] and x["link"] and x["date"]]


def do_feed(spec):
    slug, name, url, group = spec
    path = os.path.join(FEED_DIR, f"{slug}.json")
    prev = read_json(path, {"items": []})
    try:
        items = parse_feed(http_get(url))
        if not items:
            raise ValueError("feed parsed but contained 0 usable items")
        merged = merge(prev.get("items", []), items, KEEP_DAYS_ARTICLES)
        write_json(path, {"slug": slug, "name": name, "url": url, "group": group,
                          "fetched_at": NOW.isoformat(), "items": merged})
        return {"slug": slug, "name": name, "group": group, "ok": True,
                "error": None, "last_success": NOW.isoformat(),
                "n_items": len(merged), "n_fetched": len(items)}
    except Exception as e:
        # leave the previous json untouched on purpose
        return {"slug": slug, "name": name, "group": group, "ok": False,
                "error": f"{type(e).__name__}: {e}"[:200],
                "last_success": prev.get("fetched_at"),
                "n_items": len(prev.get("items", [])), "n_fetched": 0}


# ---------------------------------------------------------------- HF papers
def hf_linked(pid):
    """Linked models/datasets live on a second endpoint. Failure here is not fatal."""
    try:
        d = json.loads(http_get(HF_PAPER.format(id=pid), timeout=20))
        return ({"models": d.get("numTotalModels") or 0,
                 "datasets": d.get("numTotalDatasets") or 0,
                 "spaces": d.get("numTotalSpaces") or 0,
                 "top_models": [m.get("id") for m in (d.get("linkedModels") or [])[:3]],
                 "top_datasets": [m.get("id") for m in (d.get("linkedDatasets") or [])[:3]]})
    except Exception:
        return None


def do_papers():
    path = os.path.join(DATA, "papers.json")
    prev = read_json(path, {"items": []})
    try:
        raw = json.loads(http_get(HF_DAILY))
        if not isinstance(raw, list) or not raw:
            raise ValueError("daily_papers returned no list")
        items = []
        for r in raw:
            p = r.get("paper") or {}
            pid = p.get("id")
            if not pid:
                continue
            d = parse_dt(r.get("publishedAt") or p.get("publishedAt"))
            items.append({
                "id": pid,
                "title": (p.get("title") or r.get("title") or "").strip(),
                "link": f"https://huggingface.co/papers/{pid}",
                "arxiv": f"https://arxiv.org/abs/{pid}",
                "date": d.isoformat() if d else None,
                "upvotes": p.get("upvotes") or 0,
                "comments": r.get("numComments") or 0,
                "authors": [a.get("name") for a in (p.get("authors") or [])][:6],
                "n_authors": len(p.get("authors") or []),
                "github": p.get("githubRepo") or None,
                "thumb": r.get("thumbnail") or None,
                "summary": clean_text(p.get("summary") or r.get("summary"), 260),
                "linked": None,
            })
        items = [i for i in items if i["title"] and i["date"]]
        # second pass for linked models/datasets; individually failure-tolerant
        with ThreadPoolExecutor(8) as ex:
            for it, res in zip(items, ex.map(lambda i: hf_linked(i["id"]), items)):
                it["linked"] = res
        merged = merge(prev.get("items", []), items, KEEP_DAYS_PAPERS, key="id")
        write_json(path, {"source": "Hugging Face Daily Papers",
                          "url": HF_DAILY, "fetched_at": NOW.isoformat(),
                          "items": merged})
        n_linked = sum(1 for i in items if (i["linked"] or {}).get("models"))
        return {"slug": "hf_papers", "name": "HF Daily Papers", "group": "papers",
                "ok": True, "error": None, "last_success": NOW.isoformat(),
                "n_items": len(merged), "n_fetched": len(items), "n_linked": n_linked}
    except Exception as e:
        return {"slug": "hf_papers", "name": "HF Daily Papers", "group": "papers",
                "ok": False, "error": f"{type(e).__name__}: {e}"[:200],
                "last_success": prev.get("fetched_at"),
                "n_items": len(prev.get("items", [])), "n_fetched": 0}


def main():
    os.makedirs(FEED_DIR, exist_ok=True)
    t0 = time.time()
    with ThreadPoolExecutor(8) as ex:
        feed_status = list(ex.map(do_feed, FEEDS))
    paper_status = do_papers()

    statuses = [paper_status] + feed_status
    for s in statuses:
        ls = parse_dt(s.get("last_success"))
        s["stale_days"] = (NOW - ls).days if ls else None
    write_json(os.path.join(DATA, "status.json"),
               {"generated_at": NOW.isoformat(),
                "took_seconds": round(time.time() - t0, 1),
                "sources": statuses})

    ok = sum(1 for s in statuses if s["ok"])
    for s in statuses:
        mark = "ok  " if s["ok"] else "FAIL"
        extra = f"stale={s['stale_days']}d" if not s["ok"] else f"+{s['n_fetched']}"
        print(f"  {mark} {s['name']:<20} items={s['n_items']:<5} {extra}"
              + (f"  {s['error']}" if s["error"] else ""))
    print(f"\n{ok}/{len(statuses)} sources ok in {time.time()-t0:.1f}s")
    # Only a total wipe-out is worth failing the workflow over.
    if ok == 0:
        print("ERROR: every source failed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
