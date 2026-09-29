#!/bin/bash
# ============================================================
# Install project-cross-migration for DeepSeek Harness (DSH)
# 目标：$DSH_HOME/skills/project-cross-migration/（未设 DSH_HOME 时用 ~/.dsh）
# DSH 原生支持 <name>/SKILL.md 目录布局；frontmatter 已兼容（kebab-case name + description）
# 用法：bash scripts/install-dsh.sh
# ============================================================
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
DSH_HOME="${DSH_HOME:-$HOME/.dsh}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$(dirname "$SCRIPT_DIR")"
DEST="$DSH_HOME/skills/project-cross-migration"

if [ ! -f "$SRC_DIR/SKILL.md" ]; then
  echo "${RED}✗ 未找到 SKILL.md（请在仓库目录内运行本脚本）${NC}"; exit 1
fi

echo "▸ 目标目录: $DEST"
echo "▸ 提示: DSH_HOME 未设置，使用默认 $DSH_HOME（可用 export DSH_HOME=... 更改）"

mkdir -p "$DEST/scripts"
cp -f "$SRC_DIR/SKILL.md" "$SRC_DIR/README.md" "$SRC_DIR/CHANGELOG.md" "$SRC_DIR/_meta.json" "$DEST/"
cp -f "$SRC_DIR"/scripts/*.py "$DEST/scripts/"
# 示例文件一并复制（如有）
[ -d "$SRC_DIR/examples" ] && mkdir -p "$DEST/examples" && cp -f "$SRC_DIR"/examples/* "$DEST/examples/" 2>/dev/null || true

echo
echo "${GREEN}✓ 安装完成${NC}"
echo "▸ 验证：在 DSH 里运行 skill_list，应看到 project-cross-migration"
