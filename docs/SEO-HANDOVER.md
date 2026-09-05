# Sinan Lab · SEO 移交文档（Claude → Codex）

日期：2026-09-05（北京）。移交人：Claude（Claude Code）。接收人：Codex。拍板人：Eric。
从本文档起，三站（sinanlab.com / compute.sinanlab.com / robo.sinanlab.com）所有**面向搜索引擎**的工作归 Codex；Claude 保留数据管线、产品功能、用户系统、邮件、Robo 内容核实、基础设施。

---

## 0. 一句话现状

三站已上线且每天凌晨 3 点（北京）自动重建部署；SEO 基础设施（标题/描述/canonical/hreflang/sitemap/robots/JSON-LD/og 图/IndexNow/中英双语）全部就位；Google Search Console 已验证并提交 sitemap；Bing 通过 GSC 导入；百度三站已验证但每日提交配额约 10 条。**尚无搜索流量数据**（GSC 需 1–2 天出首批数据）。

---

## 1. 站点与部署

| 站 | 生成器 | 输出目录 | Cloudflare Pages 项目 | 部署命令（在各仓库根目录） |
|---|---|---|---|---|
| compute.sinanlab.com | `compass/site/build_v5.py`（Python，无框架） | `compass/site/dist/` | `sinan-compute` | `npx wrangler pages deploy site/dist --project-name sinan-compute --commit-dirty=true` |
| sinanlab.com | `sinanlab-site/build.py` | `sinanlab-site/public/` | `sinanlab-site` | `npx wrangler pages deploy public --project-name sinanlab-site --commit-dirty=true` |
| robo.sinanlab.com | Astro 5（`sinan-robo/`） | `sinan-robo/dist/` | `sinan-robo` | `npm run deploy`（= import → validate → astro build → deploy） |

- 本机 wrangler 已登录 Eric 的 Cloudflare 账号，部署不需要密钥。
- GitHub 仓库（已公开）：`sinanlabs/compute`、`sinanlabs/robo`、`sinanlabs/site`；本地路径 `~/Desktop/claude code/{compass,sinan-robo,sinanlab-site}`。
- **任何密钥不得进仓库**：Resend / GitHub OAuth / Session 在 Cloudflare Pages Secrets；中转站 Key 在 `compass/data/keys.env`（git-ignored）；Telegram 在 `compass/data/secrets.env`（git-ignored）。

### 1.1 每日流水线（`compass/daily_refresh.sh`，由 `run_forever.sh` 在北京 03:00 触发）

```
pull_official_refs.py → pull_all_pricing.py → probes/fingerprint.py（有 Key 的站）
→ site/export_data.py / export_media.py / export_go_links.py / export_history.py / weekly_snapshot.py
→ site/citation_context.py（GEO，Codex 交接单产物）→ site/seo_assets.py（og 图）
→ site/build_v5.py → site/i18n_apply.py（生成 /en/ 镜像 + hreflang + 切换按钮）
→ 措辞自检（core/wording.lint，命中禁用词不部署）
→ 部署 Compute → site/indexnow.py（Bing 端点）→ notify_telegram.py → notify_email.py
→ 母站 build.py → i18n_apply → 部署
```

改了生成器想立刻上线：手动按上面顺序跑（最少：`export_data.py && build_v5.py && i18n_apply.py site/dist https://compute.sinanlab.com`，再 lint、再部署）。

### 1.2 本地预览

```bash
cd ~/Desktop/claude\ code/compass && python3 -m http.server -d site/dist 8792
cd ~/Desktop/claude\ code/sinanlab-site && python3 -m http.server -d public 8793
```
注意 Cloudflare Pages 会把 `/foo.html` 308 到 `/foo`，本地简单 server 不会；站内链接一律写无后缀路径。

---

## 2. 已上线的 SEO 资产（现状清单）

### Compute（compute.sinanlab.com）— 约 1,000 个 URL（zh 500 + /en/ 500）

| 项 | 状态 | 位置 |
|---|---|---|
| 页面类型 | 首页 `/`、中转站总表 `/sites`、站点页 `/s/<域名>`（921 页）、模型页 `/m/<model_id>`（40 页）、图像视频 `/media` + 族页 `/media/<family>`、方法论 `/method`、周报 `/weekly` + `/weekly/<yyyy-wNN>`、我的 `/me`（noindex）、404 | `build_v5.py`：`build_index / build_sites / build_site / build_model / build_media / build_family / build_weekly / build_weekly_index / build_method / build_me` |
| 标题 / description | 每页独立。模型页标题直接对搜索词："X API 中转站价格对比：N 家实付 vs 参考价 $Y"；站点页 description 含站名/在卖模型数/画像/可达率 | `shell(title, desc, path, …)`；模型页 `build_model()` 里 `title=/desc=`；站点页 `build_site()` |
| canonical / og / twitter | 全部页面 | `shell()` 头部 |
| hreflang（zh-CN / en / x-default） | 中英互指，英文页 canonical 指 `/en/…` | `site/i18n_apply.py::head_fix / main` |
| JSON-LD | 首页 WebSite（含 SearchAction）+ Dataset；模型页 FAQPage（5 问）+ BreadcrumbList | `build_index()` 的 `ld=`；`build_model()` 的 `jsonld=` |
| sitemap.xml（带 lastmod） | 由 `urls` 列表生成；i18n_apply 追加 /en/ 条目；已提交 GSC | `build_v5.py` main 尾部 `urls = [...]`；`i18n_apply.py` sitemap 段 |
| robots.txt | Allow all + Sitemap 行 | `build_v5.py` `W("robots.txt", …)` |
| og.png + 每模型分享图 | PIL 生成（Songti 字体） | `site/seo_assets.py` → `dist/img/og.png`、`dist/img/og/<model>.png` |
| IndexNow | 每日部署后推全部 URL（含 /en/）到 `https://www.bing.com/indexnow`（api.indexnow.org 在本机代理下 403）；密钥文件 `site/indexnow.key`，构建时复制为 `dist/<key>.txt` | `site/indexnow.py` |
| RSS | `/feed.xml`：价格变动 + 新收录 | `build_feed()` |
| 无 .html 后缀 | 全站；`_redirects` / `_headers` 由 build 写出 | `build_v5.py` main |
| 性能 | 首页 HTML 已从 449 KB 减到 ~99 KB（921 站后 site_index 变大）；40 模型全量账本懒加载 `assets/ledger.json`；地球贴图 ~500 KB 仍在首屏后加载 | `build_index()` 的 `light` 字典 + `ensureLedger()` JS |
| 站长验证文件 | Google 走 DNS TXT（已验）；百度三站用 Pages Function 直接 200 返回（`functions/baidu_verify_codeva-*.html.js`，因 Pages 对 .html 会 308，百度不跟跳转） | `compass/functions/`、`sinanlab-site/functions/`、`sinan-robo/functions/` |

### 母站（sinanlab.com）— 11 页 ×2 语言

首页（行情板读 Compute 数据）、`/constitution`（现叫"为什么可信"）、`/about`、`/subscribe`（含邮件订阅表单）、`/privacy`、`/disclaimer`、`/disclosure`（现叫"收入透明"）、404。JSON-LD：Organization + WebSite。`build.py` 里 `page(filename, title, desc, body)`。

### Robo（robo.sinanlab.com）

Astro 原生双语（`src/i18n/{zh-CN,en}.json`），`src/layouts/Base.astro` 里 canonical/hreflang/描述；页面：首页、`/models`、`/models/<id>`（25 页）、`/matrix`、`/embodiments`、`/hardware`、`/methodology`、`/compare`、`/about`、`/subscribe`。**尚无 JSON-LD、无 og 图**——这是 Robo 最明显的 SEO 缺口。

---

## 3. 搜索引擎平台账号与状态（全部在 Eric 手里）

| 平台 | 状态 | 谁操作 | 备注 |
|---|---|---|---|
| Google Search Console | 网域属性 `sinanlab.com` 已验证（DNS TXT），三站 sitemap 已提交 | Eric 的 Google 账号 | 首批数据 1–2 天后出现；Codex 要看报告需 Eric 截图或加 Codex 为用户 |
| Bing Webmaster | 从 GSC 导入 | Eric | IndexNow 每日自动推送 |
| 百度站长平台 | 三站均已文件验证；sitemap 配额 0，手动提交每日约 10 条；已提交部分 compute URL | Eric | **待办**：拿到"API 提交"的接口地址（带 token）后接进 `daily_refresh.sh` 自动推送 |
| IndexNow | 已自动化 | 无需 | 密钥 `compass/site/indexnow.key`（公开无妨） |

---

## 4. 必须遵守的规则（不是建议）

1. **措辞宪法**：所有对外文案过 `core/wording.lint`；禁用词（"实锤/假模型/套壳/诈骗/降智"等）命中则流水线不部署。不写推荐、不写"最便宜/最好"、不对渠道下动机判断。SEO 标题也要守：可以写"价格对比""实付 vs 参考价"，不能写"最靠谱的中转站"。
2. **中英同步**：任何新增中文文案必须同时在 `compass/site/i18n_dict.py` 加英文条目（`{n}`=数字、`{s}`=任意文字），然后 `python3 i18n_dict.py` 生成 `i18n_en.json`；`i18n_apply.py` 运行时会打印"残留未翻文本节点"数，新增文案没进词典就会在英文页漏中文。母站共用同一词典。英文表头/按钮长度控制在中文 1.5 倍内，超了换短词而不是改布局。
3. **数据只能真实**：页面上任何数字必须来自 `data_v2.json` / 数据库快照；不得为 SEO 编造数量、评级、排名。
4. **共享文件协作**：`build_v5.py` 同时承载页面（Codex）和数据展示（Claude）。约定：Codex 改 `shell()`、各 `build_*()` 的标题/描述/JSON-LD/内链/新增页面类型；Claude 改 `export_data.py`、`adapters/`、`probes/`、`functions/api/`、行内数据字段。改完在给 Eric 的回复里点明改了哪一段。冲突时以数据正确性优先。
5. **URL 不变**：现有 URL 结构（`/m/`、`/s/`、`/media/`、`/weekly/`、`/en/…`）已被 GSC/百度/IndexNow 收录，改动要加 301（`_redirects`）。
6. **GEO 文件**：`llms.txt`（`build_llms()`）、`citation-context.*`（`site/citation_context.py`）已是 Codex 的产物，Codex 自行维护；`llms.txt` 数据段里已有两行 citation 链接。

---

## 5. 待办队列（按我原来的优先级，Codex 可重排）

1. **GSC 首批报告跟进**：看"网页索引"里被拒/未收录的原因，逐类修（预期问题：/en/ 与 zh 的重复判定、站点页 921 页的抓取预算）。
2. **Robo 的 JSON-LD + og 图**：模型页加 `SoftwareApplication`/`Dataset` 或 `TechArticle`，`Base.astro` 加 og:image；可复用 `seo_assets.py` 思路。
3. **站点页 FAQPage**：模型页有 5 问 FAQ 结构化数据，921 个站点页没有；站点页天然适合"X 站靠谱吗 / 充值比例是多少 / 卖哪些模型"三问（措辞守规则 1）。
4. **内链**：站点页 → 所在周报；周报 → 模型页；模型页 → 图像视频族页；首页 → 最新周报。
5. **模型×站点对比页**：接"A 站 vs B 站 哪个便宜"搜索；只生成两站都在卖且可达率 ≥ 90% 的组合，控制 200 页以内。
6. **性能**：首页 `site_index`（921 站名索引，供搜索框）可改为懒加载；地球贴图（day 239 KB / cloud 207 KB / night 61 KB）延迟到首屏之后或按需加载；LCP 目标 < 2.5 s。
7. **百度 API 推送**：Eric 拿到 token 后接进 `daily_refresh.sh`（参照 `site/indexnow.py` 写一个 `baidu_push.py`）。
8. **英文页 title/description 长度校准**：现由词典逐句翻译，部分英文 title 超 60 字符（如模型页）。

---

## 6. 基线数字（2026-09-05）

| 指标 | 值 |
|---|---|
| Compute 可索引页 | zh 约 500 + en 约 500（首页 1、sites 1、media 1+27、method 1、weekly 1+N、模型 40、站点 921 → 实际 sitemap 以生成为准） |
| 已确认中转站 / 有报价 / 报价条数 | 921 / 365 / 46,439 |
| Robo 模型 / 本体 | 25 / 12 |
| 英文词典 | HTML 694 条、JS 136 条、DATA 42 条（`i18n_dict.py`） |
| 首页 HTML | 99 KB（br 后约 20 KB） |
| GSC | 网域验证 2026-09-04，sitemap 3 条已提交 |
| 百度 | 三站验证通过 2026-09-04，已手动提交约 10 条 compute URL |

---

## 7. 相关文档

- 方法论：`compass/docs/METHOD.md`（第 8 节是一致性探针）
- 增长方案：artifact `sinan_growth_plan`（Eric 处）
- 竞品研究：artifact `sinan_competitors`（PriceAI / apiranking / Veridrop / HowToken 等的 SEO 打法值得参考：单模型全网比价页、渠道科普内容）
- GEO 交接单：`~/Documents/Codex/2026-09-04/wo-x/outputs/sinan-growth-kit/geo/DEPLOY-CITATION-CONTEXT.md`

---

## 8. 移交后 Claude 继续负责

数据采集与扩量（收录、定价、探针）、数据正确性、`export_data.py`、用户系统与邮件（`functions/api/`）、Robo 模型/本体内容核实、Cloudflare/D1/密钥、每日流水线的稳定运行。Codex 需要新的数据字段（例如给 SEO 页面用的统计量）时，通过 Eric 提需求，Claude 在 `export_data.py` 里加字段。
