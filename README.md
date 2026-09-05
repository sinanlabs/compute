# Sinan Compute · 司南·算力

**Effective-price comparison and reachability measurement for model API relay sites.**
中转站实付比价与可达性测量 —— 每个数字都能点开抓取快照。

🌐 https://compute.sinanlab.com · 🇬🇧 https://compute.sinanlab.com/en/ · 📡 [RSS](https://compute.sinanlab.com/feed.xml) · 🧾 [Methodology](https://compute.sinanlab.com/method) · 📦 [Raw data](https://compute.sinanlab.com/data_v2.json)

---

## What it does / 这是什么

Hundreds of "relay sites" (中转站) resell LLM APIs at a discount. Their panels show a *nominal* USD price, but what you actually pay depends on a top-up rate, currency and multiplier that differ per site. Sinan Compute turns all of that into one number:

```
effective $/M tokens = panel nominal price × top-up rate (¥ per $1 nominal) ÷ USD/CNY
ratio                = effective ÷ lowest public reference (official page or OpenRouter)
```

Every ratio is then placed in an arithmetic band (below cost floor / below bulk discount / within range / near public price / above). We state the band; we do not speculate on why.

| | |
|---|---|
| Relay sites indexed | 900+ (confirmed by panel fingerprint; 300+ with public pricing) |
| Models tracked | 40 text models + 27 image/video families |
| Quotes | 14,000+ effective prices, refreshed nightly |
| Reachability | hourly probe, 24h uptime + p50 latency per site |
| Consistency probe | 12 fixed prompts per model, token-count fingerprint compared across sites |
| Evidence | every number links to a sha256-hashed fetch snapshot |

## What it is not / 我们不做什么

- No recommendations, no rankings by "quality", no "scam" labels. Ratios are arithmetic; wording is gated by a banned-word linter before every deploy.
- No money from any measured vendor: zero affiliate links, zero ads, zero sponsors ([why trust us](https://sinanlab.com/constitution)).
- Not a verdict on authenticity. The consistency probe reports *counts consistent / counts differ / too few peers*, nothing more.

## Use the data / 用数据

| Endpoint | Content |
|---|---|
| `/data_v2.json` | model ledger, 900+ sites, snapshot index, FX rate |
| `/media.json` | image / video quotes vs official prices |
| `/history/<model>.json` | price history per model |
| `/feed.xml` | daily price changes + new sites |
| `/citation-context.json` · `.md` | compact, timestamped context for AI assistants and researchers |
| `/llms.txt` | how to read and cite this site |
| `/badge/<domain>.svg` | embeddable measured-facts badge for site owners |

License for data: CC BY 4.0 — cite `compute.sinanlab.com` and the snapshot date.

## How it works / 怎么运转

```
CT-log tail + directory harvest ──▶ panel fingerprint (/api/status, /v1/models)
        │                                        │
        ▼                                        ▼
  relay_candidate (SQLite)  ──▶ pricing adapters (one-api / new-api …) ──▶ offer_norm
        │                                        │
  hourly heartbeat (uptime, TTFB)          official reference pullers (OpenAI, Anthropic, Google, DeepSeek,
        │                                  Volcengine, Aliyun Bailian, Vidu, Kling … + OpenRouter)
        ▼                                        ▼
  export_data.py ──▶ data_v2.json ──▶ build_v5.py (static HTML, zh + /en/) ──▶ Cloudflare Pages
                                   └▶ i18n_apply.py · seo_assets.py · citation_context.py · notify_email.py
```

Everything runs once a night (03:00 Beijing). No framework: Python 3.9 + httpx, one static-site generator, Cloudflare Pages Functions for login / watch / mail.

## Run it yourself / 本地运行

```bash
pip install httpx pyyaml pillow markdown
python3 site/export_data.py && python3 site/export_media.py && python3 site/build_v5.py
python3 -m http.server -d site/dist 8792
```

Data lives in `data/compass.sqlite` (not in the repo) and is produced by the collection engine (private). The generators above run against the exported `data_v2.json` / `media.json`, which are also published at the URLs listed under *Use the data*.

## Corrections / 纠错

Found a wrong number? Open an issue with the page URL and a source link, or email hello@sinanlab.com. Corrections are logged publicly; original records are kept.

## Layout / 目录

| Path | What |
|---|---|
| `site/build_v5.py` | static site generator (zh) · `site/i18n_apply.py` + `site/i18n_dict.py` → `/en/` |
| `site/export_data.py` | SQLite → `data_v2.json` (bands, clusters, probes) |
| *collection engine* | pricing adapters, discovery, probes and the nightly runner live in a private repo; this public repo holds the presentation layer, the user system, the methodology and the data snapshots |
| `functions/` | Cloudflare Pages Functions: GitHub login, watches, email subscriptions, alerts |
| `docs/METHOD.md` | the full methodology, versioned |

---

Part of **Sinan Lab / 司南实验室** — neutral measurement for AI infrastructure. Sister project: [Sinan Robo](https://github.com/sinanlabs/robo), an auditable index of open embodied (VLA) models.
