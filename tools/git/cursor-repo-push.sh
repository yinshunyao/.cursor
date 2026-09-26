#!/usr/bin/env bash
# 向 origin/main 推送当前 .cursor 仓库（需已有本地 commit）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
git status -sb
git push origin HEAD
git status -sb
