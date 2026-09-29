# 分发渠道状态（Project Cross Migration）

> 手册执行追踪 · 制作 agent 维护 · 更新 2026-09-29 15:20

| 渠道 | 状态 | 链接/证据 | 日期 |
|---|---|---|---|
| GitHub repo | ✅ | https://github.com/zhouxin121/project-cross-migration-free （main 616c475；README 含安装速查表） | 2026-09-29 |
| GitHub Description | ✅ | 「Agent 项目资料跨框架迁移：五层备份还原…1418 条零丢失…MIT」 | 2026-09-29 |
| GitHub Topics ×10 | ✅ | agent / agent-skills / claude-code / codex / pi / openclaw / migration / backup / skill / cross-platform | 2026-09-29 |
| GitHub Release v2.5.0 | ✅ | https://github.com/zhouxin121/project-cross-migration-free/releases/tag/v2.5.0 · 资产 zip 回读 sha256 `8b33038a…` 与基线一致 | 2026-09-29 |
| Gitee 镜像 | ✅ | https://gitee.com/aijineng/project-cross-migration-free | 2026-09-29 |
| GitCode 镜像 | ✅ | https://gitcode.com/aijineng/project-cross-migration-free | 2026-09-29 |
| ClawHub 2.5.0 | ⏳ | 已受理待安全扫描（versionId k979wpqx…，页面 og 已翻 2.5.0）：https://clawhub.ai/zhouxin121/skills/project-cross-migration | 2026-09-29 |
| SkillHub 2.5.1 | ⏳ | 待审（skillId=255784）：https://www.skillhub.cn/skills/project-cross-migration | 2026-09-29 |
| npm / pi | 🚫挂起 | 包已备好（.openclaw/tmp/npm-pcm，dry-run 结构通过）；**npm 未登录**（NPM_NO_AUTH），待老周 `npm login` | 2026-09-29 |
| install-hermes.sh | ✅ | 全链路 curl\|bash 测过：11 文件落位 ~/.hermes/skills/project-cross-migration/；幂等重跑 9 个 ✓ | 2026-09-29 |
| install-dsh.sh | ✅ | 本地测试通过：落位 ~/.dsh/skills/project-cross-migration/（SKILL.md/scripts/examples 齐全） | 2026-09-29 |
| awesome PR：VoltAgent/awesome-openclaw-skills | ⏳ | PR #584：https://github.com/VoltAgent/awesome-openclaw-skills/pull/584 | 2026-09-29 |
| awesome PR：ComposioHQ/awesome-claude-skills (75.8k⭐) | ⏳ | PR #2039：https://github.com/ComposioHQ/awesome-claude-skills/pull/2039 | 2026-09-29 |
| awesome PR：composio-community/awesome-codex-skills (16.7k⭐) | ⏳ | PR #312：https://github.com/composio-community/awesome-codex-skills/pull/312 | 2026-09-29 |
| awesome PR：BehiSecc/awesome-claude-skills (10.2k⭐) | ⏳ | PR #799：https://github.com/BehiSecc/awesome-claude-skills/pull/799 | 2026-09-29 |
| Discord 帖 | 📝草稿 | 见下（待老周批准后手动发） | 2026-09-29 |
| 知乎/CSDN 教程评论 | 📝草稿 | 见下（待老周批准） | 2026-09-29 |

## 基线差异说明（重要）

skill workspace 基线 zip（`8b33038a…`，12 文件）与本 agent conv 目录 zip（`ac6603e3…`，13 文件）**内容有 7 文件差异**：差异全部来自 N6-N12 修复后的文本修正（SKILL.md 措辞收紧、CHANGELOG 实测段改写、_meta.json sha256 重算）+ 本地多 `release_check.py`。**GitHub 仓库主线=本地 13 文件版**（2.5.0 修复后真身，commit 03ed316）；**Release 资产=skill 基线 12 文件版**（手册红线：基线只读，资产 sha256 必须等于 `8b33038a…`）。两者 CHANGELOG 各自与自身包内文件一致，不构成版本冲突；如需统一走 v2.5.1 修复单流程。

## Discord 帖草稿（中英双语，待批）

```
📦 project-cross-migration v2.5.0 —— 把 Agent 项目完整搬到新框架/新电脑

五层迁移：对话原文 / 项目记忆 / 人格 / 工具 / 环境快照，逐字还原、恢复即用。
实测：1418 条真实对话三平台迁移零丢失（macOS/Ubuntu/Win11）；Claude Code / Codex / OpenClaw 多框架验证；2026-09-29 独立测评 41 组用例全通过。
新增：五道确认闸门（防串项目）、环境快照、--scan 隐私扫描。纯 Python 标准库，无依赖。

安装：
· OpenClaw：ClawHub 搜 project-cross-migration
· GitHub：github.com/zhouxin121/project-cross-migration-free（Release zip / git clone 均可）
MIT · 免费 · 完整部署文档见 jinengpu.chat/cross-migration.html

📦 project-cross-migration v2.5.0 — Move your agent's full project to a new framework/machine
Five-layer migration: conversations / memory / persona / tools / environment snapshots. Restored byte-for-byte, ready to use.
Proven: 1,418 real messages migrated across 3 platforms with zero loss; verified on Claude Code / Codex / OpenClaw; independent review 2026-09-29, 41 test cases all passed.
Pure Python stdlib, no dependencies. MIT, free.
```

## 知乎/CSDN 评论草稿（待批）

> 换框架/换电脑时 Agent 的对话记录和记忆怎么搬？我们做了个开源工具 project-cross-migration（MIT，纯 Python 标准库）：五层备份还原（对话/记忆/人格/工具/环境），1418 条真实对话三平台迁移零丢失。Hermes 用户一行脚本装：`bash <(curl -s https://raw.githubusercontent.com/zhouxin121/project-cross-migration-free/main/scripts/install-hermes.sh)`
