#!/usr/bin/env bash
# Sync hipp-https console code to a remote host and restart the supervisor program.
# Does not stop unrelated services. Does not install certbot or hipp-agent on the console host.
#
# Required env:
#   HIPP_DEPLOY_HOST     ssh target, e.g. root@<host>
#   HIPP_DEPLOY_REMOTE   remote code root, e.g. /data/hipp-https
# Optional env:
#   HIPP_DEPLOY_LOCAL    local hipp-https root (default: <repo>/hipp-https)
#   HIPP_DEPLOY_ENV      local .env file to copy as remote .env (omit to skip)
#   HIPP_DEPLOY_SSH_PASS ssh password when key auth is unavailable (uses expect; prefer keys)
#   HIPP_DEPLOY_BUILD=1  run npm run build in web/ before sync (uses web/.env.production)
#   HIPP_DEPLOY_SUPERVISORCTL  remote supervisorctl binary
#   HIPP_DEPLOY_SUPERVISORD_CONF  remote supervisord.conf
#   HIPP_DEPLOY_PROGRAM  supervisor program name (default: hipp-https-console)

set -euo pipefail

HOST="${HIPP_DEPLOY_HOST:?set HIPP_DEPLOY_HOST}"
REMOTE="${HIPP_DEPLOY_REMOTE:?set HIPP_DEPLOY_REMOTE}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
LOCAL="${HIPP_DEPLOY_LOCAL:-$REPO_ROOT/hipp-https}"
SUPERVISORCTL="${HIPP_DEPLOY_SUPERVISORCTL:-/home/miniconda38/bin/supervisorctl}"
SUPERVISORD_CONF="${HIPP_DEPLOY_SUPERVISORD_CONF:-/home/miniconda38/etc/supervisord.conf}"
PROGRAM="${HIPP_DEPLOY_PROGRAM:-hipp-https-console}"

if [[ ! -d "$LOCAL" ]]; then
  echo "local tree missing: $LOCAL" >&2
  exit 1
fi

if [[ "${HIPP_DEPLOY_BUILD:-}" == "1" ]]; then
  (cd "$LOCAL/web" && npm run build)
fi

if [[ ! -f "$LOCAL/web/dist/index.html" ]]; then
  echo "web/dist missing; run npm run build in web/ first (or HIPP_DEPLOY_BUILD=1)" >&2
  exit 1
fi
if grep -q 'src="/assets/' "$LOCAL/web/dist/index.html"; then
  echo "web/dist still uses root /assets/; rebuild with VITE_BASE=/cert/ (web/.env.production)" >&2
  exit 1
fi

run_remote() {
  if [[ -n "${HIPP_DEPLOY_SSH_PASS:-}" ]]; then
    if ! command -v expect >/dev/null 2>&1; then
      echo "HIPP_DEPLOY_SSH_PASS set but expect not found" >&2
      exit 1
    fi
    expect <<EOF
set timeout 600
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

RSYNC_ARGS=(
  rsync -av --delete
  --exclude '.git/'
  --exclude '.env'
  --exclude '.venv/'
  --exclude 'var/'
  --exclude 'out/'
  --exclude 'agent/config.json'
  --exclude '__pycache__/'
  --exclude '*.pyc'
  --exclude 'web/node_modules/'
  --exclude 'server/.venv/'
  --exclude '**/.DS_Store'
  "$LOCAL/"
  "$HOST:$REMOTE/"
)
run_remote "${RSYNC_ARGS[@]}"

if [[ -n "${HIPP_DEPLOY_ENV:-}" ]]; then
  if [[ ! -f "$HIPP_DEPLOY_ENV" ]]; then
    echo "HIPP_DEPLOY_ENV not found: $HIPP_DEPLOY_ENV" >&2
    exit 1
  fi
  run_remote rsync -av "$HIPP_DEPLOY_ENV" "$HOST:$REMOTE/.env"
fi

run_remote ssh "$HOST" "$SUPERVISORCTL -c '$SUPERVISORD_CONF' restart '$PROGRAM'"
run_remote ssh "$HOST" "$SUPERVISORCTL -c '$SUPERVISORD_CONF' status '$PROGRAM'"

echo "deployed $LOCAL -> $HOST:$REMOTE ($PROGRAM restarted)"
