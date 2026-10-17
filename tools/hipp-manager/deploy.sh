#!/usr/bin/env bash
# Sync hipp-manager to a remote host, install venv if missing, reload nginx fragment + supervisor.
#
# Required env:
#   HIPP_DEPLOY_HOST     ssh target, e.g. root@<host>
#   HIPP_DEPLOY_REMOTE   remote code root, e.g. /data/hipp-manager
# Optional env:
#   HIPP_DEPLOY_LOCAL    local hipp-manager root (default: <repo>/hipp-manager)
#   HIPP_DEPLOY_ENV      local .env to copy as remote .env (omit to skip)
#   HIPP_DEPLOY_SSH_PASS ssh password when key auth unavailable (expect; prefer keys)
#   HIPP_DEPLOY_BUILD=1  npm run build in web/ with VITE_BASE=/mgr/
#   HIPP_DEPLOY_NGINX_INC  local manager-locations.inc to install under /etc/nginx/conf.d/
#   HIPP_DEPLOY_SUPERVISOR_PROG  local Smanager file to copy next to supervisord.conf
#   HIPP_DEPLOY_SUPERVISORCTL / HIPP_DEPLOY_SUPERVISORD_CONF / HIPP_DEPLOY_PROGRAM

set -euo pipefail

HOST="${HIPP_DEPLOY_HOST:?set HIPP_DEPLOY_HOST}"
REMOTE="${HIPP_DEPLOY_REMOTE:?set HIPP_DEPLOY_REMOTE}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
LOCAL="${HIPP_DEPLOY_LOCAL:-$REPO_ROOT/hipp-manager}"
SUPERVISORCTL="${HIPP_DEPLOY_SUPERVISORCTL:-/home/miniconda38/bin/supervisorctl}"
SUPERVISORD_CONF="${HIPP_DEPLOY_SUPERVISORD_CONF:-/home/miniconda38/etc/supervisord.conf}"
PROGRAM="${HIPP_DEPLOY_PROGRAM:-hipp-manager}"

if [[ ! -d "$LOCAL" ]]; then
  echo "local tree missing: $LOCAL" >&2
  exit 1
fi

if [[ "${HIPP_DEPLOY_BUILD:-}" == "1" ]]; then
  (cd "$LOCAL/web" && VITE_BASE=/mgr/ npm run build)
fi

if [[ ! -f "$LOCAL/web/dist/index.html" ]]; then
  echo "web/dist missing; run VITE_BASE=/mgr/ npm run build in web/ (or HIPP_DEPLOY_BUILD=1)" >&2
  exit 1
fi
if ! grep -q '/mgr/assets/' "$LOCAL/web/dist/index.html"; then
  echo "web/dist does not reference /mgr/assets/; rebuild with VITE_BASE=/mgr/" >&2
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

RSYNC_ARGS=(
  rsync -av --delete
  --exclude '.git/'
  --exclude '.env'
  --exclude '.venv/'
  --exclude 'data/'
  --exclude 'certs/'
  --exclude '__pycache__/'
  --exclude '*.pyc'
  --exclude 'web/node_modules/'
  --exclude 'web/src/'
  "$LOCAL/"
  "$HOST:$REMOTE/"
)
run_remote "${RSYNC_ARGS[@]}"

if [[ -n "${HIPP_DEPLOY_ENV:-}" ]]; then
  if [[ ! -f "$HIPP_DEPLOY_ENV" ]]; then
    echo "HIPP_DEPLOY_ENV missing: $HIPP_DEPLOY_ENV" >&2
    exit 1
  fi
  run_remote rsync -av "$HIPP_DEPLOY_ENV" "$HOST:$REMOTE/.env"
fi

if [[ -n "${HIPP_DEPLOY_NGINX_INC:-}" ]]; then
  run_remote rsync -av "$HIPP_DEPLOY_NGINX_INC" "$HOST:/etc/nginx/conf.d/manager-locations.inc"
fi

if [[ -n "${HIPP_DEPLOY_SUPERVISOR_PROG:-}" ]]; then
  SUPER_DIR="$(dirname "$SUPERVISORD_CONF")"
  run_remote rsync -av "$HIPP_DEPLOY_SUPERVISOR_PROG" "$HOST:$SUPER_DIR/Smanager"
fi

# 远程收尾脚本先 rsync 再执行，避免 expect 把 [[ / [! 当 TCL 解析
SETUP_LOCAL="$(mktemp)"
trap 'rm -f "$SETUP_LOCAL"' EXIT
cat >"$SETUP_LOCAL" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd '$REMOTE'
if test ! -x .venv/bin/python; then
  python3 -m venv .venv
  .venv/bin/pip install -U pip
fi
.venv/bin/pip install -r requirements.txt
mkdir -p data/media
if test -f /etc/nginx/conf.d/manager-locations.inc; then
  for f in /etc/nginx/conf.d/server.conf /etc/nginx/conf.d/hipp.site.conf /etc/nginx/sites-enabled/default; do
    if test -f "\$f" && ! grep -q 'manager-locations.inc' "\$f"; then
      if grep -q 'cert-locations.inc' "\$f"; then
        sed -i '/cert-locations.inc/a\\        include /etc/nginx/conf.d/manager-locations.inc;' "\$f"
      else
        echo '        include /etc/nginx/conf.d/manager-locations.inc;' >> "\$f"
      fi
      break
    fi
  done
  nginx -t
  systemctl reload nginx || nginx -s reload || true
fi
'$SUPERVISORCTL' -c '$SUPERVISORD_CONF' update
'$SUPERVISORCTL' -c '$SUPERVISORD_CONF' restart '$PROGRAM' || '$SUPERVISORCTL' -c '$SUPERVISORD_CONF' start '$PROGRAM'
sleep 1
curl -sS http://127.0.0.1:9100/health || true
EOF
run_remote rsync -av "$SETUP_LOCAL" "$HOST:$REMOTE/.deploy-setup.sh"
run_remote ssh "$HOST" "bash '$REMOTE/.deploy-setup.sh' && rm -f '$REMOTE/.deploy-setup.sh'"

echo "deployed $PROGRAM -> $HOST:$REMOTE"
