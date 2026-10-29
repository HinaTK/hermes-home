---
name: skill-installation
description: "Use when installing agent skills from GitHub or SkillHub."
---

# 安装第三方 Agent Skill（SkillsMP / SkillHub）

适用：用户给出 GitHub skill URL、skillsmp.com/skill-install/prompt.md 链接、或 `@namespace/skill-name` 并要求安装。不适用：本仓库内自写 SKILL.md（走 hermes-agent-skill-authoring）。

## 通用原则（两种来源都适用）

1. **只装用户点名的那一个**。URL 指到仓库根时才列可选清单让用户挑；点名了就不再问。
2. **先看源再动手**：确认 SKILL.md 真实存在、目录内有哪些伴随文件（references/ scripts/ templates/），源目录只有一个 SKILL.md 就装那一个，不凭 README 描述发明文件。
3. **固定修订**：从 GitHub 装时用具体 commit SHA 的 raw URL（`raw.githubusercontent.com/<org>/<repo>/<sha>/<path>`）下载，不用可变分支；提交信息里带上 SHA。
4. **逐字节校验**：装完后 `sha256sum` 对比下载文件与落盘文件，确认未篡改未修改。frontmatter 必含 `name`，正文结构完整（UTF-8 中文正常、章节数合理）。
5. **装完整目录，不只拷 SKILL.md**。
6. **带脚本的 skill 必须实跑验证**：至少执行一次入口脚本（用临时输出路径），确认能产出非空数据；脚本能跑但数据全空 / errors[] 非空时，如实披露"数据链路未打通"及缺口（如缺依赖包），不得报"装好即能用"。文件存在 ≠ 可用。
7. **如实区分**：已完成的安装 vs 仍需用户操作的步骤（装依赖、修网络）。

## 目标目录选择（用户已纠正过，重要）

**默认装 hermes home 全局目录**：`D:/Hermes Agent CN Desktop/data/hermes-home/skills`

- 本用户的交易/投研类 skill 全部在 hermes home，聊天与飞书会话要随时可用。
- 不要按 SkillsMP prompt.md 的"默认项目级"机械执行——那不是本用户想要的默认（2026-10-22 因装错到 `D:\Code\AH_analyse\skills\` 被用户质疑"为什么不放 hermes home"）。
- 代码仓库内副本仅当用户明确要留档/提交时才放，且说明两处并存。
- 若用户明确指定其他作用域，按指定的来。

## 流程 A：SkillsMP / GitHub URL

1. `web_extract` 取 `https://skillsmp.com/skill-install/prompt.md` 与目标 skill 目录页（GitHub 页面即可看到文件清单与最新 commit SHA）。
2. 用 raw URL + SHA 下载到 `$LOCALAPPDATA/Temp`，校验字节数与开头内容。
3. 落盘到目标目录（`skills/<skill-name>/SKILL.md` + 伴随文件按源目录结构）。
4. frontmatter/结构校验 → sha256 对比 → 实跑验证（若有脚本）。
5. 用户有"自动 commit+push"偏好的仓库（如 AH_analyse）里放的副本：只 add 该 skill 目录，不要 `git add -A`。

## 流程 B：SkillHub CN（`@namespace/skill-name`）

CLI 在 `~/.skillhub/`（`skills_store_cli.py`），包装脚本 `$HOME/.local/bin/skillhub` 有实机 bug：MSYS 路径转换被禁，`exec python3 "${CLI}"` 把 `$HOME` 路径传给 python 变成 `D:\c\Users\...`，报 `can't open file`。

**可靠命令（2026-10-22 验证）**：`cd ~/.skillhub && python skills_store_cli.py <cmd>`（cwd 相对路径不经转换）。

```bash
# 搜索
skillhub search etf-value-analyzer           # 若包装脚本坏了用：cd ~/.skillhub && python skills_store_cli.py search etf-value-analyzer
# 安装（必须 --dir 指向 hermes home）
python skills_store_cli.py install <slug> --namespace <ns> --dir "D:/Hermes Agent CN Desktop/data/hermes-home/skills"
```

- 只搜索/安装且 CLI 已存在 → 直接执行，不问是否设优先源。
- 落盘布局：`<dir>/@<namespace>/<slug>/`（命名空间子目录）。
- 装完 `find <dir>/@<ns>/<slug> -type f` 核对完整文件清单。

## 装后对比分析（用户带过的需求模式）

用户常要求"新装的 skill 和已有 skill 比差别、找互补且不破坏彼此逻辑"。交付结构：

1. 安装结果表（源、修订/版本、位置、文件清单、实跑验证结果）。
2. 差别对比表（基因/方法/时间维度/数据要求/严谨机制）。
3. 互补性论证——**重点回答"为什么不会互相破坏"**：评分体系是否作用在同一对象、否决项是前置还是矛盾、估值/取数口径是否冲突；串联决策链图。用户明确怕"加了点东西就造成漏洞"，必须正面论证而非泛泛说"互补"。
4. 如实披露本机缺口（未装依赖、接口连通性）。

## 装后口碑核查（用户说"帮我看下评价"）

2026-10-27 实战验证的两平台核查路线：

1. **定位线上身份**：拿本地 SKILL.md 的名称/description 去两平台搜索（虾评 `GET /api/skills/search?q=`；SkillHub `https://lightmake.site/api/v1/search?q=`）匹配出 slug / skill_id。本地同名 ≠ 同款，先比对描述。
2. **虾评**：`GET https://xiaping.coze.com/api/skills/{skill_id}` → `review_summary`（官方对全量评论的 LLM 提炼：overall / concerns / highlights / best_use_cases，附 review_summary_review_count）+ avg_stars / weighted_score / trusted_score / comment_count。**评论列表接口 `GET /api/skills/{id}/comments` 实测返回 500 Internal server error，别用它。**
3. **SkillHub**：`GET https://api.skillhub.cn/api/v1/skills/{slug}` → stats（downloads/installs/stars/comments）+ securityReports（keen/sanbu）+ owner + latestVersion（changelog）。skillhub.cn / lightmake.site 网页版是 JS 渲染，web_extract 只能拿到 page not found，走 API。
4. **交叉判断**：星率（stars÷downloads）和文字评论数看参与度——例：11.6万下载但 0 条文字评论 → 下载量参考价值存疑；`updatedAt` 看维护状态；安全扫描照实报。
5. **交付**：表格对比（线上身份/下载/星/评论/评分/安全/维护），评语引用官方 review_summary 摘要，明确区分"有口碑背书"与"零评价无背书"。
