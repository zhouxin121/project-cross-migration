# Project Cross-Migration v2.5.0

> 你的 Agent 跑着跑着就积累了不少东西:对话、记忆、配置,全在那儿。哪天想换个框架,或者换了台电脑,这些东西得原样跟过去,过去的过程你最好感知不到。这个包就是干这个的,免费,MIT,Python 标准库就能跑。

---

## 安装（按你的框架选一行）

| 框架 | 命令 |
|---|---|
| OpenClaw / AutoClaw | [ClawHub 搜索 project-cross-migration](https://clawhub.ai/zhouxin121/skills/project-cross-migration) |
| 任意框架（GitHub） | `git clone https://github.com/zhouxin121/project-cross-migration-free.git` 后将包目录放入你的 skills 目录 |
| 离线安装 | 下载 [Release zip](https://github.com/zhouxin121/project-cross-migration-free/releases/tag/v2.5.0)（sha256 见 Release 说明）解压即用 |

---

## 这个 Skill 解决什么问题

先讲它干嘛的。你的 Agent 攒下的东西分好几层:对话原文、记忆、人格、工具、环境,一共五层。换框架或者换机器的麻烦,不在哪一层有多难,而在这五层存法各不一样,你得一层一层摸,顺序错了就白干。这个 Skill 把五层按一个跑通过的顺序排好了,你照着走就行。

当项目"住在" AI 对话里时，资料散在五层：

| 层 | 内容 | 换框架 / 换机后 |
|---|---|---|
| **L1 对话原文** | user / agent / tool 完整记录 | 留在旧框架 / 旧机器里，新环境读不到 |
| **L2 记忆通道** | 项目上下文 / 长期蒸馏 / 人的协作偏好 | 存在于 agent 记忆文件，**无法直接迁移** |
| **L3/L4/L5 人格·工具·环境** | SOUL / 工具 / 配置 / skills | 按旧环境结构化，新环境不认 |

恢复完打开,该记的还记着,和原环境一个样。每层具体怎么走的:

- L1 原文逐字存成 JSONL,什么时候都能原样还原
- L2 记忆走 MindVault 通道加可复现环境,蒸馏不搬运
- L3 走可复现环境
- L4 工具、L5 环境按目标框架的规范恢复

这个包就一个用途:备份和迁移你自己的 Agent,恢复完原文和凭据直接能用,不用重填,也不用重新教。

---

## 兼容性边界（两句话）

**能用的范围**:本地部署的主流框架,像 Claude Code、Codex、WorkBuddy、OpenClaw 这几个,都实测过(下面有记录);另外 raw-conversation-backup v1.0.1 和 MindVault v3.1 出的备份包也认。

**用不了的只有一种**:云端部署的 agent,数据放在服务端,你机器上没有文件可备,这种得用平台自己的备份。

## 快速开始

```bash
# ① 入口校验：框架匹配 + 任务名称 + 落位（先过闸再动手）
python3 scripts/preflight_check.py \
    --source-framework "claude-code@1.0.36" \
    --target-framework "openclaw@2.3.1" \
    --task-name "我的项目"

# ② 五道闸门确认：输出各闸门的候选检查点清单（版本对照见迁移文档），逐道确认落库
#    ⚠ 逐道进行：每道闸门先向用户展示候选检查点、征得确认再落库下一道，禁止打包前集中补签
python3 scripts/confirm_gate.py --backup-dir <备份目录> --list
python3 scripts/confirm_gate.py --backup-dir <备份目录> --gate G1 --set --value "项目级"
python3 scripts/confirm_gate.py --backup-dir <备份目录> --gate G3 --set --value "~/Desktop/我的项目_20260924_1530/"
python3 scripts/confirm_gate.py --backup-dir <备份目录> --gate G4 --set --value "全部附带"
python3 scripts/confirm_gate.py --backup-dir <备份目录> --gate G5 --set --value "claude-opus-4-6"
python3 scripts/confirm_gate.py --backup-dir <备份目录> --sample --rounds 3 --seed 42

# ③ 导出后校验 + 三方对账
python3 scripts/validate_jsonl.py <备份目录>/**/*rounds-*.jsonl

# ④ 还原为可读稿 + 统计报告
python3 scripts/restore_dialogue.py --backup-dir <备份目录>
```

第⑤步是跨框架/跨机才做的,就是把记忆层和人格层还原到目标框架,做法写在 SKILL.md 的 Phase D、E 里。

## 目录结构（人类可读首页）

```
project-cross-migration/
├── README.md                        # 本文件——人类可读首页
├── SKILL.md                         # Agent 可读主文档（含备份/还原完整流程）
├── LICENSE                          # MIT
├── CHANGELOG.md                     # 版本历史
├── _meta.json                       # 元数据 + 文件校验和
├── examples/
│   └── sample-raw.jsonl             # 示例数据行（全部为虚构值）
└── scripts/                         # 纯 Python 3.8+ 标准库，macOS / Linux / Windows 均可直接运行，零第三方依赖
    ├── preflight_check.py           # 运行入口校验（平台框架 + 任务名称 + 备份目录落位）
    ├── confirm_gate.py              # 五道闸门确认（候选检查点模式：G1-G5 状态管理 + 打包 --check 硬拦）
    ├── environment_snapshot.py      # 框架环境快照采集（候选路径模式，生成 _environment.json）
    ├── validate_jsonl.py            # JSONL schema + seq 连续性校验
    ├── desensitize.py               # 隐私副本工具（--scan 扫描报告 / --share 生成脱敏副本 + 本地映射清单）
    └── restore_dialogue.py          # 还原为可读对话稿 + 统计报告（附环境快照摘要）
```

## 脚本速查

```bash
# 运行入口校验（平台框架 + 任务名称 + 备份目录落位）
python3 scripts/preflight_check.py \
    --source-framework "<框架名>@<版本>" \
    --target-framework "<框架名>@<版本>" \
    --task-name "<任务名称>"
# 退出码：0 通过 / 2 参数缺失 / 3 目录被拒（agent 安装/数据目录）

# 五道闸门确认（候选检查点模式：每道闸输出候选验证点，版本对照见迁移文档）
python3 scripts/confirm_gate.py --backup-dir <备份目录> --list       # 查看 G1-G5 状态 + 候选检查点
python3 scripts/confirm_gate.py --backup-dir <备份目录> --set G1 --value "项目级"
python3 scripts/confirm_gate.py --backup-dir <备份目录> --sample --rounds 3 --seed 42  # G2 随机抽 3 轮
python3 scripts/confirm_gate.py --backup-dir <备份目录> --check      # 打包闸门：全 confirmed → 0；pending → 2

# 框架环境快照采集（备份侧，生成 _environment.json；未指定配置文件时输出候选路径清单）
python3 scripts/environment_snapshot.py \
    --framework "openclaw" --version "2.3.1" \
    --config-file <框架配置路径> \
    --output <备份目录>/_environment.json

# JSONL 校验 + 还原 + 隐私副本
python3 scripts/validate_jsonl.py <file1.jsonl> [file2.jsonl ...]
python3 scripts/restore_dialogue.py --backup-dir <备份目录> [--out <还原稿路径>]
python3 scripts/desensitize.py --scan <文件>                                    # 只扫描出报告，不改文件
python3 scripts/desensitize.py --share --in-file <数据文件> --out-dir <备份目录>/_share
```

## Schema 字段说明（raw-v1.0）

```
顶层字段（每行 JSONL 必含）：
  schema_mode, timestamp, role, round, seq,
  content, content_length, content_truncated, raw

按角色可选字段：
  role=user   → content / reasoning
  role=agent  → content / reasoning / tool_calls / key_params / experience_markers
  role=tool   → tool_name / key_param / args_summary / files / urls / errors / content
  role=system → content / content_length / content_truncated

两条红线：
  附件必须复制（files / urls / attachments 所指文件物理搬运到备份目录）
  内容必须逐字保留（content / raw 不改写、不截断）
```

## 凭据处理

备份包里 API key 和 token 这些是留着不删的,恢复出来直接能用,谁还愿意把配置重填一遍。唯一建议:恢复完按目标框架的 secret 管理方式存一下,别一直明文躺在对话里。

## 跨框架协议

导出那端:源框架按 raw-v1.0 schema 导,scripts 里六个脚本就是这套 schema 的校验和还原实现。导入那端:按 SKILL.md 的 Phase A 到 E 走。raw-v1.0 跟 raw-conversation-backup v1.0.1、MindVault v3.1 是完全兼容的,不是"尽量兼容"那种。

## 实测记录

下面几条是我自己机器上留下的迁移记录,留着主要给后来的人对账用:迁移卡住了,先看日期和系统版本,确认自己手上的组合有没有人跑通过,跑通过就照记录里的步骤来。记录里的数字都是脚本跑出来的,不是手填的。

- 2026-09-12（macOS 15.7.9，Darwin 24.6.0）：146 轮 / 1418 条真实对话迁移还原验证——校验 1418 条全通过、L1 还原 1418/1418 逐字一致（0 损失）、L2 项目快照已生成、L3 蒸馏已生成、L4 人格文件已就位（15 项验收清单通过）
- **2026-09-15（三平台对账，macOS 15.7.9 / Ubuntu 22.04 / Windows 11 23H2）**：同一备份包三端全量跑通——校验 1418/1418 全通过、L1 还原逐字一致、15 项验收三端全通过（一键脚本已内置换行修复）
- **2026-09-18（多框架，本地部署）**：Claude Code 1.0.36 / Codex CLI / WorkBuddy / OpenClaw 2.3.1 全量迁移还原实测——逐字对账 0 差异，验收清单全通过
- **2026-09-17（macOS 15.8）v2.4.x 整合验收**：v2.3.0 的 20 组回归用例全通过（preflight 5 / confirm_gate 6 / environment_snapshot 2 / restore 2 / validate 2 / desensitize 3）＋ 新增 3 组一致性断言全通过（X1 六脚本 `VERSION` 常量统一 ／ X2 六脚本运行时可自报版本 ／ X3 文档一致性）
- **2026-09-12 行为边界修复（v2.4.0 前置，P1 测评）**：① 私有备份默认不脱敏、凭据随包、恢复即用 ② 备份范围新增 `_environment.json` 环境快照 ③ 运行入口新增 `preflight_check.py` 校验：任务名称缺失即停止＋禁止备份写入 agent 安装/数据目录 ④ 验收清单 13→15 项，故障排查 14→16 条

## License

MIT License — 详见 [LICENSE](LICENSE)

## 相关

我做的另外几个包,挨个放这儿了:

- [MindVault](https://github.com/zhouxin121/mindvault)（memory + credential 管理，L2 真相源）

---

> 更多部署详情（各框架版本对照、逐层验证标准、时间与轮次优化）：**<https://jinengpu.chat/cross-migration.html>**
