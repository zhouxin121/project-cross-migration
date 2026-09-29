#!/usr/bin/env python3
"""restore_dialogue.py — 从 raw-v1.0 备份还原可读对话稿（project-cross-migration v2.5.0）

用法:
  python3 restore_dialogue.py --backup-dir <dir> [--label <label>]

产出:
  <backup-dir>/_restored_dialogue.md   可读对话稿（user/agent 逐字, tool 摘要行, reasoning 折叠）
  <backup-dir>/_restored_stats.json    统计报告（条数/轮次/角色/seq连续性/时间跨度/环境快照摘要）

要点:
  - 数据文件按文件名 rounds 范围排序（勿按 mtime，复制会改 mtime）
  - 平铺优先；无平铺时回退 conversations/ 子目录
  - 行序即真实对话流，禁止按时间戳重排
  - seq 连续性校验：断点记录进 stats，不中断还原；起点不强制为 1（v2.1.1 对齐 validate）
  - 空分片给出警告；全空目录友好退出，不抛栈（F4 修复）
  - raw 字段为原文真相源，结构化字段仅作索引展示
  - v2.2.0 新增：包内如有 _environment.json，读取并对齐"格式框架版本/工具/系统"摘要进 stats，
    提示目标环境按清单补齐（缺项只提示，不阻断还原）
  - v2.2.1 修复（P2-N2）：数据文件查找支持递归扫描（深度限 4 层），
    agents/*/sessions/ 这类深目录布局（如 CherryStudio）不再报"未找到数据文件"；
    优先级：平铺 > conversations/ 子目录 > 递归扫描
  - v2.3.0 新增（闸门 G5 模型一致性）：读取 _environment.json 的 source_model，在控制台与
    _restored_stats.json 中提示"本次备份由该模型完成，恢复时建议使用同一模型"
"""
import argparse
import json
import os
import re
import sys
from collections import Counter

VERSION = "2.5.0"


def find_files(base):
    """收集数据文件：平铺优先；无平铺时回退 conversations/ 子目录；
    再无则递归扫描（深度限 4 层，v2.2.1 P2-N2：兼容 agents/*/sessions/ 等深目录布局）。"""
    def scan(d):
        out = []
        try:
            names = os.listdir(d)
        except OSError:
            return out
        for f in names:
            m = re.search(r"rounds-(\d+)-(\d+)\.jsonl$", f)
            if m:
                out.append((int(m.group(1)), int(m.group(2)), os.path.join(d, f), f))
        return out

    def scan_recursive(d, depth, max_depth=4):
        """受限深度递归扫描：防大目录性能问题；跳过输出/隐藏目录。"""
        out = []
        if depth > max_depth:
            return out
        try:
            names = sorted(os.listdir(d))
        except OSError:
            return out
        for name in names:
            p = os.path.join(d, name)
            if os.path.isdir(p):
                if name.startswith(".") or name in ("_share", "_archive", "__pycache__", "node_modules"):
                    continue
                out += scan_recursive(p, depth + 1, max_depth)
            else:
                m = re.search(r"rounds-(\d+)-(\d+)\.jsonl$", name)
                if m:
                    out.append((int(m.group(1)), int(m.group(2)), p, name))
        return out

    files = scan(base)
    if not files:
        sub = os.path.join(base, "conversations")
        if os.path.isdir(sub):
            files = scan(sub)
    if not files:
        files = scan_recursive(base, 1)
    files.sort(key=lambda t: (t[0], t[1], t[2]))
    return files


def main():
    print(f"restore_dialogue.py v{VERSION} · 还原可读对话稿")
    ap = argparse.ArgumentParser()
    ap.add_argument("--backup-dir", required=True)
    ap.add_argument("--label", default="restored")
    args = ap.parse_args()
    base = args.backup_dir
    files = find_files(base)
    if not files:
        print("未找到 *rounds-*.jsonl 数据文件")
        sys.exit(1)

    entries, prev_seq, seq_issues = [], None, []
    roles, rounds_seen = Counter(), set()
    ts_first = ts_last = None
    for _, _, fpath, fn in files:
        n_before = len(entries)
        with open(fpath, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                e = json.loads(line)
                s = e.get("seq")
                if isinstance(s, int):
                    if prev_seq is not None and s != prev_seq + 1:
                        seq_issues.append([fn, prev_seq, s])
                    prev_seq = s
                entries.append(e)
                roles[e.get("role", "?")] += 1
                r = e.get("round")
                if isinstance(r, int):
                    rounds_seen.add(r)
                ts = e.get("timestamp")
                if ts:
                    if ts_first is None:
                        ts_first = ts
                    ts_last = ts
        if len(entries) == n_before:
            print(f"警告: {fn} 为空分片（0 条记录）")

    if not entries:
        print("未读取到任何条目（所有分片均为空），不生成还原稿")
        sys.exit(1)

    out = [f"# 还原对话 · {args.label}\n",
           f"> 共 {max(rounds_seen)} 轮 / {len(entries)} 条 · {ts_first} → {ts_last}",
           "> user/agent 正文逐字保留；tool 条目摘要行；raw 字段为原文真相源（见同目录 *.jsonl）\n"]
    cur = None
    for e in entries:
        r, role, seq, ts = e.get("round"), e.get("role"), e.get("seq", ""), e.get("timestamp", "")
        if r != cur:
            cur = r
            out.append(f"\n---\n\n## 第 {r} 轮\n")
        if role == "user":
            out += [f"### seq {seq} · 👤 用户 · {ts}\n", "```text", e.get("content", ""), "```\n"]
        elif role == "agent":
            out.append(f"### seq {seq} · 🤖 助手 · {ts}\n")
            if e.get("reasoning"):
                out += ["<details><summary>reasoning（点击展开）</summary>\n", "```text",
                        e["reasoning"], "```\n", "</details>\n"]
            if e.get("content"):
                out.append(e["content"] + "\n")
            tcs = e.get("tool_calls") or []
            if tcs:
                out.append("（工具调用: " + ", ".join(t.get("name", "?") for t in tcs) + "）\n")
        elif role == "tool":
            kp = e.get("key_param") or e.get("args_summary") or ""
            out.append(f"- seq {seq} · 🔧 `{e.get('tool_name', '?')}` · {kp}")
        else:
            out.append(f"- seq {seq} · {role} · {ts}")

    md_path = os.path.join(base, "_restored_dialogue.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))

    # v2.2.0：框架环境快照对齐（缺项只提示，不阻断还原）
    env_path = os.path.join(base, "_environment.json")
    env_summary, env_hint, model_hint = None, None, None
    if os.path.isfile(env_path):
        try:
            with open(env_path, encoding="utf-8") as f:
                env = json.load(f)
            env_summary = {
                "path": env_path,
                "task_name": env.get("task_name"),
                "os_detail": (env.get("os") or {}).get("os_detail"),
                "frameworks": env.get("frameworks"),
                "tools": [t.get("name") for t in env.get("tools", [])],
                "tools_missing": env.get("tools_missing", []),
                "config_paths_count": {k: len(v) for k, v in (env.get("config_paths") or {}).items()},
                "model_config_items": len(env.get("model_config") or []),
                "source_model": env.get("source_model"),
            }
            if env_summary["tools_missing"]:
                env_hint = ("目标环境缺少工具: " + ", ".join(env_summary["tools_missing"])
                            + "（按 _environment.json 补齐后再开聊）")
            if env_summary.get("source_model"):
                model_hint = (f"本次备份由模型 {env_summary['source_model']} 完成，"
                              "恢复时建议使用同一模型（减少语气/行为漂移，闸门 G5）。")
        except Exception as ex:
            env_summary = {"path": env_path, "error": f"环境快照解析失败: {ex}"}

    stats = {
        "label": args.label,
        "total_entries": len(entries),
        "total_rounds": max(rounds_seen),
        "roles": dict(roles),
        "seq_continuous": not seq_issues,
        "seq_issues": seq_issues[:20],
        "files": [f[3] for f in files],
        "time_span": {"start": ts_first, "end": ts_last},
        "environment_snapshot": env_summary,
    }
    if env_hint:
        stats["environment_hint"] = env_hint
    if model_hint:
        stats["model_consistency_hint"] = model_hint
    st_path = os.path.join(base, "_restored_stats.json")
    with open(st_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(json.dumps({k: stats[k] for k in ("total_entries", "total_rounds", "roles", "seq_continuous")},
                     ensure_ascii=False))
    print("还原稿:", md_path)
    print("统计:", st_path)
    if env_summary:
        if env_summary.get("error"):
            print("环境快照: 读取失败（不影响还原）—", env_summary["error"])
        else:
            print(f"环境快照: {env_summary.get('os_detail')} · 工具 {env_summary.get('tools')} · "
                  f"缺失 {env_summary.get('tools_missing')} · 框架 {env_summary.get('frameworks')}")
            if env_hint:
                print("补齐提示:", env_hint)
            if model_hint:
                print("模型提示:", model_hint)
    else:
        print("环境快照: 包内无 _environment.json（老版本备份包，可忽略）")


if __name__ == "__main__":
    main()
