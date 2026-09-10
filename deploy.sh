#!/usr/bin/env bash
# 发布《AI Systems Engineering》到 GitHub 并触发 Actions 渲染发布
#
# 用法：
#   ./deploy.sh                  # 用默认提交信息提交并推送
#   ./deploy.sh "更新 Ch47 实测" # 自定义提交信息
#
# 首次运行自动完成：git init、关联远程、首推并设上游。
# 之后每次改动只需重跑本脚本。
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
REMOTE="git@github.com:liamamilin/AI-SYSTEM-ENGINE.git"
BRANCH="main"

cd "$REPO_DIR"

# ---- 1. git 仓库初始化（幂等） ----
if [ ! -d .git ]; then
  git init -b "$BRANCH"
  echo "→ git 仓库已初始化"
fi
git remote remove origin 2>/dev/null || true
git remote add origin "$REMOTE"

# ---- 2. 密钥防线：.env 绝不能进版本库 ----
if git check-ignore -q ai-systems-engineering-book/scripts/.env 2>/dev/null; then
  echo "→ .env 已被 .gitignore 排除 ✓"
else
  echo "!! 危险：.env 未被排除，中止提交（先修复 .gitignore）" >&2
  exit 1
fi
if git ls-files --error-unmatch ai-systems-engineering-book/scripts/.env >/dev/null 2>&1; then
  echo "!! 危险：.env 已在版本库中，中止并请立即轮换密钥" >&2
  exit 1
fi

# ---- 3. 提交 ----
git add -A
if git diff --cached --quiet; then
  echo "→ 没有新的改动，跳过提交"
else
  git commit -m "${1:-publish: update book content}"
  echo "→ 已提交 $(git rev-parse --short HEAD)"
fi

# ---- 4. 推送（首次设置上游） ----
if git rev-parse --verify origin/"$BRANCH" >/dev/null 2>&1; then
  git push
else
  git push -u origin "$BRANCH"
fi

echo ""
echo "✓ 推送完成。下一步："
echo "  1. 打开 https://github.com/liamamilin/AI-SYSTEM-ENGINE/actions 确认 publish-book 工作流跑完"
echo "  2. Settings → Pages → Source 选 'GitHub Actions'（只需设置一次）"
echo "  3. 书籍地址：https://liamamilin.github.io/AI-SYSTEM-ENGINE/"
