#!/usr/bin/env python3
"""validate_jsonl.py — raw-v1.0 JSONL 校验器（project-cross-migration v2.5.0）

用法: python3 validate_jsonl.py <file1.jsonl> [file2.jsonl ...]
  多文件按命令行顺序校验 seq 全局连续性（还原侧请先按文件名 rounds 排序再传入）。

校验项:
  - 每行 JSON 可解析
  - timestamp 为 ISO 8601 +08:00 格式
  - role 在枚举内 (user/agent/tool/system/scheduled)
  - round 为整数且按行序单调不减
  - content 字段存在；role=tool 条目允许以 key_param / args_summary 替代
    （MindVault OpenClaw/Marvis 模式导出兼容，输出 INFO 说明，不判失败；
    三者皆无才判 FAIL）
  - seq 跨文件全局连续（起点不强制为 1，支持中段分片/增量包）

退出码: 0 = 全部通过; 1 = 存在问题; 2 = 参数错误
"""
import json
import os
import re
import sys

VERSION = "2.5.0"
ROLES = {"user", "agent", "tool", "system", "scheduled"}
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?\+08:00$")


def check_file(path):
    issues, infos, rows = [], [], []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError as ex:
                issues.append(f"L{i}: JSON 解析失败: {ex}")
                continue
            rows.append((i, e))
            ts = e.get("timestamp", "")
            if not TS_RE.match(ts):
                issues.append(f"L{i}: timestamp 非 ISO8601+08:00: {str(ts)[:40]}")
            if e.get("role") not in ROLES:
                issues.append(f"L{i}: role 非法: {e.get('role')}")
            if not isinstance(e.get("round"), int):
                issues.append(f"L{i}: round 非整数: {e.get('round')}")
            if "content" not in e:
                if e.get("role") == "tool" and (e.get("key_param") or e.get("args_summary")):
                    infos.append(f"L{i}: tool 条目无 content，以 key_param/args_summary 替代（MindVault OpenClaw/Marvis 模式兼容）")
                else:
                    issues.append(f"L{i}: 缺 content 字段（tool 条目需 content 或 key_param/args_summary 至少其一）")
    rounds = [e["round"] for _, e in rows if isinstance(e.get("round"), int)]
    if rounds != sorted(rounds):
        issues.append("round 按行序回退（应单调不减，禁止按时间戳重排）")
    return rows, issues, infos


def main(paths):
    total, prev_seq, ok = 0, None, True
    seq_start = None
    for p in paths:
        if not os.path.exists(p):
            print(f"FAIL {p}（文件不存在）")
            ok = False
            continue
        rows, issues, infos = check_file(p)
        total += len(rows)
        if not rows:
            infos.append("空文件（0 条记录）——请确认是否预期")
        for i, e in rows:
            s = e.get("seq")
            if isinstance(s, int):
                if prev_seq is None:
                    seq_start = s  # 支持中段分片/增量包：起点不强制为 1
                elif s != prev_seq + 1:
                    issues.append(f"L{i}: seq 不连续 (期望 {prev_seq + 1}, 实际 {s})")
                prev_seq = s
        size = os.path.getsize(p)
        print(("OK   " if not issues else "FAIL ") + f"{p}（{len(rows)} 条 / {size} bytes）")
        for msg in issues[:10]:
            print("     -", msg)
        if len(issues) > 10:
            print(f"     ... 及另外 {len(issues) - 10} 条问题")
        for msg in infos[:5]:
            print("INFO  -", msg)
        if len(infos) > 5:
            print(f"INFO  ... 及另外 {len(infos) - 5} 条说明")
        if issues:
            ok = False
    print("-" * 60)
    span = f"，seq {seq_start}→{prev_seq}" if seq_start is not None else ""
    print(f"共校验 {len(paths)} 个文件 / {total} 条记录{span}，结果: {'全部通过 ✅' if ok else '存在问题 ❌'}")
    if seq_start is not None and seq_start != 1:
        print("提示: 本组 seq 起点非 1（中段分片或增量包）。若意图是校验完整包，请按文件名顺序传入全部分片。")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    print(f"validate_jsonl.py v{VERSION}")
    main(sys.argv[1:])
