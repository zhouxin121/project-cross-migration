# Changelog

## v2.5.0 (2026-09-29) · 候选提示模式（锁定脚本重设计）

### 变更（锁定脚本改为候选提示模式）

- **confirm_gate.py**：闸门状态管理 / 抽样 / 打包闸门全部真实工作；新增候选检查点模式——`--list` 与 `--set` 输出每道闸的候选验证点清单（中性列出、含正确项不标注，需按框架版本实跑核对）
- **environment_snapshot.py**：OS / Python / 工具探测照旧真实采集；未显式传 `--config-file` 时输出各框架配置文件的候选路径清单（真实路径变体 + 手动指定出口）
- **desensitize.py**：新增 `--scan` 扫描模式（疑似敏感行 + 处理方向报告，零替换）；`--share` 脱敏照旧（基础规则集）；措辞「分享包」统一为「隐私副本」
- **SKILL.md**：frontmatter 更新（description 场景化 / keywords 换血 / tested 对齐）；删「版本差异说明」节（旧 §九），代之以「装了之后你能做到什么」功能预览表；「分享」措辞全文替换为「隐私副本」
- **README.md**：整文件重写（场景白话开头 / 五层痛点表 / 实测记录保留）
- 预留链接统一指向官网部署文档页 `https://jinengpu.chat/cross-migration.html`
- examples/sample-desensitized.jsonl 更名为 sample-raw.jsonl（名实相符）
- _meta.json 新增 requires 字段（python >=3.8）

### 兼容性

- raw-v1.0 schema 不变；与 raw-conversation-backup v1.0.1、MindVault v3.1 备份包完全互认
- CLI 参数向后兼容：v2.4.x 的全部命令行用法在 v2.5.0 原样可用


### 实测记录（2026-09-29 · 测试评审独立测评，41 组机器用例全通过）

- preflight 6 组：任务名缺失 rc=2 / agent 数据目录 rc=3 / coze 警告不拦 / 正常链路建目录
- confirm_gate 16 组：G1→G5 逐道落库→--check rc=0 放行；未确认 rc=2 拒绝；--sample --seed 42 可复现；G5 自动取 source_model；--reset 打回后 --check 立即 rc=2
- desensitize 13 组：--scan 8 类规则逐行命中零替换（rc 语义修正后干净文件 rc=0）；--share 五类脱敏 + 三平台路径折叠；F9 中文紧邻回归通过；未知参数 argparse 硬拒绝（N8 修复验证）
- environment_snapshot 6 组：候选路径模式输出正确；显式传参时 source_model 提取 / api_key 黑名单拦截 / base_url 白名单保留
- validate + restore 5 组：损坏行精确定位；model_consistency_hint 写入统计；3 条示例数据全过
- 一致性 3 组：六脚本运行时自报 2.5.0；纯标准库无 3.10+ 语法；REGEX_IDENTICAL（v2.2.1 规则零缩水）
- v2.2.1 全部修复项零退化（N1/N3/N4/N5/F9）；skill-vetter 安全审查 RISK: LOW
- 测评报告：《ProjectCrossMigration-v2.5.0-测评报告.md》（含 N6-N12 缺陷清单，除 N8/N9 下版项外均已修复）
## v2.4.1 (2026-09-17) · 整合收口（v2.2.1 测评修复 × v2.3.0 确认闸门）

> 改造动因：v2.3.0 的闸门改造建立在 v2.2.1 基线上，但两轮改造之间留下了版本与文档的"接缝"——六个脚本版本号不齐（`desensitize.py` 停留在 2.2.1），`restore_dialogue.py` / `validate_jsonl.py` 连 `VERSION` 常量都没有、运行时不报版本；v2.2.1 补入 README 的「Python 3.8+」要求在 v2.3.0 文档重写时又被冲掉。本版不新增功能，只做**对账 + 收口**：确保对外交付物自洽、可追溯。

### Fixed（① 版本一致性）
- 六脚本 `VERSION` 常量统一 `2.4.1`：`preflight_check.py` / `confirm_gate.py` / `environment_snapshot.py`（2.3.0 → 2.4.0）、`desensitize.py`（2.2.1 → 2.4.0）
- `restore_dialogue.py` / `validate_jsonl.py` **补齐此前缺失的 `VERSION` 常量**，并在启动时打印版本——此前无法从运行输出确认脚本版本，排障只能靠文件 mtime
- `environment_snapshot.py` / `desensitize.py` 补齐入口版本行，六个脚本**全部可自报版本**
- 六脚本 docstring 首行的版本标注同步为 2.4.0

### Fixed（② 文档回归）
- README 补回 **Python 3.8+ 运行要求**（v2.2.1 写入后于 v2.3.0 文档重写时丢失；六个脚本仅用标准库、无第三方依赖）
- SKILL.md：frontmatter `version` → 2.4.0，description 补 v2.4 整合说明，正文"修订"段新增 v2.4 条目
- 三份文档 + 六个脚本版本号全量对齐 2.4.0

### 实测（2026-09-17 · 六脚本 23 组用例，全通过）
- v2.3.0 的 **20 组回归用例全通过**：preflight 5 / confirm_gate 6 / environment_snapshot 2 / restore 2 / validate 2 / desensitize 3
- 新增 **3 组一致性断言**：X1 六脚本 `VERSION` 常量统一 2.4.1 ／ X2 六脚本运行时可自报版本 ／ X3 文档一致性（README 含 Python 3.8+ · SKILL `version: "2.4.1"` · CHANGELOG 含 v2.4.1 且保留历史条目 · 无残留 2.3.0 版本标注）
- 环境：macOS 15.8（Darwin 24.6.0）

### 兼容性
- 备份包格式、闸门记录 `_confirm_gates.json`、环境快照 `_environment.json`、raw-v1.0 JSONL schema **均无变更**；v2.3.0 / v2.2.1 产出的包与记录直接适用


> v2.4.1（2026-09-20）：发布打包版本统一——六脚本 VERSION / SKILL frontmatter / _meta.json 对齐 2.4.1，无功能变更。

## v2.3.0 (2026-09-17) · 五道确认闸门 + 桌面落位 + 模型一致性

> 改造动因：备份/还原的关键决策原先由 Agent 一口气执行；而部分框架会把**所有对话存在同一个库里**（不按项目分目录），一旦搬错段，事后极难排查是哪一段串了。本次把关键决策拆成 5 道**必须逐道向用户确认**的闸门，并在打包口硬性拦截。

### Added（① 五道分步确认闸门）
- 新增脚本 `scripts/confirm_gate.py`（第六个脚本）：闸门记录器 + 打包闸门
  - **G1 备份范围**：确认要备份的对话 / Agent 名称与范围（会话级 / 项目级）
  - **G2 内容抽检**：`--sample --rounds 3 [--seed N]` 从 `rounds-*.jsonl` 随机抽 3 轮**完整对话**（user/agent 原文 + tool 摘要）交用户过目，确认内容如实、未串项目
  - **G3 落位确认**：确认备份位置（默认桌面；禁 agent 框架目录）
  - **G4 附件与成果**：确认附件 / `output` 前期成果是否随包复制
  - **G5 模型一致性**：告知本次备份所用模型；`--set` 不填 `--value` 时**自动取自 `_environment.json` 的 `source_model`**
  - 纪律：`--set` 一次只接受**一个** `--gate`（禁止打包前集中补签）；`--reset` 可打回待确认；记录落 `<备份目录>/_confirm_gates.json` 随包走
- **打包闸门**：`confirm_gate.py --backup-dir <dir> --check` 五道全 `confirmed` 才放行（rc=0），否则列出 pending 并 **rc=2 拒绝打包**；Step 6.5 前置强制
- SKILL.md 新增「Step 0.5 五道确认闸门」小节（实际顺序 G1 → G3 → G4 → G5 → G2，含逐道命令与 Agent 一次只问一道的纪律）

### Changed（② 备份默认落位改桌面）
- `preflight_check.py` 默认 `DEFAULT_ROOT`：`~/AgentConversationBackup` → **`~/Desktop`**（备份落在显眼位置、用户一眼能找到；`--backup-root` 仍可指向文档等位置，agent 目录依旧硬拦 rc=3）
- 结果新增 `confirm_gate_cmd` 字段（直接给出闸门记录命令）；`next` 指引补齐"G1-G5 闸门 → 导出 → 校验 → 打包（`--check` 通过）"全链路
- 文档同步：SKILL Step 0 / Step 2 / 验收第 14 项、README 快速开始与目录结构

### Added（③ 模型一致性 source_model）
- `environment_snapshot.py`：新增顶层 `source_model`（优先 `--model`，其次 `--config-file` 白名单键中的 `model`）；`notes` 追加"本次备份所用模型 + 恢复建议同一模型"
- `restore_dialogue.py`：读取 `_environment.json` 的 `source_model` → 控制台打印"模型提示"，`_restored_stats.json` 写入 `model_consistency_hint`；Phase A 预读项由三项扩为四项（+`source_model`），并回看 `_confirm_gates.json` 的确认轨迹
- SKILL.md Phase C / Phase E 第 5 步、验收清单、README 核心设计表同步

### Docs
- SKILL.md：验收清单 14 → **15 项**（+五道确认闸门全通过）；故障排查 15 → **16 条**（+跳过闸门直接打包导致串项目难排查）；§七 配套文件补 `confirm_gate.py`；评估信息块补 `confirm_gates` / `source_model` / `v230_changes`
- README：快速开始扩为五步（含闸门）；核心设计表补两行、改一行；脚本速查补 confirm_gate 段
- 三份文档 + 六个脚本版本统一 2.3.0

### 实测（2026-09-17 全量 · 六脚本 20 组用例，全通过）
- preflight 5 组 / confirm_gate 6 组 / environment_snapshot 2 组 / restore 2 组 / validate 2 组 / desensitize 3 组，明细见 README「实测记录」
- 环境：macOS 15.8（Darwin 24.6.0）

## v2.2.1 (2026-09-16) · 测评修复

> 依据《ProjectCrossMigration-v2.2.0-测评报告》（测试评审 agent-edevuv，12 组实测 + 9 组跨框架模拟）：修 P2-N1/N2、P3-N3/N4/N5，补文档边界。全量回归 11 项通过（F1/F9/增量/CRLF 无退化）。

### Fixed
- **P2-N1 preflight 漏拦 agent 数据目录**：DENY_FRAGMENTS 补 agent home 片段（/.openclaw、/.openclaw-autoclaw、/.workbuddy、/.claude 等，大小写不敏感）——备份落 agent 数据目录（随卸载消失）现返回 rc=3
- **P2-N2 restore 不认深目录布局**：find_files 增加递归回退（深度限 4 层），CherryStudio `agents/*/sessions/` 等深层布局可还原（实测 171 条含 83 tool 条目）
- **P3-N3 winpath 只护 C:\Users**：扩为任意盘符；并兼容 JSONL 双反斜杠转义形态（`D:\\data\\y.json` 也折叠，与 F3 转义引号同类问题）
- **P3-N4 Linux home 漏**：补 `/home/<name>` 折叠为 `~`
- **P3-N5 在线框架静默放行**：preflight 对 coze/dify/扣子/腾讯元器 等命中输出显式 warning（在线平台数据在服务侧、本地文件迁移架构性不可行），不拦截不影响退出码

### 文档
- SKILL.md：平台支持表明示 Coze/Dify 类 SaaS 架构性不支持；verified 更新 v2.2.1 回归口径
- README：Python 要求改 3.8+（实测五脚本 AST 无 3.10+ 语法）
- 五脚本 VERSION 统一 2.2.1

## v2.2.0 (2026-09-15) · 三项改造

> 改造动因：v2.1 把"分享场景的约束"误写成通用迁移流程（私有换机也要脱敏、凭据不入包、还原后手工回填），且备份范围缺"框架环境"，运行入口缺校验——本次一次性重划线。

### Changed（① 脱敏策略重定位为「可选分享配件」）
- **默认不脱敏**：私有备份 / 本机还原 / 自己换机场景下原文完全照搬，**凭据原样随包、恢复即用**，不再强制生成 `_credentials_needed.md`
- **分享场景显式开启**：仅当用户主动要求生成分享包时才脱敏——`desensitize.py --share` 输出 `_share/` 脱敏副本 + `_credentials_needed.md`；**无 `--share` 直接拒绝执行**（退出码 2），杜绝"顺手脱了"的误伤
- 私有包与分享包的差别收敛为一处：私有带 `credentials/` 不含 `_share/`；分享带 `_share/` 不含 `credentials/`
- 打包清单 / Step 6.5 / Phase E 凭据交接 / 验收清单第 13 项同步改写

### Fixed
- **F9 中文紧邻敏感值脱敏静默失效**：`apikey` / `email` / `openid` 三类规则原用 `\b` 词边界，Python 3 中 CJK 属 `\w`，`apikey是sk-xxxx`、`邮箱：abc@x.com` 这类中文紧邻写法取不到边界 → 改为负向断言 `(?<![A-Za-z0-9])`，中文/全角紧邻不再漏检
- 旧版 README/使用示例中的脱敏流程表述（"迁移即脱敏"）与新版定位冲突 → 全量重写

### Added（② 备份范围补「框架环境快照」）
- 新增脚本 `scripts/environment_snapshot.py`：采集 `_environment.json`，纯 Python 标准库、mac/win/linux 尽力采集
  - `frameworks`（源+目标框架名与版本）、`os`（系统/版本/架构/shell/os_detail）
  - `tools` / `tools_missing`：python3、pip3、node、npm、git、ffmpeg、rg、jq、curl 的路径与版本
  - `config_paths`：config / hooks / 权限规则的**文件路径清单**（只列路径不列值，各上限 50 条）
  - `model_config`：模型名 / base_url / endpoint / provider / max_tokens 等**白名单键**，凭据键黑名单兜底
  - 安全三道防线：目录发现只走路径不读内容 / 模型配置白名单提取 / 成品全文敏感模式自检打码
- 五层模型：L5 明确纳入 `_environment.json`；主作用声明验收标准扩为"零丢失 + 可续聊 + **环境可复现**"
- Step 6.4 环境快照（新增）；Phase A 增环境预读、Phase E 增环境对照补齐；验收清单 12 → 14 项（+环境快照对照）
- `restore_dialogue.py` 集成：包内有 `_environment.json` 时自动读取摘要写入 `_restored_stats.json`（`environment_snapshot` / `environment_hint`），并在终端打印缺失工具补齐提示；老包无该文件时给友好提示，不阻断还原

### Added（③ 运行入口规范）
- 新增脚本 `scripts/preflight_check.py`：备份前强制校验——
  - **平台框架**：源 + 目标框架名必填（版本尽力），同名（同框架换机）仅提示不拦截
  - **任务名称**：缺失即停止并索要（退出码 2），禁止 `backup` / `new` / `test` 之类占位名；限 64 字符且不含 `<>:"/\|?*`
  - **目录落位**：默认 `~/AgentConversationBackup/<任务名称>_<时间戳>/`，**显式打印绝对路径**；命中 agent 安装目录 / 数据目录 / 系统保护路径 / 安装型目录（skills、node_modules、site-packages…）即拒绝（退出码 3）
- SKILL.md Step 0 独立成节："不通过不许开工"；故障排查新增第 13-15 条（中文紧邻脱敏失效 / 备份随 agent 卸载消失 / 换机跑不起来）

### 实测（2026-09-16 全量复验 · 五脚本 12 组用例）
- preflight_check.py：5 组用例通过（正常出路径 rc=0 / 任务名缺失 rc=2 / 框架缺失 rc=2 / 备份目录落在 agent 数据目录拒绝 rc=3 / 任务名含非法字符 rc=2）
- environment_snapshot.py：macOS 15.7.9 采集成功，工具探测与缺失登记正确，`_environment.json` 生成后自检无敏感模式命中
- desensitize.py：3 组通过——无 `--share` 默认拒绝（rc=2）；`--share` 单文件下中文紧邻的 apikey·邮箱·openid·手机号·本机路径五类全部正确脱敏（F9 修复确认）；`--share --package` 整目录生成 `_share/` 脱敏副本 + `_credentials_needed.md`，非文本文件登记待人工确认，映射清单留本地不外发
- restore_dialogue.py：2 组通过——包内含 `_environment.json` 时 `_restored_stats.json` 正确写入 `environment_snapshot` 摘要并打印工具补齐提示；老包无该文件时友好提示不阻断还原
- validate_jsonl.py：2 组通过——合规 jsonl rc=0；损坏包 rc=1 并精确定位到出错行号

## v2.1.1 (2026-09-15) · 测评修复

> 依据《ProjectCrossMigration-v2.1.0-测评报告》（测试评审 agent-edevuv，8 组实测）：修 F1-F5，F6-F8 落文档。

### Fixed
- **F1 兼容性硬伤**：validate 对 MindVault OpenClaw/Marvis 模式导出包（tool 条目无 content、仅 key_param/args_summary）误报"缺 content"——现按兼容模式放行并输出 INFO 说明；SKILL.md 兼容声明同步收缩为"WorkBuddy 管道完全兼容 / OpenClaw 模式兼容还原"
- **F2 manifest 键名 bug**：email/openid/assign 三类规则的映射清单键为字面量模板而非实际占位符——登记前先 m.expand() 展开，键与正文占位符完全一致，对账功能恢复
- **F3 转义引号漏检**：assign 规则兼容 JSON 转义形态 token=\"...\"
- **F4 空分片崩溃**：restore 对 0 条记录分片给出警告，全空目录友好退出，不再抛 ValueError
- **F5 友好报错**：validate 对不存在的文件报 FAIL 计入结果（不再裸抛 traceback）；空文件输出 INFO 提示

### 文档
- F6 取舍说明：homepath/winpath 折叠为 ~ 无指纹——隐私优先，路径类不参与占位符对账（需要可对账时用 ~user<hash4>）
- F7 版本痕迹：三脚本 docstring 统一 v2.1.1
- F8 验收指引：占位符核对一律文件级/hex 级比对（平台展示层有二次遮盖）——已写入 SKILL.md 验收清单

## v2.1.0 (2026-09-15) — 已发布（applied）

> 状态：update 提案 `project-cross-migration-20260914-7405552400` 已于 2026-09-15 获批应用，live 生效。
> 已知限制：`desensitize.py` 对含省略号的截断 key（如 `sk-tes…0abc`）不做识别——此类值已被手动截断不可用，扩大正则范围会误杀正常英文文本。

基于实战反馈修订（用户发现 v2.0 设计缺陷：把"我本人迁移"的特殊场景约束写成了通用规则）。

### Added
- L4 人格层双模式：`persona-follow`（默认，换机/重装/换框架全量恢复人格四件）/ `persona-keep`（存档 `_archive/persona/`，live 不动，仅增补记忆来源约定）
- L5 工具与环境层：TOOLS.md、自装 skills/、HEARTBEAT.md、非敏感 config 入包；跨框架逐项评估兼容性后恢复
- 凭据硬红线：API key / appSecret / token / auth-profiles 永不入包，打包时排除实体并生成 `_credentials_needed.md` 缺口清单
- 打包结构新增 `persona/` 与 `tools/` 子目录
- 验收清单 10 → 12 项（+L5 工具恢复完成、+凭据零入包）
- 故障排查第 12 条：换机后人格/工具没跟上 = v2.0 L4 缺陷，按 persona-follow 重做

### Fixed
- L4 "一刀切不覆盖"改为按迁移模式决定——通用 skill 不得把单个用户的特殊场景约束写成通用规则

> **v2.2.0 回改说明**：v2.1.0 新增的"凭据永不入包 + 缺口清单"同样犯了同一类错误（把分享场景约束写成通用规则），v2.2.0 已改为"私有随包、分享才脱敏"。

## v2.0.1 (2026-09-14) · 脚本修复

> 对 live v2.0 的脚本级修复，不涉及 v2.1 提案的设计变更；随下次打包分发。

### Fixed
- `restore_dialogue.py`：兑现 SKILL.md 的布局兼容承诺——对话分片平铺或 `conversations/` 子目录均可识别（此前子目录布局报"未找到数据文件"）
- `validate_jsonl.py`：seq 校验起点不再强制为 1——中段分片 / 增量包单独校验不再误报"不连续"；组内跨文件衔接照旧严格校验；输出 seq 起止范围与增量包提示
- 测试卫生：真实备份上做脚本自测时不再污染 `_restored_stats.json`（label 用项目名，自测改用临时目录）

## v2.0.0 (2026-09-14)

基于 raw-conversation-backup v1.0.1 的项目级升级版。JSONL schema 完全兼容（raw-v1.0），老备份无需重导即可还原。

### Added
- 主作用声明：跨平台迁移"项目全部资料"——对话原文 + 记忆文件 + 项目产出，不止聊天记录
- 迁移范围模型：四层（L1 原文 / L2 项目记忆 / L3 长期蒸馏 / L4 人格）+ 一不迁（人格不覆盖）
- 隐私脱敏规范：本地全量层永不脱敏，仅"离开私有环境"时生成 `_share/` 脱敏副本；五类敏感信息（API Key / 手机号 / 邮箱 / 用户 ID / 本机路径）→ sha256 前 4 位指纹占位符
- `_manifest.json` 打包清单：逐文件 sha256，搬运后完整性校验
- 还原侧 Phase A–D 流程：源端自检 → 转移落地 → 全量还原 → 四层记忆写入
- 十项还原验收清单（三方对账 / seq 连续 / 轮次完整 / 关键内容全文抽查等）
- 脚本 `desensitize.py`：脱敏共享副本生成器 + 本地映射清单
- 脚本 `restore_dialogue.py`：可读对话稿 + 统计报告生成器
- 故障排查扩充至 11 条（新增沙箱、mtime 陷阱、摘要注入轮、grep 窄窗口漏检、大文件定位）

### Changed
- 校验脚本 `validate_jsonl.py` 重写：支持多文件跨分片 seq 全局连续性校验、round 单调校验、字段级错误定位
- 蒸馏层策略明确：L3 重新蒸馏而非搬运（旧对话结论 → 新环境认知）

### 实测
- 2026-09-12 WorkBuddy → OpenClaw/AutoClaw：146 轮 / 1418 条零丢失，validate 10 分片全通过，seq 连续，三方对账一致
- 2026-09-14 打包前全脚本实测：validate / restore 走真实备份复验通过；desensitize 五类占位符自测通过
