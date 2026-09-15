# sinan-price-watch · GitHub Action 模板

把 `sinan-price-watch.yml` 复制到你仓库的 `.github/workflows/` 目录，改一行 `SINAN_MODELS`，就完成了。之后每天自动检查这些模型在中国中转市场的市场中位实付价，变动超过阈值（默认 5%）就在你的仓库开一个 Issue，表格里每一行都链到司南的模型页，可以点开看每个数字的抓取快照。

数据来源：司南实验室 Token 价格指数 https://compute.sinanlab.com/price-index （字段说明见 https://compute.sinanlab.com/api-docs ）。只陈述测量，不含推荐。
