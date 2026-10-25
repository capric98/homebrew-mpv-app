# homebrew-mpv-app

[English](README.md) | 简体中文

个人维护的 Homebrew Tap，将 **mpv 项目提供的完整 macOS App 构建**安装到 `/Applications/mpv.app`。

**本仓库与 mpv、Homebrew 官方没有隶属关系，也不代表它们。** 下载来自 [`mpv-player/mpv`](https://github.com/mpv-player/mpv/releases/latest) 的稳定版 Release，没有重新打包播放器，不依赖 Homebrew 的 `mpv` Formula。

## 安装与升级

```bash
brew install --cask capric98/mpv-app/mpv-app
```

如果 `/Applications/mpv.app` 是手动安装的，先移到别处，避免同名冲突。安装后确认 App 能播放，再按需卸载 Formula：

```bash
brew uninstall --formula mpv
```

若 Homebrew 提示其他软件仍依赖 Formula，请保留它，不要强制删除。本 Cask 不创建终端里的 `mpv` 命令；可以直接运行 App 内的程序：

```bash
/Applications/mpv.app/Contents/MacOS/mpv --version
```

以后正常升级即可：

```bash
brew update
brew upgrade --cask capric98/mpv-app/mpv-app
```

卸载：`brew uninstall --cask mpv-app`。配置目录 `~/.config/mpv/` 不会删除。

更新脚本分别为 Apple Silicon 和 Intel 选择支持最低 macOS 版本的构建，以扩大兼容范围。具体版本和系统要求以 Cask 定义为准。

## GitHub Actions 自动维护

`.github/workflows/update.yml` 每天 **07:23 UTC** 检查一次最新稳定版，也支持在 **Actions → Update mpv app → Run workflow** 中手动运行。可以手动运行一次确认权限和环境正常。

有更新时，工作流会：

1. 检查版本、下载域名、两种架构的附件和 GitHub 提供的 SHA-256。
2. 下载 Apple Silicon 与 Intel 两个 ZIP，计算 SHA-256，并检查 ZIP 内的 `mpv.tar.gz` 包含完整 App。
3. 运行更新器测试、检查 Cask 的 Ruby 语法，然后由 `github-actions[bot]` **直接提交并推送到默认分支**。

没有变化时，不下载附件、不创建提交；任何一项验证失败，都不会提交 Cask。自动更新仅修改 Cask，不会远程更新你的 Mac；Mac 上仍需运行 `brew update` / `brew upgrade`。

工作流使用 GitHub 自动提供的 `GITHUB_TOKEN`，请求 `contents: write`，**不需要额外 Secret 或 PAT**。仓库/组织策略需要允许 Actions 运行并写入仓库。如果默认分支禁止机器人直接推送，自动更新会失败；这种情况下应把流程改为创建更新 PR，再按你的分支规则合并。

使用 `GITHUB_TOKEN` 推送的提交不会再触发普通 `push` 工作流，因此更新工作流本身已经运行测试和语法检查。`validate.yml` 则检查你手动推送的更改和普通 PR。

GitHub 定时任务只在默认分支上运行，执行时间可能延迟；公开仓库连续 60 天无活动时，定时任务可能被自动禁用，需要在 Actions 中重新启用。

## 平时需要维护什么

正常情况下，Actions 会维护版本号、URL、SHA-256 和最低系统要求，你只需要留意 Actions 失败通知。

这些变化需要人工处理：

- mpv 改了附件命名、压缩包结构或不再提供某种架构。
- 新的 macOS 版本尚未加入脚本的 `MACOS_NAMES` 映射。
- 同一版本的附件校验值发生变化：脚本会拒绝静默替换，应先查明上游为什么重传。
- 默认分支的保护规则阻止自动提交，或定时任务被禁用。

只跟随正式稳定版；不会跟随每日变化的 `git-release` 开发构建。固定版本和校验值，不使用 `version :latest` 或 `sha256 :no_check`。

本地检查和更新：

```bash
cd ~/Git/homebrew-mpv-app
python3 -m unittest discover -s tests -v
python3 scripts/update.py --check  # 0=已是最新；1=可更新；2=检查失败
python3 scripts/update.py         # 有变化时下载校验，然后更新 Cask
git diff -- Casks/mpv-app.rb
```

本地脚本使用 Python 3.9 或更新版的标准库，无需安装 pip 依赖。若 GitHub API 达到未认证请求频率限制，可以通过环境变量 `GITHUB_TOKEN` 提供令牌；不要把令牌写入仓库。下载包本身不会收到这个 API 令牌。

GitHub Actions 的 checkout 固定到 commit SHA；Dependabot 每月检查 Actions 的版本更新。

## Gatekeeper

App 来自 mpv 项目，不代表它一定经过 Apple 开发者签名/公证。这个 Cask 保留默认安全检查，不自动执行 `xattr` 或关闭 Gatekeeper。若首次启动被拦截，请先核实来源并查看“系统设置 → 隐私与安全性”中的提示。下载校验值只能确认字节与发布附件一致，不等于 Apple 公证。

## 参考

- [mpv 安装说明](https://mpv.io/installation/)
- [mpv 最新稳定版](https://github.com/mpv-player/mpv/releases/latest)
- [Homebrew Cask Cookbook](https://docs.brew.sh/Cask-Cookbook)
- [GitHub Actions 的 schedule 事件](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [使用 GITHUB_TOKEN 触发工作流的限制](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow#triggering-a-workflow-from-a-workflow)
