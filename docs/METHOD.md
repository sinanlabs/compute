# 口径与定义 · 每个数字是什么意思（公开，永久保留，改动记版本）

> 每一条对外数字都能追回这里的某一条规则和某一个快照。规则本身也要有出处。

## 1. 中转站面板报价的读法（one-api / new-api 系）

来源：`/api/pricing`（公开，无需登录）+ `/api/status`（公开）。

| 字段 | 含义 | 出处 |
|---|---|---|
| `model_ratio` | 每百万输入 token 名义美元价 = `model_ratio × 2` | new-api `common/constants.go`：`QuotaPerUnit = 500*1000 // $0.002 / 1K tokens` |
| `completion_ratio` | 输出价 = 输入价 × completion_ratio | 同上 |
| `group_ratio[group]` | 分组倍率，乘在名义价上 | `/api/pricing` 返回 |
| `quota_type=0` | 按 token（用上两行） | new-api `model/pricing.go:389` |
| `quota_type=1` | 按次，`model_price` 为每次名义美元 | new-api `model/pricing.go:384` |
| `quota_type=2` | **按秒**，`model_price` 为每秒名义美元。上游无此类型，为分支版自加 | toapis 前端渲染代码：`1===quota_type ? "/req" : 2===quota_type ? "/s"` |
| `model_type` | 0 视频 / 1 图像 / 2 文本 / 3 音频 | toapis 前端：`{video:0,image:1,chat:2,audio:3}` |
| `pricing_version` | 全站定价哈希，任一模型变动即变 | `/api/pricing` 返回；用于变更检测，比对时剔除 |

## 2. 名义美元 → 用户实付

面板价是「名义美元」。用户实付取决于充值时 $1 名义额度收多少钱：

```
实付美元 = 名义美元 × price ÷ USD/CNY 汇率          （人民币充值通道）
实付美元 = 名义美元 × stripe_unit_price              （Stripe 美元通道）
```

| 字段 | 出处 |
|---|---|
| `price` = 每 $1 名义额度收多少人民币，默认 7.3 | new-api `setting/operation_setting/payment_setting_old.go:16`；`controller/topup.go:175`：`payMoney = amount × Price × topupGroupRatio × discount` |
| `stripe_unit_price` 默认 8.0，等于默认视为未配置 | new-api `setting/payment_stripe.go:6`；`controller/topup_stripe.go:441` |
| 汇率 | 独立证据源，每次快照（open.er-api.com） |

**两条通道价差 ≥1.5 倍时，句子里注明「按人民币通道计」并附 Stripe 价。**
**拿不到的两个因子**（`topupGroupRatio`、`AmountDiscount`）只会让实付更低 → 我们算出的比率是**上界**，方向保守。

## 3. 成本下限比率

```
比率 = 中转站实付价 ÷ 本站已收录同模型最低公开渠道价
```

- 分母取 official + marketplace（OpenRouter 转载供应商标价）里的**最低值**；多档（空闲/高峰、分辩率）取最低档 → 比率偏高，宁少标不多标
- 分档：<0.15 无补贴假设下数学上不可持续 · 0.15–0.40 显著低于常见批量折扣 · 0.40–0.75 可由批量折扣解释 · 0.75–1.25 与公开价接近 · 1.25–3 高于公开价 · ≥3 显著高于
- **极端值闸门**：比率 <0.05 或 >5 且换算链任一环缺证据 → 不发布，先核对。链条齐全则放行（闸门防的是我算错，不是防事实极端）
- 模型名归一 v2：去厂商前缀、去 `:batch/:free`、去日期尾缀、去 `-official` 等中转自加后缀、数字间 `-`→`.`

## 4. 措辞

所有对外句子过 `core/wording.py`：禁用词直接拦；质量类结论必须带样本量、时间窗、置信度；discovery 类禁一切推荐表述。
固定尾句：「此为算术比值，不构成对该渠道的任何指控，也不排除存在本站未收录的更低公开来源。」

## 5. 已知边界

- DeepSeek 官方为人民币，按快照汇率折美元后参与分母
- 多模态：目前只有 Google Veo 官方按秒价可比；Seedance / Kling / Hailuo / Vidu 官方页为 JS 渲染，参考价待接，先列报价不比对
- 「按次」计价的图像模型（gpt-image / seedream / flux）每次分辨率与张数未知，不比对

## 6. 出站入口 `/go/<域名>` 与推广参数

**入口**：每个收录站的事实页和比价表都有「前往」。跳转经本站 `/go/<域名>` 中转（Cloudflare Worker，`site/worker_go.js`），
302 到 `relay_candidate.site_url`。只记按站点击数，**不存 IP / UA / Referer**；`Referrer-Policy: no-referrer`。

**目标地址守卫**：站方 `/api/status` 的 `server_address` 只在「https + 公网主机名 + 与收录域同注册域」时采用，
否则回退 `https://<域名>/`（实测 helpcoder.cc 配的是 `http://localhost:3000/`）。

**推广参数（默认关闭，`REFERRAL_ENABLED=0`）**。若启用，硬约束写死在代码里：
1. 排序、判读、任何比率永不读 `referral_url` 字段（承诺一）
2. 带推广参数的入口渲染为「广告」标识，`rel="sponsored nofollow"`（承诺二 / 《互联网广告管理办法》）
3. **检测报告页、质量测量页不得出现本入口**，只在事实页与比价表的「前往」列（承诺四）
4. 每站点击数公开；推广收入占比按季公开（承诺五）
5. 只对有官方推广计划的站配置 `referral_url`，且该站的检测结论照常发布、不因推广关系调整措辞

**未决**：从被测中转站拿返佣，与「不收被测方的钱」的承诺冲突，是 CCTest 的路。字段和开关已备好，是否打开是产品决策，不是技术决策。


## 7. 多模态（图像 / 视频）比对

**分类**：`core/modality.py` 按模型名分 image / video / audio / other（族谱正则）。名字含 image/img/t2i/i2i 且不含 video/i2v/t2v 的先按图像判；audio/voice/lip-sync 归音频。用 toapis `model_type` 真实标签验证，97%。

**单位换算**：
- 中转按秒（`quota_type=2`）vs 官方按秒：直接比
- 中转按次 vs 官方按秒：`每秒实付 = 每次实付 ÷ 该族默认单次时长`。默认时长表（来源各家 API 文档默认参数）：Veo 8s（4/6/8）、Kling 5s（5/10）、Hailuo/H3 6s（6/10）、Seedance 5s（5/10）、Vidu 4s（4/8）、Wan 5s、Sora 10s。**每一句结论都写明"按默认 N 秒折算；若该站一次含更长时长，比率偏高"**
- 图像：中转按次 vs 官方按张。官方取最低分辩率档作分母；FLUX 官方按百万像素，1 张按 1MP（≈1024×1024）
- 全部取保守方向：假设只会让比率偏高，宁少标不多标

**参考价出处**：Google Veo / Nano Banana（ai.google.dev 定价页）、Kling 视频与图像（kling.ai/dev/pricing 嵌入 JSON）、MiniMax H3（platform.minimax.io 按量计费页）、BFL FLUX（bfl.ai/pricing）。
**未接入**：Seedance / Seedream、Vidu、Wan / Qwen-Image（页面前端渲染）、Sora / GPT Image（OpenAI 403）、Midjourney（无按次 API 价）—— 只列报价，不出比率。

**旧版本提示**：站方卖 Kling v1/v2、Veo 2、Hailuo 02 而参考为新版官方价时，句子注明（旧版官方价通常更低 → 比率偏高）。

**媒体站级闸**：某站媒体行比率中位 <0.01 或 >30 → 整站「计价方式待核」不出比率；实付 <$0.0005 的行视为占位价跳过。

### 国内图像 / 视频官方参考价（2026-09-03 起）

- 火山引擎 Seedance / Seedream：取官方定价文档的刊例价，视频按 元/秒、图像按 元/张；限时折扣写进条件不进价格。
- 阿里云百炼 万相 / Qwen-Image：取官方价格页的刊例价（单一地域口径，注明地域）。
- 生数 Vidu：官方为积分计价，按官方公布的积分单价折成 元/秒，取标准时段价，错峰价写进条件。
- 人民币标价的参考按当日 USD/CNY 汇率折成美元再与中转站实付比对，参考旁标注"人民币折算"。
- 可灵国内定价页为纯前端渲染且接口需登录，只保留其国际站美元价作参考；MiniMax 沿用国际站美元价（H3 系列）。

## 8. 一致性探针（T1 指纹）

- **前提**：只对本站用自己注册的 Key 能调用的中转站做；Key 只存本机 `data/keys.env`，不进仓库、不进日志、不进页面。
- **做法**：对该站声明的每个模型，发一组固定探针请求（内容固定、跨站跨天不变，具体构成不公开以防针对性应对），只要极少的输出 token。记录返回的用量计数、回显的模型名、首字节延迟、HTTP 状态。每站每模型成本以厘计。
- **比对**：同一模型、同一探针，不同分词器切出的 token 数不同。当足够多的渠道对同一模型报出完全相同的一组计数时，视为该模型的**共识簇**；某渠道计数与共识簇不同 → 记「计数与同模型其他渠道不一致」；共识渠道不足 → 记「共识样本不足」，不下结论。回显模型名与请求不符 → 附注「回显模型名不同」。
- **措辞**：这是**一致性测量**，不是真伪判定；不出现任何指控性词汇。页面只写 一致 / 不一致 / 样本不足 + 成功条数 + 日期。
- **边界**：中转站可能对同一模型接了多个上游并随机分流，一轮探针只覆盖当时命中的那条；按次计价的模型不测。
- **数据**：`probe_t1` 表（每条一行）；导出时取最近 7 天每个 站×模型×探针 的最新一条参与共识；`data_v2.json` 里每行带 `probe{status, ok, n, echo, peers, ts}`。
