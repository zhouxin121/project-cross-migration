#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""release_check.py — 发布前置机器断言（测评 N12/流程根因 治本脚本）
用法：python3 scripts/release_check.py [--fix-meta]
  1. 六脚本 VERSION 常量统一 = _meta.json version
  2. 六脚本 docstring 首行含同版本号
  3. _meta.json files_checksum 与实际文件 sha256 逐一匹配（--fix-meta 时现算重写）
  4. 已登记文件全部存在 / 包内新增文件无漏登记
  5. 术语残留检查：完整版/wzyp.cn/分享（SKILL.md）
退出码：0 全过 / 1 有阻断项
"""
import argparse, hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix-meta", action="store_true", help="现算并重写 _meta.json 的 files_checksum")
    args = ap.parse_args()

    fails = []

    meta = json.load(open(os.path.join(HERE, "_meta.json"), encoding="utf-8"))
    ver = meta.get("version")

    # 1+2 脚本版本一致性
    scripts = sorted(f for f in os.listdir(os.path.join(HERE, "scripts")) if f.endswith(".py") and f != "release_check.py")
    for f in scripts:
        p = os.path.join(HERE, "scripts", f)
        body = open(p, encoding="utf-8").read()
        m = re.search(r'VERSION = "([^"]+)"', body)
        if not m or m.group(1) != ver:
            fails.append(f"VERSION 不一致: {f} ({m.group(1) if m else '缺失'} != {ver})")
        head = body[:400]
        if f"v{ver}" not in head:
            fails.append(f"docstring 版本滞后: {f} 头部未含 v{ver}")

    # 3+4 checksum 与文件清单
    if args.fix_meta:
        cs = {}
        for root, dirs, files in os.walk(HERE):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
            for f in sorted(files):
                if f in {".DS_Store", "_meta.json", "release_check.py"}: continue
                p = os.path.join(root, f)
                cs[os.path.relpath(p, HERE)] = hashlib.sha256(open(p, "rb").read()).hexdigest()
        meta["files_checksum"] = dict(sorted(cs.items()))
        meta["release_date"] = meta.get("release_date")
        json.dump(meta, open(os.path.join(HERE, "_meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"[fix-meta] 已重写 files_checksum（{len(cs)} 文件）")

    actual = {}
    for root, dirs, files in os.walk(HERE):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for f in sorted(files):
            if f in {".DS_Store", "_meta.json", "release_check.py"}: continue
            p = os.path.join(root, f)
            actual[os.path.relpath(p, HERE)] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    registered = meta.get("files_checksum", {})
    for rel, h in registered.items():
        if rel not in actual:
            fails.append(f"登记文件不存在: {rel}")
        elif actual[rel] != h:
            fails.append(f"sha256 不匹配: {rel}")
    for rel in actual:
        if rel not in registered and rel != "scripts/release_check.py":
            fails.append(f"漏登记: {rel}（用 --fix-meta 补齐）")

    # 5 术语残留
    skill = open(os.path.join(HERE, "SKILL.md"), encoding="utf-8").read()
    for word in ("完整版", "wzyp.cn"):
        if word in skill:
            fails.append(f"SKILL.md 残留术语: {word}")
    for i, line in enumerate(skill.split("\n"), 1):
        if "分享" in line and "_share" not in line and "--share" not in line:
            fails.append(f"SKILL.md L{i} 残留『分享』")

    print(f"release_check · v{ver} · {'❌ %d 项阻断' % len(fails) if fails else '✅ 全过'}")
    for f in fails:
        print("  -", f)
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
