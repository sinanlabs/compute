# 上线步骤（Eric 版 · 只做三件事）

> 三个站、三个仓库、三个 Cloudflare Pages 项目。你只需要**登录三次**，其余命令由我在这台机器上执行。

| 站 | 本地目录 | GitHub 仓库 | Pages 项目名 | 域名 |
|---|---|---|---|---|
| 母站 | `~/Desktop/claude code/sinanlab-site` | `sinanlabs/site` | `sinanlab-site` | sinanlab.com、www.sinanlab.com |
| Sinan Compute | `~/Desktop/claude code/compass` | `sinanlabs/compute` | `sinan-compute` | compute.sinanlab.com |
| Sinan Robo（占位） | `~/Desktop/claude code/sinan-robo` | `sinanlabs/robo` | `sinan-robo` | robo.sinanlab.com |

## 第 1 步 · 登录 GitHub（一次，2 分钟）

在你的终端里粘贴运行（会弹浏览器让你授权）：

```bash
brew install gh && gh auth login --web --git-protocol https
```

选 GitHub.com → HTTPS → 浏览器登录 → 复制一次性码粘进去。完成后告诉我"GitHub 好了"，我来创建/推送三个仓库。

## 第 2 步 · 登录 Cloudflare 命令行（一次，1 分钟）

```bash
cd "$HOME/Desktop/claude code/compass" && npx wrangler login
```

弹浏览器 → Allow。完成后告诉我"Cloudflare 好了"，我来创建三个 Pages 项目并部署。

## 第 3 步 · 面板里绑域名（三个项目各 30 秒）

部署完我会给你三个 `*.pages.dev` 地址。然后在 https://dash.cloudflare.com：
**Workers & Pages → 点项目 → Custom domains → Set up a custom domain**

- `sinanlab-site` 加 `sinanlab.com`，再加一次 `www.sinanlab.com`
- `sinan-compute` 加 `compute.sinanlab.com`
- `sinan-robo` 加 `robo.sinanlab.com`

每次点 Activate domain 即可，DNS 记录 Cloudflare 自动创建，证书 1–5 分钟签好。

## 第 4 步 · 安全项（各 5 分钟，可稍后）

- Cloudflare：SSL/TLS → Full (strict)；Always Use HTTPS 开；Bot Fight Mode 开
- 腾讯云：域名自动续费开、转移锁开、两步验证开
- GitHub：两步验证开

---

## 我这边执行的（供对照）

```bash
# 推送三个仓库（第 1 步之后）
cd "$HOME/Desktop/claude code/sinanlab-site" && gh repo create sinanlabs/site --private --source . --push
cd "$HOME/Desktop/claude code/compass"       && git push -u origin main
cd "$HOME/Desktop/claude code/sinan-robo"    && gh repo create sinanlabs/robo --private --source . --push

# 部署三个 Pages 项目（第 2 步之后）
cd "$HOME/Desktop/claude code/sinanlab-site" && npx wrangler pages project create sinanlab-site --production-branch main && npx wrangler pages deploy public --project-name sinanlab-site
cd "$HOME/Desktop/claude code/compass"       && npx wrangler pages project create sinan-compute --production-branch main && npx wrangler pages deploy site/dist --project-name sinan-compute
cd "$HOME/Desktop/claude code/sinan-robo"    && npx wrangler pages project create sinan-robo --production-branch main && npx wrangler pages deploy public --project-name sinan-robo
```

Compute 站的构建命令（更新数据后重跑）：`python3 site/export_data.py && python3 site/export_media.py && python3 site/export_go_links.py && python3 site/build_v5.py`，输出目录 `site/dist/`（v5 定稿视觉；build_v3.py 为旧版保留）。`/go/<域名>` 出站跳转由 `functions/go/[domain].js` 提供（Pages Functions），默认不带推广参数。

**密钥只放 Cloudflare Pages 环境变量，不进仓库。**

---

## 已完成记录（2026-09-03）

- GitHub：三个仓库已推送 —— https://github.com/sinanlabs/site · https://github.com/sinanlabs/compute · https://github.com/sinanlabs/robo
- Cloudflare Pages 已部署（直传方式，不走 Git 自动构建）：
  - 母站 https://sinanlab-site.pages.dev
  - Sinan Compute https://sinan-compute.pages.dev （含 `/go/<域名>` 跳转函数）
  - Sinan Robo https://sinan-robo.pages.dev
- 待 Eric 在面板绑定自定义域名（第 3 步）。
- 以后更新内容：重跑构建命令后 `npx wrangler pages deploy site/dist --project-name sinan-compute`（其余两个站同理）。
