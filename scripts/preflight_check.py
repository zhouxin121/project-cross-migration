#!/usr/bin/env python3
"""preflight_check.py — 备份运行入口校验（project-cross-migration v2.5.0）

为什么需要它:
  迁移日志里最常见的三类事故，都发生在"动手之前"：
  ① 框架没对齐 —— 从 A 框架导出的包往 B 框架上还原，格式/路径全不兼容，白搬一趟；
  ② 任务名称没定 —— 备份目录名随手写（backup/、new/、test/），事后谁也认不出是哪个项目；
  ③ 备份目录落在 agent 安装目录里 —— 跟着 agent 卸载一起被删，资料"备份"了个寂寞。

本脚本是三件事的**执行闸门**：备份前先跑，不通过就不许开工。

用法:
  python3 preflight_check.py --task-name <任务名称> \
      --source-framework <源框架[@版本]> --target-framework <目标框架[@版本]> \
      [--backup-root <目录，默认 ~/Desktop>] \
      [--extra-deny <额外禁止写入的前缀，可多次>]

退出码: 0 = 允许开工; 2 = 参数缺失/非法（含任务名称缺失，需向用户索要）; 3 = 目录落位违规（禁止写入 agent 目录）

v2.2.1 修订:
  - 目录落位补 agent home 片段（/.openclaw-autoclaw、/.workbuddy、/.claude 等），
    agent 数据目录（如 ~/.openclaw-autoclaw/agents/<agent>）不再漏拦（P2-N1）
  - 源/目标框架名命中在线平台（coze/dify/扣子 等）时输出显式 warning，
    不拦截、不影响退出码（P3-N5）

v2.3.0 修订:
  - 备份默认落位改「桌面」~/Desktop（原 ~/AgentConversationBackup 仍可用 --backup-root 指定）——
    备份要落在显眼位置，用户一眼能找到；
  - 输出追加「五道确认闸门」下一步指引：G1 范围 → G3 落位 → G4 附件 → G5 模型 → G2 抽检，
    逐道由 confirm_gate.py 落库，打包前 --check 必须通过；
  - 结果新增 confirm_gate_cmd 字段，直接给出闸门记录命令。
"""
import argparse
import json
import os
import platform
import re
import sys
from datetime import datetime

VERSION = "2.5.0"
DEFAULT_ROOT = "~/Desktop"

# 硬性禁止写入的位置（大小写不敏感；命中即拒绝）
DENY_FRAGMENTS = [
    # 系统保护路径
    "/system/", "/usr/", "/bin/", "/sbin/", "/private/", "/volumes/", "/applications/", "/opt/",
    "c:\\windows", "c:\\program files",
    # agent 安装目录线索
    "/skills/", "/extensions/", "/plugins/", "/node_modules/", "site-packages/",
    "/.openclaw/", "/.marvis/", "/.autoclaw/", "/autoclaw/", "/openclaw/", "/workbuddy/", "/mindvault/",
    "/.git/", "/__pycache__/",
    # agent home 目录（v2.2.1 补，P2-N1："/.openclaw/" 这类带斜杠结尾的片段拦不住
    #   "/.openclaw-autoclaw" 等连字符变体；agent 数据目录随卸载/重装一起消失，同样禁写）
    "/.openclaw-autoclaw", "/.workbuddy", "/.agents", "/.claude", "/.codex", "/.cursor",
    "/.continue", "/.aider", "/.gemini", "/.ollama", "/.jan", "/.cherrystudio", "/.cherry-studio",
    "/.copilot", "/.windsurf", "/.trae", "/.codeium",
    # agent 数据目录线索（随卸载一起消失）
    "marvisdata", "com.tencent.mac.marvis", "application support", "appdata/roaming", "appdata/local",
    "/library/",
]

# 在线（SaaS）平台线索：对话数据在服务侧、无本地文件形态——本地文件迁移架构性不可行。
# 命中**不拦截**（用户可能已拿到平台导出包），但必须显式 warning（v2.2.1，P3-N5）。
ONLINE_FRAMEWORKS = ["coze", "扣子", "dify", "fastgpt", "n8n", "flowise", "langflow",
                     "腾讯元器", "文心智能体"]
ONLINE_HINT = ("在线平台数据在服务侧，本地文件迁移架构性不可行——本 Skill 只处理本地文件形态"
               "（导出包/本地目录）。请先走平台自带导出/API 把数据落地为本地文件，再进入备份流程")


def norm(p):
    """规范化绝对路径用于比较（windows 反斜杠统一）。"""
    return os.path.abspath(os.path.expanduser(p)).replace("\\", "/").lower()


def deny_reason(path, extra_deny=()):
    n = norm(path)
    if not n.endswith("/"):
        n_dir = n + "/"
    else:
        n_dir = n
    for frag in list(DENY_FRAGMENTS) + [norm(e).rstrip("/") + "/" for e in extra_deny]:
        f = frag if frag.endswith("/") else frag + "/"
        if f in n_dir:
            return frag
    return None


def valid_task_name(name):
    """任务名称合法性；返回 (ok, 清洗后名称, 原因)。"""
    if name is None or not str(name).strip():
        return False, "", "任务名称缺失"
    n = str(name).strip()
    if len(n) > 64:
        return False, n, "任务名称过长（>64 字符）"
    if n in (".", ".."):
        return False, n, "任务名称不得为 . / .."
    if re.search(r'[<>:"/\\|?*\x00-\x1f]', n):
        return False, n, "任务名称含非法字符（<>:\"/\\|?* 等）"
    return True, n, ""


def parse_framework(s):
    if not s or not str(s).strip():
        return None
    s = str(s).strip()
    if "@" in s:
        name, ver = s.split("@", 1)
        return {"raw": s, "name": name.strip(), "version": ver.strip() or None}
    m = re.match(r"^(.*?)[\s]+v?([0-9][0-9A-Za-z.\-]*)$", s)
    if m:
        return {"raw": s, "name": m.group(1).strip(), "version": m.group(2).strip()}
    return {"raw": s, "name": s, "version": None}


def main():
    ap = argparse.ArgumentParser(description="备份运行入口校验")
    ap.add_argument("--task-name", default=None)
    ap.add_argument("--source-framework", default=None)
    ap.add_argument("--target-framework", default=None)
    ap.add_argument("--backup-root", default=DEFAULT_ROOT)
    ap.add_argument("--extra-deny", action="append", default=[])
    ap.add_argument("--ts", default=None, help="时间戳覆盖（测试用），默认本地 now")
    args = ap.parse_args()

    errors, checks = [], []

    # ① 任务名称
    ok_name, task_name, why = valid_task_name(args.task_name)
    checks.append({"item": "task_name", "ok": ok_name, "value": task_name or None, "detail": why or "已提供"})
    if not ok_name:
        errors.append(f"[任务名称] {why} → 必须**停止并向用户索要任务名称**（用于命名备份目录，勿用 backup/new/test 之类占位名）")

    # ② 平台框架（源 + 目标）
    src_fw, tgt_fw = parse_framework(args.source_framework), parse_framework(args.target_framework)
    for label, fw in (("source_framework", src_fw), ("target_framework", tgt_fw)):
        ok = bool(fw and fw["name"])
        checks.append({"item": label, "ok": ok, "value": fw, "detail": "已提供" if ok else "缺失"})
        if not ok:
            errors.append(f"[平台框架] {label} 缺失 → 源框架与目标框架都需确认（框架名必填、版本尽力提供），避免跨框架格式不兼容白搬")
    if src_fw and tgt_fw and src_fw["name"].lower() == tgt_fw["name"].lower():
        checks.append({"item": "same_framework", "ok": True, "value": True,
                       "detail": "源=目标同名（同框架换机场景），非错误，仅提示"})

    # ②-bis 在线框架提示（v2.2.1，P3-N5：显式 warning，不拦截、不影响退出码）
    warnings, online_hits = [], []
    for label, fw in (("source_framework", src_fw), ("target_framework", tgt_fw)):
        if not fw or not fw["name"]:
            continue
        name_l = str(fw["name"]).lower()
        matched = [k for k in ONLINE_FRAMEWORKS if k in name_l]
        if matched:
            online_hits.append(f"{label}={fw['raw']}")
            warnings.append(f"[在线平台] {label}={fw['raw']}（命中: {','.join(matched)}）: {ONLINE_HINT}")
    if warnings:
        checks.append({"item": "online_framework", "ok": True, "warning": True,
                       "value": online_hits, "detail": ONLINE_HINT})

    # ③ 备份目录落位
    ts = args.ts or datetime.now().strftime("%Y%m%d-%H%M%S")
    root = os.path.expanduser(args.backup_root)
    backup_dir = os.path.join(root, f"{task_name}_{ts}") if task_name else None
    check_dir = backup_dir or root
    reason = deny_reason(check_dir, args.extra_deny) or deny_reason(root, args.extra_deny)
    if reason:
        checks.append({"item": "backup_dir", "ok": False, "value": check_dir, "detail": f"命中禁止写入位置: {reason}"})
        errors.append(f"[目录落位] {check_dir} 命中禁止写入位置（{reason}）—— agent 安装目录/数据目录会随卸载一起被删除，"
                      f"备份必须落在显眼位置（默认 {DEFAULT_ROOT}，或文档等用户自己的目录）")
    else:
        checks.append({"item": "backup_dir", "ok": True, "value": check_dir, "detail": "落位合规（非 agent 安装/数据目录）"})

    result = {
        "generator": f"preflight_check.py v{VERSION}",
        "os": f"{platform.system()} {platform.release()}",
        "task_name": task_name or None,
        "source_framework": src_fw,
        "target_framework": tgt_fw,
        "backup_root": os.path.abspath(root),
        "backup_dir": os.path.abspath(check_dir) if check_dir else None,
        "backup_dir_abs": os.path.abspath(check_dir) if check_dir else None,
        "confirm_gate_cmd": (f"python3 scripts/confirm_gate.py --backup-dir {os.path.abspath(check_dir)} --list"
                             if check_dir else None),
        "timestamp": ts,
        "checks": checks,
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "next": ("可以开工，但打包前必须逐道走完五道确认闸门：G1 备份范围 → G3 落位确认 → G4 附件与成果 "
                 "→ G5 模型一致性 → G2 内容抽检（用 confirm_gate.py 逐道落库，--check 通过才可打包）；"
                 "流程：Step 1 定范围 → Step 3 全量导出 → Step 6 校验 → Step 6.5 打包（含 _environment.json）。"
                 if not errors else "禁止开工：先补齐上述缺项；任务名称缺失时向用户索要，不得自行编造。"),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["backup_dir_abs"]:
        print(f"\n备份目录（绝对路径）: {result['backup_dir_abs']}")
    if warnings:
        print("\n" + "\n".join("⚠️ " + w for w in warnings))
    if errors:
        print("\n" + "\n".join("✗ " + e for e in errors), file=sys.stderr)
        sys.exit(3 if any("目录落位" in e for e in errors) else 2)
    print("✓ 运行入口校验通过")
    sys.exit(0)


if __name__ == "__main__":
    main()
