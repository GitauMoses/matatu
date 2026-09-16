#!/usr/bin/env bash
# One command to get the phone talking to the backend, every time.
#
# The recurring failure this session was never really "the backend is
# down" - it was one of two things, both silent:
#   1. the backend genuinely wasn't running, or a stale process still held
#      the port from a previous run
#   2. `adb reverse` (which tunnels the phone's localhost:8123/8081 to this
#      laptop over USB) gets dropped by Android on its own, e.g. on a USB
#      reconnect - nothing in this repo can prevent that, only recover
#      from it fast.
#
# mobile/.env points at http://localhost:8123 specifically so the app never
# again depends on this laptop's LAN IP, which changed three times in one
# session. `adb reverse` is what makes "localhost" on the phone mean
# "this laptop" - so it's kept alive continuously here instead of being a
# one-off command someone has to remember to re-run.
set -uo pipefail
cd "$(dirname "$0")"

echo "== backend =="
if lsof -i :8123 -t >/dev/null 2>&1; then
  echo "already running on :8123"
else
  echo "starting..."
  ( cd backend && source .venv/bin/activate && nohup python3 -m app.main > /tmp/flask.log 2>&1 & disown )
  sleep 2
fi

echo "== metro =="
if lsof -i :8081 -t >/dev/null 2>&1; then
  echo "already running on :8081"
else
  echo "starting..."
  ( cd mobile && nohup npx expo start > /tmp/expo.log 2>&1 & disown )
  sleep 3
fi

echo "== adb reverse watcher =="
if pgrep -f "adb-reverse-watch" >/dev/null 2>&1; then
  echo "already watching"
else
  nohup bash -c '
    while true; do
      adb reverse tcp:8081 tcp:8081 >/dev/null 2>&1
      adb reverse tcp:8123 tcp:8123 >/dev/null 2>&1
      sleep 5
    done
  ' > /tmp/adb-reverse-watch.log 2>&1 &
  disown
  echo "started (re-asserts every 5s, survives USB reconnects)"
fi

sleep 1
echo
echo "== status =="
echo "backend:  $(lsof -i :8123 -t >/dev/null 2>&1 && echo up || echo DOWN)"
echo "metro:    $(lsof -i :8081 -t >/dev/null 2>&1 && echo up || echo DOWN)"
echo "adb devices connected: $(adb devices | grep -c 'device$')"
adb reverse --list 2>/dev/null | sed 's/^/adb reverse: /'
