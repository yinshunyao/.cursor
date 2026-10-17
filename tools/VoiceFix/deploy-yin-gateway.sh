#!/usr/bin/env bash
# Deploy VoiceFix gateway (API + Admin + Web SPA) to yin-style host. No Worker.
#
# Required env:
#   HIPP_DEPLOY_HOST     ssh target, e.g. root@<host>
# Optional env:
#   HIPP_DEPLOY_REMOTE_SERVER  remote server root (default /data/vf/server)
#   HIPP_DEPLOY_REMOTE_WEB     remote web root (default /data/vf/web)
#   HIPP_DEPLOY_LOCAL          local VoiceFix root (default <repo>/VoiceFix)
#   HIPP_DEPLOY_ENV            local .env to install only if remote .env missing
#   HIPP_DEPLOY_SSH_PASS       ssh password when key auth unavailable (expect)
#   HIPP_DEPLOY_BUILD=1        build web with VITE_BASE=/vf/ VITE_API_BASE=/vf/api/v1
#   HIPP_DEPLOY_NGINX_INC      local vf-locations.inc
#   HIPP_DEPLOY_SUPERVISOR_PROG  local Svf-api
#   HIPP_DEPLOY_SEED=1         run seed_initial_data (first install only)
#   HIPP_DEPLOY_SUPERVISORCTL / HIPP_DEPLOY_SUPERVISORD_CONF

set -euo pipefail

HOST="${HIPP_DEPLOY_HOST:?set HIPP_DEPLOY_HOST}"
REMOTE_SERVER="${HIPP_DEPLOY_REMOTE_SERVER:-/data/vf/server}"
REMOTE_WEB="${HIPP_DEPLOY_REMOTE_WEB:-/data/vf/web}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
LOCAL="${HIPP_DEPLOY_LOCAL:-$REPO_ROOT/VoiceFix}"
SUPERVISORCTL="${HIPP_DEPLOY_SUPERVISORCTL:-/home/miniconda38/bin/supervisorctl}"
SUPERVISORD_CONF="${HIPP_DEPLOY_SUPERVISORD_CONF:-/home/miniconda38/etc/supervisord.conf}"

if [[ ! -d "$LOCAL/server" ]]; then
  echo "local server missing: $LOCAL/server" >&2
  exit 1
fi

if [[ "${HIPP_DEPLOY_BUILD:-}" == "1" ]]; then
  (
    cd "$LOCAL/web"
    rm -rf dist
    VITE_BASE=/vf/ VITE_API_BASE=/vf/api/v1 npm run build
  )
fi

if [[ ! -f "$LOCAL/web/dist/index.html" ]]; then
  echo "web/dist missing; build with VITE_BASE=/vf/ or HIPP_DEPLOY_BUILD=1" >&2
  exit 1
fi
if ! grep -q '/vf/assets/' "$LOCAL/web/dist/index.html"; then
  echo "web/dist does not reference /vf/assets/; rebuild with VITE_BASE=/vf/" >&2
  exit 1
fi

run_remote() {
  if [[ -n "${HIPP_DEPLOY_SSH_PASS:-}" ]]; then
    if ! command -v expect >/dev/null 2>&1; then
      echo "HIPP_DEPLOY_SSH_PASS set but expect not found" >&2
      exit 1
    fi
    expect <<EOF
set timeout 1200
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

run_remote ssh "$HOST" "mkdir -p '$REMOTE_SERVER' '$REMOTE_WEB' /data/vf/tasks /data/vf/certs /data/vf/server/media /data/vf/server/staticfiles"

run_remote rsync -av --delete \
  --exclude '.venv/' \
  --exclude '.env' \
  --exclude 'media/' \
  --exclude 'staticfiles/' \
  --exclude 'logs/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '.pytest_cache/' \
  "$LOCAL/server/" \
  "$HOST:$REMOTE_SERVER/"

run_remote rsync -av --delete \
  "$LOCAL/web/dist/" \
  "$HOST:$REMOTE_WEB/"

if [[ -n "${HIPP_DEPLOY_ENV:-}" ]]; then
  if [[ ! -f "$HIPP_DEPLOY_ENV" ]]; then
    echo "HIPP_DEPLOY_ENV missing: $HIPP_DEPLOY_ENV" >&2
    exit 1
  fi
  # Only install when remote has no .env (never overwrite production secrets).
  ENV_TMP="$(mktemp)"
  trap 'rm -f "$ENV_TMP" "$SETUP_LOCAL"' EXIT
  # shellcheck disable=SC2016
  if ! run_remote ssh "$HOST" "test -f '$REMOTE_SERVER/.env'"; then
    SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
    sed "s|^DJANGO_SECRET_KEY=.*|DJANGO_SECRET_KEY=$SECRET|" "$HIPP_DEPLOY_ENV" >"$ENV_TMP"
    run_remote rsync -av "$ENV_TMP" "$HOST:$REMOTE_SERVER/.env"
    echo "installed new .env with generated DJANGO_SECRET_KEY"
  else
    echo "remote .env exists; skip HIPP_DEPLOY_ENV"
  fi
fi

if [[ -n "${HIPP_DEPLOY_NGINX_INC:-}" ]]; then
  run_remote rsync -av "$HIPP_DEPLOY_NGINX_INC" "$HOST:/etc/nginx/conf.d/vf-locations.inc"
fi

if [[ -n "${HIPP_DEPLOY_SUPERVISOR_PROG:-}" ]]; then
  SUPER_DIR="$(dirname "$SUPERVISORD_CONF")"
  run_remote rsync -av "$HIPP_DEPLOY_SUPERVISOR_PROG" "$HOST:$SUPER_DIR/Svf-api"
fi

SETUP_LOCAL="$(mktemp)"
SEED_FLAG="${HIPP_DEPLOY_SEED:-0}"
cat >"$SETUP_LOCAL" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd '$REMOTE_SERVER'
if test ! -x .venv/bin/python; then
  python3 -m venv .venv
  .venv/bin/python -m pip install -U pip -i https://mirrors.aliyun.com/pypi/simple/
fi
.venv/bin/python -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# Ensure DB exists from .env (idempotent)
set -a
# shellcheck disable=SC1091
. ./.env
set +a
mysql -h"\${DB_HOST}" -P"\${DB_PORT}" -u"\${DB_USER}" -p"\${DB_PASSWORD}" \
  -e "CREATE DATABASE IF NOT EXISTS \${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

mkdir -p media staticfiles /data/vf/tasks /home/miniconda38/log
.venv/bin/python manage.py migrate --noinput
if test '$SEED_FLAG' = '1'; then
  .venv/bin/python manage.py seed_initial_data || true
fi
.venv/bin/python manage.py collectstatic --noinput

chmod -R g+rX,o+rX /data/vf/web /data/vf/server/staticfiles /data/vf/server/media || true

# 只写入 server 块内的站点 conf；禁止改 nginx.conf（http 级 include 会让 location 报错）
if test -f /etc/nginx/conf.d/vf-locations.inc; then
  INCLUDED=0
  for f in /etc/nginx/conf.d/server.conf /etc/nginx/sites-enabled/default; do
    if test -f "\$f" && grep -q 'vf-locations.inc' "\$f"; then
      INCLUDED=1
      break
    fi
  done
  if test "\$INCLUDED" = '0'; then
    for f in /etc/nginx/conf.d/server.conf /etc/nginx/sites-enabled/default; do
      if test -f "\$f"; then
        if grep -q 'manager-locations.inc' "\$f"; then
          sed -i '/manager-locations.inc/a\\        include /etc/nginx/conf.d/vf-locations.inc;' "\$f"
        elif grep -q 'cert-locations.inc' "\$f"; then
          sed -i '/cert-locations.inc/a\\        include /etc/nginx/conf.d/vf-locations.inc;' "\$f"
        else
          echo '        include /etc/nginx/conf.d/vf-locations.inc;' >> "\$f"
        fi
        break
      fi
    done
  fi
  nginx -t
  systemctl reload nginx || nginx -s reload || true
fi

'$SUPERVISORCTL' -c '$SUPERVISORD_CONF' update
'$SUPERVISORCTL' -c '$SUPERVISORD_CONF' restart vf-api: || '$SUPERVISORCTL' -c '$SUPERVISORD_CONF' start vf-api:
sleep 2
'$SUPERVISORCTL' -c '$SUPERVISORD_CONF' status | grep -i vf || true
curl -sS http://127.0.0.1:38010/vf/api/v1/health/ || true
echo
curl -sSI http://127.0.0.1/vf/ | head -5 || true
curl -sSI http://127.0.0.1/vf/api/v1/health/ | head -5 || true
command -v ffmpeg >/dev/null && ffmpeg -version | head -1 || echo 'WARN: ffmpeg missing'
command -v ffprobe >/dev/null && ffprobe -version | head -1 || echo 'WARN: ffprobe missing'
EOF

run_remote rsync -av "$SETUP_LOCAL" "$HOST:$REMOTE_SERVER/.deploy-setup.sh"
run_remote ssh "$HOST" "bash '$REMOTE_SERVER/.deploy-setup.sh' && rm -f '$REMOTE_SERVER/.deploy-setup.sh'"

echo "deployed VoiceFix gateway -> $HOST ($REMOTE_SERVER + $REMOTE_WEB); no worker"
