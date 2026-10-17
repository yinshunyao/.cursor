#!/usr/bin/env bash
# Permanently disable systemd UAPI OSC 3008 shell spam on Ubuntu.
#
# Why not just `mv … .disabled`?
#   /etc/profile.d/80-systemd-osc-context.sh is owned by the systemd package
#   (often a symlink into /usr/lib/systemd/profile.d/). Apt upgrade / package
#   reconfigure recreates it after reboot — the old rename comes back.
#
# Why not only `SYSTEMD_OSC_CONTEXT=0`?
#   Newer Ubuntu systemd profile scripts may ignore that variable (only check
#   bash + TERM=dumb). Divert + stub is the durable fix.
#
# Local (on the Ubuntu host):
#   sudo bash disable-systemd-osc-context.sh
#
# Remote (from Mac / another host; password via env, never hardcode):
#   OSC_SSH=user@host OSC_SSH_PORT=22 OSC_SSH_PASS='…' bash disable-systemd-osc-context.sh
set -euo pipefail

apply_on_host() {
  if [[ "$(id -u)" -ne 0 ]]; then
    echo "need root (sudo)" >&2
    exit 1
  fi

  TARGET=/etc/profile.d/80-systemd-osc-context.sh
  DIVERT=/etc/profile.d/80-systemd-osc-context.sh.distrib

  # Optional early export (harmless; some older scripts honor it)
  printf '%s\n' 'export SYSTEMD_OSC_CONTEXT=0' > /etc/profile.d/00-disable-systemd-osc.sh
  chmod 644 /etc/profile.d/00-disable-systemd-osc.sh

  rm -f "${TARGET}.disabled"

  # Take the path away from the package so upgrades install into .distrib instead
  if ! dpkg-divert --list "$TARGET" 2>/dev/null | grep -q .; then
    rm -f "$TARGET"
    dpkg-divert --local --divert "$DIVERT" --rename --add "$TARGET" \
      || dpkg-divert --local --add "$TARGET"
  fi

  # Real file that profile.d sources — no OSC, not a symlink to systemd
  printf '%s\n' \
    '# OSC 3008 disabled permanently (dpkg-divert). Do not replace with systemd symlink.' \
    > "$TARGET"
  chmod 644 "$TARGET"

  echo "=== divert ==="
  dpkg-divert --list '*osc-context*' || true
  echo "=== /etc/profile.d stubs ==="
  ls -la /etc/profile.d/00-disable-systemd-osc.sh "$TARGET"
  cat "$TARGET"
  echo "=== login check ==="
  if bash -lc 'true' 2>&1 | grep -q '3008'; then
    echo "RESULT=STILL_HAS_3008" >&2
    exit 2
  fi
  echo "RESULT=CLEAN"
}

run_remote() {
  local host="${OSC_SSH:?set OSC_SSH=user@host}"
  local port="${OSC_SSH_PORT:-22}"
  local pass="${OSC_SSH_PASS:?set OSC_SSH_PASS}"
  local self
  self="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
  local remote_tmp="/tmp/disable-systemd-osc-context.$$.sh"

  if ! command -v expect >/dev/null 2>&1; then
    echo "remote mode needs expect" >&2
    exit 1
  fi

  export OSC_EXPECT_PASS="$pass"
  expect <<EOF
set timeout 90
set pass \$env(OSC_EXPECT_PASS)
# Escape single quotes for remote sh: ' -> '\'' 
set passq [string map {' '\\''} \$pass]
spawn scp -o StrictHostKeyChecking=accept-new -P $port $self ${host}:${remote_tmp}
expect {
  -re "(?i)yes/no" { send "yes\r"; exp_continue }
  -re "(?i)password:" { send "\$pass\r"; exp_continue }
  eof
}
catch wait result
if {[lindex \$result 3] != 0} { exit [lindex \$result 3] }

set remotecmd "printf '%s\\n' '\$passq' | sudo -S bash ${remote_tmp}; rm -f ${remote_tmp}"
spawn ssh -o StrictHostKeyChecking=accept-new -p $port $host \$remotecmd
expect {
  -re "(?i)yes/no" { send "yes\r"; exp_continue }
  -re "(?i)password:" { send "\$pass\r"; exp_continue }
  eof
}
catch wait result
exit [lindex \$result 3]
EOF
  unset OSC_EXPECT_PASS
}

if [[ -n "${OSC_SSH:-}" ]]; then
  run_remote
else
  apply_on_host
fi
