#!/usr/bin/env bash
# Sync hipp-or hipp-admin SPA dist to remote. Optional local build with --mode or.
#
# Required env:
#   HIPP_DEPLOY_HOST     e.g. root@<host>
#   HIPP_DEPLOY_REMOTE   e.g. /data/or/hipp-admin
# Optional:
#   HIPP_DEPLOY_LOCAL    local hipp-admin root (default: <repo>/hipp-or/hipp-admin)
#   HIPP_DEPLOY_SSH_PASS
#   HIPP_DEPLOY_BUILD=1  run `pnpm vite build --mode or` (needs .env.or with VITE_BASE_PATH=/or/manager/)

set -euo pipefail

HOST="${HIPP_DEPLOY_HOST:?set HIPP_DEPLOY_HOST}"
REMOTE="${HIPP_DEPLOY_REMOTE:?set HIPP_DEPLOY_REMOTE}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
LOCAL="${HIPP_DEPLOY_LOCAL:-$REPO_ROOT/hipp-or/hipp-admin}"

if [[ ! -d "$LOCAL" ]]; then
  echo "local tree missing: $LOCAL" >&2
  exit 1
fi

if [[ "${HIPP_DEPLOY_BUILD:-}" == "1" ]]; then
  if [[ ! -f "$LOCAL/.env.or" ]]; then
    echo "HIPP_DEPLOY_BUILD=1 needs $LOCAL/.env.or (VITE_BASE_PATH=/or/manager/)" >&2
    exit 1
  fi
  (cd "$LOCAL" && pnpm vite build --mode or)
fi

if [[ ! -f "$LOCAL/dist/index.html" ]]; then
  echo "dist/index.html missing; build with HIPP_DEPLOY_BUILD=1 or pnpm vite build --mode or" >&2
  exit 1
fi
if ! grep -q '/or/manager/assets/' "$LOCAL/dist/index.html"; then
  echo "dist does not reference /or/manager/assets/; rebuild with VITE_BASE_PATH=/or/manager/" >&2
  exit 1
fi

run_remote() {
  if [[ -n "${HIPP_DEPLOY_SSH_PASS:-}" ]]; then
    if ! command -v expect >/dev/null 2>&1; then
      echo "HIPP_DEPLOY_SSH_PASS set but expect not found" >&2
      exit 1
    fi
    expect <<EOF
set timeout 900
set pass \$env(HIPP_DEPLOY_SSH_PASS)
spawn $*
expect {
  -re "(?i)yes/no" { send -- "yes\r"; exp_continue }
  -re "(?i)password:" { send -- "\$pass\r"; exp_continue }
  eof {}
  timeout { puts stderr "TIMEOUT"; exit 1 }
}
catch wait result
set code [lindex \$result 3]
exit \$code
EOF
  else
    "$@"
  fi
}

run_remote ssh "$HOST" "mkdir -p '$REMOTE'"
run_remote rsync -av --delete \
  --exclude '.DS_Store' \
  "$LOCAL/dist/" \
  "$HOST:$REMOTE/"

# 远程校验走临时脚本，避免 expect 把 shell 元字符当 TCL 解析
CHECK_LOCAL="$(mktemp)"
trap 'rm -f "$CHECK_LOCAL"' EXIT
cat >"$CHECK_LOCAL" <<EOF
#!/usr/bin/env bash
set -euo pipefail
curl -sS -o /dev/null -w 'or/manager %{http_code}\n' http://127.0.0.1/or/manager/
grep -o 'dashboard/[a-z]*' '$REMOTE/assets/index-'*.js 2>/dev/null | sort | uniq -c | head -20 || true
head -c 200 '$REMOTE/index.html'; echo
EOF
run_remote rsync -av "$CHECK_LOCAL" "$HOST:/tmp/hipp-admin-deploy-check.sh"
run_remote ssh "$HOST" "bash /tmp/hipp-admin-deploy-check.sh && rm -f /tmp/hipp-admin-deploy-check.sh"

echo "deployed hipp-admin -> $HOST:$REMOTE"
