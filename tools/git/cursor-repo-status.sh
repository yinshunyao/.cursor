#!/usr/bin/env bash
# 查看 .cursor 仓库状态（独立 git：yinshunyao/.cursor）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
echo "== remote =="
git remote -v
echo "== branch =="
git status -sb
echo "== recent =="
git log -5 --oneline
echo "== dirty summary =="
git status --short
