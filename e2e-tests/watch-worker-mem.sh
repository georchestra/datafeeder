#!/usr/bin/env bash
# Poll the airflow-worker container's cgroup memory usage and print it live.
#
# Usage:
#   ./watch-worker-mem.sh [container] [interval_seconds]
#
# Defaults:
#   container        datafeeder-airflow-worker-1
#   interval_seconds 0.5
#
# Start this before triggering an Airflow DAG run, let it run for the
# duration of the run, then Ctrl+C. The printed peak_mb (from the cgroup v2
# memory.peak file, since-boot high-water mark for that cgroup) gives the
# true peak without needing high-frequency polling.
#
# If memory.peak isn't available in the container (older kernel/runtime),
# falls back to tracking the max of memory.current seen across polls.

set -euo pipefail

CONTAINER="${1:-datafeeder-airflow-worker-1}"
INTERVAL="${2:-2}"

if ! docker inspect -f '{{.State.Running}}' "$CONTAINER" >/dev/null 2>&1; then
  echo "Container '$CONTAINER' is not running." >&2
  exit 1
fi

echo "Watching '$CONTAINER' memory every ${INTERVAL}s. Ctrl+C to stop."
printf "%-10s %12s %12s\n" "time" "current_mb" "peak_mb"

max_current_mb=0

while docker inspect -f '{{.State.Running}}' "$CONTAINER" >/dev/null 2>&1; do
  read -r cur peak <<< "$(docker exec "$CONTAINER" sh -c \
    'cat /sys/fs/cgroup/memory.current /sys/fs/cgroup/memory.peak 2>/dev/null | tr "\n" " "')"

  if [ -n "${cur:-}" ]; then
    current_mb=$((cur / 1048576))
    if [ -n "${peak:-}" ] && [ "$peak" != "max" ]; then
      peak_mb=$((peak / 1048576))
    else
      [ "$current_mb" -gt "$max_current_mb" ] && max_current_mb=$current_mb
      peak_mb=$max_current_mb
    fi
    printf "%-10s %12s %12s\n" "$(date +%H:%M:%S)" "$current_mb" "$peak_mb"
  fi

  sleep "$INTERVAL"
done

echo "Container stopped."
