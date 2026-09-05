# -*- coding: utf-8 -*-
"""Presentation-only metadata for rank snapshots; never select or re-sort rows."""
import hashlib
import json
import re
from datetime import date
from urllib.parse import quote

BASE = "https://compute.sinanlab.com"
IMAGE_TEMPLATE_VERSION = 1


def edition(rank):
    week = rank["week"]
    if not re.fullmatch(r"\d{4}-w\d{2}", week):
        raise ValueError("Invalid rank edition")
    date.fromisocalendar(int(week[:4]), int(week[-2:]), 1)
    date.fromisoformat(rank["date"])
    return week


def rank_image_path(rank, locale="zh"):
    """Hash only the card's displayed facts so cached images stay consistent."""
    if locale not in ("zh", "en"):
        raise ValueError("Unsupported rank image language")
    week = edition(rank)
    facts = {key: rank.get(key) for key in
             ("week", "date", "window_days", "n_sites", "n_quotes", "eligible_uptime")}
    payload = json.dumps([IMAGE_TEMPLATE_VERSION, facts], sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    return "/img/og/rank/%s%s-%s.png" % ("en/" if locale == "en" else "", week, digest)


def rank_metadata(rank, path="/rank"):
    week = edition(rank)
    if path not in ("/rank", "/rank/" + week):
        raise ValueError("Rank URL does not match its edition")
    url = BASE + path
    title = "司南榜 %s · 中转站价格与响应测量 · Sinan Compute" % week
    description = "%s 期司南榜，数据日期 %s。查看中转站响应、价格、可达率与模型覆盖榜，附样本门槛和口径说明。按测量值排序，不构成推荐。" % (week, rank["date"])
    alt = "司南榜 %s 分享图：数据日期 %s、中转站与报价数量、进入榜单门槛的站数。" % (week, rank["date"])
    lists = []

    def add_list(key, name, rows, domain_key="domain"):
        if not rows:
            return  # An empty board is not a ranking with invented members.
        lists.append({
            "@type": "ItemList", "@id": url + "#list-" + quote(key, safe=""),
            "name": name, "numberOfItems": len(rows),
            "itemListElement": [
                {"@type": "ListItem", "position": position,
                 "item": {"@type": "WebPage", "name": row[domain_key],
                          "url": BASE + "/s/" + quote(row[domain_key], safe="")}}
                for position, row in enumerate(rows, 1)
            ],
        })

    # Same sequence and same row arrays as build_rank; no metric computation.
    add_list("fast", "响应榜", rank.get("fast", []))
    add_list("price", "价格优势榜", rank.get("price", []))
    for model in rank.get("flagship", []):
        add_list("flagship-" + model["id"], "新旗舰榜 · " + model["name"], model["rows"], "vendor")
    add_list("dual", "双旗舰榜", rank.get("dual", []))
    # The visible reachability board is the LOWEST tail, not the highest.
    add_list("low", "可达榜（最低可达率）", rank.get("low", []))
    add_list("volatility", "价格波动榜", rank.get("volatility", []))
    add_list("coverage", "覆盖榜", rank.get("coverage", []))
    media = rank.get("media") or {}
    for kind, label in (("video", "视频合理价榜"), ("image", "图像合理价榜")):
        for family in media.get(kind, []):
            add_list(kind + "-" + family["family"], label + " · " + family["name"], family["rows"], "site")
    add_list("media-coverage", "多模态覆盖榜", media.get("coverage", []))
    add_list("media-price", "多模态价格优势榜", media.get("price", []))
    # rank['uptime'] is not displayed; the probe table is not ordered. Neither
    # is advertised as a ranking. Do not expose private engine fields here.
    image = rank_image_path(rank)
    graph = {
        "@context": "https://schema.org", "@type": "CollectionPage",
        "@id": url + "#rankings", "url": url, "name": title,
        "description": description, "inLanguage": "zh-CN",
        "identifier": week, "dateModified": rank["date"],
        "isPartOf": {"@type": "WebSite", "name": "Sinan Compute", "url": BASE + "/"},
        "primaryImageOfPage": {"@type": "ImageObject", "url": BASE + image,
                               "width": 1200, "height": 630, "caption": alt},
        "mainEntity": lists,
    }
    return {"title": title, "description": description, "image": image,
            "image_alt": alt, "jsonld": graph}


def translate_rank_graph(graph, translate):
    """Translate only our rank graph, leaving unrelated structured data alone."""
    if (graph.get("@type") != "CollectionPage" or
            not re.fullmatch(re.escape(BASE) + r"/rank(?:/\d{4}-w\d{2})?#rankings", graph.get("@id", ""))):
        return graph

    def walk(value, key=""):
        if isinstance(value, list):
            return [walk(item) for item in value]
        if isinstance(value, dict):
            return {k: walk(v, k) for k, v in value.items()}
        if not isinstance(value, str):
            return value
        if key in ("name", "description", "caption"):
            return translate(value)
        if key == "inLanguage":
            return "en"
        if key in ("@id", "url") and value.startswith(BASE + "/"):
            path = value[len(BASE):]
            if path.startswith("/img/og/rank/"):
                return BASE + path.replace("/img/og/rank/", "/img/og/rank/en/", 1)
            if path == "/" or re.match(r"/(?:rank(?:/|#|$)|s/)", path):
                return BASE + "/en" + path
        return value

    return walk(graph)
