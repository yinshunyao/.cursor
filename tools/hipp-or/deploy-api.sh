#!/usr/bin/env bash
# Sync hipp-or hipp-api to remote and restart or-api. Does not touch hipp.ink 46000 /home/hipp-or.
#
# Required env:
#   HIPP_DEPLOY_HOST     e.g. root@<host>
#   HIPP_DEPLOY_REMOTE   e.g. /data/or/hipp-api
# Optional:
#   HIPP_DEPLOY_LOCAL    local hipp-api root (default: <repo>/hipp-or/hipp-api)
#   HIPP_DEPLOY_ENV      local .env to copy as remote .env
#   HIPP_DEPLOY_SSH_PASS
#   HIPP_DEPLOY_MIGRATE=1  remote: alembic upgrade head only (no autogenerate; avoid main.py migrate)
#   HIPP_DEPLOY_SUPERVISORCTL / HIPP_DEPLOY_SUPERVISORD_CONF / HIPP_DEPLOY_PROGRAM (default or-api)

set -euo pipefail

HOST="${HIPP_DEPLOY_HOST:?set HIPP_DEPLOY_HOST}"
REMOTE="${HIPP_DEPLOY_REMOTE:?set HIPP_DEPLOY_REMOTE}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
LOCAL="${HIPP_DEPLOY_LOCAL:-$REPO_ROOT/hipp-or/hipp-api}"
SUPERVISORCTL="${HIPP_DEPLOY_SUPERVISORCTL:-/home/miniconda38/bin/supervisorctl}"
SUPERVISORD_CONF="${HIPP_DEPLOY_SUPERVISORD_CONF:-/home/miniconda38/etc/supervisord.conf}"
PROGRAM="${HIPP_DEPLOY_PROGRAM:-or-api}"

if [[ ! -d "$LOCAL" ]]; then
  echo "local tree missing: $LOCAL" >&2
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
  --exclude '.venv/' \
  --exclude '.env' \
  --exclude 'static/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  "$LOCAL/" \
  "$HOST:$REMOTE/"

if [[ -n "${HIPP_DEPLOY_ENV:-}" ]]; then
  [[ -f "$HIPP_DEPLOY_ENV" ]] || { echo "HIPP_DEPLOY_ENV missing: $HIPP_DEPLOY_ENV" >&2; exit 1; }
  # 防止 shell 残留 HIPP_DEPLOY_ENV 把 manager.env 盖到 or-api
  if grep -qE '^(MANAGER_SESSION_SECRET|MANAGER_HOST)=' "$HIPP_DEPLOY_ENV" 2>/dev/null; then
    echo "HIPP_DEPLOY_ENV looks like hipp-manager env, refuse overwrite of or-api .env: $HIPP_DEPLOY_ENV" >&2
    exit 1
  fi
  run_remote rsync -av "$HIPP_DEPLOY_ENV" "$HOST:$REMOTE/.env"
fi

if [[ "${HIPP_DEPLOY_MIGRATE:-}" == "1" ]]; then
  MIGRATE_LOCAL="$(mktemp)"
  cat >"$MIGRATE_LOCAL" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd '$REMOTE'
if [[ ! -f .venv/bin/activate ]]; then
  echo "remote .venv missing; run ./run.sh once to create venv" >&2
  exit 1
fi
# shellcheck disable=SC1091
source .venv/bin/activate
# 只用 upgrade，勿用 python main.py migrate（会 autogenerate 噪声 revision）
alembic --name pro upgrade head
EOF
  run_remote rsync -av "$MIGRATE_LOCAL" "$HOST:/tmp/hipp-or-migrate.sh"
  rm -f "$MIGRATE_LOCAL"
  run_remote ssh "$HOST" "bash /tmp/hipp-or-migrate.sh && rm -f /tmp/hipp-or-migrate.sh"
fi

run_remote ssh "$HOST" "'$SUPERVISORCTL' -c '$SUPERVISORD_CONF' restart '$PROGRAM'"
run_remote ssh "$HOST" "curl -sSI http://127.0.0.1:46010/docs | head -5"

echo "deployed $PROGRAM -> $HOST:$REMOTE"
