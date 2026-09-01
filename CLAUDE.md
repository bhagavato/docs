# Bhagavato Docs

基于 [OINK](https://oink.pgsty.com) 主题的个人文档站，由
[`pgsty/oink-starter`](https://github.com/pgsty/oink-starter) 模板创建。
生产地址 <https://docs.arahato.com/>。

主题实现不在本仓库，它以 Hugo Module 形式在 `go.mod` 里被锁定版本消费。主题的
文档与源码在上游 `oink.pgsty.com` / `pgsty/oink`，本地另有一份克隆在
`~/Base-Infra/GitHub/my-docs`。

## 构建

CI 与本地必须用同一条命令，`--panicOnWarning` 意味着有警告即失败：

```bash
hugo --cleanDestinationDir --gc --minify --environment production \
  --printPathWarnings --panicOnWarning
```

这个仓库**没有 `package.json`**——`npm test` 那套检查属于上游 `oink.pgsty.com`，
不在这里。严格构建就是本仓库的验收手段。

不要提交 `public/`、`resources/`、模块缓存，或本地的 module replacement。

## 语言

中文是 `defaultContentLanguage`，服务于 `/`；英文在 `/en/`。法文在 `hugo.yaml` 里
仍然声明，但由 `disableLanguages` 关闭，好让 Hugo 把 `.fr.md` 认作被禁用的译文而
不是未知页面。

因此**无后缀的 `page.md` 是中文**，英文是 `page.en.md`，法文是 `page.fr.md`。

> [!DANGER] 改 `defaultContentLanguage` 必须同时重命名文件
> 只改配置会静默毁掉另一种语言：无后缀文件被重新判给新的默认语言，与显式加后缀的
> 同名文件撞键，Hugo 保留一份、丢掉另一份，**不发任何警告**，`--panicOnWarning`
> 也照常通过。实测把默认语言从 en 改到 zh，英文站从 91 页塌到 12 页而构建全绿。
>
> 正确做法是在同一个提交里按顺序重命名（反过来会在中途撞名）：
> 先把无后缀文件加上旧默认语言的后缀，再把新默认语言的文件去掉后缀。
> 验收标准是构建表里的**各语言页数与改动前镜像对称**，不是「构建成功」。

## 内容结构

```
content/
  blog/                 博客
  docs/                 文档
  book/                 Starter 自带的教程书
  nirodha/              苦的止息 —— 南传佛教典籍文库
    dipani/             三十七道品导引手册（已发布）
    local/              仅本地，见下
```

`nirodha` 取自第三圣谛「苦灭圣谛」（*dukkha-nirodha-ariya-sacca*）。文库以目标命名，
其下的书讲的是通往它的道路（道谛 *magga*）。

一本书就是一个普通的 Hugo section，书根用 `type: book` 加 `cascade`，章用
`book_kind: chapter` 与 `book_number`。`book_number` 手写，主题不按目录顺序自动编号。

### `linkTitle` 与面包屑

面包屑沿 `.Parent` 上溯到首页为止，**每一级都渲染 `.LinkTitle`**；没有显式设置
`linkTitle` 的页面，这个字段回退到 `.Title`。所以当某一章的标题与它所属书的
`linkTitle` 相同时，面包屑会出现重复，需要给那一章单独设 `linkTitle`。

`.Title` 用于页面 `<h1>` 与 `<title>`，`.LinkTitle` 用于导航、目录与翻页器。

### 只在本地保留的内容

任何名为 `local` 的目录都被 `.gitignore` 排除，不入库因而也不会被部署。用于著作权
完整保留、仅供个人阅读的副本，以及只在本机跑的工具。

> [!IMPORTANT] 忽略规则本身是公开的
> 本仓库公开。忽略规则只写通用路径，**不要在里面写具体书名、ISBN 或作者**——那等于
> 在公开仓库里宣告本机持有哪本书的副本。需要更具体的规则时放
> `.git/info/exclude`，git 无法追踪它。
>
> 同理，已入库的页面不要链接到 `local/` 下的内容：那个路径只在本地存在，线上会 404。

## 部署

推送到 `main` 触发 `.github/workflows/cloudflare-pages.yaml`：在 GitHub Actions 里
做严格构建，再用 Wrangler 把 `public/` 上传到 Cloudflare Pages（Direct Upload）。

| 设置 | 类型 | 值 |
| --- | --- | --- |
| `CLOUDFLARE_API_TOKEN` | secret | 权限为 Account → Cloudflare Pages → Edit |
| `CLOUDFLARE_ACCOUNT_ID` | secret | Cloudflare 账号 ID |
| `CLOUDFLARE_PROJECT_NAME` | variable | `bhagavato-docs` |
| `CLOUDFLARE_SITE_URL` | variable | `https://docs.arahato.com/` |
| `CLOUDFLARE_PAGES_ENABLED` | variable | `true` |

Cloudflare 项目名刻意不等于仓库名：`pages.dev` 子域全网唯一，`docs.pages.dev` 已被
占用，`CLOUDFLARE_PROJECT_NAME` 就是为解耦这两者而存在的。

**`hugo.yaml` 的 `baseURL` 必须与 `CLOUDFLARE_SITE_URL` 保持相同**，否则构建出的
绝对地址与实际部署地址不一致。

`.github/workflows/github-pages.yaml` 作为备选路径保留，但由 `GITHUB_PAGES_ENABLED`
控制，默认不与 Cloudflare 部署并行。把该变量设为 `true` 即可切换托管方。

### 推送前

本地工作区可能含有 `local/` 下不会被部署的内容，所以本地构建结果不等于线上形态。
要验证线上真实产物，用一份干净克隆单独构建：

```bash
git clone --no-hardlinks . /tmp/cibuild && cd /tmp/cibuild
GOWORK=off HUGO_MODULE_WORKSPACE=off hugo --cleanDestinationDir --gc --minify \
  -e production --printPathWarnings --panicOnWarning --baseURL https://docs.arahato.com/
```

必须用 clone 而不是 `git archive`：`enableGitInfo: true` 需要 `.git` 才能取「最后
修改时间」，归档解出来的目录没有它，构建会以 `Failed to read local Git log` 中止。

## 从 PDF 加一本书

流水线与注意事项见 [`tools/README.md`](tools/README.md)。章节 front matter 以
`tools/*.py` 里的配置为准，直接编辑生成的 `.md` 会在重跑时被覆盖。
