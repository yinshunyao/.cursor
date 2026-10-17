#!/usr/bin/env bash
# Sync hipp-or hipp-web SPA dist to remote. Optional local build with /or/ base.
#
# Required env:
#   HIPP_DEPLOY_HOST     e.g. root@<host>
#   HIPP_DEPLOY_REMOTE   e.g. /data/or/hipp-web
# Optional:
#   HIPP_DEPLOY_LOCAL    default <repo>/hipp-or/hipp-web
#   HIPP_DEPLOY_SSH_PASS
#   HIPP_DEPLOY_BUILD=1  npm run build with VITE_BASE_PATH=/or/ VITE_API_BASE=/or/api

set -euo pipefail

HOST="${HIPP_DEPLOY_HOST:?set HIPP_DEPLOY_HOST}"
REMOTE="${HIPP_DEPLOY_REMOTE:?set HIPP_DEPLOY_REMOTE}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
LOCAL="${HIPP_DEPLOY_LOCAL:-$REPO_ROOT/hipp-or/hipp-web}"

if [[ ! -d "$LOCAL" ]]; then
  echo "local tree missing: $LOCAL" >&2
  exit 1
fi

if [[ "${HIPP_DEPLOY_BUILD:-}" == "1" ]]; then
  (cd "$LOCAL" && VITE_BASE_PATH=/or/ VITE_API_BASE=/or/api npm run build)
fi

if [[ ! -f "$LOCAL/dist/index.html" ]]; then
  echo "dist/index.html missing; build with HIPP_DEPLOY_BUILD=1" >&2
  exit 1
fi
if ! grep -q '/or/assets/' "$LOCAL/dist/index.html"; then
  echo "dist does not reference /or/assets/; rebuild with VITE_BASE_PATH=/or/" >&2
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
run_remote rsync -av --delete --exclude '.DS_Store' "$LOCAL/dist/" "$HOST:$REMOTE/"

CHECK_LOCAL="$(mktemp)"
trap 'rm -f "$CHECK_LOCAL"' EXIT
cat >"$CHECK_LOCAL" <<EOF
#!/usr/bin/env bash
set -euo pipefail
curl -sS -o /dev/null -w 'or/ %{http_code}\n' http://127.0.0.1/or/
head -c 160 '$REMOTE/index.html'; echo
EOF
run_remote rsync -av "$CHECK_LOCAL" "$HOST:/tmp/hipp-web-deploy-check.sh"
run_remote ssh "$HOST" "bash /tmp/hipp-web-deploy-check.sh && rm -f /tmp/hipp-web-deploy-check.sh"

echo "deployed hipp-web -> $HOST:$REMOTE"
