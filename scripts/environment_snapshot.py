#!/usr/bin/env python3
"""environment_snapshot.py — 框架环境快照采集器（project-cross-migration v2.5.0 · 候选路径模式）

用途:
  把"源框架环境"采成一份 _environment.json 随备份包走，回答：
  "当时的框架是什么版本、装了哪些工具、config/hooks/权限规则在哪、模型怎么配的、系统是什么"。
  换机/换框架后按此清单补齐环境，避免"资料搬过去了但环境对不上"。

范围（只描述环境，不搬运隐私）:
  - 源框架名 + 版本（+ 目标框架名 + 版本）
  - 依赖工具及版本：python3 / pip3 / node / npm / git / ffmpeg / rg / jq（存在才记，缺失记 missing）
  - config / hooks / 权限规则 **文件路径清单**（只列路径，绝不列文件内容/值）
  - 模型配置项：模型名 / 端点（不含任何凭据值）
  - 操作系统版本

安全纪律（脚本内置三道防线）:
  1. 路径采集只 walk 指定根目录、只登记文件名命中的路径，不读取内容；
  2. 模型配置提取走 **键名白名单**（model/base_url/endpoint/provider…），并叠加
     凭据键黑名单（key/token/secret/password/auth/cookie），黑名单键一律丢弃；
  3. 成品自检：对序列化结果跑敏感模式扫描，命中即打码并在 warnings 中登记，
     保证"不含凭据值"这条不是口头承诺。

用法:
  python3 environment_snapshot.py --task-name <任务名称> [--out <path>]
      [--source-framework "Marvis@2.2.0"] [--target-framework "OpenClaw@1.4"]
      [--scan-root <dir> ...] [--config-file <file> ...]
      [--model <模型名>] [--endpoint <API 端点>] [--agent-home <dir>]

跨平台：纯 Python 标准库，macOS / Windows / Linux 尽力采集（取不到的项记 null/missing，不报错退出）。

v2.3.0 修订:
  - 新增顶层 source_model 字段（闸门 G5「模型一致性」）：记录本次备份所用模型，
    来源优先 --model，其次 --config-file 白名单键中的 model；还原侧据此提示"建议用同一模型恢复"。
"""
import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime

VERSION = "2.5.0"
SCHEMA = "environment-snapshot/1.0"

# 工具探测表：(展示名, 可执行名候选, 取版本参数)
TOOL_PROBES = [
    ("python3", ["python3", "python"], ["--version"]),
    ("pip3", ["pip3", "pip"], ["--version"]),
    ("node", ["node"], ["--version"]),
    ("npm", ["npm"], ["--version"]),
    ("git", ["git"], ["--version"]),
    ("ffmpeg", ["ffmpeg"], ["-version"]),
    ("rg", ["rg"], ["--version"]),
    ("jq", ["jq"], ["--version"]),
    ("curl", ["curl"], ["--version"]),
]

# v2.5.0 框架配置候选路径（真实路径变体：同一框架不同版本/平台位置不同，中性列出需核对；
# 版本→路径的准确对照表见迁移部署文档 https://jinengpu.chat/cross-migration.html）
FRAMEWORK_CONFIG_CANDIDATES = {
    "claude-code": [
        "~/.claude.json                       # 早期版本：全局配置（含项目历史）在此单文件",
        "~/.claude/settings.json              # 新版拆分：用户级设置移入 ~/.claude/ 目录",
    ],
    "codex": [
        "~/.codex/config.toml                 # macOS / Linux 默认位置",
        "~/.config/codex/config.toml          # XDG 规范位置（部分安装方式使用）",
    ],
    "openclaw": [
        "~/.openclaw/openclaw.json            # 开源版默认",
        "~/.openclaw-autoclaw/openclaw.json   # AutoClaw 发行版（国内镜像安装）",
    ],
    "marvis": [
        "~/Library/Application Support/com.tencent.mac.marvis/   # macOS 全量数据目录",
        "~/.marvis/                                           # 跨平台布局（部分版本）",
    ],
    "workbuddy": [
        "~/.workbuddy/settings.json           # 用户设置 + 环境变量覆盖",
        "~/WorkBuddy/                         # 工作区布局（版本相关）",
    ],
}

# config / hooks / 权限规则 的路径发现模式（只登记路径，不读内容）
PATH_PATTERNS = {
    "config": re.compile(r"^(config|settings|app|mcp|providers?|models?)\.(json|jsonc|ya?ml|toml|ini)$", re.I),
    "hooks": re.compile(r"^hooks?\.(json|jsonc|ya?ml|toml|sh|py|js|ts)$|^hooks$|after_?hook|before_?hook|on_(start|stop|message)", re.I),
    "permission_rules": re.compile(r"^(permissions?|permission[_-]?rules?|rules|allowlist|denylist|policy)\.(json|jsonc|ya?ml|toml|md|txt)$", re.I),
}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".cache",
             "Library", "AppData", ".Trash", "Trash", "Applications"}

# 模型配置键：白名单（只允许这些语义的键进包）
MODEL_KEY_ALLOW = re.compile(r"^(model|model_name|model_id|base_url|baseurl|api_base|endpoint|url|provider|api_type|max_tokens|temperature)$", re.I)
# 凭据键黑名单（命中一律丢弃，双重保险）
CRED_KEY_DENY = re.compile(r"(key|token|secret|password|passwd|credential|auth|cookie|session|signature|app_?id|openid|bearer|apikey)", re.I)

# 成品自检使用的敏感模式（与 desensitize.py 同源，用于兜底拦漏）
SENSITIVE_PATTERNS = [
    re.compile(r"(?<![A-Za-z0-9])(?:sk|vda|rk)[-_][A-Za-z0-9]{10,}"),
    re.compile(r"(?i)(?:api[_-]?key|token|secret|password)(?:\\?[\"':=\s])+\\?[\"']?[A-Za-z0-9._-]{12,}"),
    re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
]


def _run(cmd, timeout=6):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = (p.stdout or "") + (p.stderr or "")
        return out.strip().splitlines()[0] if out.strip() else None
    except Exception:
        return None


def collect_tools():
    tools, missing = [], []
    for name, cands, args in TOOL_PROBES:
        path = None
        for c in cands:
            path = shutil.which(c)
            if path:
                break
        if not path:
            missing.append(name)
            continue
        version = _run([path] + args) or None
        tools.append({"name": name, "path": path, "version": version})
    return tools, missing


def collect_os():
    try:
        uname = platform.uname()
    except Exception:
        uname = None
    info = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor() or None,
        "python_runtime": sys.version.split()[0],
        "shell": os.environ.get("SHELL") or os.environ.get("COMSPEC") or None,
        "os_detail": None,
    }
    # 各平台补充"人能看懂"的版本串
    try:
        if platform.system() == "Darwin":
            info["os_detail"] = f"macOS {_run(['sw_vers', '-productVersion']) or platform.mac_ver()[0]}"
        elif platform.system() == "Windows":
            info["os_detail"] = f"{uname.system} {uname.release} (build {uname.version})" if uname else None
        else:
            distro = None
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            distro = line.split("=", 1)[1].strip().strip('"')
                            break
            info["os_detail"] = distro or f"{platform.system()} {platform.release()}"
    except Exception:
        pass
    return info


def discover_paths(roots, max_depth=3):
    """只登记路径，不读内容。"""
    found = {"config": [], "hooks": [], "permission_rules": []}
    for root in roots:
        root = os.path.abspath(os.path.expanduser(root))
        if not os.path.isdir(root):
            continue
        base_depth = root.rstrip(os.sep).count(os.sep)
        for cur, dirs, files in os.walk(root):
            if cur.rstrip(os.sep).count(os.sep) - base_depth >= max_depth:
                dirs[:] = []
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            for d in list(dirs):
                for kind, pat in PATH_PATTERNS.items():
                    if pat.match(d) and os.path.join(cur, d) not in found[kind]:
                        found[kind].append(os.path.join(cur, d))
            for fn in files:
                for kind, pat in PATH_PATTERNS.items():
                    if pat.match(fn):
                        p = os.path.join(cur, fn)
                        if p not in found[kind]:
                            found[kind].append(p)
    return {k: sorted(v)[:50] for k, v in found.items()}


def extract_model_config(files):
    """从显式指定的 config 文件里只提白名单键（丢弃凭据类键），不保留原文。"""
    items, notes = [], []
    for fp in files:
        fp = os.path.abspath(os.path.expanduser(fp))
        if not os.path.isfile(fp):
            notes.append(f"config 文件不存在，已跳过: {fp}")
            continue
        if not fp.lower().endswith((".json", ".jsonc")):
            notes.append(f"仅支持 .json/.jsonc 的模型配置提取（其它格式请用 --model/--endpoint 手工指定）: {fp}")
            continue
        try:
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as ex:
            notes.append(f"解析失败，已跳过（不读为妙）: {fp} ({ex})")
            continue
        flat = {}

        def walk(node, prefix=""):
            if isinstance(node, dict):
                for k, v in node.items():
                    if CRED_KEY_DENY.search(str(k)):
                        continue  # 凭据键黑名单：直接丢弃
                    if isinstance(v, (dict, list)):
                        walk(v, f"{prefix}{k}.")
                    elif MODEL_KEY_ALLOW.match(str(k)):
                        flat[f"{prefix}{k}"] = v

        walk(data)
        if flat:
            items.append({"source_config_path": fp, "items": flat})
    return items, notes


def parse_framework(s):
    if not s:
        return None
    s = s.strip()
    if "@" in s:
        name, ver = s.split("@", 1)
        return {"name": name.strip(), "version": ver.strip() or None}
    m = re.match(r"^(.*?)[\s]+v?([0-9][0-9A-Za-z.\-]*)$", s)
    if m:
        return {"name": m.group(1).strip(), "version": m.group(2).strip()}
    return {"name": s, "version": None}


def detect_agent_homes():
    """尽力探测可能存在的 agent 安装/数据目录（只作为路径线索记录，不写入）。"""
    cands = []
    for env in ("MARVIS_HOME", "OPENCLAW_HOME", "AUTOCLAW_HOME", "AGENT_HOME", "WORKBUDDY_HOME"):
        v = os.environ.get(env)
        if v:
            cands.append({"env": env, "path": v})
    for p in ("~/.marvis", "~/.openclaw", "~/.autoclaw", "~/WorkBuddy",
              "~/Library/Application Support/com.tencent.mac.marvis"):
        ap = os.path.abspath(os.path.expanduser(p))
        if os.path.isdir(ap):
            cands.append({"env": None, "path": ap})
    return cands


def selfcheck(payload):
    """成品自检：序列化后扫敏感模式，命中即打码。"""
    text = json.dumps(payload, ensure_ascii=False)
    warnings = []
    for pat in SENSITIVE_PATTERNS:
        for m in pat.finditer(text):
            warnings.append(f"自检命中疑似敏感值，已打码: {pat.pattern[:40]}… ≈ {m.group(0)[:6]}***")
    if warnings:
        for pat in SENSITIVE_PATTERNS:
            text = pat.sub("***REDACTED***", text)
        return json.loads(text), warnings
    return payload, warnings


def main():
    print(f"environment_snapshot.py v{VERSION} · 框架环境快照采集")
    ap = argparse.ArgumentParser(description="框架环境快照采集器")
    ap.add_argument("--task-name", required=True, help="任务名称（与备份目录同名）")
    ap.add_argument("--out", default=None, help="输出路径，默认 <cwd>/_environment.json")
    ap.add_argument("--source-framework", default=None, help="源框架，形如 Marvis@2.2.0")
    ap.add_argument("--target-framework", default=None, help="目标框架，形如 OpenClaw@1.4")
    ap.add_argument("--scan-root", action="append", default=[], help="config/hooks/权限规则 路径扫描根（可多次）")
    ap.add_argument("--config-file", action="append", default=[], help="显式指定模型配置文件（只提白名单键）")
    ap.add_argument("--model", default=None, help="模型名（手工指定）")
    ap.add_argument("--endpoint", default=None, help="API 端点（手工指定，不含凭据）")
    ap.add_argument("--agent-home", action="append", default=[], help="agent 安装/数据目录线索（只记路径）")
    args = ap.parse_args()

    task_name = (args.task_name or "").strip()
    if not task_name:
        print("[停止] 缺少任务名称：请先确定本次迁移的任务名称（用于命名备份目录）。", file=sys.stderr)
        sys.exit(2)

    tools, missing = collect_tools()
    paths = discover_paths(args.scan_root) if args.scan_root else {"config": [], "hooks": [], "permission_rules": []}

    # v2.5.0 候选路径模式：未显式传 --config-file 时，按框架列候选（真实路径变体，需核对本机版本）
    config_candidates_hint = None
    if not args.config_file:
        fw_key = None
        for fwl in ((args.source_framework or "") + " " + (args.target_framework or "")).lower().split():
            for key in FRAMEWORK_CONFIG_CANDIDATES:
                if key in fwl:
                    fw_key = key
                    break
            if fw_key:
                break
        lines = []
        for key, cands in FRAMEWORK_CONFIG_CANDIDATES.items():
            if fw_key and key != fw_key:
                continue
            lines.append(f"  [{key}]")
            lines.extend(f"    {c}" for c in cands)
        lines.append("  [其他] 用 --config-file <路径> 手动指定（跨版本/自定义安装位置走此出口）")
        config_candidates_hint = (
            "未指定 --config-file。各框架配置文件的常见位置（同框架不同版本位置不同，需按本机版本核对）：\n"
            + "\n".join(lines)
            + "\n  版本→路径的准确对照表，见迁移部署文档：https://jinengpu.chat/cross-migration.html"
        )
        print(config_candidates_hint)
    model_items, notes = extract_model_config(args.config_file)
    if args.model or args.endpoint:
        model_items.append({"source_config_path": "cli", "items": {
            k: v for k, v in (("model", args.model), ("base_url", args.endpoint)) if v}})

    # v2.3.0（闸门 G5）：本次备份所用模型——优先 CLI 显式指定，其次 config 白名单键中的 model
    source_model = (args.model or "").strip() or None
    if not source_model:
        for it in model_items:
            v = (it.get("items") or {}).get("model")
            if v:
                source_model = str(v).strip()
                break

    payload = {
        "schema": SCHEMA,
        "generator": f"environment_snapshot.py v{VERSION}",
        "task_name": task_name,
        "collected_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "frameworks": {
            "source": parse_framework(args.source_framework),
            "target": parse_framework(args.target_framework),
        },
        "os": collect_os(),
        "source_model": source_model,
        "tools": tools,
        "tools_missing": missing,
        "config_paths": paths,
        "model_config": model_items,
        "agent_home_hints": detect_agent_homes() + [{"env": None, "path": os.path.abspath(os.path.expanduser(p))} for p in args.agent_home],
        "notes": notes + [
            "config/hooks/权限规则 只登记路径，不含文件内容；模型配置只保留白名单键（model/base_url/endpoint/provider 等），凭据键一律丢弃。",
            "config_file_source: " + ("explicit" if args.config_file else "candidates-hint（候选路径模式：版本→路径对照见迁移部署文档）"),
            "本快照用于目标环境对照补齐；凭据不经此文件传递。",
            ("本次备份所用模型: " + (source_model or "未记录")
             + "；恢复时建议使用同一模型，减少语气/行为漂移（闸门 G5）。"),
        ],
        "warnings": [],
    }
    payload, warns = selfcheck(payload)
    payload["warnings"] = warns

    out = args.out or os.path.join(os.getcwd(), "_environment.json")
    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(json.dumps({
        "out": os.path.abspath(out),
        "task_name": task_name,
        "os_detail": payload["os"].get("os_detail"),
        "frameworks": payload["frameworks"],
        "source_model": source_model,
        "tools_found": len(tools),
        "tools_missing": missing,
        "config_paths": {k: len(v) for k, v in payload["config_paths"].items()},
        "model_config_items": len(payload["model_config"]),
        "warnings": len(warns),
    }, ensure_ascii=False, indent=2))
    print(f"环境快照已写入: {os.path.abspath(out)}")


if __name__ == "__main__":
    main()
