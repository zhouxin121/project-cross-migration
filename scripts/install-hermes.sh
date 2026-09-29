#!/bin/bash
# ============================================================
# Install project-cross-migration for Hermes Agent
# 目标：~/.hermes/skills/project-cross-migration/
# 幂等：重复运行覆盖更新，不产生重复文件；无需 sudo
# 用法：bash <(curl -s https://raw.githubusercontent.com/zhouxin121/project-cross-migration-free/main/scripts/install-hermes.sh)
# ============================================================
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
REPO_RAW="https://raw.githubusercontent.com/zhouxin121/project-cross-migration-free/main"
DEST="$HOME/.hermes/skills/project-cross-migration"

echo "▸ 目标目录: $DEST"

# 前置检查
if ! command -v curl >/dev/null 2>&1; then
  echo "${RED}✗ 未找到 curl，请先安装（brew install curl 或系统包管理器）${NC}"; exit 1
fi

FILES=(
  "SKILL.md"
  "README.md"
  "CHANGELOG.md"
  "_meta.json"
  "scripts/preflight_check.py"
  "scripts/confirm_gate.py"
  "scripts/desensitize.py"
  "scripts/environment_snapshot.py"
  "scripts/validate_jsonl.py"
  "scripts/restore_dialogue.py"
)

# 创建目录（幂等：-p 不报错）
mkdir -p "$DEST/scripts"

echo "▸ 拉取文件..."
FAIL=0
for f in "${FILES[@]}"; do
  if curl -fsSL "$REPO_RAW/$f" -o "$DEST/$f"; then
    echo "  ${GREEN}✓${NC} $f"
  else
    echo "  ${RED}✗ $f 拉取失败（检查网络或仓库地址）${NC}"; FAIL=1
  fi
done
[ "$FAIL" -eq 1 ] && { echo "${RED}✗ 有文件下载失败，安装中止（目标目录保留，可重跑本脚本续传）${NC}"; exit 1; }

echo
echo "${GREEN}✓ 安装完成${NC}"
echo "▸ 验证：问你的 Hermes agent「你有哪些 skill」，应能看到 project-cross-migration"
echo "▸ 或检查文件: ls ~/.hermes/skills/project-cross-migration/"
