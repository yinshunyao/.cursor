#!/usr/bin/env bash
# Sync Dify hipp.site nginx locations include and reload nginx.
#
# Required env:
#   HIPP_DEPLOY_HOST   e.g. root@<host>
# Optional:
#   HIPP_DEPLOY_SSH_PASS
#   HIPP_DEPLOY_LOCAL_INC   local dify-locations.inc (default: study/.../dify/dify-locations.inc)
#   HIPP_DEPLOY_REMOTE_INC  remote path (default: /etc/nginx/conf.d/dify-locations.inc)

set -euo pipefail

HOST="${HIPP_DEPLOY_HOST:?set HIPP_DEPLOY_HOST}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
LOCAL_INC="${HIPP_DEPLOY_LOCAL_INC:-$REPO_ROOT/study/配置信息/生产-yin/dify/dify-locations.inc}"
REMOTE_INC="${HIPP_DEPLOY_REMOTE_INC:-/etc/nginx/conf.d/dify-locations.inc}"

if [[ ! -f "$LOCAL_INC" ]]; then
  echo "local include missing: $LOCAL_INC" >&2
  exit 1
fi

if ! grep -q 'location /vs/' "$LOCAL_INC"; then
  echo "local include missing location /vs/: $LOCAL_INC" >&2
  exit 1
fi

run_remote() {
  if [[ -n "${HIPP_DEPLOY_SSH_PASS:-}" ]]; then
    if ! command -v expect >/dev/null 2>&1; then
      echo "HIPP_DEPLOY_SSH_PASS set but expect not found" >&2
      exit 1
    fi
    expect <<EOF
set timeout 120
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

run_remote scp "$LOCAL_INC" "$HOST:$REMOTE_INC"
run_remote ssh "$HOST" "nginx -t && systemctl reload nginx && grep -n 'location /vs/' '$REMOTE_INC' | head -3"

echo "deployed $LOCAL_INC -> $HOST:$REMOTE_INC ; nginx reloaded"
