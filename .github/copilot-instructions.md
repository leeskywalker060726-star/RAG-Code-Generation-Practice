## 快速概览

这是一个使用 MkDocs + Material for MkDocs 构建的静态文档网站（页面生成器元信息显示为 mkdocs-1.4.2, mkdocs-material-8.5.11）。仓库顶层已经包含大量已渲染的 HTML 页面（例如 `index.html`、`basic/`, `dp/`, `ds/`, `tools/` 等目录），以及哈希命名的静态资源在 `assets/` 下。

要点：
- 架构：静态站点，页面由 MkDocs 生成。资源文件名通常带 hash（例：`assets/stylesheets/main.d9cc33f8.min.css`、`assets/javascripts/bundle.561f57c7.min.js`），方便缓存策略。
- 搜索：站内搜索使用 web-worker（例如 `assets/javascripts/workers/search.8e7a41fd.min.js`）。
- PWA：注册了 `service-worker.js`，存在 `manifest.webmanifest`，站点启用离线/缓存策略。
- 部署：页面包含 Netlify、Docker 指南线索（参见 `intro/docker-deploy` 页面），并有 `CNAME`、`_redirects`、`redirect-nginx.conf` 等部署相关文件。

## 推荐的开发者工作流（可直接执行）

环境假设：Python 3.8+ 可用且 pip 可用（因 MkDocs 基于 Python）。若你发现本仓库只是“已构建的站点”，请优先确认上游源码仓库（OI-wiki/OI-wiki）以进行内容编辑。

在本地预览（PowerShell 示例）：

```powershell
# 安装指定版本以保证一致性
pip install mkdocs==1.4.2 mkdocs-material==8.5.11

# 在本地启动实时预览（会监听 docs/ 内容并在修改时热重载）
mkdocs serve -a 127.0.0.1:8000

# 生产构建到默认 site 目录
mkdocs build -d site
```

如果你需要用 Docker 部署或查看已有部署说明，请打开 `intro/docker-deploy/` 页面（仓库内已生成的 HTML 位于 `intro/docker-deploy/index.html`）。

注意：有时仓库内为已渲染的站点而非 Markdown 源（本工作区包含大量 HTML）。如果你打算修改文章源文件，先确认是否存在 `docs/` 或 `site/` 的源头，或直接在 GitHub 上访问 https://github.com/OI-wiki/OI-wiki（页面顶部 source 链接通常指向该仓库）。

## 代码与资源约定（项目特有）

- 目录映射：每个主题（如 `basic/`, `dp/`, `ds/`, `tools/`）为一组页面的静态输出。编辑时应定位对应的 Markdown 源（通常位于 upstream 的 `docs/` 目录）。
- 静态资产：所有 CSS/JS 经过打包并带哈希，修改前需重建打包（即 run `mkdocs build` 或上游的构建脚本）。
- 搜索索引：站内搜索通过 worker 加载预构建索引文件，修改结构后需重新生成并部署相关 worker 文件。
- PWA & Analytics：页面引入 Google Analytics 脚本及 PWA 注册，调试时注意这些脚本可能会影响本地控制台日志或缓存行为。

## 常见任务的具体文件/路径参考

- 本地主页（示例）： `index.html`
- 全站样式/脚本： `assets/stylesheets/`、`assets/javascripts/`（注意 hash）
- PWA： `service-worker.js`, `manifest.webmanifest`
- 部署相关： `CNAME`, `_redirects`, `redirect-nginx.conf`
- Docker 教程页面（HTML）： `intro/docker-deploy/index.html`
- 站内搜索 worker： `assets/javascripts/workers/search.*.min.js`

## 编辑建议与 AI 助手使用提示（针对 Copilot / 代码生成）

- 不要直接修改编译输出（*.html、带 hash 的 assets）。如果目标是更改页面内容或结构，优先定位并修改源 Markdown（如果在此仓库中没有，请在 upstream repo 查找）。
- 修改任何静态资源（CSS/JS）后，应运行完整构建以更新哈希并验证站点：`mkdocs build`。如果构建在 CI 中有额外脚本，参考仓库 README（或上游仓库）以获得精确构建步骤。
- 当生成或替换静态资源时，保持原有缓存友好策略（不要删除未被替换的哈希文件，除非整个构建产物都同步更新）。
- 搜索与索引：若更新大量页面结构，确保重新生成搜索索引 worker 文件并部署。

## Docker 部署（可复制命令）

下面是从仓库生成站点页面（`intro/docker-deploy`）提取的常用 Docker 命令示例，方便在需要快速部署/测试时参考。请注意这些命令应在主机（非容器内）运行，且需要 root 或 docker 组权限。

常见镜像拉取：

```powershell
# Docker Hub（官方）
docker pull 24oi/oi-wiki

# DaoCloud（国内）
docker pull daocloud.io/sirius/oi-wiki

# 腾讯云镜像（国内）
docker pull ccr.ccs.tencentyun.com/oi-wiki/oi-wiki
```

本地构建镜像（从源代码克隆并构建）：

```powershell
git clone https://github.com/OI-wiki/OI-wiki.git
cd OI-wiki/
docker build -t <name>[:tag] . --build-arg WIKI_REPO=https://hub.fastgit.xyz/OI-wiki/OI-wiki.git --build-arg PYPI_MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple/
```

运行容器示例（将容器 8000 端口映射到主机）：

```powershell
docker run -d -it -p <host_port>:8000 --name <container_name> <image>
```

进入正在运行的容器：

```powershell
docker exec -it <container_name> /bin/bash
```

容器内常用脚本（容器镜像内包含的 helper 脚本）：

```powershell
# 更新仓库（容器内）
wiki-upd
# 构建 mkdocs（容器内，会在 site/ 目录生成静态页面）
wiki-bld
# 构建并渲染 MathJax（容器内）
wiki-bld-math
# 运行服务器（容器内）
wiki-svr
```

停止 / 启动 / 删除 / 删除镜像：

```powershell
docker stop <container_name>
docker start <container_name>
docker restart <container_name>
# 删除容器（先停止）
docker rm <container_name>
# 删除镜像（请先删除使用该镜像构建的容器）
docker rmi <image>
```

把这些命令加入 Copilot 指导文档可以让 AI 更容易给出可执行的建议；仍然提醒：如果你要修改页面内容，请在源码仓库（如 OI-wiki/OI-wiki）中的 Markdown 源头修改并重新构建，而不是直接编辑渲染后的 HTML 或带 hash 的静态资产。

## 发现与限制

- 本工作区里包含大量已渲染的 HTML 页面；仓库可能是站点发布副本。上游源（Markdown、构建脚本、CI 配置）可能在另一个仓库（参见页面顶部的 GitHub 链接指向 `OI-wiki/OI-wiki`）。在进行内容修改前，请确认你是否在正确的源码仓库中工作。

如果有想要我补充的领域（例如：定位 Markdown 源的位置、CI/CD 流程、或把编辑/构建脚本加入到本仓库），告诉我你想要达成的具体目标，我会继续补充和改写这份说明。
