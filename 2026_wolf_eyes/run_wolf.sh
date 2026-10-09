#!/usr/bin/env bash
# Starts the wolf eyes on the Pi and keeps them running.
#  - waits for both screens, restarts the eyes if they ever crash
#  - pressing q / Esc on a keyboard quits for good (until next boot)
# Extra options for wolf_eyes.py go in WOLF_ARGS below (e.g. "--swap").
WOLF_ARGS="--mode dual"

cd "$(dirname "$0")" || exit 1
mkdir -p logs
LOG=logs/wolf.log
[ -f "$LOG" ] && [ "$(stat -c%s "$LOG" 2>/dev/null || echo 0)" -gt 2000000 ] && mv "$LOG" "$LOG.old"

if [ "${XDG_SESSION_TYPE:-}" = "x11" ]; then
  xset s off -dpms s noblank 2>/dev/null      # no screen blanking
  command -v unclutter >/dev/null && unclutter -idle 0.5 -root &  # hide the cursor
fi

sleep 3  # let the desktop and both screens come up
while true; do
  echo "=== $(date) starting wolf eyes" >> "$LOG"
  python3 wolf_eyes.py $WOLF_ARGS >> "$LOG" 2>&1
  code=$?
  if [ $code -eq 0 ]; then
    echo "=== $(date) quit from keyboard" >> "$LOG"
    exit 0
  fi
  echo "=== $(date) stopped (code $code), restarting in 5s" >> "$LOG"
  sleep 5
done
