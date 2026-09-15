# OpenRouter 对标研究（2026-09-15）

> 研究问题：OpenRouter 怎么从 2023 年 4 个模型的浏览器插件，做到 2026 年 8 月被 Stripe 以 70 多亿美元收购？它靠什么赚钱、怎么推广、投资人为什么投、护城河在哪？司南实验室能学什么、不该学什么？
> 数据来源见文末；所有数字保留原始出处口径，不同来源不一致的地方分别标注。

---

## 一、时间线

| 时间 | 事件 |
|---|---|
| 2022-08 | Alex Atallah 离开 OpenSea（他是联合创始人兼 CTO，OpenSea 峰值估值 140 亿美元） |
| 2022-11 | ChatGPT 发布，Atallah 转向 AI |
| 2023-02 | Meta 发布 LLaMA，开源模型开始井喷；Atallah 判断"会有成千上万个模型" |
| 2023-04-05 | 发布 Window.ai：开源 Chrome 插件，让用户把任意模型接进任意网页应用。只有 4 个模型（GPT-3.5、GPT-4、Together 的 GPT-NeoXT、Cohere xlarge） |
| 2023-05 | 与 Plasmo 框架作者 Louis Vichy 共同创立 OpenRouter |
| 2023-08-10 | 更名 OpenRouter，约 30 亿 token / 周 |
| 2023-11 | 52 个模型、2000+ 个接入应用、约 80 亿 token / 周，Menlo 认为这是"产品市场契合"的时点 |
| 2024 底 | 年化处理的推理消费约 1900 万美元 |
| 2025-02 | 种子轮 1250 万美元，a16z 领投（通过 Menlo 与 Anthropic 的 Anthology 基金也有种子参与） |
| 2025-04 | A 轮 2800 万美元，Menlo 领投；两轮合计 4000 万美元于 2025-06 公布，估值约 5 亿美元（Sequoia 跟投） |
| 2025-06 | 250 万开发者；年化 100 万亿 token（半年前 10 万亿） |
| 2025-11 | 发布《State of AI：100 万亿 token 实证研究》（与 a16z 联合） |
| 2025 底 | 500 万+ 开发者；年化收入约 5000 万美元 |
| 2026-05-26 | B 轮 1.13 亿美元，CapitalG（Alphabet）领投，NVentures、ServiceNow、MongoDB、Snowflake、Databricks 的风投跟投；估值 13 亿美元；25 万亿 token / 周（半年前 5 万亿）；800 万+ 用户；400–500+ 模型、80+ 供应商 |
| 2026-08-16 | Bloomberg 报道 Stripe 以 70 亿美元以上收购（Contrary 记为 75 亿；Sacra 提到早先传闻 100 亿）；距 B 轮仅 3 个月，溢价 5–6 倍 |
| 2026-08 | Sacra 估算年化收入 1.6 亿美元；年处理 1 千万亿（quadrillion）token 以上 |

三年增长的节奏：Menlo 的说法是"连续三年月环比 33%，约每 11 周翻一倍"，token 量从上线到被收购增长约 3 万倍。

---

## 二、盈利模式

**只收一道钱：买额度时收 5.5% 平台费，模型价格原价透传。**

- 用户在 OpenRouter 买 1000 美元额度，OpenRouter 收约 55 美元，剩下按各供应商挂牌价按量扣。不在 token 单价上再加价。
- 自带 Key（BYOK）：每月挂牌价 2.5 万美元以内免费（企业版 20 万），超出收 5%。
- 小额充值有最低手续费（约 0.80 美元）。
- 三档：免费版（限 25 个模型、4 个供应商，没有自动路由和预算控制）→ 按量版（5.5%，全部功能）→ 企业版（SSO、策略管控、合同 SLA、供应商数据浏览器）。
- 收入随平台上流过的美元同步增长：2025-05 月度客户消费约 800 万美元、平台月收入约 40 万美元；2025-10 年化 1000 万；2026-04 年化 5000 万；2026-08 年化 1.6 亿。

**为什么是这个模式而不是加价**
- 加价会让"比价"失去可信度；5.5% 明码标价，用户能算清楚自己为"一个账号、一套 API、随时切换、自动兜底"付了多少。
- Menlo 的总结：OpenRouter 和 Stripe 一样，都是"用一个抽成，把复杂交易变成一行代码"的开发者优先生意。

**风险**（Contrary 列出的三条，值得记住）
1. 云厂商捆绑：AWS Bedrock 2025 年四季度已是数十亿美元年化，并自带智能路由；有云合同的企业可能不再需要第三方。
2. 单价下跌：抽成按美元不按 token，token 单价 2022–2024 跌了 1000 倍，收入要靠 token 量增长跑赢降价。
3. 被绕开：大客户和模型厂商都有动力直连省下 5.5%；被 Stripe 收购后"中立聚合者"身份也会受质疑。

---

## 三、它是怎么推广起来的

没有大规模销售团队（2026-04 只有 2 个销售），几乎全靠产品自己带来用户。拆开看有五个动作：

1. **公开榜单是获客入口，不是附属功能。** 2023 年最早的产品就是"公开模型排行榜"：按真实 token 用量列出哪个模型被谁用、用在什么场景。它解决的是当时最大的信息不对称"到底哪个模型好用"。Menlo 说这个榜单"成了所有 AI 工程师的家常名词"，Karpathy 公开引用；Contrary 说它是"唯一真实来源"，竞争对手没有可比资产。
2. **让模型厂商主动来。** 因为榜单聚集了最高密度的重度开发者，新模型愿意"先在 OpenRouter 上线"。OpenAI 发 GPT-4.1 前先用化名 Quasar Alpha 在 OpenRouter 上放出来收反馈，改完再以 Optimus Alpha 上线对比。每一次这样的"神秘模型"事件都是免费流量。
3. **开发者工具默认集成。** Cline、Roo Code 这类编码 agent 把 OpenRouter 做成默认供应商选项；后来 OpenClaw 一个应用就跑 20 万亿 token。榜单上还专门有"应用排行"，反过来给这些工具曝光，形成互相引流。
4. **免费层 + 免费模型。** 新用户有少量免费额度，一批模型永久免费（低限速、不适合生产），把"试一下"的门槛降到零。
5. **权力用户当测试员。** 社区（Discord）里的重度用户会最快发现新模型的怪异行为、供应商报错，等于免费 QA；OpenRouter 还托管由用户跑的开源基准。

Atallah 自己总结的原则里有两条与推广直接相关：**榜单区分"流行"和"好"**（token 量只说明有人用，不说明最合适），以及**拒绝付费排位**——"网关必须被信任能公平比较模型和供应商，中立不是政策，是产品可信度的一部分"。

---

## 四、融资路线与策略

- **先做出数据再融资。** 2023-05 成立到 2025-02 才拿种子轮，中间近两年靠产品和早期收入撑着（OpenSea 背景让创始人有底气不急着融）。第一次融资时已有 100 万开发者、用户 7 个月内推理消费涨 10 倍。
- **种子和 A 轮几乎连着。** 2025-02 a16z 领种子 1250 万，2025-04 Menlo 领 A 轮 2800 万，6 月一起公布为 4000 万、估值 5 亿。Menlo 是先通过 Anthology 基金进种子，观察到"超高速增长"后领 A 轮。
- **B 轮引入战略方。** 2026-05 CapitalG 领投，跟投名单是英伟达、ServiceNow、MongoDB、Snowflake、Databricks 的风投——全是希望自家生态里有一个中立推理入口的基础设施公司。估值一年从 5.47 亿到 13 亿。
- **退出。** B 轮后三个月内出现多家收购意向，Stripe 最终成交。Stripe 的逻辑：token 正在变成企业间"新的通用价值交换媒介"，谁负责"计量和结算推理"，谁就站在 AI 时代的支付位置。a16z 把这称为"智能网络"。

**投资人为什么愿意投（三家的原话要点）**
- a16z：模型"忽明忽暗、价格一夜变、接口各不相同"，OpenRouter 是"AI 急需的电网调度员"，处理故障切换、负载均衡、路由；已成为"可观测、监控、用量管理的控制平面"。
- Menlo：这是一个"会越来越重要的新品类"；护城河是双边网络效应 + 公开榜单形成的中立评测基础设施 + 数据资产；创始人此前做出过 140 亿美元的市场。
- CapitalG 轮的跟投方：需要一个不属于任何云、不属于任何模型厂商的入口。

---

## 五、技术优势与护城河

**技术上做对的事（来自 Atallah 的访谈整理）**
- 模型选择与供应商选择分离：开发者只选模型，OpenRouter 在底下处理供应商差异、可用性、性能。
- 接口兼容 OpenAI 格式，让人"不改应用就能试别的模型"；同时在语义层做归一（工具调用、结束原因、缓存行为、输出格式）。
- 把逻辑和缓存推到边缘，避免"路由带来的好处被路由延迟吃掉"。第三方测试仍认为它比自托管网关多 40–55 毫秒，这是它最常被攻击的点。
- 严格类型在生产事故前拦住供应商的字段变化；网关集中修复畸形 JSON 之类的窄问题，而不是让每个应用自己处理。
- 把可靠性当产品：缺陷率从 2% 降到 1%，等于工单和中断减半。

**真正的护城河不是代码，是三样别人复制不了的东西**
1. **交易规模带来的谈判力与数据。** 800 万用户、日均 1 万亿 token，让它能"预测需求、扛住负载、更容易和模型实验室谈合同"；同时积累了"提示、模型、上下文、结果"的海量真实数据，用来做智能路由。
2. **公开榜单的公信力。** 三年不卖排位，榜单成为行业默认参考，新模型主动来首发。
3. **早。** 2026 年"十几家公司都推出了自己的路由器"，但窗口只属于 2023 年就动手的人。

---

## 六、对司南实验室的启示

### 6.1 一句话判断

**OpenRouter 的本质是"中立榜单 + 交易抽成"，两者互相成全。司南今天只有前一半。** 我们有榜单、指数、检测、1800 个站的数据，但没有交易；OpenRouter 没有交易前的 2023 年，也正是靠榜单起来的。所以路线上有可学之处，但终点未必一样。

### 6.2 能直接模仿的（不花钱、不改定位）

1. **把榜单做成"行业默认引用"。** OpenRouter 的榜单之所以成为家常名词，是因为它有别人拿不到的真实用量数据。我们对应的独家数据是：1800 个站的实付价、一致性探针、Token 价格指数。每周固定出刊、永久链接、可嵌入徽章、可下载数据，这些我们已经在做；缺的是**被引用**——要主动给媒体、券商、做词元贷的银行喂数据，让"司南 Token 价格指数"出现在别人的报告里。
2. **每年一份《中国中转市场 State of AI》。** OpenRouter 用 100 万亿 token 的实证研究一次性确立了"数据权威"身份。我们可以用一年的报价、可达、检测数据做同样的事：谁在降价、哪档模型折价最深、多少站关停、Sub2API 订阅制崛起等。这是零成本的公信力放大器。
3. **让被测方主动来。** OpenRouter 让模型厂商愿意"先上 OpenRouter"；我们的对应物是让中转站愿意**主动提交、主动挂徽章、主动申请核验**。上榜徽章已有，下一步是"经司南核验"标识：站长交 Key 让我们跑一致性和能力抽样，通过的挂标。这就是 OpenRouter 的"权力用户当测试员"的反向版本。
4. **拒绝付费排位，写进宪法并公开。** 这是 OpenRouter 反复强调的可信度来源，我们的措辞宪法已经有，但要像它一样当成对外的核心卖点讲。
5. **开发者工具默认集成。** OpenRouter 借 Cline、Roo Code 起量。我们可以做一个极小的开源 CLI 或 SDK：输入站点和 Key，跑一致性、能力、延迟三项测试并出报告（站上的 /check 已有网页版）。被 Claude Code、Codex 用户的工具链引用，就是我们的"默认集成"。

### 6.3 需要慎重的（改变定位、要资金或牌照）

**做"中国版 OpenRouter"——自己当路由和结算层。** 这是最直接的"模仿"，也是最需要想清楚的：

- 有利：我们已经知道 1800 个站谁便宜、谁稳、谁一致，这正是路由器最需要的数据；Token 价格指数天然是路由的定价依据；用户已经在问"我该用哪个"。
- 不利：① 一旦自己收钱、自己路由，就不再是中立测量者，榜单公信力会受质疑（OpenRouter 被 Stripe 收购后也面临同样问题）；② 中转站市场里大量上游来路不明，做结算层等于替它们背信用风险和合规风险；③ 需要资金池、支付通道和企业资质，这不是几个月能补的。
- 一条中间路线：**只给"合规上游"做路由**（火山、百炼、硅基流动、MiniMax 等有正式定价接口的官方或一级代理），中转站部分继续只测不卖。这样榜单和交易分属两类对象，中立性可以守住。但这块市场已有硅基流动、302.ai 等玩家，OpenRouter 自己也覆盖中国模型，切入要靠我们的价格与检测数据做"按实测路由"的差异化。

**我的建议：现在不做路由，先把 6.2 做透，用 6 个月看两个信号再决定。** 信号一：指数和榜单有没有被第三方引用（媒体、报告、银行）；信号二：有没有站长主动申请核验、愿意为"经司南核验"付费。这两个信号成立，说明公信力已经变成资产，再决定是自己做结算层，还是把数据和核验卖给做结算层的人（词元贷银行、城投 Token 运营中心、企业采购）。

### 6.4 OpenRouter 路线里和我们不一样、不能照搬的

- 它面对的是**合规供应商市场**（OpenAI、Anthropic、Google 直接签约），我们面对的是**灰色中转市场**，检测与核验在我们这里是产品核心，在它那里只是运维。
- 它的用户是**开发者按量付费**，我们的用户里大量是**订阅制（Sub2API）买套餐的个人用户**，价格比较的口径完全不同，这也是为什么我们要另做套餐类。
- 它 2023 年吃到的是"模型爆发、没人能比较"的时间窗；我们 2026 年吃到的是"Token 成为计量单位、中转站爆发、没人敢担保真伪"的时间窗。窗口不同，抓法相同：**先成为那个别人都引用的尺子。**

---

## 来源

- Contrary Research，OpenRouter Business Breakdown & Founding Story：https://research.contrary.com/company/openrouter
- a16z，Investing in OpenRouter：https://a16z.com/announcement/investing-in-openrouter/
- a16z，OpenRouter & Stripe: The Intelligence Network：https://a16z.com/openrouter-stripe-the-intelligence-network/
- a16z × OpenRouter，State of AI: 100 Trillion Token Study：https://openrouter.ai/state-of-ai
- Menlo Ventures，Investing in OpenRouter：https://menlovc.com/perspective/investing-in-openrouter-the-one-api-for-all-ai/
- Menlo Ventures，Stripe to Acquire OpenRouter: Why Everyone Is Obsessed With Model Routing：https://menlovc.com/perspective/stripe-to-acquire-openrouter-why-everyone-is-obsessed-with-model-routing/
- OpenRouter，Series B 公告：https://openrouter.ai/blog/announcements/series-b/
- TechCrunch，OpenRouter more than doubles valuation to $1.3B（2026-05-26）：https://techcrunch.com/2026/05/26/openrouter-more-than-doubles-valuation-to-1-3b-in-a-year/
- TechCrunch，Stripe will reportedly acquire OpenRouter for $7B+（2026-08-16）：https://techcrunch.com/2026/08/16/stripe-will-reportedly-acquire-ai-gateway-startup-openrouter-for-7b/
- Sacra，OpenRouter revenue, valuation & funding：https://sacra.com/c/openrouter/
- Business Wire，Series B 新闻稿：https://www.businesswire.com/news/home/20260526953416/en/
- Antoine Buteau，Lessons from Alex Atallah：https://www.antoinebuteau.com/lessons-from-alex-atallah/
- Requesty，LLM 网关对比（延迟数据）：https://www.requesty.ai/blog/litellm-vs-portkey-vs-openrouter-best-llm-gateway-2026
- The Block，OpenSea co-founder Alex Atallah raises $40M：https://www.theblock.co/post/360093/
