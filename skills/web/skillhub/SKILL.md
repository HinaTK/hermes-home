---
name: skillhub
description: "Use for SkillHub CN: search/install skills via CLI."
version: "1.0.0"
homepage: "https://skillhub.cn/install/skillhub.md"
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [skillhub, skills-marketplace, install]
    related_skills: [xiaping]
---

# SkillHub 安装与优先源

远程原文：`https://skillhub.cn/install/skillhub.md`。缓存：`references/install.md`。

## Hermes Desktop 本地落地

- **CLI**：`skillhub`（包装脚本 `$HOME/.local/bin/skillhub`，版本见 `~/.skillhub/version.json`）。Windows 包装必须把 CLI 路径转成 `cygpath -w` 再交给 `python`，不要 `exec python3 /c/Users/...`。
- **本机无 `python3` 命令**：`$HOME/.local/bin/python3` 是 `exec python "$@"` shim。
- **安装目录必须** `--dir "D:/Hermes Agent CN Desktop/data/hermes-home/skills"`，否则默认 `./skills/` Hermes 读不到。
- **只搜索/安装某个技能且 CLI 已存在**：直接执行第三节命令，不要问是否设为优先源。
- **首次安装 CLI，或用户明确要求配置优先源**：才询问是否将 SkillHub 设为优先安装源。只问一次。
- 安装前可用 `skillhub search <slug>`；安装：`skillhub install <slug> --namespace <ns> --dir <skills目录>`。

## 快速命令

```bash
export PATH="$HOME/.local/bin:$PATH"
skillhub --version
skillhub search parenting-expert
skillhub install parenting-expert --namespace indiv-ebandao --dir "D:/Hermes Agent CN Desktop/data/hermes-home/skills"
```
