#!/usr/bin/env python3
"""confirm_gate.py — 五道分步确认闸门（project-cross-migration v2.5.0 · 候选检查点模式）

为什么需要它:
  部分框架会把**所有对话存在同一个库里**（不按项目分目录），备份/还原一旦出错，
  事后极难排查到底是哪一段搬错了。所以 v2.3 起，把"动手前 / 打包前"的关键决策
  拆成 5 道**必须逐道向用户确认**的闸门，由 Agent 分步征询、逐道落库，禁止一把梭：

  G1 备份范围    —— 确认要备份的对话 / Agent 名称，界定范围（会话级 or 项目级）
  G2 内容抽检    —— 备份完成后随机抽若干轮完整对话给用户过目，确认内容如实、未串项目
  G3 落位确认    —— 确认备份位置（默认桌面；禁止落在 agent 框架安装/数据目录）
  G4 附件与成果  —— 确认附件 / output 前期成果是否随包一并复制
  G5 模型一致性  —— 告知本次备份所用的模型，恢复时建议用同一模型

本脚本是这 5 道闸门的**记录器 + 打包闸门**：Agent 每向用户确认一道就落库一道；
`--check` 在打包前（Step 6.5）运行，5 道全 confirmed 才放行（退出码 0），
否则退出码 2 并列出未确认项，拒绝打包。

用法:
  # 1) 查看闸门定义与当前状态（不指定 --backup-dir 时只显示定义）
  python3 confirm_gate.py --list [--backup-dir <dir>]

  # 2) 逐道确认（Agent 征得用户同意后调用，一次只落一道）
  python3 confirm_gate.py --backup-dir <dir> --gate G1 --set --value "范围: 项目级…"

  # 3) 随机抽检（辅助 G2：把真实内容摆给用户看）
  python3 confirm_gate.py --backup-dir <dir> --sample --rounds 3

  # 4) 打包前校验（Step 6.5 前置；未全确认拒绝打包）
  python3 confirm_gate.py --backup-dir <dir> --check

退出码: 0 = 通过（查询 / 单道落库成功 / --check 时五道全确认）; 2 = 打包闸门未通过 / 参数缺失 / 目录不存在

设计纪律:
  - 逐道确认、逐道落库：一次 --set 只接受一个 --gate，禁止在打包前集中补签；
  - 记录文件 <backup_dir>/_confirm_gates.json 随备份包落位，还原侧可回看确认轨迹；
  - 本脚本不替用户做决定：--value 应来自用户的实际回复。
"""
import argparse
import json
import os
import random
import re
import sys
from datetime import datetime

VERSION = "2.5.0"
SCHEMA = "confirm-gates/1.0"
GATE_FILE = "_confirm_gates.json"
JSONL_RE = re.compile(r"rounds-(\d+)-(\d+)\.jsonl$")

GATES = [
    ("G1", "备份范围", "确认要备份的对话 / Agent 名称与范围（会话级 or 项目级）",
     "例: Agent=marvis-main；范围=项目级（L1+L2+L4+L5+output）"),
    ("G2", "内容抽检", "备份完成后随机抽若干轮完整对话给用户过目，确认内容如实、未串项目",
     "先跑 --sample 出样，用户过目后再 --gate G2 --set"),
    ("G3", "落位确认", "确认备份位置（默认桌面；禁止落在 agent 框架安装/数据目录）",
     "例: ~/Desktop/<任务名>_<时间戳>/"),
    ("G4", "附件与成果", "确认附件 / output 前期成果是否随包一并复制",
     "例: 附件=是；output=是"),
    ("G5", "模型一致性", "告知本次备份所用的模型，恢复时建议用同一模型",
     "例: 模型=deepseek-chat（可取自 _environment.json 的 source_model）"),
]
GATE_MAP = {g[0]: g for g in GATES}
GATE_IDS = [g[0] for g in GATES]

# v2.5.0 候选检查点：每道闸在确认前可参考的验证点候选（中性列出，需按你的框架版本实跑核对；
# 各框架版本→检查点的逐条对照，见迁移部署文档 https://jinengpu.chat/cross-migration.html）
GATE_CANDIDATES = {
    "G1": [
        "会话数据库所在路径与项目对话边界（不同框架按项目分库或共库，先确认边界再定范围）",
        "项目对应的 Agent 名称 / 实例 ID（从会话元数据或工作区目录名核对）",
        "output 前期成果目录的实际位置（随包 or 排除）",
    ],
    "G2": [
        "抽样轮次里是否出现他项目关键词（串库检查）",
        "user 消息的时间连续性（有无跨日跳变）",
        "工具调用记录里的文件路径是否属于本项目",
    ],
    "G3": [
        "目标目录是否在 agent 框架安装/数据目录之外（各框架的数据目录位置不同，需核对本机）",
        "磁盘剩余空间与备份包预估大小",
        "目录命名是否含任务名与时间戳（还原侧可读）",
    ],
    "G4": [
        "attachments/ 内文件是否被 JSONL 的 files/urls 字段引用（无主附件是否随包）",
        "output/ 成果是否含临时文件（temp/、.tool-results/ 等是否剔除）",
        "凭据文件是否按私有迁移策略保留原样（默认随包、恢复即用）",
    ],
    "G5": [
        "备份会话使用的模型名（从会话配置或环境快照 source_model 核对）",
        "目标框架恢复时可用同一模型 or 等价模型（跨框架时模型名可能不同）",
        "模型行为漂移的回退方案（如恢复后风格差异明显，需保留旧模型线索）",
    ],
}


def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def parse_task_name(backup_dir):
    name = os.path.basename(os.path.abspath(backup_dir))
    m = re.match(r"^(.*)_\d{8}-\d{6}$", name)
    return m.group(1) if m else name


def gate_path(backup_dir):
    return os.path.join(os.path.abspath(os.path.expanduser(backup_dir)), GATE_FILE)


def blank(backup_dir):
    return {
        "schema": SCHEMA,
        "generator": f"confirm_gate.py v{VERSION}",
        "task_name": parse_task_name(backup_dir),
        "backup_dir": os.path.abspath(os.path.expanduser(backup_dir)),
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "gates": {
            gid: {"id": gid, "name": gname, "question": question, "hint": hint,
                  "status": "pending", "value": None, "confirmed_at": None}
            for gid, gname, question, hint in GATES
        },
    }


def load(backup_dir):
    p = gate_path(backup_dir)
    data = None
    if os.path.isfile(p):
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data.get("gates"), dict):
                raise ValueError("gates 结构异常")
        except Exception as ex:
            print(f"[警告] 记录文件解析失败，将重建: {p} ({ex})", file=sys.stderr)
            data = None
    if data is None:
        data = blank(backup_dir)
    for gid, gname, question, hint in GATES:
        data["gates"].setdefault(gid, {"id": gid, "name": gname, "question": question,
                                       "hint": hint, "status": "pending", "value": None,
                                       "confirmed_at": None})
    data["gates"] = {gid: data["gates"][gid] for gid in GATE_IDS}  # 固定闸门顺序
    return data


def save(backup_dir, data):
    data["updated_at"] = now_iso()
    p = gate_path(backup_dir)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return p


def pending_of(data):
    return [gid for gid in GATE_IDS if data["gates"][gid].get("status") != "confirmed"]


def status_lines(data):
    out = []
    for gid, _gname, question, _hint in GATES:
        g = data["gates"][gid]
        mark = "✅ 已确认" if g.get("status") == "confirmed" else "⬜ 待确认"
        extra = f" · {g['value']}" if g.get("value") else ""
        out.append(f"  {gid} {g['name']}：{mark}{extra}")
        out.append(f"      {question}")
    return "\n".join(out)


def find_jsonl(base, max_depth=4):
    """递归查找 rounds-*.jsonl（深度限 4；跳过隐藏目录与 _share/_archive 等）。"""
    out = []
    base = os.path.abspath(os.path.expanduser(base))

    def walk(d, depth):
        if depth > max_depth:
            return
        try:
            names = sorted(os.listdir(d))
        except OSError:
            return
        for name in names:
            if name.startswith(".") or name in ("_share", "_archive", "__pycache__", "node_modules"):
                continue
            p = os.path.join(d, name)
            if os.path.isdir(p):
                walk(p, depth + 1)
            else:
                m = JSONL_RE.search(name)
                if m:
                    out.append((int(m.group(1)), int(m.group(2)), p))

    walk(base, 1)
    out.sort(key=lambda x: (x[0], x[1], x[2]))
    return out


def collect_rounds(base):
    rounds, bad = {}, 0
    for _, _, p in find_jsonl(base):
        try:
            with open(p, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        e = json.loads(line)
                    except json.JSONDecodeError:
                        bad += 1
                        continue
                    r = e.get("round")
                    rounds.setdefault(r if isinstance(r, int) else -1, []).append(e)
        except OSError:
            continue
    return rounds, bad


def clip(s, n=400):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return s if len(s) <= n else s[:n] + "…"


def render_sample(rounds, picked, limit=400):
    lines = []
    for r in picked:
        entries = rounds[r]
        lines.append(f"── 第 {r} 轮（{len(entries)} 条）")
        for e in entries:
            role = e.get("role", "?")
            ts = str(e.get("timestamp", ""))[11:19] or "--:--:--"
            if role in ("user", "agent", "system", "scheduled"):
                lines.append(f"   [{role}] {ts} · {clip(e.get('content'), limit)}")
            elif role == "tool":
                kp = e.get("key_param") or e.get("args_summary") or ""
                lines.append(f"   [tool] {ts} · `{e.get('tool_name', '?')}` · {clip(kp, 120)}")
            else:
                lines.append(f"   [{role}] {ts}")
        lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="五道分步确认闸门（记录 + 打包闸门）")
    ap.add_argument("--backup-dir", default=None, help="备份目录（G1-G5 记录落在该目录）")
    ap.add_argument("--list", action="store_true", help="列出闸门定义与当前状态")
    ap.add_argument("--gate", default=None, help="要操作的闸门 ID：G1..G5")
    ap.add_argument("--set", action="store_true", help="将该闸门标记为已确认")
    ap.add_argument("--reset", action="store_true", help="将该闸门重置为待确认")
    ap.add_argument("--value", default=None, help="确认备注（范围 / 路径 / 模型名等）")
    ap.add_argument("--sample", action="store_true", help="随机抽若干轮完整对话（辅助 G2）")
    ap.add_argument("--rounds", type=int, default=3, help="抽样轮数（默认 3）")
    ap.add_argument("--seed", type=int, default=None, help="抽样随机种子（复现用）")
    ap.add_argument("--check", action="store_true", help="打包前校验：五道全确认才放行")
    args = ap.parse_args()

    if args.gate and args.gate.upper() not in GATE_MAP:
        print(f"[停止] 未知闸门: {args.gate}（可选 G1-G5）", file=sys.stderr)
        sys.exit(2)
    if not any((args.list, args.gate, args.sample, args.check)):
        args.list = True

    if not args.backup_dir:
        if args.list and not (args.gate or args.check or args.sample):
            print(f"confirm_gate.py v{VERSION} · 五道分步确认闸门（未指定 --backup-dir，仅显示定义）\n")
            print(status_lines(blank("-")))
            print("\n提示: 五道闸门须**逐道**向用户确认、逐道落库，禁止在打包前集中补签。")
            print("\n各闸门候选检查点（中性列出，需按你的框架版本实跑核对）：")
            for gid in GATE_IDS:
                print(f"\n  [{gid} {GATE_MAP[gid][1]}] 常见验证点：")
                for c in GATE_CANDIDATES[gid]:
                    print(f"    - {c}")
            print(f"\n  各框架版本→检查点的逐条对照表，见迁移部署文档：https://jinengpu.chat/cross-migration.html")
            sys.exit(0)
        print("[停止] 缺少 --backup-dir（G1-G5 记录需落在备份目录内）", file=sys.stderr)
        sys.exit(2)

    bd = os.path.abspath(os.path.expanduser(args.backup_dir))
    if not os.path.isdir(bd):
        print(f"[停止] 备份目录不存在: {bd}（请先跑 preflight_check.py 建目录）", file=sys.stderr)
        sys.exit(2)

    data = load(bd)

    if args.sample:
        rounds, bad = collect_rounds(bd)
        avail = sorted(r for r in rounds if r >= 0)
        if not avail:
            print(f"[停止] 目录内未找到 rounds-*.jsonl 数据文件: {bd}", file=sys.stderr)
            sys.exit(2)
        rnd = random.Random(args.seed)
        n = max(1, min(args.rounds, len(avail)))
        picked = sorted(rnd.sample(avail, n))
        print(f"随机抽检 {n} / 共 {len(avail)} 轮（抽中轮号: {picked}）" + (f"；解析失败行 {bad}" if bad else ""))
        print()
        print(render_sample(rounds, picked))
        print("请把以上内容交用户过目；确认无误后执行：")
        print(f'  confirm_gate.py --backup-dir {bd} --gate G2 --set --value "已抽检轮号 {picked}"')
        sys.exit(0)

    if args.gate:
        gid = args.gate.upper()
        g = data["gates"][gid]
        if args.set and args.reset:
            print("[停止] --set 与 --reset 不能同时使用", file=sys.stderr)
            sys.exit(2)
        if args.set:
            note = (args.value or "").strip() or None
            if gid == "G5" and not note:
                env_p = os.path.join(bd, "_environment.json")
                if os.path.isfile(env_p):
                    try:
                        with open(env_p, encoding="utf-8") as f:
                            sm = json.load(f).get("source_model")
                        if sm:
                            note = f"模型={sm}（取自 _environment.json）"
                    except Exception:
                        pass
            g.update({"status": "confirmed", "value": note, "confirmed_at": now_iso()})
            print(f"✅ {gid} {g['name']} 已确认" + (f"：{note}" if note else ""))
            print(f"   闸门问题: {g['question']}")
            print(f"   提示: {gid} 的候选检查点是否全部覆盖，需按框架版本核对——对照表见迁移部署文档 https://jinengpu.chat/cross-migration.html")
        elif args.reset:
            g.update({"status": "pending", "value": None, "confirmed_at": None})
            print(f"↩️ {gid} {g['name']} 已重置为待确认")
        else:
            print(f"{gid} {g['name']}：{g.get('status')} · {g.get('value') or '—'}")
        p = save(bd, data)
        print(f"\n记录: {p}\n")
        print(status_lines(data))
        pend = pending_of(data)
        print("\n" + (f"待确认: {', '.join(pend)}（逐道向用户确认，勿一把梭）"
                      if pend else "五道闸门全部通过 → 可进入 Step 6.5 打包。"))
        sys.exit(0)

    if args.check:
        pend = pending_of(data)
        result = {
            "generator": f"confirm_gate.py v{VERSION}",
            "backup_dir": bd,
            "gates": {gid: data["gates"][gid].get("status") for gid in GATE_IDS},
            "pending": pend,
            "ok": not pend,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if pend:
            print("\n[拒绝打包] 以下闸门未确认：" + ", ".join(pend), file=sys.stderr)
            print("请逐道向用户确认后重跑本命令；未通过不得进入 Step 6.5。", file=sys.stderr)
            sys.exit(2)
        print("\n✓ 五道确认闸门全部通过，可打包（Step 6.5）")
        sys.exit(0)

    print(f"confirm_gate.py v{VERSION} · 任务: {data['task_name']} · 目录: {bd}\n")
    print(status_lines(data))
    pend = pending_of(data)
    print("\n" + (f"待确认: {', '.join(pend)}" if pend else "五道闸门全部已确认 ✅"))
    print("\n各闸门候选检查点（中性列出，需按你的框架版本实跑核对）：")
    for gid in GATE_IDS:
        print(f"\n  [{gid} {GATE_MAP[gid][1]}] 常见验证点：")
        for c in GATE_CANDIDATES[gid]:
            print(f"    - {c}")
    print(f"\n  各框架版本→检查点的逐条对照表，见迁移部署文档：https://jinengpu.chat/cross-migration.html")
    print(f"记录文件: {gate_path(bd)}")
    sys.exit(0)


if __name__ == "__main__":
    main()
